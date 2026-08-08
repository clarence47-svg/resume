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
