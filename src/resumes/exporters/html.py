from pathlib import Path

from resumes.models import ResumeDocument
from resumes.templates import ats_standard, student_compact, technical

RENDERERS = {
    "ats_standard": ats_standard.render_html,
    "student_compact": student_compact.render_html,
    "technical": technical.render_html,
}


def export_html(document: ResumeDocument, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(RENDERERS[document.template.value](document), encoding="utf-8")
    return path
