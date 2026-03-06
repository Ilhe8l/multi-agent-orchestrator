import os
import requests
from langchain_core.runnables import RunnableConfig
from state import MultiAgentState
import json

EDITE_URL = os.getenv("EDITE_URL", "http://localhost:8003")
ORACLE_API_TOKEN = os.getenv("ORACLE_API_TOKEN", "")

def edite_agent_node(state: MultiAgentState):
    
    # Este nó é responsável por enviar mensagem para a API Edite e retornar a resposta
    instruction = state.get("delegation_instruction", "")

    # Obtendo session_id e user_id da configuração do LangGraph, com fallbacks consistentes com o exemplo
    #configurable = config.get("configurable", {})
    session_id = "session-123"    #configurable.get("thread_id", "sessao-teste-123")
    user_id = "user-456"   #configurable.get("user_id", "usuario-teste-456")

    payload = {
        "content": instruction,
        "session_id": session_id,
        "user_id": user_id
    }

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ORACLE_API_TOKEN}"
    }

    print(f"[Edite API] Enviando mensagem à Edite: {instruction}")
    try:
        response = requests.post(
            f"{EDITE_URL}/api/message",
            json=payload,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()
        result = response.json()

        response_data = result.get("response", "")       
        response_data = json.loads(response_data)

        if result.get("status") == "error":
            final_content = f"A Edite retornou um erro: {response_data.get('response', 'Erro desconhecido')}"
        else:
            final_content = response_data.get("response", "")

        print("[Edite API] Resposta da Edite: ", final_content)
        return {"messages": [final_content]}

    except requests.exceptions.RequestException as e:
        error_msg = f"Houve uma falha de conexão ao consultar a base da Edite: {str(e)}"
        return {"messages": [error_msg]}
