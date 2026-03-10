from pydantic import BaseModel, Field
from typing import Literal, List

# classe auxiliar para representar a chamada a um agente específico, incluindo a intenção e as instruções de delegação.
class AgentCall(BaseModel):
    intent: Literal["oraculo", "edite", "conversational"]
    delegation_instruction: str = Field(
        description="Instrução imperativa e detalhada para o agente especialista."
    )

# classe principal que representa a decisão do roteador, contendo uma lista de chamadas a agentes. Isso permite que o roteador delegue tarefas a múltiplos agentes ou ao mesmo agente várias vezes, se necessário.
class RouterDecision(BaseModel):
    calls: List[AgentCall] = Field(
        description="Lista de chamadas a agentes. Pode conter múltiplos agentes ou o mesmo agente mais de uma vez."
    )

