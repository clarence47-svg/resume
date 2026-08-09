import hashlib
import json

from applications.models import ApplicationPreview


def compute_preview_hash(preview: ApplicationPreview) -> str:
    payload = preview.model_dump(mode="json", exclude={"preview_hash"})
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
