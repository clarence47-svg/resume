import re
from difflib import SequenceMatcher
from profile.models import ConflictRecord, ProfileFact


def merge_facts(state: dict) -> dict:
    candidates: list[ProfileFact] = [
        ProfileFact.model_validate(item) for item in state.get("facts", [])
    ]
    for batch in state.get("extracted_fact_batches", []):
        candidates.extend(ProfileFact.model_validate(item) for item in batch)

    merged: dict[tuple[str, str], ProfileFact] = {}
    for fact in candidates:
        key = (fact.category.value, _normalize(fact.statement))
        existing = merged.get(key)
        if existing is None:
            merged[key] = fact
            continue
        evidence = {item.span_id: item for item in existing.evidence_refs}
        evidence.update({item.span_id: item for item in fact.evidence_refs})
        merged[key] = existing.model_copy(
            update={
                "confidence": max(existing.confidence, fact.confidence),
                "evidence_refs": list(evidence.values()),
            }
        )

    facts = list(merged.values())
    conflicts = _detect_conflicts(facts)
    return {
        "facts": [fact.model_dump(mode="json") for fact in facts],
        "conflicts": [conflict.model_dump(mode="json") for conflict in conflicts],
    }


def _normalize(text: str) -> str:
    return re.sub(r"\W+", "", text).lower()


def _detect_conflicts(facts: list[ProfileFact]) -> list[ConflictRecord]:
    conflicts: list[ConflictRecord] = []
    for index, left in enumerate(facts):
        left_numbers = set(re.findall(r"\d+(?:\.\d+)?", left.statement))
        if not left_numbers:
            continue
        for right in facts[index + 1 :]:
            if left.category != right.category:
                continue
            right_numbers = set(re.findall(r"\d+(?:\.\d+)?", right.statement))
            if not right_numbers or left_numbers == right_numbers:
                continue
            similarity = SequenceMatcher(
                None, _normalize(left.statement), _normalize(right.statement)
            ).ratio()
            if similarity < 0.45:
                continue
            evidence = {item.span_id: item for item in left.evidence_refs + right.evidence_refs}
            conflicts.append(
                ConflictRecord(
                    field=left.category.value,
                    description="相似材料中出现不同数字或日期，需要用户核对。",
                    fact_ids=[left.id, right.id],
                    evidence_refs=list(evidence.values()),
                )
            )
    return conflicts
