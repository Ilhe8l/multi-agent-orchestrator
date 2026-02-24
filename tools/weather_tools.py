from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """Retorna a previsao do tempo de uma determinada cidade.
    
    Args:
        city: O nome da cidade (str).
    """
    forecasts = {
        "saopaulo": "Ensolarado, 28 graus.",
        "london": "Chuvoso, 12 graus.",
        "newyork": "Nublado, 15 graus."
    }
    normalized_city = city.lower().replace(" ", "")
    return forecasts.get(normalized_city, f"Clima desconhecido para {city}. Previsão padrão: Parcialmente nublado, 20 graus.")
