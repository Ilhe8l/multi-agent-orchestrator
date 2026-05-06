
# atualmente não está em uso, porque não suportava multiplas tool_calls que o EditalAgent fazia para a EditalTool
# mas pode ser útil no futuro, talvez resolvendo o problema de múltiplas chamadas de ferramentas
# funciona bem quando o agente principal (EditalAgent) não fizer múltiplas chamadas de ferramentas

from stateTypes import State
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage
)
from stateTypes import State
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from config import MODEL_CONFIG_WRITER
from langchain_core.tools import tool
import logging
from langgraph.graph.message import add_messages

load_dotenv()
logger = logging.getLogger(__name__)

agent = init_chat_model(**MODEL_CONFIG_WRITER)

@tool
def WriterAgent(tool_results: str, user_question: str) -> str:
    """
    Ferramenta que recebe os resultados das ferramentas anteriores e a pergunta do usuário,
    e gera uma resposta final clara e estruturada.
    
    Args:
        tool_results: Informações coletadas pelas ferramentas anteriores
        user_question: A pergunta original do usuário
    Returns:
        Uma resposta bem formatada e clara
    """
    writer_agent = agent.bind_tools([])  # Sem ferramentas adicionais

    messages = [
        SystemMessage(content="""Você é um assistente especializado em editais e licitações. 
        Sua função é fornecer respostas claras, precisas e bem estruturadas com base nas informações fornecidas.
        Seja objetivo e organize a informação de forma fácil de entender.
        Formate a resposta em parágrafos curtos e utilize listas quando apropriado.
        Use apenas *para negrito* e _para itálico_ como formatação (use apenas uma asterisco, *assim* nunca mais de um asterisco).
        Sempre use emojis, mantendo uma resposta bem legivel e decorada (com moderação).
        Sugira outras perguntas que o usuário possa ter relacionadas ao tema.
        A mensagem deve ser o mais humana possível, evitando soar como um robô.
        Mencione de onde a informação foi retirada, citando o número do edital e a seção (se disponível).
        Não use links em formatação markdown (Ex: [texto](link)), apenas o texto simples.
        A mensagem é enviada pelo WhatsApp, então evite formatações que não funcionam bem nessa plataforma (Ex: tabelas, listas numeradas, etc).
        """),
        HumanMessage(content=f"""Com base nas seguintes informações:

        {tool_results}

        Responda à seguinte pergunta do usuário: {user_question}

        Forneça uma resposta clara e bem estruturada.""")
    ]

    #logger.info("WriterAgent gerando resposta final")
    response = writer_agent.invoke(messages)
    #logger.info("Resposta gerada com sucesso: %s", response.content)
    return response.content 