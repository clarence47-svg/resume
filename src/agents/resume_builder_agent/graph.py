from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agents.resume_builder_agent.nodes.ats_audit import ats_audit, repair
from agents.resume_builder_agent.nodes.composition import compose_resume
from agents.resume_builder_agent.nodes.pagination import plan_pages
from agents.resume_builder_agent.nodes.rendering import render_exports
from agents.resume_builder_agent.nodes.selection import select_content
from agents.resume_builder_agent.state import ResumeBuilderState


def route_audit(state: ResumeBuilderState):
    return "render_exports" if state.get("audit", {}).get("passed", False) else "repair"


def build_graph(checkpointer=None):
    builder = StateGraph(ResumeBuilderState)
    builder.add_node("select_content", select_content)
    builder.add_node("compose_resume", compose_resume)
    builder.add_node("plan_pages", plan_pages)
    builder.add_node("ats_audit", ats_audit)
    builder.add_node("repair", repair)
    builder.add_node("render_exports", render_exports)
    builder.add_edge(START, "select_content")
    builder.add_edge("select_content", "compose_resume")
    builder.add_edge("compose_resume", "plan_pages")
    builder.add_edge("plan_pages", "ats_audit")
    builder.add_conditional_edges("ats_audit", route_audit)
    builder.add_edge("repair", "render_exports")
    builder.add_edge("render_exports", END)
    return builder.compile(checkpointer=checkpointer)


graph = build_graph(checkpointer=InMemorySaver())
