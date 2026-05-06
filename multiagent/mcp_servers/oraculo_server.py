import os
import requests
from fastmcp import FastMCP

mcp = FastMCP("oraculo-mcp-server")

# Se estiver rodando em container e o backend no host → OK
ORACULO_URL = os.getenv("ORACULO_URL", "http://host.docker.internal:8001")


@mcp.tool()
def consultar_oraculo(instruction: str) -> str:
    """
    Consulta dados estruturados (SQL/BI) da base interna da FAPES.
    Use para buscar valores financeiros, datas, listas de projetos, bolsistas, etc.
    """

    payload = {"question": instruction}

    try:
        resp = requests.post(
            f"{ORACULO_URL}/api/chat",
            json=payload,
            timeout=30
        )
        resp.raise_for_status()

        data = resp.json()

        #  DEBUG (ESSENCIAL)
        print(" RESPOSTA BRUTA DO ORÁCULO:", data)

        #  Tratamento de erro
        if data.get("type") == "error":
            text_response = data.get("text", "")
            sql_used = None
            data_rows = []

            final_content = f" Erro do Oráculo:\n{text_response}"

        else:
            text_response = data.get("text", "")

            # Suporte a múltiplos formatos de SQL
            sql_used = (
                data.get("sql")
                or data.get("query")
                or data.get("generated_sql")
                or data.get("sql_query")
            )

            data_rows = data.get("data", [])

            # TEXTO FINAL (O MAIS IMPORTANTE)
            final_content = text_response

            if sql_used:
                final_content += f"\n\n SQL gerado:\n{sql_used}"

            if data_rows:
                final_content += f"\n\n Dados retornados:\n{data_rows}"

        # LOG FINAL
        print("[Oráculo API] Resposta formatada:", final_content)
        # RETORNO (Como JSON)
        import json # (apenas para garantir)
        return json.dumps({
            "final_content": final_content,
            "text_response": text_response,
            "sql_used": sql_used,
            "data_rows": data_rows
        }, ensure_ascii=False)

    except requests.exceptions.RequestException as e:
        error_msg = f" Falha de conexão com o Oráculo: {str(e)}"
        print("[Oráculo API] Erro:", error_msg)
        return error_msg


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8005,
        path="/mcp",
        stateless_http=True
    )