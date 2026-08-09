from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from agents.jd_match_agent.nodes.audit import assemble_result, audit_result, repair_result
from agents.jd_match_agent.nodes.generation import SECTION_NAMES, generate_section
from agents.jd_match_agent.nodes.jd_analysis import analyze_jd
from agents.jd_match_agent.nodes.matching import match_requirements
from agents.jd_match_agent.nodes.persist import persist_and_export
from agents.jd_match_agent.nodes.preparation import prepare
from agents.jd_match_agent.nodes.research import research_role
from agents.jd_match_agent.nodes.scoring import score_and_select
from agents.jd_match_agent.state import JDMatchAgentState


def route_sections(state: JDMatchAgentState):
    shared = {
        key: state.get(key)
        for key in (
            "facts",
            "tailored_profile_sections",
            "jd_analysis",
            "job_research",
            "requirement_matches",
            "selected_entries",
            "selected_fact_ids",
            "fact_relevance",
            "material_scores",
        )
    }
    return [Send("generate_section", {**shared, "section_name": name}) for name in SECTION_NAMES]


def route_after_audit(state: JDMatchAgentState):
    if state.get("audit_passed") or state.get("audit_attempt", 0) >= 1:
        return "persist_and_export"
    return "repair"


def build_graph(checkpointer=None):
    builder = StateGraph(JDMatchAgentState)
    builder.add_node("prepare", prepare)
    builder.add_node("analyze_jd", analyze_jd)
    builder.add_node("research_role", research_role)
    builder.add_node("match_requirements", match_requirements)
    builder.add_node("score_and_select", score_and_select)
    builder.add_node("generate_section", generate_section)
    builder.add_node("assemble", assemble_result)
    builder.add_node("audit", audit_result)
    builder.add_node("repair", repair_result)
    builder.add_node("persist_and_export", persist_and_export)
    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "analyze_jd")
    builder.add_edge("analyze_jd", "research_role")
    builder.add_edge("research_role", "match_requirements")
    builder.add_edge("match_requirements", "score_and_select")
    builder.add_conditional_edges("score_and_select", route_sections)
    builder.add_edge("generate_section", "assemble")
    builder.add_edge("assemble", "audit")
    builder.add_conditional_edges("audit", route_after_audit)
    builder.add_edge("repair", "audit")
    builder.add_edge("persist_and_export", END)
    return builder.compile(checkpointer=checkpointer)


graph = build_graph(checkpointer=InMemorySaver())
