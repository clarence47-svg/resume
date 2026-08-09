from pathlib import Path
from profile.models import FactCategory, ProfileFact

from matching.models import JDMatchResult
from matching.section_documents import render_result_section_documents

RESUME_DOCUMENT_FILENAMES = {
    FactCategory.PERSONAL.value: "01_岗位母版_个人信息.md",
    FactCategory.PROJECT.value: "02_岗位母版_项目经历.md",
    FactCategory.COMPETITION.value: "03_岗位母版_比赛经历.md",
    FactCategory.INTERNSHIP.value: "04_岗位母版_实习经历.md",
    FactCategory.EDUCATION.value: "05_岗位母版_学校履历.md",
    "final_resume": "06_最终简历.md",
}


def write_resume_source_documents(
    result: JDMatchResult,
    facts: list[ProfileFact],
    target_dir: Path,
) -> dict[str, Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    documents = render_result_section_documents(result, facts)
    paths: dict[str, Path] = {}
    for section_name, content in documents.items():
        path = target_dir / RESUME_DOCUMENT_FILENAMES[section_name]
        path.write_text(content, encoding="utf-8")
        paths[section_name] = path
    return paths


def resume_document_path(target_dir: Path, document_key: str) -> Path | None:
    filename = RESUME_DOCUMENT_FILENAMES.get(document_key)
    return target_dir / filename if filename else None
