from langchain_core.tools import tool

@tool
def uppercase_text(text: str) -> str:
    """Converte todo o texto fornecido para letras maiusculas.
    
    Args:
        text: Resumo ou palavra que deve ser alterada.
    """
    return text.upper()
