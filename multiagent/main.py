import os
import asyncio
import warnings
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langchain_core.messages import HumanMessage
from fastapi.middleware.cors import CORSMiddleware
from graph import builder

warnings.filterwarnings("ignore", category=UserWarning)
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
TTL_CONFIG = {"default_ttl": 5, "refresh_on_read": False}

_checkpointer = None
_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _checkpointer, _graph
    async with AsyncRedisSaver.from_conn_string(REDIS_URL, ttl=TTL_CONFIG) as _checkpointer:
        await _checkpointer.asetup()
        _graph = builder.compile(checkpointer=_checkpointer)
        yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_input: str
    thread_id: str = "default_session"


async def process_message(user_input: str, config: dict):
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
        "text": final_state.get("text_response"),
        "sql": final_state.get("sql_used"),
        "data": final_state.get("graph"),
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    result = await process_message(request.user_input, config)
    if result["type"] == "error":
        raise HTTPException(status_code=500, detail=result["text"])
    return result


@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
                