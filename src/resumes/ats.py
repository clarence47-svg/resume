from job_search.scoring import extract_job_keywords
from resumes.models import ResumeAudit, ResumeDocument


def audit_resume(document: ResumeDocument, jd_text: str) -> ResumeAudit:
    text = _resume_text(document).casefold()
    keywords = extract_job_keywords(jd_text)
    matched = [item for item in keywords if item.casefold() in text]
    ratio = len(matched) / max(len(keywords), 1)
    warnings = []
    if not document.contact_line:
        warnings.append("尚未填写联系方式。")
    if not document.summary:
        warnings.append("个人介绍为空。")
    if ratio < 0.5:
        warnings.append("JD 关键词覆盖率偏低。")
    if not any((document.projects, document.internships, document.competitions)):
        warnings.append("缺少可展示的项目、实习或比赛经历。")
    pages = estimate_pages(document)
    if pages > document.target_pages:
        warnings.append(f"内容预计为 {pages} 页，超过目标页数。")
    return ResumeAudit(
        passed=not any("为空" in item for item in warnings),
        ats_score=round(min(100, 55 + ratio * 45 - max(pages - document.target_pages, 0) * 10), 1),
        keyword_coverage=round(ratio, 3),
        estimated_pages=pages,
        warnings=warnings,
    )


def estimate_pages(document: ResumeDocument) -> int:
    characters = len(_resume_text(document))
    bullets = sum(
        len(item.bullets)
        for group in (document.projects, document.competitions, document.internships)
        for item in group
    ) + sum(len(item.bullets) for item in document.education)
    units = characters / 2200 + bullets / 18
    return max(1, min(10, round(units + 0.49)))


def _resume_text(document: ResumeDocument) -> str:
    values = [
        document.name,
        document.target_title,
        document.summary,
    ]
    values.extend(document.skills)
    for group in (document.projects, document.competitions, document.internships):
        for item in group:
            values.extend([item.name, item.organization, item.role, item.period, item.summary])
            values.extend(bullet.content for bullet in item.bullets)
    for item in document.education:
        values.extend([item.institution, item.degree, item.major, item.period])
        values.extend(bullet.content for bullet in item.bullets)
    return "\n".join(values)
