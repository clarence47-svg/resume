import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from core.security import ensure_within, sanitize_filename, sha256_file
from core.settings import Settings, get_settings
from ingestion.models import ParsedDocument


class FileStorage:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.settings.ensure_directories()

    async def save_upload(self, task_id: str, upload: UploadFile) -> tuple[str, Path, int, str]:
        document_id = str(uuid4())
        filename = sanitize_filename(upload.filename or "document")
        task_dir = self.settings.uploads_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        path = ensure_within(task_dir, task_dir / f"{document_id}_{filename}")
        size = 0
        try:
            with path.open("wb") as handle:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.settings.max_file_size_mb * 1024 * 1024:
                        raise ValueError(f"文件超过 {self.settings.max_file_size_mb} MB 限制。")
                    handle.write(chunk)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()
        return document_id, path, size, sha256_file(path)

    def write_parsed(self, task_id: str, document: ParsedDocument) -> Path:
        task_dir = self.settings.parsed_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        path = ensure_within(task_dir, task_dir / f"{document.document_id}.json")
        path.write_text(
            json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def read_parsed(self, path: str | Path) -> ParsedDocument:
        return ParsedDocument.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def export_paths(self, task_id: str) -> tuple[Path, Path]:
        task_dir = self.settings.exports_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir / "profile.md", task_dir / "profile.docx"

    def profile_sections_dir(self, task_id: str) -> Path:
        target = self.settings.parsed_dir / task_id / "sections"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def match_export_paths(self, match_id: str, version: int) -> tuple[Path, Path]:
        task_dir = self.settings.match_exports_dir / match_id / f"v{version}"
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir / "match.md", task_dir / "match.docx"

    def resume_export_paths(self, job_id: str, version: int) -> dict[str, Path]:
        task_dir = self.settings.resume_exports_dir / job_id / f"v{version}"
        task_dir.mkdir(parents=True, exist_ok=True)
        return {
            "markdown": task_dir / "resume.md",
            "html": task_dir / "resume.html",
            "docx": task_dir / "resume.docx",
            "pdf": task_dir / "resume.pdf",
        }

    def application_dir(self, application_id: str) -> Path:
        target = self.settings.applications_dir / application_id
        target.mkdir(parents=True, exist_ok=True)
        return target

    def application_confirmation_path(self, application_id: str) -> Path:
        return self.application_dir(application_id) / "confirmation.png"

    def interview_export_path(self, kit_id: str) -> Path:
        target = self.settings.interview_exports_dir / kit_id
        target.mkdir(parents=True, exist_ok=True)
        return target / "interview-kit.md"

    def delete_interview_files(self, kit_id: str) -> None:
        target = ensure_within(
            self.settings.interview_exports_dir,
            self.settings.interview_exports_dir / kit_id,
        )
        if target.exists():
            shutil.rmtree(target)

    def delete_match_files(self, match_id: str) -> None:
        target = ensure_within(
            self.settings.match_exports_dir,
            self.settings.match_exports_dir / match_id,
        )
        if target.exists():
            shutil.rmtree(target)

    def delete_campaign_files(self, campaign_id: str) -> None:
        target = ensure_within(self.settings.jobs_dir, self.settings.jobs_dir / campaign_id)
        if target.exists():
            shutil.rmtree(target)

    def delete_job_files(self, job_id: str) -> None:
        for root in (self.settings.resume_exports_dir, self.settings.jobs_dir):
            target = ensure_within(root, root / job_id)
            if target.exists():
                shutil.rmtree(target)

    def delete_application_files(self, application_id: str) -> None:
        target = ensure_within(
            self.settings.applications_dir,
            self.settings.applications_dir / application_id,
        )
        if target.exists():
            shutil.rmtree(target)

    def delete_task_files(self, task_id: str) -> None:
        for root in (
            self.settings.uploads_dir,
            self.settings.parsed_dir,
            self.settings.exports_dir,
        ):
            target = ensure_within(root, root / task_id)
            if target.exists():
                shutil.rmtree(target)
