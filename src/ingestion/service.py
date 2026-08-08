from pathlib import Path

from core.settings import Settings, get_settings
from ingestion.conversion import convert_legacy_office
from ingestion.models import ParsedDocument
from ingestion.normalize import normalize_document
from ingestion.parsers import DoclingParser, MarkdownParser
from schema.profile_api import DocumentStatus
from storage.files import FileStorage
from storage.repositories import ProfileRepository


class IngestionService:
    def __init__(
        self,
        repository: ProfileRepository,
        storage: FileStorage,
        settings: Settings | None = None,
    ):
        self.repository = repository
        self.storage = storage
        self.settings = settings or get_settings()
        self.docling_parser = DoclingParser(self.settings)
        self.markdown_parser = MarkdownParser()

    def parse_task(self, task_id: str) -> tuple[list[ParsedDocument], list[str]]:
        documents = self.repository.get_documents(task_id)
        parsed_documents: list[ParsedDocument] = []
        errors: list[str] = []
        total_pages = 0
        conversion_dir = self.settings.parsed_dir / task_id / "converted"

        for document in documents:
            if not document.stored_path or document.status == DocumentStatus.FAILED.value:
                continue
            self.repository.update_document(
                document.id, status=DocumentStatus.PARSING.value, error=None
            )
            try:
                source_path = Path(document.stored_path)
                parse_path = source_path
                if document.extension in {".doc", ".ppt"}:
                    parse_path = convert_legacy_office(source_path, conversion_dir)
                parser = (
                    self.markdown_parser
                    if parse_path.suffix.lower() == ".md"
                    else self.docling_parser
                )
                parsed = normalize_document(
                    parser.parse(parse_path, document.id, document.original_name)
                )
                if not parsed.spans:
                    raise RuntimeError("未提取到可用文本。")
                total_pages += max(parsed.page_count, 1)
                if total_pages > self.settings.max_total_pages:
                    raise RuntimeError(
                        f"总页数或幻灯片数超过 {self.settings.max_total_pages} 限制。"
                    )
                parsed_path = self.storage.write_parsed(task_id, parsed)
                self.repository.update_document(
                    document.id,
                    status=DocumentStatus.PARSED.value,
                    parsed_path=str(parsed_path),
                    page_count=parsed.page_count,
                )
                parsed_documents.append(parsed)
            except Exception as exc:
                message = f"{document.original_name}: {exc}"
                errors.append(message)
                self.repository.update_document(
                    document.id, status=DocumentStatus.FAILED.value, error=str(exc)
                )
        return parsed_documents, errors
