from uuid import uuid4

from ingestion.models import DocumentChunk, ParsedDocument, SourceSpan


def chunk_documents(documents: list[ParsedDocument], max_chars: int = 6_000) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    current_spans: list[SourceSpan] = []
    current_size = 0
    for document in documents:
        for span in document.spans:
            span_size = len(span.text)
            if current_spans and current_size + span_size > max_chars:
                chunks.append(_build_chunk(current_spans))
                current_spans = []
                current_size = 0
            current_spans.append(span)
            current_size += span_size
    if current_spans:
        chunks.append(_build_chunk(current_spans))
    return chunks


def _build_chunk(spans: list[SourceSpan]) -> DocumentChunk:
    text = "\n\n".join(f"[来源:{span.id} 文件:{span.file_name}]\n{span.text}" for span in spans)
    return DocumentChunk(id=str(uuid4()), text=text, spans=list(spans))
