import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from contextlib import asynccontextmanager
from config import ORACULO_MCP_URL, EDITE_MCP_URL

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

