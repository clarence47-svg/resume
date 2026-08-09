import asyncio
import re
from collections import defaultdict
from difflib import SequenceMatcher
from profile.models import FactCategory, ProfileFact

import httpx

from core.settings import Settings, get_settings
from matching.job_research import parse_baidu_html, parse_bing_rss
from matching.models import JobResearchSource

COMPETITION_MARKERS = (
    "竞赛",
    "比赛",
    "大赛",
    "挑战赛",
    "锦标赛",
    "competition",
    "contest",
    "challenge",
    "cup",
)
AWARD_SUFFIX_PATTERN = re.compile(
    r"(?:国家级|省级|市级|校级|国际级|全国|华南赛区|一等奖|二等奖|三等奖|"
    r"特等奖|金奖|银奖|铜奖|冠军|亚军|季军|获奖|奖项).*$",
    re.IGNORECASE,
)


async def verify_competition_facts(
    facts: list[ProfileFact], settings: Settings | None = None
) -> tuple[list[ProfileFact], list[str]]:
    settings = settings or get_settings()
    competition_facts = [fact for fact in facts if fact.category == FactCategory.COMPETITION]
    if not competition_facts:
        return facts, []
    grouped: defaultdict[str, list[ProfileFact]] = defaultdict(list)
    for fact in competition_facts:
        grouped[fact.material_group_id or fact.id].append(fact)
    names = [_competition_name(group) for group in grouped.values()]
    if not settings.job_search_enabled or not settings.competition_verification_enabled:
        results = [
            {
                "verified": False,
                "status": "disabled",
                "query_name": name,
                "matched_name": "",
                "score": 0.0,
                "sources": [],
            }
            for name in names
        ]
    else:
        results = await asyncio.gather(
            *[_verify_name(name, settings) for name in names],
            return_exceptions=True,
        )
    warnings: list[str] = []
    resolved: dict[str, dict] = {}
    for group_id, name, result in zip(grouped, names, results, strict=True):
        if isinstance(result, Exception):
            error = result
            result = {
                "verified": False,
                "status": "unavailable",
                "query_name": name,
                "matched_name": "",
                "score": 0.0,
                "sources": [],
            }
            warnings.append(f"赛事“{name}”联网核验失败：{error}")
        resolved[group_id] = result
        if not result["verified"]:
            warnings.append(f"赛事“{name}”未找到足够可靠的联网证据，已从比赛画像中暂时排除。")
    output = []
    for fact in facts:
        if fact.category != FactCategory.COMPETITION:
            output.append(fact)
            continue
        group_id = fact.material_group_id or fact.id
        output.append(
            fact.model_copy(
                update={
                    "metadata": {
                        **fact.metadata,
                        "competition_verification": resolved[group_id],
                    }
                }
            )
        )
    return output, list(dict.fromkeys(warnings))


def competition_fact_is_verified(fact: ProfileFact) -> bool:
    verification = fact.metadata.get("competition_verification")
    return bool(isinstance(verification, dict) and verification.get("verified"))


async def _verify_name(name: str, settings: Settings) -> dict:
    if not _looks_like_competition(name):
        return _verification(name, "not_a_competition", [])
    queries = [f'"{name}" 竞赛', f'"{name}" 比赛 官网', f'"{name}" 获奖']
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/126 Safari/537.36"
        )
    }
    timeout = httpx.Timeout(settings.job_search_timeout_seconds)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        sources = await _collect(client, settings.job_search_endpoint, queries)
        if not _has_candidate(sources, name, settings.competition_verification_min_score):
            sources.extend(await _collect(client, settings.job_search_fallback_endpoint, queries))
    ranked = sorted(
        _dedupe(sources),
        key=lambda source: _source_score(source, name),
        reverse=True,
    )
    return _verification(
        name,
        "completed",
        ranked[: settings.competition_verification_max_results],
        settings.competition_verification_min_score,
    )


async def _collect(
    client: httpx.AsyncClient, endpoint: str, queries: list[str]
) -> list[JobResearchSource]:
    responses = await asyncio.gather(
        *[_fetch(client, endpoint, query) for query in queries],
        return_exceptions=True,
    )
    output: list[JobResearchSource] = []
    parser = parse_baidu_html if "baidu.com" in endpoint else parse_bing_rss
    for query, response in zip(queries, responses, strict=True):
        if isinstance(response, Exception):
            continue
        output.extend(parser(response, query))
    return output


async def _fetch(client: httpx.AsyncClient, endpoint: str, query: str) -> str:
    params = {"wd": query} if "baidu.com" in endpoint else {"format": "rss", "q": query}
    response = await client.get(endpoint, params=params)
    response.raise_for_status()
    return response.text


def _verification(
    name: str,
    status: str,
    sources: list[JobResearchSource],
    threshold: float = 1.0,
) -> dict:
    best = sources[0] if sources else None
    score = _source_score(best, name) if best else 0.0
    return {
        "verified": bool(best and score >= threshold),
        "status": status,
        "query_name": name,
        "matched_name": best.title if best else "",
        "score": round(score, 3),
        "sources": [source.model_dump(mode="json") for source in sources],
    }


def _competition_name(facts: list[ProfileFact]) -> str:
    names = [
        str(
            fact.metadata.get("canonical_name") or fact.metadata.get("experience_name") or ""
        ).strip()
        for fact in facts
    ]
    named = [name for name in names if _looks_like_competition(name)]
    if named:
        return max(named, key=len)
    statements = [fact.statement for fact in facts]
    return _clean_name(max(statements, key=len, default=""))


def _clean_name(value: str) -> str:
    cleaned = re.sub(r"^(?:获得|荣获|参加)\s*", "", value.strip())
    cleaned = AWARD_SUFFIX_PATTERN.sub("", cleaned).strip(" ：:，,；;")
    return cleaned[:160]


def _looks_like_competition(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in COMPETITION_MARKERS)


def _has_candidate(sources: list[JobResearchSource], name: str, threshold: float) -> bool:
    return any(_source_score(source, name) >= threshold for source in sources)


def _source_score(source: JobResearchSource | None, name: str) -> float:
    if source is None:
        return 0.0
    source_text = f"{source.title} {source.snippet}".casefold()
    if not any(marker in source_text for marker in COMPETITION_MARKERS):
        return 0.0
    aliases = _aliases(name)
    normalized_source = _normalize(source_text)
    scores = []
    for alias in aliases:
        normalized_alias = _normalize(alias)
        if not normalized_alias:
            continue
        substring = 1.0 if normalized_alias in normalized_source else 0.0
        sequence = SequenceMatcher(None, normalized_alias, normalized_source).ratio()
        dice = _dice(_bigrams(normalized_alias), _bigrams(normalized_source))
        scores.append(max(substring, sequence, dice))
    return max(scores, default=0.0)


def _aliases(name: str) -> list[str]:
    cleaned = _clean_name(name)
    aliases = [cleaned]
    without_scope = re.sub(r"^(?:中国|全国|国际|全球|大学生)", "", cleaned)
    if without_scope and without_scope != cleaned:
        aliases.append(without_scope)
    latin = "".join(re.findall(r"\b[A-Z]{2,}\b", name))
    if latin:
        aliases.append(latin)
    return list(dict.fromkeys(alias for alias in aliases if alias))


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.casefold())


def _bigrams(value: str) -> set[str]:
    if len(value) < 2:
        return {value} if value else set()
    return {value[index : index + 2] for index in range(len(value) - 1)}


def _dice(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return 2 * len(left.intersection(right)) / (len(left) + len(right))


def _dedupe(sources: list[JobResearchSource]) -> list[JobResearchSource]:
    output = []
    seen = set()
    for source in sources:
        key = source.url.casefold() or source.title.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(source)
    return output
