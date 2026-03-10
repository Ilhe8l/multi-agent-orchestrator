import os
import warnings
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langchain_core.messages import HumanMessage
from graph import builder
from fastapi.middleware.cors import CORSMiddleware



warnings.filterwarnings("ignore", category=UserWarning)
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
TTL_CONFIG = {"default_ttl": 5, "refresh_on_read": False}


app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):

    async with AsyncRedisSaver.from_conn_string(REDIS_URL, ttl=TTL_CONFIG) as _checkpointer:
        await _checkpointer.asetup()

    app_state["graph"] = builder.compile(checkpointer=_checkpointer)
    app_state["checkpointer"] = _checkpointer

    print("[API] Grafo e Redis inicializados.")
    yield

    
    await _checkpointer.__aexit__(None, None, None)
    print("[API] Redis encerrado.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    graph = app_state["graph"]
    config = {"configurable": {"thread_id": request.session_id}}

    initial_state = {
        "messages": [HumanMessage(content=request.question)],
        "user_input": request.question,
        "next_agent": None,
        "delegation_instruction": None,
        "final_response": None
    }

    print(f"\n[API] Pergunta recebida (session: {request.session_id}): {request.question}")

    try:
        async for output in graph.astream(initial_state, config):
            for node_name, state_update in output.items():
                if "next_agent" in state_update:
                    print(f"-> roteando para: [{state_update['next_agent']}]")

                if "final_response" in state_update and state_update["final_response"]:
                    return {
                        "type": "success",
                        "text": state_update["final_response"]
                    }

        return {"type": "error", "text": "Nenhuma resposta final gerada."}

    except Exception as e:
        print(f"[API] Erro: {e}")
        return {"type": "error", "text": f"Erro interno: {str(e)}"}
    
if __name__ == "__main__":
    
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
