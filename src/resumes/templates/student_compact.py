from resumes.models import ResumeDocument
from resumes.templates.ats_standard import render_html as _render_html
from resumes.templates.ats_standard import render_markdown as _render_markdown


def render_markdown(document: ResumeDocument) -> str:
    return _render_markdown(document)


def render_html(document: ResumeDocument) -> str:
    return _render_html(document).replace("max-width:820px", "max-width:780px")
