from pathlib import Path
from profile.exporters import export_docx, export_markdown
from profile.models import ProfileResult


def persist_and_export(state: dict) -> dict:
    result = ProfileResult.model_validate(state["result"])
    task_dir = Path(state["export_dir"]) / state["task_id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    markdown_path, docx_path = task_dir / "profile.md", task_dir / "profile.docx"
    export_markdown(result, markdown_path)
    export_docx(result, docx_path)
    return {"export_paths": {"markdown": str(markdown_path), "docx": str(docx_path)}}
