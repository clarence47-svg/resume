from profile.models import EvidenceRef, FactCategory, ProfileFact, ProfileResult
from profile.section_documents import (
    MASTER_FILENAME,
    SECTION_FILENAMES,
    extract_document_fact_ids,
    write_profile_section_documents,
)


def test_writes_five_profile_section_documents(tmp_path) -> None:
    evidence = EvidenceRef(
        span_id="span-project",
        document_id="doc",
        file_name="resume.md",
        quote="使用 Python 完成服务开发",
        paragraph=1,
    )
    fact = ProfileFact(
        id="fact-project",
        category=FactCategory.PROJECT,
        statement="使用 Python 完成服务开发",
        evidence_refs=[evidence],
    )
    paths = write_profile_section_documents(ProfileResult(task_id="profile"), [fact], tmp_path)
    assert set(paths) == set(SECTION_FILENAMES)
    assert paths[FactCategory.PROJECT.value].name == "画像母版_项目经历.md"
    assert (tmp_path / MASTER_FILENAME).exists()
    project_document = paths[FactCategory.PROJECT.value].read_text(encoding="utf-8")
    assert "使用 Python 完成服务开发" in project_document
    assert extract_document_fact_ids(project_document) == {"fact-project"}
    assert "使用 Python 完成服务开发" in (tmp_path / MASTER_FILENAME).read_text(encoding="utf-8")
