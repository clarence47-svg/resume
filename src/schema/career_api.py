from pydantic import BaseModel, Field

from career.models import AnswerBankEntry, CareerSettings


class CareerSettingsResponse(BaseModel):
    settings: CareerSettings


class AnswerBankResponse(BaseModel):
    answers: list[AnswerBankEntry] = Field(default_factory=list)
