import json

from career.encryption import LocalEncryptor
from career.models import AnswerBankEntry, CareerSettings
from storage.career_repositories import CareerRepository


class CareerService:
    def __init__(self, repository: CareerRepository, encryptor: LocalEncryptor):
        self.repository = repository
        self.encryptor = encryptor

    def get_settings(self) -> CareerSettings:
        payload = self.repository.get_settings_payload()
        if not payload:
            return CareerSettings()
        return CareerSettings.model_validate_json(self.encryptor.decrypt(payload))

    def save_settings(self, settings: CareerSettings) -> CareerSettings:
        encrypted = self.encryptor.encrypt(settings.model_dump_json())
        self.repository.save_settings_payload(encrypted)
        return settings

    def list_answers(self) -> list[AnswerBankEntry]:
        output = []
        for row in self.repository.list_answer_rows():
            payload = json.loads(self.encryptor.decrypt(row.encrypted_payload))
            output.append(AnswerBankEntry.model_validate(payload))
        return output

    def save_answers(self, answers: list[AnswerBankEntry]) -> list[AnswerBankEntry]:
        rows = [
            (
                item.id,
                item.question_key,
                item.status.value,
                self.encryptor.encrypt(item.model_dump_json()),
            )
            for item in answers
        ]
        self.repository.replace_answers(rows)
        return answers
