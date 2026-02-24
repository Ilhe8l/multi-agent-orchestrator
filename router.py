import os
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from state import MultiAgentState
from models import RouterDecision

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    api_key=os.getenv("LLM_API_KEY"),
    temperature=0.0
)

def orchestrator_node(state: MultiAgentState):
    user_input = state.get("user_input", "")
    
    system_prompt = """Você é um orquestrador central do sistema de agentes.
                    Sua função é ler a requisição do usuário, definir a intenção correspondente
                    e gerar uma instrução direta para o agente especialista.

                    Você não lida diretamente com ferramentas; apenas gerencia a delegação e o roteamento.

                    Existem 3 especialistas disponíveis:
                    1. math: especialista em operações matemáticas
                    2. weather: especialista em verificar previsão do tempo
                    3. text: especialista em processamento e formatação de texto
                    4. conversational: use caso não se encaixe nos agentes acima

                    Retorne a intenção selecionada e a instrução clara a ser passada."""
    
    structured_llm = llm.with_structured_output(RouterDecision, method="function_calling")
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]
    
    decision: RouterDecision = structured_llm.invoke(messages)
    
    return {
        "next_agent": decision.intent,
        "delegation_instruction": decision.delegation_instruction
    }

def conversational_node(state: MultiAgentState):
    # nó para quando o orquestrador classifica a requisição como "conversational"
    # não possuí ferramentas
    # resposta não é enviada para o orquestrador, vai direto para o usuário
    instruction = state.get("delegation_instruction", "")
    user_input = state.get("user_input", "")
    
    system_prompt = SystemMessage(
        content="Você é uma assistente de IA prestativa e amigável, responda de forma clara e objetiva."
    )
    
    response = llm.invoke([system_prompt, HumanMessage(content=user_input)])
    print(f"[agente conversacional] recebeu a instrução: {instruction}")
    print(f"[agente conversacional] resposta: {response.content}")
    
    return {"final_response": response.content}
