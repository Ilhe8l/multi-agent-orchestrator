from langgraph.graph import StateGraph, START, END
from typing import Literal
from state import MultiAgentState
from router import orchestrator_node
from agents.conversational_agent import conversational_node
from langgraph.types import Send
import json

mcp_tools = []


async def mcp_tool_node(state: MultiAgentState):
    global mcp_tools
    tool_name = state.get("tool_name")
    instruction = state.get("delegation_instruction", "")
    
    print(f"[MCP Executor] Executing {tool_name} with instruction: {instruction}")
    
    for t in mcp_tools:
        if t.name == tool_name:
            try:
                result = await t.ainvoke({"instruction": instruction})
                
                # Extraindo o texto livre de invólucros do Model Context Protocol
                content_str = ""
                
                # Se for uma lista (formato comum que o ainvoke da tool retorna)
                if isinstance(result, list):
                    parts = []
                    for r in result:
                        if isinstance(r, dict) and r.get("type") == "text":
                            parts.append(r.get("text", ""))
                        elif hasattr(r, "text"):
                            parts.append(r.text)
                        else:
                            parts.append(str(r))
                    content_str = "".join(parts)
                # Se for um objeto com a propriedade .content
                elif hasattr(result, 'content') and isinstance(result.content, list):
                    content_str = "".join([c.text if hasattr(c, 'text') else str(c) for c in result.content])
                
                if not content_str:
                    content_str = str(result)

                try:
                    import re
                    # Tenta extrair o dicionário JSON caso o content_str esteja empacotado em ToolMessage(content='{...}')
                    json_match = re.search(r'(\{.*\})', content_str, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(1))
                    else:
                        parsed = json.loads(content_str)

                    if isinstance(parsed, dict) and "final_content" in parsed:
                        return {
                            "messages": [f"[{tool_name}]:\n{parsed['final_content']}"],
                            "text_response": parsed.get("text_response"),
                            "sql_used": parsed.get("sql_used"),
                            "graph": parsed.get("data_rows")
                        }
                except Exception:
                    pass
                
                return {"messages": [f"[{tool_name}]:\n{content_str}"]}

            except Exception as e:
                return {"messages": [f"Erro na ferramenta {tool_name}: {str(e)}"]}
                
    return {"messages": [f"Ferramenta MCP {tool_name} não encontrada."]}


def route_from_orchestrator(state: MultiAgentState):
    # o send permite enviar para múltiplos agentes, e esperar as respostas de todos eles antes de seguir para o próximo nó do grafo (no caso, o agente conversacional)
    sends = []
    for call in state["calls"]:
        intent = call.intent
        if intent == "conversational":
            sends.append(Send("conversational_agent", {"delegation_instruction": call.delegation_instruction}))
        else:
            sends.append(Send("mcp_tool_node", {"tool_name": intent, "delegation_instruction": call.delegation_instruction}))
    return sends


def format_final_output(state: MultiAgentState):
    messages = state.get("messages", [])
    if messages:
        return {"final_response": messages[-1].content}
    return {}


builder = StateGraph(MultiAgentState)

builder.add_node("orchestrator", orchestrator_node)

builder.add_node("conversational_agent", conversational_node)
builder.add_node("mcp_tool_node", mcp_tool_node)

builder.add_node("format_final_output", format_final_output)

builder.add_edge(START, "orchestrator")

# o orquestrador decide para qual agente/api enviar com base nas chamadas (calls)
builder.add_conditional_edges("orchestrator", route_from_orchestrator)

# depois de consultar a api, o fluxo deve voltar para o agente conversacional
builder.add_edge("mcp_tool_node", "conversational_agent")

# o agente conversacional é sempre o último da cadeia
builder.add_edge("conversational_agent", "format_final_output")
builder.add_edge("format_final_output", END)