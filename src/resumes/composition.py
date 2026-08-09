from career.models import CareerSettings
from job_search.models import JobPosting
from matching.models import JDMatchResult
from resumes.models import (
    ApplicationMaterials,
    ResumeBullet,
    ResumeDocument,
    ResumeEducation,
    ResumeExperience,
    ResumeTemplate,
)


def compose_resume(
    result: JDMatchResult,
    job: JobPosting,
    settings: CareerSettings,
    template: ResumeTemplate,
) -> ResumeDocument:
    return ResumeDocument(
        name=settings.display_name,
        target_title=job.title or result.jd_analysis.role_title,
        contact_line=_contact_line(settings),
        summary=result.personal_introduction.overview.content,
        skills=_dynamic_skills(result),
        projects=[_experience(item) for item in result.project_experiences.entries[:3]],
        competitions=[_experience(item) for item in result.competition_experiences.entries[:2]],
        internships=[_experience(item) for item in result.internship_experiences.entries[:2]],
        education=[_education(item) for item in result.education_history.entries],
        application_materials=_application_materials(result, job, settings),
        section_statuses={
            "personal_introduction": result.personal_introduction.status,
            "project_experiences": result.project_experiences.status,
            "competition_experiences": result.competition_experiences.status,
            "internship_experiences": result.internship_experiences.status,
            "education_history": result.education_history.status,
        },
        source_match_id=result.match_id,
        source_match_version=result.version,
        template=template,
        target_pages=1,
    )


def _experience(item) -> ResumeExperience:
    return ResumeExperience(
        name=item.name,
        organization=item.organization or "",
        role=item.role or "",
        period=item.period or "",
        technologies=item.technologies,
        summary=item.tailored_summary.content,
        bullets=[
            ResumeBullet(
                content=bullet.content,
                source_fact_ids=bullet.source_fact_ids,
                evidence_refs=bullet.evidence_refs,
            )
            for bullet in item.bullets[:4]
        ],
    )


def _education(item) -> ResumeEducation:
    return ResumeEducation(
        institution=item.institution,
        degree=item.degree or "",
        major=item.major or "",
        period=item.period or "",
        bullets=[
            ResumeBullet(
                content=bullet.content,
                source_fact_ids=bullet.source_fact_ids,
                evidence_refs=bullet.evidence_refs,
            )
            for bullet in item.bullets[:4]
        ],
    )


def _contact_line(settings: CareerSettings) -> str:
    values = [
        settings.phone,
        settings.email,
        settings.city,
        settings.github_url,
        settings.linkedin_url,
        settings.portfolio_url,
    ]
    return " | ".join(value for value in values if value)


def _dynamic_skills(result: JDMatchResult) -> list[str]:
    matched = {item.casefold(): item for item in result.keyword_coverage.matched}
    output: list[str] = []
    for dimension in sorted(
        result.jd_analysis.capability_dimensions,
        key=lambda item: item.weight,
        reverse=True,
    ):
        supported = [
            matched[keyword.casefold()]
            for keyword in dimension.keywords
            if keyword.casefold() in matched
        ]
        if supported:
            output.append(f"{dimension.name}：{'、'.join(dict.fromkeys(supported))}")
    return output or result.keyword_coverage.matched


def _application_materials(
    result: JDMatchResult,
    job: JobPosting,
    settings: CareerSettings,
) -> ApplicationMaterials:
    name = settings.display_name or "候选人"
    summary = result.personal_introduction.overview.content
    project_names = [item.name for item in result.project_experiences.entries[:2]]
    evidence_sentence = (
        f"相关经历包括{'、'.join(project_names)}。"
        if project_names
        else "相关能力均来自已审核画像材料。"
    )
    cover_letter = (
        f"尊敬的 {job.company} 招聘团队：\n\n"
        f"您好，我是{name}，希望申请{job.title}岗位。{summary}"
        f"{evidence_sentence}\n\n"
        "感谢审阅，期待进一步交流岗位目标与具体贡献。"
    )
    greeting = f"您好，我关注到贵司的{job.title}岗位。{summary[:80]}希望有机会进一步沟通。"
    return ApplicationMaterials(
        cover_letter=cover_letter,
        boss_greeting=greeting,
        form_answers={
            "self_evaluation": summary,
            "why_company": "该岗位方向与我的目标岗位及已有能力素材具有较高关联。",
            "why_fit": "；".join(result.strengths[:3]) or summary,
        },
    )
