import os
import requests
from state import MultiAgentState

ORACULO_URL = os.getenv("ORACULO_URL", "http://localhost:8001")

def oracle_agent_node(state: MultiAgentState):
    # Este nó é responsável por enviar ao backend Oráculo perguntas relacionadas à Fapes, editais, processos, etc.
    # Ele funciona apenas como um intermédio, recebendo a pergunta do usuário e retornando a resposta do backend, sem lógica adicional.
    
    instruction = state.get("delegation_instruction", "")

    payload = {
        "question": instruction,
    }

    print(f"[Oráculo API] Enviando pergunta ao Oráculo: {instruction}")
    try:

        response = requests.post(
            f"{ORACULO_URL}/api/chat",
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()
        

        if result.get("type") == "error":
            final_content = f"O Oráculo retornou um erro: {result.get('text')}"
        else:
            text_response = result.get("text", "")
            sql_used = result.get("sql", "Nenhum SQL gerado")
            data_rows = result.get("data", [])
            
            final_content = (
                f"{text_response}\n\n"
                f"SQL utilizado: {sql_used}\n"
                f"Dados brutos retornados: {data_rows}"
            )

        return {"messages": [final_content]}


    except requests.exceptions.RequestException as e:
        error_msg = f"Houve uma falha de conexão ao consultar a base do Oráculo: {str(e)}"
        return {"messages": [error_msg]}
