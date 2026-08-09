from profile.models import EvidenceRef, FactCategory, ProfileFact, ProfileResult

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from agents.profile_agent.graph import build_graph


@pytest.mark.asyncio
async def test_graph_always_returns_six_sections(tmp_path) -> None:
    fact = ProfileFact(
        category=FactCategory.PROJECT,
        statement="负责校园平台后端开发，使用 FastAPI。",
        evidence_refs=[
            EvidenceRef(
                span_id="span-1",
                document_id="doc-1",
                file_name="resume.md",
                quote="负责校园平台后端开发，使用 FastAPI。",
            )
        ],
    )
    graph = build_graph(InMemorySaver())
    output = await graph.ainvoke(
        {
            "task_id": "task-1",
            "export_dir": str(tmp_path),
            "mode": "facts_only",
            "review_mode": "auto",
            "review_completed": True,
            "chunks": [],
            "facts": [fact.model_dump(mode="json")],
            "conflicts": [],
            "extracted_fact_batches": [],
            "section_outputs": [],
            "warnings": [],
        },
        config={"configurable": {"thread_id": "task-1"}},
    )
    result = ProfileResult.model_validate(output["result"])
    assert result.task_id == "task-1"
    assert result.project_experiences.entries
    assert (tmp_path / "task-1" / "profile.md").exists()
    assert (tmp_path / "task-1" / "profile.docx").exists()


@pytest.mark.asyncio
async def test_graph_semantically_groups_renamed_project_materials(tmp_path) -> None:
    facts = [
        ProfileFact(
            id="fact-product",
            category=FactCategory.PROJECT,
            statement="负责眼动数据处理、能力诊断流程和教学反馈方案设计。",
            metadata={
                "experience_name": "学生数学素养智能测评产品",
                "organization": "广州大学",
                "period": "2025.03-至今",
            },
            evidence_refs=[
                EvidenceRef(
                    span_id="span-product",
                    document_id="doc-product",
                    file_name="产品岗位简历.md",
                    quote="负责眼动数据处理、能力诊断流程和教学反馈方案设计。",
                )
            ],
        ),
        ProfileFact(
            id="fact-engineering",
            category=FactCategory.PROJECT,
            statement="完成学生能力画像、诊断报告和数据可视化前端开发。",
            metadata={
                "experience_name": "教育 AI 数据分析平台",
                "organization": "广州大学",
                "period": "2025.03-2026.06",
            },
            evidence_refs=[
                EvidenceRef(
                    span_id="span-engineering",
                    document_id="doc-engineering",
                    file_name="开发岗位简历.md",
                    quote="完成学生能力画像、诊断报告和数据可视化前端开发。",
                )
            ],
        ),
    ]
    output = await build_graph(InMemorySaver()).ainvoke(
        {
            "task_id": "semantic-profile",
            "export_dir": str(tmp_path),
            "mode": "facts_only",
            "review_mode": "auto",
            "review_completed": True,
            "chunks": [],
            "facts": [fact.model_dump(mode="json") for fact in facts],
            "conflicts": [],
            "extracted_fact_batches": [],
            "section_outputs": [],
            "warnings": [],
        },
        config={"configurable": {"thread_id": "semantic-profile"}},
    )
    result = ProfileResult.model_validate(output["result"])
    assert output["conflicts"] == []
    assert len(result.project_experiences.entries) == 1
    assert set(result.project_experiences.entries[0].source_fact_ids) == {
        "fact-product",
        "fact-engineering",
    }
    contents = [
        claim.content
        for claim in result.project_experiences.entries[0].details
        + result.project_experiences.entries[0].outcomes
    ]
    assert any("眼动数据处理" in content for content in contents)
    assert any("数据可视化前端" in content for content in contents)
