from pathlib import Path
from profile.models import SectionStatus

import fitz

from career.models import CareerSettings
from job_search.models import JobPosting
from matching.models import JDAnalysis, JDMatchResult, TailoredCopyUnit, TailoredTextSection
from resumes.ats import audit_resume
from resumes.composition import compose_resume
from resumes.exporters.docx import export_docx
from resumes.exporters.html import export_html
from resumes.exporters.markdown import export_markdown
from resumes.exporters.pdf import export_pdf
from resumes.models import ResumeTemplate
from resumes.source_documents import (
    RESUME_DOCUMENT_FILENAMES,
    write_resume_source_documents,
)


def test_resume_materials_and_all_exports(tmp_path: Path):
    unit = TailoredCopyUnit(content="具备 Python 与 FastAPI 项目经验。", relevance_score=90)
    empty_experience = {
        "status": SectionStatus.INSUFFICIENT_EVIDENCE,
        "overview": unit,
        "entries": [],
    }
    result = JDMatchResult(
        match_id="m1",
        profile_task_id="p1",
        jd_analysis=JDAnalysis(role_title="Python 开发", keywords=["Python", "FastAPI"]),
        personal_introduction=TailoredTextSection(
            status=SectionStatus.COMPLETE,
            overview=unit,
        ),
        keyword_coverage={"matched": ["Python", "FastAPI"], "ratio": 1},
        project_experiences=empty_experience,
        competition_experiences=empty_experience,
        internship_experiences=empty_experience,
        education_history=empty_experience,
    )
    job = JobPosting(
        campaign_id="c1",
        profile_task_id="p1",
        company="示例公司",
        title="Python 开发",
        jd_text="Python FastAPI",
    )
    document = compose_resume(
        result,
        job,
        CareerSettings(display_name="张三", email="a@example.com"),
        ResumeTemplate.ATS_STANDARD,
    )
    document.audit = audit_resume(document, job.jd_text)
    assert "示例公司" in document.application_materials.cover_letter
    assert "Python 开发" in document.application_materials.boss_greeting
    source_paths = write_resume_source_documents(result, [], tmp_path)
    markdown_path = export_markdown(document, tmp_path / RESUME_DOCUMENT_FILENAMES["final_resume"])
    html_path = export_html(document, tmp_path / "resume.html")
    docx_path = export_docx(document, tmp_path / "resume.docx")
    pdf_path = export_pdf(docx_path, tmp_path / "resume.pdf", html_path)
    assert markdown_path.exists()
    assert html_path.exists()
    assert docx_path.exists()
    assert pdf_path and pdf_path.exists()
    assert len(source_paths) == 5
    assert len(list(tmp_path.glob("*.md"))) == 6
    with fitz.open(pdf_path) as pdf:
        assert pdf.page_count >= 1
