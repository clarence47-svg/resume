from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agents.interview_agent.state import InterviewAgentState


def prepare(state: dict) -> dict:
    return state


def generate(state: dict) -> dict:
    return {"result": state.get("result", {})}


def build_graph(checkpointer=None):
    builder = StateGraph(InterviewAgentState)
    builder.add_node("prepare", prepare)
    builder.add_node("generate_interview_kit", generate)
    builder.add_node("persist", generate)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "generate_interview_kit")
    builder.add_edge("generate_interview_kit", "persist")
    builder.add_edge("persist", END)
    return builder.compile(checkpointer=checkpointer)


graph = build_graph(checkpointer=InMemorySaver())
