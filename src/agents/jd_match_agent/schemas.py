from profile.models import FactCategory

from pydantic import BaseModel, Field

from matching.models import RequirementPriority, SupportLevel


class JDRequirementDraft(BaseModel):
    text: str
    category: FactCategory
    priority: RequirementPriority
    keywords: list[str] = Field(default_factory=list)


class CapabilityDimensionDraft(BaseModel):
    name: str
    description: str = ""
    keywords: list[str] = Field(default_factory=list)


class JDAnalysisDraft(BaseModel):
    role_title: str = "目标岗位"
    seniority: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    requirements: list[JDRequirementDraft] = Field(default_factory=list)
    capability_dimensions: list[CapabilityDimensionDraft] = Field(default_factory=list)


class JobResearchDraft(BaseModel):
    role_summary: str
    core_capabilities: list[str] = Field(default_factory=list)
    typical_responsibilities: list[str] = Field(default_factory=list)
    common_tools: list[str] = Field(default_factory=list)
    market_keywords: list[str] = Field(default_factory=list)


class RequirementMatchDraft(BaseModel):
    requirement_id: str
    support_level: SupportLevel
    source_fact_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    rationale: str = ""


class RequirementMatchResponse(BaseModel):
    matches: list[RequirementMatchDraft] = Field(default_factory=list)


class CopyUnitDraft(BaseModel):
    content: str
    source_fact_ids: list[str] = Field(default_factory=list)
    matched_requirement_ids: list[str] = Field(default_factory=list)


class TailoredEntryDraft(BaseModel):
    source_name: str
    summary: CopyUnitDraft
    bullets: list[CopyUnitDraft] = Field(default_factory=list)
    selected_reason: str = ""


class TailoredSectionDraft(BaseModel):
    overview: CopyUnitDraft
    bullets: list[CopyUnitDraft] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    entries: list[TailoredEntryDraft] = Field(default_factory=list)
