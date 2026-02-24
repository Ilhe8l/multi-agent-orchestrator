from pydantic import BaseModel, Field
from typing import Literal

class RouterDecision(BaseModel):
    # estrutura de decisão do orquestrador (router)
    # ele analisa a conversa e determina o agente alvo e a instrução clara para ele

    intent: Literal["math", "weather", "text", "conversational"] = Field(
        description="Qual é o domínio da requisição do usuário"
    )
    delegation_instruction: str = Field(
        description="""Um resumo detalhado e conciso contendo a exata instrução e o contexto necessário para que
                o agente especialista execute a ferramenta dele e responda a pergunta.
                Deve ser escrito na forma imperativa (ex: 'Calcule o tempo na cidade de São Paulo' ou 'Some 15 com 27').
                Se for 'conversational', essa instrução pode ser vazia ou nula."""
    )
