from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from state import MultiAgentState

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    api_key=os.getenv("LLM_API_KEY"),
    temperature=0.0
)

def conversational_node(state: MultiAgentState):
    # Nó responsável por tratar mensagens classificadas como 'conversational'.
    # Não utiliza ferramentas.
    # Retorna resposta final diretamente ao usuário.


    user_input = state.get("user_input", "")
    instruction = state.get("delegation_instruction", "")

    system_prompt = SystemMessage(
        content="Você é uma assistente de IA prestativa e amigável. "
                "Responda de forma clara, objetiva e útil."
    )

    response = llm.invoke([
        system_prompt,
        HumanMessage(content=user_input)
    ])

    print(f"[Conversational Agent] Instrução recebida: {instruction}")
    print(f"[Conversational Agent] Resposta gerada: {response.content}")

    return {
        "final_response": response.content
    }