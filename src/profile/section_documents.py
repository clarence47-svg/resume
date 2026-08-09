import re
from pathlib import Path
from profile.models import (
    EducationHistory,
    EvidenceRef,
    ExperienceSection,
    FactCategory,
    FactStatus,
    PersonalIntroduction,
    ProfileClaim,
    ProfileFact,
    ProfileResult,
)

SECTION_TITLES = {
    FactCategory.PERSONAL.value: "个人信息",
    FactCategory.PROJECT.value: "项目经历",
    FactCategory.COMPETITION.value: "比赛经历",
    FactCategory.INTERNSHIP.value: "实习经历",
    FactCategory.EDUCATION.value: "学校履历",
}
SECTION_FILENAMES = {key: f"画像母版_{title}.md" for key, title in SECTION_TITLES.items()}
MASTER_FILENAME = "profile_master.md"
SECTION_SNAPSHOT_KEY = "_section_documents"
FACT_ID_PATTERN = re.compile(r"\[fact_id:([^\]]+)\]")


def render_profile_section_documents(
    result: ProfileResult, facts: list[ProfileFact]
) -> dict[str, str]:
    sections = {
        FactCategory.PERSONAL.value: _personal(result.personal_introduction),
        FactCategory.PROJECT.value: _experience(result.project_experiences),
        FactCategory.COMPETITION.value: _experience(result.competition_experiences),
        FactCategory.INTERNSHIP.value: _experience(result.internship_experiences),
        FactCategory.EDUCATION.value: _education(result.education_history),
    }
    output: dict[str, str] = {}
    for section_name, body in sections.items():
        references = _section_span_ids(getattr(result, section_name))
        related = [
            fact
            for fact in facts
            if fact.status != FactStatus.REJECTED
            and (
                fact.category.value == section_name
                or references.intersection(item.span_id for item in fact.evidence_refs)
            )
        ]
        lines = [
            f"# {SECTION_TITLES[section_name]}",
            "",
            (
                "> 本文档是该维度的完整经历素材池。同一经历的不同名称、职责、"
                "技术重点、成果和数字表达会作为互补素材保留。"
            ),
            "",
            *body,
            "## 可引用事实",
            "",
        ]
        if related:
            lines.extend(_fact_line(fact) for fact in related)
        else:
            lines.append("- 资料中未识别到可引用事实。")
        output[section_name] = "\n".join(lines).strip() + "\n"
    return output


def write_profile_section_documents(
    result: ProfileResult, facts: list[ProfileFact], target_dir: Path
) -> dict[str, Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    documents = render_profile_section_documents(result, facts)
    paths = {}
    for section_name, content in documents.items():
        path = target_dir / SECTION_FILENAMES[section_name]
        path.write_text(content, encoding="utf-8")
        paths[section_name] = path
    master_lines = ["# 用户画像完整素材母版", ""]
    for section_name in SECTION_TITLES:
        master_lines.extend([documents[section_name].strip(), ""])
    (target_dir / MASTER_FILENAME).write_text(
        "\n".join(master_lines).strip() + "\n", encoding="utf-8"
    )
    return paths


def extract_document_fact_ids(content: str) -> set[str]:
    return set(FACT_ID_PATTERN.findall(content))


def _personal(section: PersonalIntroduction) -> list[str]:
    lines = [f"状态：{section.status.value}", "", section.overview, ""]
    for item in section.items:
        lines.append(
            f"- {item.label}：{item.value}（置信度 {item.confidence:.0%}；"
            f"证据：{_evidence(item.evidence_refs)}；事实：{'、'.join(item.source_fact_ids)}）"
        )
    if section.items:
        lines.append("")
    return lines


def _experience(section: ExperienceSection) -> list[str]:
    lines = [f"状态：{section.status.value}", "", section.overview, ""]
    for entry in section.entries:
        lines.extend(
            [
                f"## {entry.name}",
                "",
                entry.summary,
                "",
                f"- 单位/组织：{entry.organization or '资料未提供'}",
                f"- 时间：{entry.period or '资料未提供'}",
                f"- 角色：{entry.role or '资料未提供'}",
                f"- 技术：{'、'.join(entry.technologies) or '资料未提供'}",
                f"- 证据：{_evidence(entry.evidence_refs)}",
                f"- 素材事实：{'、'.join(entry.source_fact_ids) or '资料未提供'}",
                "",
            ]
        )
        lines.extend(_claims("行动与成果", entry.details + entry.outcomes))
    return lines


def _education(section: EducationHistory) -> list[str]:
    lines = [f"状态：{section.status.value}", "", section.overview, ""]
    for entry in section.entries:
        lines.extend(
            [
                f"## {entry.institution}",
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
                f"- 证据：{_evidence(entry.evidence_refs)}",
                f"- 素材事实：{'、'.join(entry.source_fact_ids) or '资料未提供'}",
                "",
            ]
        )
        lines.extend(_claims("荣誉与校园经历", entry.honors + entry.campus_experiences))
    return lines


def _claims(title: str, claims: list[ProfileClaim]) -> list[str]:
    if not claims:
        return []
    lines = [f"## {title}", ""]
    for claim in claims:
        lines.append(
            f"- {claim.content}（{claim.basis_type.value}，置信度 {claim.confidence:.0%}；"
            f"证据：{_evidence(claim.evidence_refs)}）"
        )
    lines.append("")
    return lines


def _fact_line(fact: ProfileFact) -> str:
    return (
        f"- [fact_id:{fact.id}] {fact.statement}（{fact.basis_type.value}，"
        f"置信度 {fact.confidence:.0%}；证据：{_evidence(fact.evidence_refs)}）"
    )


def _evidence(items: list[EvidenceRef]) -> str:
    output = []
    for item in items:
        locator = item.page or item.slide or item.paragraph
        output.append(f"{item.file_name}#{locator}" if locator else item.file_name)
    return "、".join(dict.fromkeys(output)) or "无"


def _section_span_ids(section) -> set[str]:
    output: set[str] = set()
    if isinstance(section, PersonalIntroduction):
        output.update(ref.span_id for item in section.items for ref in item.evidence_refs)
    elif isinstance(section, ExperienceSection):
        for entry in section.entries:
            output.update(ref.span_id for ref in entry.evidence_refs)
            output.update(
                ref.span_id
                for claim in entry.details + entry.outcomes
                for ref in claim.evidence_refs
            )
    elif isinstance(section, EducationHistory):
        for entry in section.entries:
            output.update(ref.span_id for ref in entry.evidence_refs)
            output.update(
                ref.span_id
                for claim in entry.honors + entry.campus_experiences
                for ref in claim.evidence_refs
            )
    return output
