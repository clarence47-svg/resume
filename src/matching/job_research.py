import asyncio
import html
import re
import xml.etree.ElementTree as ET

import httpx

from core.settings import Settings
from matching.models import JobResearchSource

TAG_PATTERN = re.compile(r"<[^>]+>")
BAIDU_RESULT_PATTERN = re.compile(
    r"<h3\b[^>]*>.*?<a\b[^>]*href=[\"'](?P<url>[^\"']+)[\"'][^>]*>"
    r"(?P<title>.*?)</a>.*?</h3>(?P<after>.*?)(?=<h3\b|$)",
    re.IGNORECASE | re.DOTALL,
)
BAIDU_SUMMARY_PATTERN = re.compile(
    r'data-module="abstract".*?<span\b[^>]*class="[^"]*summary-text[^"]*"[^>]*>'
    r"(?P<snippet>.*?)</span>",
    re.IGNORECASE | re.DOTALL,
)


async def fetch_search_results(
    role_title: str, settings: Settings
) -> tuple[list[str], list[JobResearchSource]]:
    queries = [
        f'"{role_title}" 招聘 任职要求',
        f'"{role_title}" 岗位职责 核心能力 技能',
        f'"{role_title}" 职位描述 工作内容',
    ]
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/126 Safari/537.36"
        )
    }
    timeout = httpx.Timeout(settings.job_search_timeout_seconds)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        output = await _collect_results(client, settings.job_search_endpoint, queries)
        if not _relevant_results(output, role_title):
            fallback = await _collect_results(
                client, settings.job_search_fallback_endpoint, queries
            )
            output.extend(fallback)
    output = _dedupe_sources(output)
    ranked = sorted(output, key=lambda item: _relevance_score(item, role_title), reverse=True)
    relevant = [item for item in ranked if _relevance_score(item, role_title) >= 3]
    return queries, (relevant or ranked)[: settings.job_search_max_results]


async def _collect_results(
    client: httpx.AsyncClient, endpoint: str, queries: list[str]
) -> list[JobResearchSource]:
    responses = await asyncio.gather(
        *[_fetch_query(client, endpoint, query) for query in queries],
        return_exceptions=True,
    )
    output: list[JobResearchSource] = []
    for query, response in zip(queries, responses, strict=True):
        if isinstance(response, Exception):
            continue
        parser = parse_baidu_html if "baidu.com" in endpoint else parse_bing_rss
        output.extend(parser(response, query))
    return output


async def _fetch_query(client: httpx.AsyncClient, endpoint: str, query: str) -> str:
    params = {"wd": query} if "baidu.com" in endpoint else {"format": "rss", "q": query}
    response = await client.get(endpoint, params=params)
    response.raise_for_status()
    return response.text


def parse_bing_rss(payload: str, query: str) -> list[JobResearchSource]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return []
    output = []
    for item in root.findall("./channel/item"):
        title = _clean(item.findtext("title") or "")
        url = (item.findtext("link") or "").strip()
        snippet = _clean(item.findtext("description") or "")
        if not title or not url:
            continue
        output.append(
            JobResearchSource(title=title[:300], url=url, snippet=snippet[:1000], query=query)
        )
    return output


def parse_baidu_html(payload: str, query: str) -> list[JobResearchSource]:
    output = []
    for match in BAIDU_RESULT_PATTERN.finditer(payload):
        title = _clean(match.group("title"))
        url = html.unescape(match.group("url")).strip()
        summary_match = BAIDU_SUMMARY_PATTERN.search(match.group("after"))
        snippet = _clean(summary_match.group("snippet")) if summary_match else ""
        if not title or not url:
            continue
        output.append(
            JobResearchSource(title=title[:300], url=url, snippet=snippet[:1000], query=query)
        )
    return output


def _clean(value: str) -> str:
    cleaned = " ".join(html.unescape(TAG_PATTERN.sub(" ", value)).split())
    return re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", cleaned)


def _relevance_score(source: JobResearchSource, role_title: str) -> float:
    text = f"{source.title} {source.snippet} {source.url}".casefold()
    normalized_text = re.sub(r"\s+", "", text)
    normalized_role = re.sub(r"\s+", "", role_title.casefold())
    score = 8.0 if normalized_role and normalized_role in normalized_text else 0.0
    role_tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9+#.\-]+", role_title)
    score += sum(2.0 for token in role_tokens if token.casefold() in text)
    score += sum(
        0.75
        for token in ("招聘", "任职", "岗位", "职位", "职责", "能力", "技能", "要求")
        if token in text
    )
    if any(domain in source.url for domain in ("zhipin.com", "liepin.com", "jobs", "career")):
        score += 2.0
    return score


def _relevant_results(sources: list[JobResearchSource], role_title: str) -> bool:
    return any(_relevance_score(item, role_title) >= 3 for item in sources)


def _dedupe_sources(sources: list[JobResearchSource]) -> list[JobResearchSource]:
    output = []
    seen: set[str] = set()
    for source in sources:
        key = source.url.casefold() or source.title.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(source)
    return output
