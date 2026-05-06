from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from typing import TypedDict, List
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.graph import END
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from edital.tools.edital_tool import EditalTool
from dotenv import load_dotenv
import os
import asyncio
from edital.agent import CallEditalAgent
from stateTypes import State
from config import REDIS_URL, TTL_CONFIG
from langfuse.langchain import CallbackHandler
load_dotenv()

tools = [EditalTool]
tool_nodes = ToolNode(tools)

# Variável global para reusar o checkpointer
_checkpointer = None
_graph = None
langfuse_handler = None

def route_agent(state):
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "tools"
    return END

async def get_graph():
    global _checkpointer, _graph, langfuse_handler
    
    # Se já existe, reutiliza
    if _graph is not None:
        return _graph
    
    # Cria uma vez só
    if _checkpointer is None:
        async with AsyncRedisSaver.from_conn_string(REDIS_URL, ttl=TTL_CONFIG) as _checkpointer:
            await _checkpointer.asetup()

    # Configura o Langfuse callback handler
    #if langfuse_handler is None:
    #    langfuse_handler = CallbackHandler()
    
    builder = StateGraph(State)
    builder.add_node("agent", CallEditalAgent)
    builder.add_node("tools", tool_nodes)
    builder.set_entry_point("agent")
    builder.add_edge("tools", "agent")
    builder.add_conditional_edges("agent", route_agent)
    
    _graph = builder.compile(checkpointer=_checkpointer)#.with_config({"callbacks": [langfuse_handler]})
    return _graph

if __name__ == "__main__":
    asyncio.run(get_graph())