from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from state import MultiAgentState
from tools.text_tools import uppercase_text

def text_agent_node(state: MultiAgentState):
    instruction = state.get("delegation_instruction", "")
    
    system_prompt = SystemMessage(
        content=(
            """Você é especialista em formatação de textos.
                Use a ferramenta disponível para colocar a requisição do usuário em letras maiúsculas, 
                e retorne apenas o texto formatado."""
        )
    )
    
    load_dotenv()
    llm = ChatOpenAI(model="gpt-4.1-mini", api_key=os.getenv("LLM_API_KEY"), temperature=0.0)
    llm_with_tools = llm.bind_tools([uppercase_text])
    
    state_messages = state.get("messages", [])
    invoke_messages = [system_prompt, HumanMessage(content=instruction)] + state_messages
    response = llm_with_tools.invoke(invoke_messages)
    
    if response.content:
        print(f"[agente estruturador] recebeu a instrução: {instruction}")
        print(f"[agente estruturador] resposta: {response.content}")
        
    return {"messages": [response]}
