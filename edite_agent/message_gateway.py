from langchain_core.messages import HumanMessage
from graph import get_graph
from stateTypes import State

async def process_message(user_message: str, thread_id: str, user_id: str) -> dict:
    # Obtém o grafo já configurado com o Langfuse handler
    graph = await get_graph()

    # Executa o grafo com informações do usuário e da sessão
    response = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=user_message)],
            "last_user_message": user_message
        },
        config={
            "metadata": { # langfuse
                "langfuse_user_id": user_id,      
                "langfuse_session_id": thread_id, 
            },
            "configurable": { # interno do grafo
                "user_id": user_id,               
                "thread_id": thread_id
            }
        }
    )

    return {
        "response": response["messages"][-1].content,
        "thread_id": thread_id,
        "user_id": user_id
    }
