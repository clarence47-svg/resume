from dataclasses import dataclass
from typing import Any

from agents.application_agent.graph import build_graph as build_application_graph
from agents.interview_agent.graph import build_graph as build_interview_graph
from agents.jd_match_agent.graph import build_graph as build_jd_match_graph
from agents.job_discovery_agent.graph import build_graph as build_job_discovery_graph
from agents.profile_agent.graph import build_graph
from agents.resume_builder_agent.graph import build_graph as build_resume_builder_graph


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
    "job-discovery-agent": AgentDefinition(
        description="采集、去重、硬筛选并评分岗位。",
        graph_factory=build_job_discovery_graph,
        protocol="job-discovery",
    ),
    "resume-builder-agent": AgentDefinition(
        description="根据岗位匹配结果生成 ATS 简历和多格式文件。",
        graph_factory=build_resume_builder_graph,
        protocol="resume-builder",
    ),
    "application-agent": AgentDefinition(
        description="在逐岗位确认边界内预填、提交并验证申请。",
        graph_factory=build_application_graph,
        protocol="application",
    ),
    "interview-agent": AgentDefinition(
        description="根据岗位与简历生成面试准备包。",
        graph_factory=build_interview_graph,
        protocol="interview",
    ),
}


def get_agent(agent_id: str = "profile-agent", checkpointer=None):
    return agents[agent_id].graph_factory(checkpointer=checkpointer)
