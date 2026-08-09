from profile.models import EvidenceRef, FactCategory, ProfileFact, SectionStatus

from matching.models import (
    CopyUnitUpdate,
    JDAnalysis,
    JDMatchResult,
    TailoredCopyUnit,
    TailoredEducationSection,
    TailoredExperienceSection,
    TailoredTextSection,
)
from matching.validation import apply_draft_updates


def _result(unit: TailoredCopyUnit) -> JDMatchResult:
    empty = TailoredCopyUnit(content="资料未提供足够证据。")
    return JDMatchResult(
        match_id="match",
        profile_task_id="profile",
        jd_analysis=JDAnalysis(
            required_skills=["Python"], preferred_skills=["Docker"], keywords=["Python", "Docker"]
        ),
        personal_introduction=TailoredTextSection(status=SectionStatus.COMPLETE, overview=unit),
        project_experiences=TailoredExperienceSection(overview=empty),
        competition_experiences=TailoredExperienceSection(overview=empty),
        internship_experiences=TailoredExperienceSection(overview=empty),
        education_history=TailoredEducationSection(overview=empty),
    )


def test_edit_rejects_unsupported_numbers_and_skills() -> None:
    evidence = EvidenceRef(
        span_id="span", document_id="doc", file_name="resume.md", quote="使用 Python 开发系统"
    )
    fact = ProfileFact(
        id="fact",
        category=FactCategory.CAPABILITY,
        statement="使用 Python 开发系统",
        evidence_refs=[evidence],
    )
    unit = TailoredCopyUnit(
        id="unit",
        content=fact.statement,
        source_fact_ids=[fact.id],
        evidence_refs=[evidence],
    )
    _, violations = apply_draft_updates(
        _result(unit),
        [CopyUnitUpdate(unit_id="unit", content="使用 Python 和 Docker 开发 3 个系统")],
        [fact],
        _result(unit).jd_analysis,
    )
    assert len(violations) == 2


def test_edit_preserves_evidence_metadata() -> None:
    evidence = EvidenceRef(
        span_id="span", document_id="doc", file_name="resume.md", quote="使用 Python 开发系统"
    )
    fact = ProfileFact(
        id="fact",
        category=FactCategory.CAPABILITY,
        statement="使用 Python 开发系统",
        evidence_refs=[evidence],
    )
    unit = TailoredCopyUnit(
        id="unit",
        content=fact.statement,
        source_fact_ids=[fact.id],
        evidence_refs=[evidence],
    )
    updated, violations = apply_draft_updates(
        _result(unit),
        [CopyUnitUpdate(unit_id="unit", content="负责 Python 系统开发与交付")],
        [fact],
        _result(unit).jd_analysis,
    )
    assert not violations
    assert updated.personal_introduction.overview.source_fact_ids == ["fact"]
    assert updated.personal_introduction.overview.user_edited is True
