from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    left: float
    top: float
    right: float
    bottom: float


class SourceSpan(BaseModel):
    id: str
    document_id: str
    file_name: str
    text: str
    page: int | None = None
    slide: int | None = None
    paragraph: int | None = None
    section: str | None = None
    bbox: BoundingBox | None = None
    source_type: str = "text"


class ParsedDocument(BaseModel):
    document_id: str
    file_name: str
    media_type: str | None = None
    spans: list[SourceSpan] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    page_count: int = 0
    language: str | None = None

    @property
    def text(self) -> str:
        return "\n\n".join(span.text for span in self.spans if span.text.strip())


class DocumentChunk(BaseModel):
    id: str
    text: str
    spans: list[SourceSpan]
