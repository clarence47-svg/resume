from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class StarStory(BaseModel):
    title: str
    situation: str
    task: str
    action: str
    result: str
    source_fact_ids: list[str] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    question: str
    answer_outline: list[str] = Field(default_factory=list)
    category: str = "behavioral"


class InterviewKit(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    resume_version_id: str
    role_summary: str
    self_introduction: str
    star_stories: list[StarStory] = Field(default_factory=list)
    likely_questions: list[InterviewQuestion] = Field(default_factory=list)
    questions_to_ask: list[str] = Field(default_factory=list)
    risks_and_gaps: list[str] = Field(default_factory=list)
    model: str = "heuristic-fallback"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
