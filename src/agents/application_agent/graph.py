from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agents.application_agent.nodes import (
    form_fill,
    navigation,
    preparation,
    preview,
    submission,
    verification,
)
from agents.application_agent.nodes.confirmation import confirmation
from agents.application_agent.state import ApplicationAgentState


def build_graph(checkpointer=None):
    builder = StateGraph(ApplicationAgentState)
    builder.add_node("prepare", preparation)
    builder.add_node("connect_browser", navigation)
    builder.add_node("open_job", navigation)
    builder.add_node("detect_platform", navigation)
    builder.add_node("fill_safe_fields", form_fill)
    builder.add_node("upload_resume", form_fill)
    builder.add_node("validate_preview", preview)
    builder.add_node("confirmation", confirmation)
    builder.add_node("revalidate", preview)
    builder.add_node("submit", submission)
    builder.add_node("verify", verification)
    builder.add_node("persist", verification)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "connect_browser")
    builder.add_edge("connect_browser", "open_job")
    builder.add_edge("open_job", "detect_platform")
    builder.add_edge("detect_platform", "fill_safe_fields")
    builder.add_edge("fill_safe_fields", "upload_resume")
    builder.add_edge("upload_resume", "validate_preview")
    builder.add_edge("validate_preview", "confirmation")
    builder.add_edge("confirmation", "revalidate")
    builder.add_edge("revalidate", "submit")
    builder.add_edge("submit", "verify")
    builder.add_edge("verify", "persist")
    builder.add_edge("persist", END)
    return builder.compile(checkpointer=checkpointer)


graph = build_graph(checkpointer=InMemorySaver())
