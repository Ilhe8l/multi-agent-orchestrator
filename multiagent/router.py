import os
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from state import MultiAgentState
from models import RouterDecision

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("LLM_API_KEY"),
    temperature=0.0
)

mcp_tools = []

def orchestrator_node(state: MultiAgentState):
    global mcp_tools
    
    tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in mcp_tools]) if mcp_tools else "Nenhuma ferramenta externa disponível."
    
    system_prompt = f"""
        Você é o ORQUESTRADOR central de um sistema multiagente.

        Sua função é:
        1. Ler a solicitação do usuário.
        2. Identificar todas as intenções presentes na solicitação.
        3. Para cada intenção, selecionar a ferramenta especialista adequada.
        4. Gerar uma instrução clara, completa e autocontida para cada ferramenta.

        Você NÃO executa tarefas, NÃO utiliza ferramentas nativamente e NÃO responde diretamente ao usuário.
        Sua única função é decidir quais ferramentas devem agir e preparar as instruções.

        Sempre considere TODO o histórico da conversa ao tomar a decisão.

        Os agentes especialistas NÃO possuem memória.
        Portanto, toda instrução deve ser AUTOCONTIDA e incluir:
        - contexto relevante da conversa
        - informações fornecidas pelo usuário
        - objetivo final da tarefa
    
        Você pode e deve gerar múltiplas chamadas quando a solicitação envolver tarefas independentes
        que possam ser executadas em paralelo. O mesmo agente pode ser chamado mais de uma vez
        se houver consultas distintas e independentes para ele.

        Ferramentas externas disponíveis via MCP:
        {tools_desc}
        
        Caso a solicitação possua múltiplas intenções, gere múltiplas chamadas, podendo chamar a mesma ferramenta mais de uma vez ou diferentes ferramentas em paralelo.

        Utilize o conversational quando:
        - a solicitação não estiver relacionada aos domínios do oraculo ou edite
        - a tarefa envolver apenas comunicação natural
        Não inclua o conversational junto com oraculo ou edite — ele será chamado automaticamente
        após os outros agentes para consolidar e apresentar os resultados ao usuário.
    """
    
    structured_llm = llm.with_structured_output(RouterDecision, method="function_calling")
    
    history = state.get("messages", [])
    messages = [SystemMessage(content=system_prompt)] + history
    
    decision: RouterDecision = structured_llm.invoke(messages)
    
# retorna todas as chamadas do agente roteador
    return {
        "calls": decision.calls
    }

