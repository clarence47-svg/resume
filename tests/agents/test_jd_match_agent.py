from pathlib import Path
from profile.models import (
    EvidenceRef,
    ExperienceEntry,
    ExperienceSection,
    FactCategory,
    ProfileFact,
    ProfileResult,
)

import pytest

from agents.jd_match_agent.graph import build_graph


@pytest.mark.asyncio
async def test_jd_match_graph_limits_project_entries(tmp_path: Path) -> None:
    facts = []
    entries = []
    for index in range(4):
        evidence = EvidenceRef(
            span_id=f"span-{index}",
            document_id="doc",
            file_name="resume.md",
            quote=f"Python 项目 {index}",
            paragraph=index + 1,
        )
        facts.append(
            ProfileFact(
                id=f"fact-{index}",
                category=FactCategory.PROJECT,
                statement=f"使用 Python 完成项目 {index}",
                evidence_refs=[evidence],
            )
        )
        entries.append(
            ExperienceEntry(
                name=f"项目 {index}",
                summary=f"使用 Python 完成项目 {index}",
                evidence_refs=[evidence],
            )
        )
    profile = ProfileResult(
        task_id="profile",
        project_experiences=ExperienceSection(entries=entries),
    )
    output = await build_graph().ainvoke(
        {
            "match_id": "match",
            "profile_task_id": "profile",
            "jd_text": "Python 后端工程师\n任职要求：熟悉 Python，具备项目开发经验。",
            "profile_result": profile.model_dump(mode="json"),
            "facts": [fact.model_dump(mode="json") for fact in facts],
            "conflicts": [],
            "section_outputs": [],
            "warnings": [],
            "audit_attempt": 0,
            "target_version": 1,
            "export_dir": str(tmp_path),
        }
    )
    assert len(output["result"]["project_experiences"]["entries"]) <= 3
    assert output["result"]["audit"]["passed"] is True
