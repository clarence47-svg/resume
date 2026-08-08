from dataclasses import dataclass
from typing import Any

from agents.jd_match_agent.graph import build_graph as build_jd_match_graph
from agents.profile_agent.graph import build_graph


@dataclass(frozen=True)
class AgentDefinition:
    description: str
    graph_factory: Any
    protocol: str


agents = {
    "profile-agent": AgentDefinition(
        description="从用户上传资料生成可追溯的六维详细画像。",
        graph_factory=build_graph,
        protocol="profile",
    ),
    "jd-match-agent": AgentDefinition(
        description="根据六维用户画像和岗位 JD 生成证据约束的匹配分析与简历文案。",
        graph_factory=build_jd_match_graph,
        protocol="jd-match",
    ),
}


def get_agent(agent_id: str = "profile-agent", checkpointer=None):
    return agents[agent_id].graph_factory(checkpointer=checkpointer)
