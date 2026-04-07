from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from state import MultiAgentState

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-nano",
    api_key=os.getenv("LLM_API_KEY"),
    temperature=0.0
)

def conversational_node(state: MultiAgentState):
    # Nó responsável por tratar mensagens classificadas como 'conversational'.
    # Não utiliza ferramentas.
    # Retorna resposta final diretamente ao usuário.
    instruction = state.get("delegation_instruction") or ""
    history = state.get("messages", [])

    # Quando vindo do mcp_tool_node, delegation_instruction é None.
    # Nesse caso, usamos o resultado das mensagens (já no histórico) como contexto.
    if not instruction and history:
        # Pega o conteúdo da última mensagem (resultado do MCP)
        last_msg = history[-1]
        instruction = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    system_prompt = SystemMessage(
        content=(
            "Você é uma assistente de IA responsável por transformar as respostas dos agentes especialistas "
            "em uma resposta final clara para o usuário.\n\n"

            "Sua função é apenas organizar e reescrever as informações recebidas. "
            "Você NÃO deve gerar novas informações, NÃO deve inferir dados e NÃO deve complementar "
            "conteúdos que não estejam explicitamente presentes na instrução recebida.\n\n"

            "As informações podem vir de dois agentes especialistas:\n"
            "- oraculo: responsável por retornar dados obtidos por consultas na base da FAPES.\n"
            "- edite: responsável por responder dúvidas sobre o conteúdo de editais da FAPES.\n\n"

            "Ao montar a resposta final:\n"
            "1. Separe claramente as informações de acordo com o agente de origem.\n"
            "2. Utilize seções identificadas como:\n"
            "   - Informações obtidas do sistema de dados da FAPES (oraculo)\n"
            "   - Informações sobre o conteúdo de editais (edite)\n"
            "3. Apresente apenas as seções que possuírem conteúdo.\n"
            "4. Reescreva as informações de forma clara, objetiva e amigável para o usuário.\n"
            "5. Não altere o significado das informações recebidas.\n\n"

            "Caso a instrução contenha informações de apenas um agente, apresente somente a seção correspondente.\n\n"

            f"Siga a instrução do orquestrador: {instruction}"
        )
    )

    messages = [system_prompt] + history
    response = llm.invoke(messages)

    print(f"[Conversational Agent] Instrução recebida: {instruction[:120] if instruction else None}")
    print(f"[Conversational Agent] Resposta gerada: {response.content}")

    return {
        "messages": [response],
        "final_response": response.content
    }