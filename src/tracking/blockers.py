from storage.career_repositories import CareerRepository
from tracking.models import BlockerRecord


def list_open_blockers(repository: CareerRepository) -> list[BlockerRecord]:
    return repository.list_blockers(open_only=True)
