from datetime import UTC, datetime
from enum import StrEnum
from profile.models import EvidenceRef, FactCategory, SectionStatus
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RequirementPriority(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    CONTEXT = "context"


class SupportLevel(StrEnum):
    EXACT = "exact"
    PARTIAL = "partial"
    NONE = "none"


class RequirementOrigin(StrEnum):
    JD = "jd"
    MARKET_RESEARCH = "market_research"


class ResearchStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class MatchVersionSource(StrEnum):
    GENERATED = "generated"
    USER_EDIT = "user_edit"
    REGENERATED = "regenerated"
    RESTORED = "restored"


class JDRequirement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    category: FactCategory
    priority: RequirementPriority
    weight: float = Field(gt=0)
    keywords: list[str] = Field(default_factory=list)
    origin: RequirementOrigin = RequirementOrigin.JD
    source_urls: list[str] = Field(default_factory=list)


class JobResearchSource(BaseModel):
    title: str
    url: str
    snippet: str = ""
    query: str = ""


class JobResearch(BaseModel):
    role_title: str = "目标岗位"
    role_summary: str = "未获得岗位市场研究信息。"
    core_capabilities: list[str] = Field(default_factory=list)
    typical_responsibilities: list[str] = Field(default_factory=list)
    common_tools: list[str] = Field(default_factory=list)
    market_keywords: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    sources: list[JobResearchSource] = Field(default_factory=list)
    status: ResearchStatus = ResearchStatus.UNAVAILABLE


class JDAnalysis(BaseModel):
    role_title: str = "目标岗位"
    seniority: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    requirements: list[JDRequirement] = Field(default_factory=list)


class RequirementMatch(BaseModel):
    requirement_id: str
    support_level: SupportLevel
    source_fact_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    rationale: str = ""


class KeywordCoverage(BaseModel):
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    ratio: float = Field(default=0, ge=0, le=1)


class DimensionMatch(BaseModel):
    score: float = Field(default=0, ge=0, le=100)
    matched_requirement_ids: list[str] = Field(default_factory=list)
    missing_requirement_ids: list[str] = Field(default_factory=list)


class TailoredCopyUnit(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    source_fact_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    matched_requirement_ids: list[str] = Field(default_factory=list)
    relevance_score: float = Field(default=0, ge=0, le=100)
    user_edited: bool = False


class TailoredTextSection(BaseModel):
    status: SectionStatus = SectionStatus.INSUFFICIENT_EVIDENCE
    overview: TailoredCopyUnit
    bullets: list[TailoredCopyUnit] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class TailoredExperienceEntry(BaseModel):
    name: str
    organization: str | None = None
    period: str | None = None
    role: str | None = None
    technologies: list[str] = Field(default_factory=list)
    tailored_summary: TailoredCopyUnit
    bullets: list[TailoredCopyUnit] = Field(default_factory=list)
    selected_reason: str = ""
    relevance_score: float = Field(default=0, ge=0, le=100)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class TailoredExperienceSection(BaseModel):
    status: SectionStatus = SectionStatus.INSUFFICIENT_EVIDENCE
    overview: TailoredCopyUnit
    entries: list[TailoredExperienceEntry] = Field(default_factory=list)


class TailoredEducationEntry(BaseModel):
    institution: str
    degree: str | None = None
    major: str | None = None
    period: str | None = None
    tailored_summary: TailoredCopyUnit
    bullets: list[TailoredCopyUnit] = Field(default_factory=list)
    relevance_score: float = Field(default=0, ge=0, le=100)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class TailoredEducationSection(BaseModel):
    status: SectionStatus = SectionStatus.INSUFFICIENT_EVIDENCE
    overview: TailoredCopyUnit
    entries: list[TailoredEducationEntry] = Field(default_factory=list)


class MatchAudit(BaseModel):
    passed: bool = True
    evidence_coverage: float = Field(default=1, ge=0, le=1)
    unsupported_claims: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    sensitive_inference_detected: bool = False


class JDMatchCopy(BaseModel):
    personal_introduction: TailoredTextSection
    professional_introduction: TailoredTextSection
    project_experiences: TailoredExperienceSection
    competition_experiences: TailoredExperienceSection
    internship_experiences: TailoredExperienceSection
    education_history: TailoredEducationSection


class JDMatchResult(JDMatchCopy):
    match_id: str
    profile_task_id: str
    jd_analysis: JDAnalysis
    job_research: JobResearch = Field(default_factory=JobResearch)
    requirement_matches: list[RequirementMatch] = Field(default_factory=list)
    overall_score: float = Field(default=0, ge=0, le=100)
    dimension_scores: dict[FactCategory, DimensionMatch] = Field(default_factory=dict)
    keyword_coverage: KeywordCoverage = Field(default_factory=KeywordCoverage)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    section_documents: dict[str, str] = Field(default_factory=dict)
    audit: MatchAudit = Field(default_factory=MatchAudit)
    model: str = ""
    version: int = Field(default=1, ge=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def copy_bundle(self) -> JDMatchCopy:
        return JDMatchCopy.model_validate(
            {
                field: getattr(self, field).model_dump(mode="json")
                for field in JDMatchCopy.model_fields
            }
        )


class CopyUnitUpdate(BaseModel):
    unit_id: str
    content: str = Field(min_length=1, max_length=1200)


class CopyViolation(BaseModel):
    unit_id: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


def iter_copy_units(result: JDMatchCopy | JDMatchResult):
    for section_name in (
        "personal_introduction",
        "professional_introduction",
        "project_experiences",
        "competition_experiences",
        "internship_experiences",
        "education_history",
    ):
        section = getattr(result, section_name)
        yield section_name, "overview", section.overview
        if isinstance(section, TailoredTextSection):
            for index, unit in enumerate(section.bullets):
                yield section_name, f"bullet:{index}", unit
        else:
            for entry_index, entry in enumerate(section.entries):
                yield section_name, f"entry:{entry_index}:summary", entry.tailored_summary
                for bullet_index, unit in enumerate(entry.bullets):
                    yield section_name, f"entry:{entry_index}:bullet:{bullet_index}", unit
