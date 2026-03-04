import os
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from state import MultiAgentState
from models import RouterDecision

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1",
    api_key=os.getenv("LLM_API_KEY"),
    temperature=0.0
)

def orchestrator_node(state: MultiAgentState):
    user_input = state.get("user_input", "")
    
    system_prompt = """
    Você é o orquestrador central do sistema de agentes.
    Sua responsabilidade é:

    1. Ler e interpretar cuidadosamente a requisição do usuário.
    2. Identificar a intenção principal da solicitação.
    3. Selecionar o agente especialista mais adequado.
    4. Gerar uma instrução objetiva, clara e completa para esse agente.

    Você NÃO executa tarefas diretamente, NÃO utiliza ferramentas e NÃO resolve o problema final. 
    Sua função é exclusivamente gerenciar o roteamento e a delegação da tarefa.

    Ao gerar a instrução para o agente especialista:
    - Considere todo o histórico da conversa.
    - Extraia e inclua todas as informações relevantes já fornecidas pelo usuário.
    - Reescreva o contexto de forma clara e estruturada.
    - Forneça todos os dados necessários para que o agente consiga executar a tarefa sem depender de memória anterior.

    Importante:
    Os agentes especialistas NÃO possuem memória. 
    Apenas o agente conversacional tem acesso ao histórico, ao mesmo que você.
    Toda informação vital para a execução da tarefa deve ser incluída na instrução que você gerar.
    Portanto, toda instrução deve ser autocontida, contendo contexto completo, dados relevantes e objetivo final claramente definido.


    Existem 2 especialistas disponíveis:
    3. conversational: especialista em processamento e formatação de texto, use quando a tarefa envolver manipulação de linguagem natural, formatação de respostas ou análise de texto.
    4. oráculo: utilize em caso de perguntas relacionadas à Fapes, informações sobre editais, processos, chamadas públicas ou qualquer conteúdo institucional relacionado à Fapes.

    Sua resposta final deve conter apenas:

    - Intenção selecionada: <nome_do_agente>
    - Instrução para o agente: <instrução clara, completa e autocontida>

    """
    
    structured_llm = llm.with_structured_output(RouterDecision, method="function_calling")
    
    history = state.get("messages", [])
    
    messages = [SystemMessage(content=system_prompt)] + history
    
    decision: RouterDecision = structured_llm.invoke(messages)
    
    return {
        "next_agent": decision.intent,
        "delegation_instruction": decision.delegation_instruction
    }
