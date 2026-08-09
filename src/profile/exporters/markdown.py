from pathlib import Path
from profile.models import EvidenceRef, ExperienceSection, ProfileClaim, ProfileResult


def export_markdown(result: ProfileResult, path: Path) -> Path:
    lines = ["# 用户六维画像", "", f"生成时间：{result.generated_at.isoformat()}", ""]
    lines.extend(_personal(result))
    lines.extend(_professional(result))
    lines.extend(_experience("项目经历", result.project_experiences))
    lines.extend(_experience("比赛经历", result.competition_experiences))
    lines.extend(_experience("实习经历", result.internship_experiences))
    lines.extend(["## 学校履历", "", result.education_history.overview, ""])
    for entry in result.education_history.entries:
        lines.extend(
            [
                f"### {entry.institution}",
                "",
                entry.overview,
                "",
                f"- 学历：{entry.degree or '资料未提供'}",
                f"- 专业：{entry.major or '资料未提供'}",
                f"- 时间：{entry.period or '资料未提供'}",
                f"- 课程：{'、'.join(entry.courses) or '资料未提供'}",
                f"- 来源：{_evidence(entry.evidence_refs)}",
                "",
            ]
        )
        lines.extend(_claims(entry.honors + entry.campus_experiences))
    lines.extend(["## 质量审计", "", f"- 引用覆盖率：{result.audit.citation_coverage:.0%}"])
    lines.extend(f"- {warning}" for warning in result.audit.warnings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path


def _personal(result: ProfileResult) -> list[str]:
    section = result.personal_introduction
    lines = ["## 个人介绍", "", section.overview, ""]
    lines.extend(
        _claims(section.core_strengths + section.work_characteristics + section.career_direction)
    )
    if section.keywords:
        lines.extend([f"关键词：{'、'.join(section.keywords)}", ""])
    return lines


def _professional(result: ProfileResult) -> list[str]:
    section = result.professional_introduction
    lines = ["## 专业介绍", "", section.overview, ""]
    lines.extend(
        _claims(
            section.knowledge_domains
            + section.skills
            + section.research_interests
            + section.certifications
        )
    )
    if section.tools_and_technologies:
        lines.extend([f"工具与技术：{'、'.join(section.tools_and_technologies)}", ""])
    return lines


def _experience(title: str, section: ExperienceSection) -> list[str]:
    lines = [f"## {title}", "", section.overview, ""]
    for entry in section.entries:
        lines.extend(
            [
                f"### {entry.name}",
                "",
                entry.summary,
                "",
                f"- 单位/组织：{entry.organization or '资料未提供'}",
                f"- 时间：{entry.period or '资料未提供'}",
                f"- 角色：{entry.role or '资料未提供'}",
                f"- 技术：{'、'.join(entry.technologies) or '资料未提供'}",
                f"- 来源：{_evidence(entry.evidence_refs)}",
                "",
            ]
        )
        lines.extend(_claims(entry.details + entry.outcomes))
    return lines


def _claims(claims: list[ProfileClaim]) -> list[str]:
    lines: list[str] = []
    for claim in claims:
        label = "事实" if claim.basis_type.value == "fact" else "推断"
        source = _evidence(claim.evidence_refs)
        lines.append(f"- [{label} {claim.confidence:.0%}] {claim.content}；来源：{source}")
    if lines:
        lines.append("")
    return lines


def _evidence(items: list[EvidenceRef]) -> str:
    references = []
    for item in items:
        locator = item.page or item.slide or item.paragraph
        label = f"{item.file_name}#{locator}" if locator else item.file_name
        references.append(label)
    return "、".join(dict.fromkeys(references)) or "无"
