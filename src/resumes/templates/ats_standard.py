from html import escape

from resumes.models import ResumeDocument


def render_markdown(document: ResumeDocument) -> str:
    lines = [f"# {document.name or '候选人'}", document.contact_line]
    lines.extend(["", f"## 求职目标：{document.target_title}", "", "## 个人简介", document.summary])
    if document.skills:
        lines.extend(["", "**技能关键词：** " + "、".join(document.skills)])
    _append_experiences(lines, "项目经历", document.projects)
    _append_experiences(lines, "比赛经历", document.competitions)
    _append_experiences(lines, "实习经历", document.internships)
    if document.education:
        lines.extend(["", "## 教育经历"])
        for item in document.education:
            header = " | ".join(
                value for value in (item.institution, item.degree, item.major, item.period) if value
            )
            lines.append(f"### {header}")
            lines.extend(f"- {bullet.content}" for bullet in item.bullets)
    return "\n".join(line for line in lines if line is not None).strip() + "\n"


def render_html(document: ResumeDocument) -> str:
    markdown = render_markdown(document)
    lines = []
    for line in markdown.splitlines():
        if line.startswith("### "):
            lines.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("## "):
            lines.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("# "):
            lines.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("- "):
            lines.append(f"<li>{escape(line[2:])}</li>")
        elif line:
            lines.append(f"<p>{escape(line)}</p>")
    body = "\n".join(lines)
    return f"""<!doctype html><html><head><meta charset=\"utf-8\"><style>
body{{font-family:Arial,'Noto Sans CJK SC',sans-serif;max-width:820px;
margin:32px auto;color:#182230;line-height:1.5}}
h1{{margin-bottom:4px}}h2{{border-bottom:1px solid #b8c2cc;padding-bottom:4px;margin-top:22px}}
h3{{margin-bottom:4px}}p{{margin:5px 0}}li{{margin:4px 0}}
</style></head><body>{body}</body></html>"""


def _append_experiences(lines: list[str], title: str, items) -> None:
    if not items:
        return
    lines.extend(["", f"## {title}"])
    for item in items:
        header = " | ".join(
            value for value in (item.name, item.organization, item.role, item.period) if value
        )
        lines.extend([f"### {header}", item.summary])
        if item.technologies:
            lines.append("**技术/能力：** " + "、".join(item.technologies))
        lines.extend(f"- {bullet.content}" for bullet in item.bullets)
