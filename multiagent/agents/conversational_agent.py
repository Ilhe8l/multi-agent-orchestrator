from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from state import MultiAgentState
from config import CONVERSATIONAL_SYSTEM_PROMPT

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-nano",
    api_key=os.getenv("LLM_API_KEY"),
    temperature=0.0
)

async def conversational_node(state: MultiAgentState):
    instruction = state.get("delegation_instruction") or ""
    history = state.get("messages", [])

    last_msg = history[-1] if history else None
    came_from_tool = last_msg and not isinstance(last_msg, HumanMessage)

    if not instruction and last_msg:
        instruction = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    system_prompt = CONVERSATIONAL_SYSTEM_PROMPT.format(instruction=instruction)
    
    if came_from_tool:
        messages = [SystemMessage(content=system_prompt)] + history
    else:
        human_messages = [m for m in history if isinstance(m, HumanMessage)]
        messages = [SystemMessage(content=system_prompt)] + human_messages

    response = await llm.ainvoke(messages)

    print(f"[Conversational Agent] came_from_tool={came_from_tool}")
    print(f"[Conversational Agent] Instrução recebida: {instruction[:120] if instruction else None}")
    print(f"[Conversational Agent] Resposta gerada: {response.content}")

    return {
        "messages": [response],
        "final_response": response.content
    }