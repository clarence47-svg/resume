from pathlib import Path

from ingestion.parsers.markdown_parser import MarkdownParser


def test_markdown_parser_preserves_sections(tmp_path: Path) -> None:
    path = tmp_path / "profile.md"
    path.write_text(
        "# 项目经历\n\n负责平台后端开发。\n\n## 学校履历\n\n示例大学。", encoding="utf-8"
    )
    parsed = MarkdownParser().parse(path, "doc-1", path.name)
    assert len(parsed.spans) == 2
    assert parsed.spans[0].section == "项目经历"
    assert parsed.spans[1].section == "学校履历"
