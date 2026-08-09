from pathlib import Path
from profile.models import EvidenceRef, ExperienceSection, ProfileClaim, ProfileResult


def export_markdown(result: ProfileResult, path: Path) -> Path:
    lines = ["# 用户五维画像", "", f"生成时间：{result.generated_at.isoformat()}", ""]
    lines.extend(_personal(result))
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
                f"- 平均成绩：{entry.average_score or '资料未提供'}",
                f"- 排名：{entry.ranking or '资料未提供'}",
                f"- 综合评价：{entry.evaluation or '资料未提供'}",
                f"- 语言成绩：{'、'.join(entry.language_scores) or '资料未提供'}",
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
    lines = ["## 个人信息", "", section.overview, ""]
    for item in section.items:
        lines.append(
            f"- {item.label}：{item.value}（置信度 {item.confidence:.0%}；"
            f"来源：{_evidence(item.evidence_refs)}）"
        )
    if section.items:
        lines.append("")
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
