from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from state import MultiAgentState
from tools.math_tools import add

def math_agent_node(state: MultiAgentState):
    instruction = state.get("delegation_instruction", "")
    
    system_prompt = SystemMessage(
        content=(
            """Você é um especialista em matemática. 
                Use as ferramentas disponíveis para resolver o problema enviado
                e retorne a resposta final ao usuário de forma clara."""
        )
    )
    
    load_dotenv()
    llm = ChatOpenAI(model="gpt-4.1-mini", api_key=os.getenv("LLM_API_KEY"), temperature=0.0)
    llm_with_tools = llm.bind_tools([add])
    
    state_messages = state.get("messages", [])
    invoke_messages = [system_prompt, HumanMessage(content=instruction)] + state_messages
    response = llm_with_tools.invoke(invoke_messages)
    
    # se a llm retornou a reposta, imprime
    # isso evita prints causados pela execução das ferramentas
    if response.content:
        print(f"[agente matemático] recebeu a instrução: {instruction}")
        print(f"[agente matemático] resposta: {response.content}")
        
    return {"messages": [response]}
