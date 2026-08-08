import re
from profile.models import ProfileFact

from matching.models import (
    CopyUnitUpdate,
    CopyViolation,
    JDAnalysis,
    JDMatchResult,
    iter_copy_units,
)

MIN_JD_CHARS = 20
MAX_JD_CHARS = 30_000
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?%?")


def validate_jd_text(jd_text: str) -> str:
    normalized = jd_text.strip()
    if len(normalized) < MIN_JD_CHARS:
        raise ValueError(f"JD 内容至少需要 {MIN_JD_CHARS} 个字符。")
    if len(normalized) > MAX_JD_CHARS:
        raise ValueError(f"JD 内容不能超过 {MAX_JD_CHARS} 个字符。")
    return normalized


def apply_draft_updates(
    current: JDMatchResult,
    updates: list[CopyUnitUpdate],
    facts: list[ProfileFact],
    analysis: JDAnalysis,
) -> tuple[JDMatchResult, list[CopyViolation]]:
    updated = current.model_copy(deep=True)
    unit_map = {unit.id: unit for _, _, unit in iter_copy_units(updated)}
    fact_map = {fact.id: fact for fact in facts}
    violations: list[CopyViolation] = []
    seen: set[str] = set()
    for item in updates:
        if item.unit_id in seen:
            violations.append(CopyViolation(unit_id=item.unit_id, message="同一文案单元重复提交。"))
            continue
        seen.add(item.unit_id)
        unit = unit_map.get(item.unit_id)
        if unit is None:
            violations.append(CopyViolation(unit_id=item.unit_id, message="文案单元不存在。"))
            continue
        source_facts = [
            fact_map[fact_id] for fact_id in unit.source_fact_ids if fact_id in fact_map
        ]
        if not source_facts:
            violations.append(
                CopyViolation(unit_id=item.unit_id, message="文案没有可验证的来源事实。")
            )
            continue
        source_text = " ".join(fact.statement for fact in source_facts).casefold()
        content = item.content.strip()
        unsupported_numbers = sorted(
            set(NUMBER_PATTERN.findall(content)) - set(NUMBER_PATTERN.findall(source_text))
        )
        if unsupported_numbers:
            violations.append(
                CopyViolation(
                    unit_id=item.unit_id,
                    message="编辑内容包含来源事实中不存在的数字。",
                    details={"numbers": unsupported_numbers},
                )
            )
        unsupported_skills = [
            skill
            for skill in [*analysis.required_skills, *analysis.preferred_skills]
            if skill.casefold() in content.casefold() and skill.casefold() not in source_text
        ]
        if unsupported_skills:
            violations.append(
                CopyViolation(
                    unit_id=item.unit_id,
                    message="编辑内容加入了来源事实未支持的岗位技能。",
                    details={"skills": sorted(set(unsupported_skills))},
                )
            )
        unit.content = content
        unit.user_edited = True
    return updated, violations
