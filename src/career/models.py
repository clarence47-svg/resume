from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class ApplicationStrategy(StrEnum):
    VOLUME = "volume"
    PRECISION = "precision"


class AnswerSensitivity(StrEnum):
    NORMAL = "normal"
    SENSITIVE = "sensitive"
    LEGAL = "legal"


class AnswerStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ApplicationRuleSet(BaseModel):
    strategy: ApplicationStrategy = ApplicationStrategy.VOLUME
    minimum_match_score: float = Field(default=65, ge=0, le=100)
    precision_score_threshold: float = Field(default=82, ge=0, le=100)
    excluded_keywords: list[str] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list)
    excluded_work_patterns: list[str] = Field(default_factory=lambda: ["外包"])
    preferred_industries: list[str] = Field(default_factory=list)
    allow_internship: bool = False
    allow_outsource: bool = False
    require_fresh_posting_days: int = Field(default=30, ge=1, le=365)
    daily_action_limit: int = Field(default=10, ge=1, le=100)
    action_interval_min_seconds: int = Field(default=90, ge=5, le=3600)
    action_interval_max_seconds: int = Field(default=180, ge=5, le=7200)
    require_submission_confirmation: bool = True
    require_message_confirmation: bool = True

    @model_validator(mode="after")
    def validate_intervals(self):
        if self.action_interval_max_seconds < self.action_interval_min_seconds:
            raise ValueError("最大操作间隔不能小于最小操作间隔。")
        return self


class CareerSettings(BaseModel):
    display_name: str = ""
    email: str = ""
    phone: str = ""
    city: str = ""
    address: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    target_roles: list[str] = Field(default_factory=list)
    target_cities: list[str] = Field(default_factory=list)
    salary_min_k: float | None = Field(default=None, ge=0)
    salary_max_k: float | None = Field(default=None, ge=0)
    employment_status: str = ""
    work_authorization: str = ""
    sponsorship_required: bool | None = None
    relocation_willing: bool | None = None
    graduation_year: int | None = Field(default=None, ge=1950, le=2200)
    rules: ApplicationRuleSet = Field(default_factory=ApplicationRuleSet)
    never_guess_fields: list[str] = Field(
        default_factory=lambda: [
            "work_authorization",
            "sponsorship_required",
            "salary",
            "identity",
            "legal",
            "voluntary_self_identification",
        ]
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_salary(self):
        if (
            self.salary_min_k is not None
            and self.salary_max_k is not None
            and self.salary_max_k < self.salary_min_k
        ):
            raise ValueError("最高期望薪资不能低于最低期望薪资。")
        return self


class AnswerBankEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    question_key: str = Field(min_length=1, max_length=120)
    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=4000)
    sensitivity: AnswerSensitivity = AnswerSensitivity.NORMAL
    status: AnswerStatus = AnswerStatus.DRAFT
    tags: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
