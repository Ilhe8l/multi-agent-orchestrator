from typing import Optional, List, Any, Dict, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class MultiAgentState(TypedDict):
    # o state aqui guarda a conversa toda e controla pra onde vai rotear a requisição
    messages: Annotated[List[BaseMessage], add_messages]
    # o texto que o usuario digitou 
    user_input: str
    # quem o orquestrador decidiu que vai pegar a tarefa
    next_agent: Optional[str]
    # instrução que o orquestrador gera para o agente especialista
    delegation_instruction: Optional[str]    
    # resposta final
    final_response: Optional[str]
