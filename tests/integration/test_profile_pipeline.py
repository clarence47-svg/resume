from pathlib import Path

from ingestion.chunking import chunk_documents
from ingestion.parsers.markdown_parser import MarkdownParser


def test_parsed_sources_survive_chunking(tmp_path: Path) -> None:
    path = tmp_path / "mixed.md"
    path.write_text(
        "# 学校履历\n\n示例大学计算机专业。\n\n# 比赛经历\n\n获得省级二等奖。",
        encoding="utf-8",
    )
    document = MarkdownParser().parse(path, "doc-1", path.name)
    chunks = chunk_documents([document], max_chars=30)
    assert chunks
    assert all(chunk.spans for chunk in chunks)
    assert all("来源:" in chunk.text for chunk in chunks)
