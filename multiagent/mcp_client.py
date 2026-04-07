import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from contextlib import asynccontextmanager

# Usa as URLs dos serviços Docker se estiverem rodando na rede
ORACULO_MCP_URL = os.getenv("ORACULO_MCP_URL", "http://oraculo_mcp:8005/mcp")
EDITE_MCP_URL = os.getenv("EDITE_MCP_URL", "http://edite_mcp:8006/mcp")

@asynccontextmanager
async def get_mcp_client():
    client = MultiServerMCPClient({
        "oraculo": {
            "url": ORACULO_MCP_URL,
            "transport": "streamable_http",
        },
        "edite": {
            "url": EDITE_MCP_URL,
            "transport": "streamable_http",
        },
    })
    
    yield client

