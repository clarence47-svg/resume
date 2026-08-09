from pathlib import Path
from profile.models import (
    EvidenceRef,
    ExperienceEntry,
    ExperienceSection,
    FactCategory,
    ProfileFact,
    ProfileResult,
)
from profile.section_documents import SECTION_FILENAMES

import pytest

from agents.jd_match_agent.graph import build_graph
from matching.materials import match_result_materials
from matching.models import JDMatchResult


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
                technologies=["Python"],
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
    project_master = output["result"]["section_documents"][FactCategory.PROJECT.value]
    assert project_master.startswith("# 画像母版_项目经历")
    assert project_master.count("## 项目") <= 3
    section_path = (
        tmp_path
        / "matches"
        / "match"
        / "v1"
        / "sections"
        / SECTION_FILENAMES[FactCategory.PROJECT.value]
    )
    assert section_path.exists()
    assert section_path.read_text(encoding="utf-8") == project_master
    historical_materials = match_result_materials(
        JDMatchResult.model_validate(output["result"]), facts
    )
    assert historical_materials
    assert all(material.evidence_refs for material in historical_materials)
    assert any("Python" in material.statement for material in historical_materials)


@pytest.mark.asyncio
async def test_jd_match_graph_uses_only_corresponding_section_document(tmp_path: Path) -> None:
    facts = []
    entries = []
    for index in range(2):
        evidence = EvidenceRef(
            span_id=f"span-filter-{index}",
            document_id="doc",
            file_name="resume.md",
            quote=f"Python 项目 {index}",
            paragraph=index + 1,
        )
        facts.append(
            ProfileFact(
                id=f"fact-filter-{index}",
                category=FactCategory.PROJECT,
                statement=f"使用 Python 完成项目 {index}",
                evidence_refs=[evidence],
            )
        )
        entries.append(
            ExperienceEntry(
                name=f"项目 {index}",
                summary=f"使用 Python 完成项目 {index}",
                technologies=["Python"],
                evidence_refs=[evidence],
            )
        )
    profile = ProfileResult(
        task_id="profile-filter",
        project_experiences=ExperienceSection(entries=entries),
    )
    output = await build_graph().ainvoke(
        {
            "match_id": "match-filter",
            "profile_task_id": "profile-filter",
            "jd_text": "Python 后端工程师\n任职要求：熟悉 Python，具备项目开发经验。",
            "profile_result": profile.model_dump(mode="json"),
            "profile_sections": {
                FactCategory.PROJECT.value: "# 项目经历\n- [fact_id:fact-filter-0] 项目 0\n"
            },
            "facts": [fact.model_dump(mode="json") for fact in facts],
            "conflicts": [],
            "section_outputs": [],
            "warnings": [],
            "audit_attempt": 0,
            "target_version": 1,
            "export_dir": str(tmp_path),
        }
    )
    names = [item["name"] for item in output["result"]["project_experiences"]["entries"]]
    assert names == ["项目 0"]
    entry = output["result"]["project_experiences"]["entries"][0]
    assert "使用 Python 完成项目 0" in entry["tailored_summary"]["content"]
    assert entry["technologies"] == ["Python"]
