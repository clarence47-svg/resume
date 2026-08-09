import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz


def export_pdf(docx_path: Path, pdf_path: Path, html_path: Path | None = None) -> Path | None:
    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if executable is None:
        return _export_html_pdf(html_path, pdf_path) if html_path else None
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(
            [executable, "--headless", "--convert-to", "pdf", "--outdir", temp_dir, str(docx_path)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        generated = Path(temp_dir) / f"{docx_path.stem}.pdf"
        if not generated.exists():
            return None
        shutil.copy2(generated, pdf_path)
    return pdf_path


def _export_html_pdf(html_path: Path, pdf_path: Path) -> Path | None:
    if not html_path.exists():
        return None
    document = fitz.open()
    story = fitz.Story(html=html_path.read_text(encoding="utf-8"))
    more = 1
    while more:
        page = document.new_page(width=595, height=842)
        more, _ = story.place(fitz.Rect(36, 36, 559, 806))
        story.draw(page)
    document.save(pdf_path)
    document.close()
    return pdf_path
