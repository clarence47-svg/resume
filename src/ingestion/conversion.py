import shutil
import subprocess
from pathlib import Path


class ConversionError(RuntimeError):
    pass


def convert_legacy_office(path: Path, output_dir: Path) -> Path:
    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if not executable:
        raise ConversionError("未检测到 LibreOffice，无法转换旧版 .doc/.ppt 文件。")
    output_dir.mkdir(parents=True, exist_ok=True)
    target_extension = ".docx" if path.suffix.lower() == ".doc" else ".pptx"
    result = subprocess.run(
        [
            executable,
            "--headless",
            "--convert-to",
            target_extension.lstrip("."),
            "--outdir",
            str(output_dir),
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    converted = output_dir / f"{path.stem}{target_extension}"
    if result.returncode != 0 or not converted.exists():
        message = result.stderr.strip() or result.stdout.strip() or "未知转换错误"
        raise ConversionError(f"LibreOffice 转换失败：{message}")
    return converted
