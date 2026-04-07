from pydantic import BaseModel, Field
from typing import List

# classe auxiliar para representar a chamada a um agente específico, incluindo a intenção e as instruções de delegação.
class AgentCall(BaseModel):
    intent: str = Field(
        description="Nome da ferramenta (tool) que deve ser chamada, ou 'conversational' caso NENHUMA ferramenta seja aplicável."
    )
    delegation_instruction: str = Field(
        description="Instrução imperativa e detalhada para o agente especialista."
    )

# classe principal que representa a decisão do roteador, contendo uma lista de chamadas a agentes. Isso permite que o roteador delegue tarefas a múltiplos agentes ou ao mesmo agente várias vezes, se necessário.
class RouterDecision(BaseModel):
    calls: List[AgentCall] = Field(
        description="Lista de chamadas a ferramentas. Pode conter múltiplas chamadas à mesma ferramenta com argumentos diferentes ou chamadas a ferramentas variadas."
    )

