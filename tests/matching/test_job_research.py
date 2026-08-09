import pytest

from agents.jd_match_agent.nodes import research
from core.settings import get_settings
from matching.job_research import parse_baidu_html, parse_bing_rss
from matching.models import JDAnalysis, JobResearchSource


def test_parse_bing_rss_extracts_sources() -> None:
    payload = """
    <rss><channel><item>
      <title>后端工程师招聘要求</title>
      <link>https://example.com/backend</link>
      <description>要求具备较强的编码能力，熟悉 Python。</description>
    </item></channel></rss>
    """
    sources = parse_bing_rss(payload, "后端工程师 岗位能力")
    assert sources[0].title == "后端工程师招聘要求"
    assert sources[0].url == "https://example.com/backend"
    assert "编码能力" in sources[0].snippet


def test_parse_baidu_html_extracts_sources() -> None:
    payload = """
    <h3 class="title"><a href="http://www.baidu.com/link?url=example">
    <em>AI绘图师</em>岗位职责</a></h3>
    <div data-module="abstract"><span class="summary-text">
    负责使用 Stable Diffusion 完成视觉内容生产，要求具备审美能力。
    </span></div>
    """
    sources = parse_baidu_html(payload, "AI绘图师 岗位职责")
    assert sources[0].title == "AI绘图师岗位职责"
    assert "Stable Diffusion" in sources[0].snippet


@pytest.mark.asyncio
async def test_role_research_adds_market_capabilities(monkeypatch) -> None:
    monkeypatch.setenv("JOB_SEARCH_ENABLED", "true")
    get_settings.cache_clear()

    async def fake_search(role_title, settings):
        return [f"{role_title} 岗位能力"], [
            JobResearchSource(
                title="后端工程师能力要求",
                url="https://example.com/backend",
                snippet="同类岗位要求具备较强的编码能力，熟悉 Python 和 SQL。",
            )
        ]

    monkeypatch.setattr(research, "fetch_search_results", fake_search)
    output = await research.research_role(
        {
            "jd_analysis": JDAnalysis(
                role_title="后端工程师",
                responsibilities=["负责后端服务开发"],
            ).model_dump(mode="json")
        }
    )
    assert output["job_research"]["sources"]
    assert any("编码能力" in item for item in output["job_research"]["core_capabilities"])
    assert any(
        item["origin"] == "market_research" for item in output["jd_analysis"]["requirements"]
    )
    get_settings.cache_clear()
