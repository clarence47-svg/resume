from pathlib import Path
from uuid import uuid4

from charset_normalizer import from_bytes

from ingestion.models import ParsedDocument, SourceSpan
from ingestion.parsers.base import BaseParser


class MarkdownParser(BaseParser):
    def parse(self, path: Path, document_id: str, file_name: str) -> ParsedDocument:
        raw = path.read_bytes()
        match = from_bytes(raw).best()
        text = str(match) if match else raw.decode("utf-8", errors="replace")
        spans: list[SourceSpan] = []
        section: str | None = None
        buffer: list[str] = []
        paragraph = 0

        def flush() -> None:
            nonlocal paragraph
            content = "\n".join(buffer).strip()
            if content:
                paragraph += 1
                spans.append(
                    SourceSpan(
                        id=str(uuid4()),
                        document_id=document_id,
                        file_name=file_name,
                        text=content,
                        paragraph=paragraph,
                        section=section,
                    )
                )
            buffer.clear()

        for line in text.splitlines():
            if line.lstrip().startswith("#"):
                flush()
                section = line.lstrip("# ").strip() or section
                continue
            if not line.strip():
                flush()
            else:
                buffer.append(line)
        flush()
        return ParsedDocument(document_id=document_id, file_name=file_name, spans=spans)
