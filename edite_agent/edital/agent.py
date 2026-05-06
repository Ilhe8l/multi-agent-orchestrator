#from graph import StateGraph, State
from stateTypes import State
from langchain_core.messages import trim_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    BaseMessage,
    SystemMessage,
    trim_messages,
    ToolMessage
)
import os
from dotenv import load_dotenv
from edital.tools.edital_tool import EditalTool
from edital.tools.writer_tool import WriterAgent
from config import MODEL_CONFIG, LLM_API_KEY, LLM_MODEL, MAX_CHAT_HISTORY_TOKENS
from edital.prompt_builder import build_prompt
import logging

load_dotenv()

# Inicializa o agente diretamente com DeepSeek-R1 local
agent = ChatOpenAI(
    model=LLM_MODEL,
    api_key=LLM_API_KEY,
    #service_tier="priority",
    temperature=0.3,  # exemplo de outros parâmetros
)

# Adiciona as tools
agent_with_tools = agent.bind_tools([EditalTool])

async def CallEditalAgent(state: State) -> State:
    
    # adiciona o prompt inicial ao estado, se ainda não estiver presente
    if not isinstance(state["messages"][0], SystemMessage):
        system_prompt = await build_prompt()
        state["messages"].insert(0, SystemMessage(content=system_prompt))
        
    messages = state["messages"]
    
    messages = trim_messages(
        messages,
        max_tokens=MAX_CHAT_HISTORY_TOKENS,
        allow_partial=False,
        include_system=True,
        strategy="last",
        token_counter=len,
        start_on="human"
    )
        
    response = await agent_with_tools.ainvoke(messages)
    #logging.info(f"Resposta gerada pelo Agente: {response.content}")
    
    state["messages"].append(response)
    state["response"] = response.content # salva a resposta para acesso fácil
    
    return state
