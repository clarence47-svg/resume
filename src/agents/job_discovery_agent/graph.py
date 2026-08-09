from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agents.job_discovery_agent.nodes.collection import collect_sources, prepare_campaign
from agents.job_discovery_agent.nodes.filtering import hard_filter
from agents.job_discovery_agent.nodes.normalization import normalize_and_dedupe
from agents.job_discovery_agent.nodes.scoring import score_jobs
from agents.job_discovery_agent.nodes.shortlist import persist, shortlist
from agents.job_discovery_agent.state import JobDiscoveryAgentState


def build_graph(checkpointer=None):
    builder = StateGraph(JobDiscoveryAgentState)
    builder.add_node("prepare_campaign", prepare_campaign)
    builder.add_node("collect_sources", collect_sources)
    builder.add_node("normalize_and_dedupe", normalize_and_dedupe)
    builder.add_node("hard_filter", hard_filter)
    builder.add_node("score_jobs", score_jobs)
    builder.add_node("shortlist", shortlist)
    builder.add_node("persist", persist)
    builder.add_edge(START, "prepare_campaign")
    builder.add_edge("prepare_campaign", "collect_sources")
    builder.add_edge("collect_sources", "normalize_and_dedupe")
    builder.add_edge("normalize_and_dedupe", "hard_filter")
    builder.add_edge("hard_filter", "score_jobs")
    builder.add_edge("score_jobs", "shortlist")
    builder.add_edge("shortlist", "persist")
    builder.add_edge("persist", END)
    return builder.compile(checkpointer=checkpointer)


graph = build_graph(checkpointer=InMemorySaver())
