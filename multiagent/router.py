import os
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from state import MultiAgentState
from models import RouterDecision
from config import ORCHESTRATOR_SYSTEM_PROMPT

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("LLM_API_KEY"),
    temperature=0.0
)

mcp_tools = []

async def orchestrator_node(state: MultiAgentState):
    global mcp_tools
    
    tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in mcp_tools]) if mcp_tools else "Nenhuma ferramenta externa disponível."

    system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(tools_desc=tools_desc)
    
    structured_llm = llm.with_structured_output(RouterDecision, method="function_calling")
    
    history = state.get("messages", [])
    messages = [SystemMessage(content=system_prompt)] + history
    
    decision: RouterDecision = await structured_llm.ainvoke(messages)
    
    print(f"[Orchestrator] Calls geradas: {[(c.intent, c.delegation_instruction[:60]) for c in decision.calls]}")

# retorna todas as chamadas do agente roteador
    return {
        "calls": decision.calls
    }

