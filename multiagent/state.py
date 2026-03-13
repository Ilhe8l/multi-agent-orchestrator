from typing import Optional, List, Any, Dict, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from models import AgentCall

class MultiAgentState(TypedDict):
    # o state aqui guarda a conversa toda e controla pra onde vai rotear a requisição
    messages: Annotated[List[BaseMessage], add_messages]
    # o texto que o usuario digitou 
    user_input: str
    # chamadas 
    calls: List[AgentCall]
    # resposta final
    final_response: Optional[str]
    # dados tragos da api do BI (oraculo)
    graph: Optional[Any]
    sql_used: Optional[str]
    text_response: Optional[str]
