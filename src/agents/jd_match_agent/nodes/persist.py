from pathlib import Path

from matching.exporters import export_match_docx, export_match_markdown
from matching.models import JDMatchResult


def persist_and_export(state: dict) -> dict:
    result = JDMatchResult.model_validate(state["result"])
    task_dir = Path(state["export_dir"]) / "matches" / state["match_id"] / f"v{result.version}"
    markdown_path = task_dir / "match.md"
    docx_path = task_dir / "match.docx"
    export_match_markdown(result, markdown_path)
    export_match_docx(result, docx_path)
    return {"export_paths": {"markdown": str(markdown_path), "docx": str(docx_path)}}
