import re

from ingestion.models import ParsedDocument, SourceSpan

_WHITESPACE = re.compile(r"[ \t\u00a0]+")
_EXCESS_NEWLINES = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    value = "\n".join(_WHITESPACE.sub(" ", line).strip() for line in value.splitlines())
    return _EXCESS_NEWLINES.sub("\n\n", value).strip()


def normalize_document(document: ParsedDocument) -> ParsedDocument:
    seen: set[str] = set()
    spans: list[SourceSpan] = []
    for span in document.spans:
        text = normalize_text(span.text)
        fingerprint = re.sub(r"\W+", "", text).lower()
        if len(text) < 2 or fingerprint in seen:
            continue
        seen.add(fingerprint)
        spans.append(span.model_copy(update={"text": text}))
    return document.model_copy(update={"spans": spans})
