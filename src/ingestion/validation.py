import zipfile
from pathlib import Path

import filetype

from core.settings import Settings, get_settings

SUPPORTED_EXTENSIONS = {".doc", ".docx", ".pdf", ".md", ".ppt", ".pptx"}
OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")


class FileValidationError(ValueError):
    pass


def validate_file(path: Path, original_name: str, settings: Settings | None = None) -> str | None:
    resolved = settings or get_settings()
    extension = Path(original_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise FileValidationError(f"不支持的文件格式：{extension or '无扩展名'}。")
    size = path.stat().st_size
    if size == 0:
        raise FileValidationError("文件为空。")
    if size > resolved.max_file_size_mb * 1024 * 1024:
        raise FileValidationError(f"文件超过 {resolved.max_file_size_mb} MB 限制。")
    head = path.read_bytes()[:16]
    if extension == ".pdf" and not head.startswith(b"%PDF-"):
        raise FileValidationError("PDF 文件签名无效。")
    if extension in {".doc", ".ppt"} and not head.startswith(OLE_SIGNATURE):
        raise FileValidationError("旧版 Office 文件签名无效。")
    if extension in {".docx", ".pptx"}:
        _validate_ooxml(path, extension, resolved)
    if extension == ".md" and b"\x00" in path.read_bytes()[:4096]:
        raise FileValidationError("Markdown 文件包含非法二进制内容。")
    kind = filetype.guess(path)
    return kind.mime if kind else None


def _validate_ooxml(path: Path, extension: str, settings: Settings) -> None:
    if not zipfile.is_zipfile(path):
        raise FileValidationError("Office Open XML 文件不是有效 ZIP 容器。")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > 10_000:
            raise FileValidationError("Office 文件包含过多内部条目。")
        total_uncompressed = sum(member.file_size for member in members)
        maximum = settings.max_file_size_mb * 1024 * 1024 * 20
        if total_uncompressed > maximum:
            raise FileValidationError("Office 文件解压后体积异常。")
        names = {member.filename for member in members}
        required_prefix = "word/" if extension == ".docx" else "ppt/"
        if "[Content_Types].xml" not in names or not any(
            name.startswith(required_prefix) for name in names
        ):
            raise FileValidationError("Office 文件内容与扩展名不匹配。")
        for member in members:
            if member.compress_size and member.file_size / member.compress_size > 500:
                raise FileValidationError("Office 文件疑似压缩炸弹。")
