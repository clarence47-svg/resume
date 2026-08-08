from pathlib import Path

from matching.exporters import export_match_docx, export_match_markdown
from matching.models import (
    JDAnalysis,
    JDMatchResult,
    TailoredCopyUnit,
    TailoredEducationSection,
    TailoredExperienceSection,
    TailoredTextSection,
)


def test_match_exporters_create_files(tmp_path: Path) -> None:
    empty = TailoredCopyUnit(content="资料未提供足够证据。")
    result = JDMatchResult(
        match_id="match",
        profile_task_id="profile",
        jd_analysis=JDAnalysis(role_title="后端工程师"),
        personal_introduction=TailoredTextSection(overview=empty),
        professional_introduction=TailoredTextSection(overview=empty),
        project_experiences=TailoredExperienceSection(overview=empty),
        competition_experiences=TailoredExperienceSection(overview=empty),
        internship_experiences=TailoredExperienceSection(overview=empty),
        education_history=TailoredEducationSection(overview=empty),
    )
    markdown = export_match_markdown(result, tmp_path / "match.md")
    docx = export_match_docx(result, tmp_path / "match.docx")
    assert markdown.exists()
    assert "后端工程师" in markdown.read_text(encoding="utf-8")
    assert docx.exists() and docx.stat().st_size > 0
