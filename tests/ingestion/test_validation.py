from pathlib import Path

import pytest
from docx import Document

from ingestion.validation import FileValidationError, validate_file


def test_markdown_validation(tmp_path: Path, test_settings) -> None:
    path = tmp_path / "resume.md"
    path.write_text("# 简历\n\n项目经历", encoding="utf-8")
    assert validate_file(path, path.name, test_settings) is None


def test_docx_validation(tmp_path: Path, test_settings) -> None:
    path = tmp_path / "resume.docx"
    document = Document()
    document.add_paragraph("项目经历")
    document.save(path)
    validate_file(path, path.name, test_settings)


def test_rejects_unsupported_file(tmp_path: Path, test_settings) -> None:
    path = tmp_path / "resume.exe"
    path.write_bytes(b"MZ")
    with pytest.raises(FileValidationError):
        validate_file(path, path.name, test_settings)
