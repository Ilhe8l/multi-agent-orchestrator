from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from state import MultiAgentState

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1",
    api_key=os.getenv("LLM_API_KEY"),
    temperature=0.0
)

def conversational_node(state: MultiAgentState):
    # Nó responsável por tratar mensagens classificadas como 'conversational'.
    # Não utiliza ferramentas.
    # Retorna resposta final diretamente ao usuário.


    user_input = state.get("user_input", "")
    instruction = state.get("delegation_instruction", "")
    history = state.get("messages", [])

    system_prompt = SystemMessage(
        content="Você é uma assistente de IA prestativa e amigável. "
                "Responda de forma clara, objetiva e útil.\n"
                f"Siga a instrução do orquestrador: {instruction}"
    )

    messages = [system_prompt] + history # (descomente para passar o histórico)
    response = llm.invoke(messages)

    print(f"[Conversational Agent] Instrução recebida: {instruction}")
    print(f"[Conversational Agent] Resposta gerada: {response.content}")

    return {
        "messages": [response],
        "final_response": response.content
    }