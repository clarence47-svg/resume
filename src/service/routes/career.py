from fastapi import APIRouter, Depends

from career.models import AnswerBankEntry, CareerSettings
from career.service import CareerService
from schema.career_api import AnswerBankResponse, CareerSettingsResponse
from service.dependencies import get_career_service

router = APIRouter(prefix="/career", tags=["career"])


@router.get("/settings", response_model=CareerSettingsResponse)
def get_settings(service: CareerService = Depends(get_career_service)) -> CareerSettingsResponse:
    return CareerSettingsResponse(settings=service.get_settings())


@router.put("/settings", response_model=CareerSettingsResponse)
def put_settings(
    payload: CareerSettings,
    service: CareerService = Depends(get_career_service),
) -> CareerSettingsResponse:
    return CareerSettingsResponse(settings=service.save_settings(payload))


@router.get("/answers", response_model=AnswerBankResponse)
def get_answers(service: CareerService = Depends(get_career_service)) -> AnswerBankResponse:
    return AnswerBankResponse(answers=service.list_answers())


@router.put("/answers", response_model=AnswerBankResponse)
def put_answers(
    payload: list[AnswerBankEntry],
    service: CareerService = Depends(get_career_service),
) -> AnswerBankResponse:
    return AnswerBankResponse(answers=service.save_answers(payload))
