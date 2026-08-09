from profile.models import BasisType, FactCategory
from typing import Any

from pydantic import BaseModel, Field


class ExtractedFactDraft(BaseModel):
    category: FactCategory
    statement: str
    basis_type: BasisType = BasisType.FACT
    confidence: float = Field(default=0.8, ge=0, le=1)
    evidence_span_ids: list[str] = Field(default_factory=list)
    rationale: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    experience_name: str | None = None
    organization: str | None = None
    period: str | None = None
    role: str | None = None
    personal_field: str | None = None


class FactExtractionResponse(BaseModel):
    facts: list[ExtractedFactDraft] = Field(default_factory=list)


class MaterialGroupDraft(BaseModel):
    canonical_name: str = ""
    fact_ids: list[str] = Field(default_factory=list)


class MaterialGroupingResponse(BaseModel):
    groups: list[MaterialGroupDraft] = Field(default_factory=list)


class ClaimDraft(BaseModel):
    group: str = "detail"
    content: str
    basis_type: BasisType = BasisType.FACT
    confidence: float = Field(default=0.8, ge=0, le=1)
    fact_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


class EntryDraft(BaseModel):
    name: str
    organization: str | None = None
    period: str | None = None
    role: str | None = None
    summary: str
    details: list[ClaimDraft] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    outcomes: list[ClaimDraft] = Field(default_factory=list)
    attributes: dict[str, str] = Field(default_factory=dict)
    fact_ids: list[str] = Field(default_factory=list)


class SectionDraft(BaseModel):
    overview: str
    claims: list[ClaimDraft] = Field(default_factory=list)
    entries: list[EntryDraft] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
