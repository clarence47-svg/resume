from abc import ABC, abstractmethod
from pathlib import Path

from ingestion.models import ParsedDocument


class BaseParser(ABC):
    @abstractmethod
    def parse(self, path: Path, document_id: str, file_name: str) -> ParsedDocument:
        raise NotImplementedError
