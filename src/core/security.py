import hashlib
import re
from pathlib import Path

_SAFE_FILENAME = re.compile(r"[^\w.\-()\u4e00-\u9fff]+", re.UNICODE)


def sanitize_filename(filename: str) -> str:
    candidate = Path(filename).name.strip().replace("\x00", "")
    candidate = _SAFE_FILENAME.sub("_", candidate)
    return candidate[:180] or "document"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_within(base: Path, candidate: Path) -> Path:
    base_resolved = base.resolve()
    candidate_resolved = candidate.resolve()
    if base_resolved != candidate_resolved and base_resolved not in candidate_resolved.parents:
        raise ValueError("非法文件路径。")
    return candidate_resolved
