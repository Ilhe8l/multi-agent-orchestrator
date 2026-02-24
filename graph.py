from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from typing import Literal
from state import MultiAgentState
from router import orchestrator_node, conversational_node
from agents.math_agent import math_agent_node
from tools.math_tools import add
from agents.weather_agent import weather_agent_node
from tools.weather_tools import get_weather
from agents.text_agent import text_agent_node
from tools.text_tools import uppercase_text

def route_from_orchestrator(state: MultiAgentState) -> Literal["math_agent", "weather_agent", "text_agent", "conversational_node"]:
    intent = state.get("next_agent")
    if intent == "math":
        return "math_agent"
    elif intent == "weather":
        return "weather_agent"
    elif intent == "text":
        return "text_agent"
    return "conversational_node"

def route_to_tools(state: MultiAgentState) -> Literal["tools", END]:
    messages = state.get("messages", [])
    if not messages:
        return END
        
    last_msg = messages[-1]
    if hasattr(last_msg, "tool_calls") and len(last_msg.tool_calls) > 0:
        return "tools"
    
    return END

def format_final_output(state: MultiAgentState):
    messages = state.get("messages", [])
    if messages:
        return {"final_response": messages[-1].content}
    return {}

builder = StateGraph(MultiAgentState)

builder.add_node("orchestrator", orchestrator_node)
builder.add_node("conversational_node", conversational_node)

builder.add_node("math_agent", math_agent_node)
builder.add_node("weather_agent", weather_agent_node)
builder.add_node("text_agent", text_agent_node)

all_tools = [add, get_weather, uppercase_text]
tool_node = ToolNode(all_tools)
builder.add_node("tools", tool_node)

builder.add_node("format_final_output", format_final_output)

builder.add_edge(START, "orchestrator")
builder.add_conditional_edges("orchestrator", route_from_orchestrator)

builder.add_conditional_edges("math_agent", route_to_tools, {"tools": "tools", END: "format_final_output"})
builder.add_conditional_edges("weather_agent", route_to_tools, {"tools": "tools", END: "format_final_output"})
builder.add_conditional_edges("text_agent", route_to_tools, {"tools": "tools", END: "format_final_output"})

# como o toolnode unificado não retém o remetente original
# precisamos de uma função de roteamento para devolver o estado
# ao agente correto após a execução da ferramenta
def route_after_tools(state: MultiAgentState) -> Literal["math_agent", "weather_agent", "text_agent", END]:
    agent = state.get("next_agent")
    if agent == "math":
        return "math_agent"
    elif agent == "weather":
        return "weather_agent"
    elif agent == "text":
        return "text_agent"
    return END

builder.add_conditional_edges("tools", route_after_tools)

builder.add_edge("format_final_output", END)
builder.add_edge("conversational_node", END)

app = builder.compile()
