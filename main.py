import os
import warnings
from dotenv import load_dotenv
warnings.filterwarnings("ignore", category=UserWarning)

load_dotenv()

from graph import app

def rodar_teste(entrada_usuario: str):
    print(f"\n{'-'*50}")
    print(f"entrada do usuário: {entrada_usuario}")
    
    estado_inicial = {
        "messages": [],
        "user_input": entrada_usuario,
        "next_agent": None,
        "delegation_instruction": None,
        "final_response": None
    }
    
    estado_final = estado_inicial
    
    for output in app.stream(estado_inicial):
        for nome_do_no, atualizacao_estado in output.items():
            if "next_agent" in atualizacao_estado:
                print(f"-> roteando o controle para: [{atualizacao_estado['next_agent']}]")
            estado_final = atualizacao_estado
            
    print(f"\n[resposta final]: {estado_final.get('final_response')}")

if __name__ == "__main__":
    entradas = [
        "quanto é 15 mais 27?",
        "qual a previsão do tempo para são paulo?",
        "por favor, deixe isso tudo em letra maiúscula: eu gosto muito de batatas fritas",
        "oi, poderia me falar sobre batatas fritas?"
    ]
    
    for entrada in entradas:
        rodar_teste(entrada)
