from pathlib import Path

from resumes.models import ResumeDocument
from resumes.templates import ats_standard, student_compact, technical

RENDERERS = {
    "ats_standard": ats_standard.render_markdown,
    "student_compact": student_compact.render_markdown,
    "technical": technical.render_markdown,
}


def export_markdown(document: ResumeDocument, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(RENDERERS[document.template.value](document), encoding="utf-8")
    return path
