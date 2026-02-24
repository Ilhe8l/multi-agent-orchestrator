from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from state import MultiAgentState
from tools.weather_tools import get_weather

def weather_agent_node(state: MultiAgentState):
    instruction = state.get("delegation_instruction", "")
    
    system_prompt = SystemMessage(
        content=(
            """Você é um meteorologista. 
                Use a ferramenta disponível para consultar o clima da cidade informada, 
                e depois repasse a previsão de forma amigável ao usuário."""
        )
    )
    
    load_dotenv()
    llm = ChatOpenAI(model="gpt-4.1-mini", api_key=os.getenv("LLM_API_KEY"), temperature=0.0)
    llm_with_tools = llm.bind_tools([get_weather])
    
    state_messages = state.get("messages", [])
    invoke_messages = [system_prompt, HumanMessage(content=instruction)] + state_messages
    response = llm_with_tools.invoke(invoke_messages)
    
    if response.content:
        print(f"[agente meteorológico] recebeu a instrução: {instruction}")
        print(f"[agente meteorológico] resposta: {response.content}")
        
    return {"messages": [response]}
