# Não utilizado
from pydantic import BaseModel, Field

class StructuredOutput(BaseModel):
    response: str = Field(description="Full, friendly, organized answer with balanced use of emojis for the user, based on information retrieved by EditalTool. Include references to call number and section whenever possible. Encourage the user to continue the conversation.")
    mentioned_calls: list[int] = Field(description="List of IDs of the calls mentioned or an empty list")