from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class BasisType(StrEnum):
    FACT = "fact"
    INFERENCE = "inference"


class FactCategory(StrEnum):
    PERSONAL = "personal_introduction"
    PROFESSIONAL = "professional_introduction"
    PROJECT = "project_experiences"
    COMPETITION = "competition_experiences"
    INTERNSHIP = "internship_experiences"
    EDUCATION = "education_history"


class FactStatus(StrEnum):
    EXTRACTED = "extracted"
    CONFIRMED = "confirmed"
    EDITED = "edited"
    REJECTED = "rejected"


class SectionStatus(StrEnum):
    COMPLETE = "complete"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceRef(BaseModel):
    span_id: str
    document_id: str
    file_name: str
    quote: str
    page: int | None = None
    slide: int | None = None
    paragraph: int | None = None
    section: str | None = None


class ProfileFact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    category: FactCategory
    statement: str
    basis_type: BasisType = BasisType.FACT
    confidence: float = Field(default=0.8, ge=0, le=1)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    rationale: str = ""
    status: FactStatus = FactStatus.EXTRACTED
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def material_group_id(self) -> str | None:
        value = self.metadata.get("material_group_id")
        return str(value) if value else None


class ConflictRecord(BaseModel):
    field: str
    description: str
    fact_ids: list[str]
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ProfileClaim(BaseModel):
    content: str
    basis_type: BasisType
    confidence: float = Field(ge=0, le=1)
    evidence_refs: list[EvidenceRef]
    rationale: str = ""


class PersonalIntroduction(BaseModel):
    status: SectionStatus = SectionStatus.INSUFFICIENT_EVIDENCE
    overview: str = "未从资料中获得足够信息。"
    core_strengths: list[ProfileClaim] = Field(default_factory=list)
    work_characteristics: list[ProfileClaim] = Field(default_factory=list)
    career_direction: list[ProfileClaim] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ProfessionalIntroduction(BaseModel):
    status: SectionStatus = SectionStatus.INSUFFICIENT_EVIDENCE
    overview: str = "未从资料中获得足够信息。"
    knowledge_domains: list[ProfileClaim] = Field(default_factory=list)
    skills: list[ProfileClaim] = Field(default_factory=list)
    tools_and_technologies: list[str] = Field(default_factory=list)
    research_interests: list[ProfileClaim] = Field(default_factory=list)
    certifications: list[ProfileClaim] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    name: str
    organization: str | None = None
    period: str | None = None
    role: str | None = None
    summary: str
    details: list[ProfileClaim] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    outcomes: list[ProfileClaim] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    source_fact_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0, le=1)
    attributes: dict[str, str] = Field(default_factory=dict)


class ExperienceSection(BaseModel):
    status: SectionStatus = SectionStatus.INSUFFICIENT_EVIDENCE
    overview: str = "未从资料中识别到相关经历。"
    entries: list[ExperienceEntry] = Field(default_factory=list)


class EducationEntry(BaseModel):
    institution: str
    degree: str | None = None
    major: str | None = None
    period: str | None = None
    overview: str
    courses: list[str] = Field(default_factory=list)
    honors: list[ProfileClaim] = Field(default_factory=list)
    campus_experiences: list[ProfileClaim] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    source_fact_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0, le=1)


class EducationHistory(BaseModel):
    status: SectionStatus = SectionStatus.INSUFFICIENT_EVIDENCE
    overview: str = "未从资料中识别到学校履历。"
    entries: list[EducationEntry] = Field(default_factory=list)


class ProfileAudit(BaseModel):
    passed: bool = True
    citation_coverage: float = Field(default=1, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    sensitive_inference_detected: bool = False


class ProfileResult(BaseModel):
    task_id: str
    personal_introduction: PersonalIntroduction = Field(default_factory=PersonalIntroduction)
    professional_introduction: ProfessionalIntroduction = Field(
        default_factory=ProfessionalIntroduction
    )
    project_experiences: ExperienceSection = Field(default_factory=ExperienceSection)
    competition_experiences: ExperienceSection = Field(default_factory=ExperienceSection)
    internship_experiences: ExperienceSection = Field(default_factory=ExperienceSection)
    education_history: EducationHistory = Field(default_factory=EducationHistory)
    conflicts: list[ConflictRecord] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    audit: ProfileAudit = Field(default_factory=ProfileAudit)
    model: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
