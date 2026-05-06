import os
import requests
from fastmcp import FastMCP


mcp = FastMCP("edite-mcp-server")
EDITE_URL = os.getenv("EDITE_URL", "http://edite_agent:8003")

@mcp.tool()
def consultar_edite(instruction: str) -> str:
    """
    Consulta conteúdo documental de editais (RAG) da FAPES.
    Use para regras, cláusulas, requisitos, anexos e documentos exigidos.
    NÃO use para buscar dados financeiros ou quantitativos — use consultar_oraculo para isso.
    """
    try:
        resp = requests.post(f"{EDITE_URL}/api/chat", json={"question": instruction}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        return str(data.get("answer", data))
    except requests.exceptions.RequestException as e:
        return f"Houve uma falha de conexão ao consultar o Edite: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8006, path="/mcp")
