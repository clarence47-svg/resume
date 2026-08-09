from pathlib import Path
from profile.models import FactCategory, ProfileFact
from profile.section_documents import SECTION_FILENAMES, SECTION_TITLES

from matching.models import JDAnalysis, JDMatchResult, TailoredTextSection


def render_selected_section_documents(
    facts: list[ProfileFact],
    selected_entries: dict[str, list[dict]],
    selected_fact_ids: dict[str, list[str]],
    analysis: JDAnalysis,
) -> dict[str, str]:
    fact_map = {fact.id: fact for fact in facts}
    documents: dict[str, str] = {}
    for category in FactCategory:
        section_name = category.value
        lines = [
            f"# 画像母版_{SECTION_TITLES[section_name]}",
            "",
            (
                f"> 当前岗位：{analysis.role_title}。本文档仅包含从完整素材池中筛选出的"
                "高相关记录，最终页面内容必须基于这些记录生成。"
            ),
            (
                "> 同一经历的不同表达互相补充；同口径数字存在多个候选时，"
                "可优先采用更有利且在素材中明确出现的数值。"
            ),
            "",
        ]
        if category in {FactCategory.PERSONAL, FactCategory.PROFESSIONAL}:
            lines.extend(_fact_lines(selected_fact_ids.get(section_name, []), fact_map))
        else:
            entries = selected_entries.get(section_name, [])
            if entries:
                for selected in entries:
                    lines.extend(_entry_lines(selected, fact_map))
            else:
                lines.append("- 当前岗位未筛选到该维度的相关素材。")
        documents[section_name] = "\n".join(lines).strip() + "\n"
    return documents


def write_selected_section_documents(
    documents: dict[str, str], target_dir: Path
) -> dict[str, Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for section_name, content in documents.items():
        path = target_dir / SECTION_FILENAMES[section_name]
        path.write_text(content, encoding="utf-8")
        paths[section_name] = path
    return paths


def render_result_section_documents(
    result: JDMatchResult, facts: list[ProfileFact]
) -> dict[str, str]:
    selected_entries: dict[str, list[dict]] = {}
    selected_fact_ids: dict[str, list[str]] = {}
    for category in FactCategory:
        section = getattr(result, category.value)
        if isinstance(section, TailoredTextSection):
            selected_fact_ids[category.value] = list(
                dict.fromkeys(
                    fact_id
                    for unit in [section.overview, *section.bullets]
                    for fact_id in unit.source_fact_ids
                )
            )
            continue
        entries = []
        for entry in section.entries:
            units = [entry.tailored_summary, *entry.bullets]
            fact_ids = list(
                dict.fromkeys(fact_id for unit in units for fact_id in unit.source_fact_ids)
            )
            entry_data = entry.model_dump(mode="json")
            entry_data["summary"] = entry.tailored_summary.content
            entry_data["source_fact_ids"] = fact_ids
            entries.append(
                {
                    "entry": entry_data,
                    "fact_ids": fact_ids,
                    "relevance_score": entry.relevance_score,
                }
            )
        selected_entries[category.value] = entries
    return render_selected_section_documents(
        facts,
        selected_entries,
        selected_fact_ids,
        result.jd_analysis,
    )


def _entry_lines(selected: dict, fact_map: dict[str, ProfileFact]) -> list[str]:
    entry = selected["entry"]
    name = entry.get("name") or entry.get("institution") or "经历"
    lines = [
        f"## {name}",
        "",
        f"- 匹配相关度：{float(selected.get('relevance_score', 0)):.1f}",
    ]
    for label, key in (
        ("单位/组织", "organization"),
        ("时间", "period"),
        ("角色", "role"),
        ("学历", "degree"),
        ("专业", "major"),
    ):
        if entry.get(key):
            lines.append(f"- {label}：{entry[key]}")
    technologies = entry.get("technologies") or []
    if technologies:
        lines.append(f"- 技术：{'、'.join(technologies)}")
    lines.extend(["", "### 可选素材", ""])
    lines.extend(_fact_lines(selected.get("fact_ids", []), fact_map))
    lines.append("")
    return lines


def _fact_lines(fact_ids: list[str], fact_map: dict[str, ProfileFact]) -> list[str]:
    lines = []
    for fact_id in fact_ids:
        fact = fact_map.get(fact_id)
        if fact is None:
            continue
        sources = "、".join(
            dict.fromkeys(
                f"{item.file_name}#{item.page or item.slide or item.paragraph}"
                if item.page or item.slide or item.paragraph
                else item.file_name
                for item in fact.evidence_refs
            )
        )
        lines.append(f"- [fact_id:{fact.id}] {fact.statement}（来源：{sources or '画像素材'}）")
    return lines or ["- 当前岗位未筛选到该维度的相关素材。"]
