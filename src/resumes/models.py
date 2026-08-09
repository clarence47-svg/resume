from datetime import UTC, datetime
from enum import StrEnum
from profile.models import EvidenceRef, SectionStatus
from uuid import uuid4

from pydantic import BaseModel, Field


class ResumeTemplate(StrEnum):
    ATS_STANDARD = "ats_standard"
    STUDENT_COMPACT = "student_compact"
    TECHNICAL = "technical"


class ResumeBullet(BaseModel):
    content: str
    source_fact_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ResumeExperience(BaseModel):
    name: str
    organization: str = ""
    role: str = ""
    period: str = ""
    technologies: list[str] = Field(default_factory=list)
    summary: str = ""
    bullets: list[ResumeBullet] = Field(default_factory=list)


class ResumeEducation(BaseModel):
    institution: str
    degree: str = ""
    major: str = ""
    period: str = ""
    bullets: list[ResumeBullet] = Field(default_factory=list)


class ResumeAudit(BaseModel):
    passed: bool = True
    ats_score: float = Field(default=0, ge=0, le=100)
    keyword_coverage: float = Field(default=0, ge=0, le=1)
    estimated_pages: int = Field(default=1, ge=1, le=10)
    warnings: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)


class ApplicationMaterials(BaseModel):
    cover_letter: str = ""
    boss_greeting: str = ""
    form_answers: dict[str, str] = Field(default_factory=dict)


class ResumeDocument(BaseModel):
    name: str = ""
    target_title: str = ""
    contact_line: str = ""
    summary: str = ""
    professional_overview: str = ""
    skills: list[str] = Field(default_factory=list)
    projects: list[ResumeExperience] = Field(default_factory=list)
    competitions: list[ResumeExperience] = Field(default_factory=list)
    internships: list[ResumeExperience] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    application_materials: ApplicationMaterials = Field(default_factory=ApplicationMaterials)
    section_statuses: dict[str, SectionStatus] = Field(default_factory=dict)
    source_match_id: str
    source_match_version: int
    template: ResumeTemplate = ResumeTemplate.ATS_STANDARD
    target_pages: int = Field(default=1, ge=1, le=2)
    audit: ResumeAudit = Field(default_factory=ResumeAudit)


class ResumeVersion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    profile_task_id: str
    match_id: str
    match_version: int
    version: int = Field(default=1, ge=1)
    template: ResumeTemplate = ResumeTemplate.ATS_STANDARD
    document: ResumeDocument
    markdown_path: str = ""
    html_path: str = ""
    docx_path: str = ""
    pdf_path: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
