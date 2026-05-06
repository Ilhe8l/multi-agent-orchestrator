import os
import json
import time
import asyncio
import warnings
from uuid import uuid4
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langchain_core.messages import HumanMessage
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis
from graph import builder
from config import REDIS_URL, TTL_CONFIG, STREAM_GROUP, STREAM_NAME, JOB_TTL, ALLOW_ORIGINS, ALLOW_METHODS, ALLOW_HEADERS

warnings.filterwarnings("ignore", category=UserWarning)
load_dotenv()

_checkpointer = None
_graph        = None
_mcp_tools_loaded = False
_redis_client: aioredis.Redis = None

from mcp_client import get_mcp_client
import router
import graph


async def ensure_mcp_tools():
    global _mcp_tools_loaded
    if _mcp_tools_loaded:
        return
    async with get_mcp_client() as mcp_client:
        tools = await mcp_client.get_tools()
        router.mcp_tools = tools
        graph.mcp_tools  = tools
    _mcp_tools_loaded = True
    print(f"[Startup] MCP tools carregadas: {[t.name for t in router.mcp_tools]}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _checkpointer, _graph, _redis_client

    _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

    try:
        await _redis_client.xgroup_create(
            STREAM_NAME, STREAM_GROUP, id="0", mkstream=True
        )
    except Exception:
        pass

    async with AsyncRedisSaver.from_conn_string(REDIS_URL, ttl=TTL_CONFIG) as _checkpointer:
        await _checkpointer.asetup()
        _graph = builder.compile(checkpointer=_checkpointer)
        yield

    await _redis_client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_methods=ALLOW_METHODS,
    allow_headers=ALLOW_HEADERS
)


class ChatRequest(BaseModel):
    user_input: str
    thread_id: str = "default_session"


async def process_message(user_input: str, config: dict):
    await ensure_mcp_tools()

    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_input": user_input,
        "next_agent": None,
        "delegation_instruction": None,
        "final_response": None,
        "graph": None,
        "sql_used": None,
        "text_response": None,
        "calls": []
    }

    final_state = await _graph.ainvoke(initial_state, config)

    return {
        "type": "success",
        "final_response": final_state.get("final_response"),
        "text": final_state.get("text_response") or final_state.get("final_response"),
        "sql": final_state.get("sql_used"),
        "data": final_state.get("graph"),
    }


async def run_graph_job(job_id: str, user_input: str, thread_id: str, msg_id: str = None):
    stream_key   = f"stream:job:{job_id}"
    history_key  = f"chat:history:{thread_id}"
    config       = {"configurable": {"thread_id": thread_id}}

    try:
        await _redis_client.xadd(stream_key, {
            "event": "start",
            "timestamp": str(time.time())
        })

        result = await process_message(user_input, config)

        payload = {
            "status": "done",
            "type":           result.get("type"),
            "text":           result.get("text") or "Não consegui gerar uma resposta.",
            "final_response": result.get("final_response"),
            "sql":            result.get("sql"),
            "data":           result.get("data"),
        }

        await _redis_client.xadd(stream_key, {
            "event": "final",
            "payload": json.dumps(payload, default=str)
        })

        if msg_id:
            await _redis_client.xack(STREAM_NAME, STREAM_GROUP, msg_id)

        await _redis_client.rpush(history_key, json.dumps({"type": "user", "text": user_input}))
        await _redis_client.rpush(history_key, json.dumps({"type": "ai",   "text": result.get("text"), "data": result}))
        await _redis_client.expire(history_key, 86400)

    except Exception as e:
        await _redis_client.xadd(stream_key, {
            "event": "error",
            "payload": json.dumps({"status": "error", "text": str(e)})
        })


@app.post("/api/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    job_id     = str(uuid4())
    stream_key = f"stream:job:{job_id}"

    await _redis_client.xadd(stream_key, {
        "event": "pending",
        "payload": json.dumps({"status": "pending"})
    })
    await _redis_client.expire(stream_key, JOB_TTL)

    background_tasks.add_task(
        run_graph_job,
        job_id,
        request.user_input,
        request.thread_id,
    )

    return {"job_id": job_id, "status": "pending"}


@app.get("/api/result/{job_id}")
async def get_result(job_id: str):
    stream_key = f"stream:job:{job_id}"
    messages   = await _redis_client.xrevrange(stream_key, count=1)

    if not messages:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    _, data = messages[0]
    event   = data.get("event")

    if event in ("final", "error"):
        return json.loads(data["payload"])

    return {"status": "pending"}


@app.get("/api/stream/{job_id}")
async def stream_job(job_id: str):
    async def event_generator():
        last_id    = "0"
        stream_key = f"stream:job:{job_id}"

        while True:
            results = await _redis_client.xread(
                {stream_key: last_id}, block=0
            )
            for _, messages in results:
                for msg_id, data in messages:
                    last_id = msg_id
                    yield f"data: {json.dumps(data)}\n\n"

                    if data.get("event") in ("final", "error"):
                        return   # fecha o stream após evento terminal

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/history/{thread_id}")
async def get_history(thread_id: str):
    history_key = f"chat:history:{thread_id}"
    messages    = await _redis_client.lrange(history_key, 0, -1)
    return [json.loads(m) for m in messages]


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)