from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    # contexto para o agente
    """Soma dois numeros inteiros.
    
    Args:
        a: O primeiro inteiro.
        b: O segundo inteiro.
    """
    return a + b
