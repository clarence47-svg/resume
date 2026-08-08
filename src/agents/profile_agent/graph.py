from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from agents.profile_agent.nodes.audit import assemble_profile, audit_profile
from agents.profile_agent.nodes.extraction import extract_fact_chunk, prepare
from agents.profile_agent.nodes.generation import SECTION_NAMES, generate_section
from agents.profile_agent.nodes.merge import merge_facts
from agents.profile_agent.nodes.persist import persist_and_export
from agents.profile_agent.nodes.review import optional_review
from agents.profile_agent.state import ProfileAgentState


def route_after_prepare(state: ProfileAgentState):
    if state.get("mode") == "facts_only":
        return "merge_facts"
    return [
        Send(
            "extract_fact_chunk",
            {
                "task_id": state["task_id"],
                "chunk": chunk,
            },
        )
        for chunk in state.get("chunks", [])
    ]


def route_sections(state: ProfileAgentState):
    return [
        Send(
            "generate_section",
            {
                "task_id": state["task_id"],
                "section_name": section_name,
                "facts": state.get("facts", []),
            },
        )
        for section_name in SECTION_NAMES
    ]


def build_graph(checkpointer=None):
    builder = StateGraph(ProfileAgentState)
    builder.add_node("prepare", prepare)
    builder.add_node("extract_fact_chunk", extract_fact_chunk)
    builder.add_node("merge_facts", merge_facts)
    builder.add_node("optional_review", optional_review)
    builder.add_node("generate_section", generate_section)
    builder.add_node("assemble_profile", assemble_profile)
    builder.add_node("audit", audit_profile)
    builder.add_node("persist_and_export", persist_and_export)

    builder.add_edge(START, "prepare")
    builder.add_conditional_edges("prepare", route_after_prepare)
    builder.add_edge("extract_fact_chunk", "merge_facts")
    builder.add_edge("merge_facts", "optional_review")
    builder.add_conditional_edges("optional_review", route_sections)
    builder.add_edge("generate_section", "assemble_profile")
    builder.add_edge("assemble_profile", "audit")
    builder.add_edge("audit", "persist_and_export")
    builder.add_edge("persist_and_export", END)
    return builder.compile(checkpointer=checkpointer)


graph = build_graph(checkpointer=InMemorySaver())
