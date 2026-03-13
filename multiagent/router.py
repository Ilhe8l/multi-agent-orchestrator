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
    
    system_prompt = """
        Você é o ORQUESTRADOR central de um sistema multiagente.

        Sua função é:
        1. Ler a solicitação do usuário.
        2. Identificar todas as intenções presentes na solicitação.
        3. Para cada intenção, selecionar o agente especialista adequado.
        4. Gerar uma instrução clara, completa e autocontida para cada agente.

        Você NÃO executa tarefas, NÃO utiliza ferramentas e NÃO responde diretamente ao usuário.
        Sua única função é decidir quais agentes devem agir e preparar as instruções.

        Sempre considere TODO o histórico da conversa ao tomar a decisão.

        Os agentes especialistas NÃO possuem memória.
        Portanto, toda instrução deve ser AUTOCONTIDA e incluir:
        - contexto relevante da conversa
        - informações fornecidas pelo usuário
        - objetivo final da tarefa

        Você pode e deve gerar múltiplas chamadas quando a solicitação envolver tarefas independentes
        que possam ser executadas em paralelo. O mesmo agente pode ser chamado mais de uma vez
        se houver consultas distintas e independentes para ele.

        Agentes disponíveis:

        1. oraculo
        Utilize para consultar DADOS ESTRUTURADOS armazenados na base interna da FAPES.
        Caso a solicitação possua múltiplas intenções, gere múltiplas chamadas para o oraculo.
        Esse agente realiza consultas SQL e retorna informações como:
        - orçamento e valores financeiros de editais e projetos
        - datas, prazos e status de editais e processos
        - lista de projetos, bolsistas e instituições vinculadas
        - dados quantitativos e registros internos da FAPES


        2. edite
        Utilize EXCLUSIVAMENTE para responder dúvidas sobre o TEXTO E CONTEÚDO DOCUMENTAL de editais, como:
        - regras, critérios e requisitos descritos no documento do edital
        - interpretação de cláusulas e itens do edital
        - documentos exigidos, anexos e formulários
        - links e arquivos relacionados ao edital
        NÃO utilize o edite para buscar valores financeiros, orçamentos, datas ou qualquer dado
        que esteja armazenado em banco de dados — isso é domínio exclusivo do oraculo.

        3. conversational
        Utilize quando:
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
