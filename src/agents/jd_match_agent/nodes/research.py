import json
import re
from profile.models import FactCategory

from langchain_core.messages import HumanMessage, SystemMessage

from agents.jd_match_agent.nodes.jd_analysis import KNOWN_SKILLS
from agents.jd_match_agent.prompts.research import (
    JOB_RESEARCH_SYSTEM_PROMPT,
    job_research_user_prompt,
)
from agents.jd_match_agent.schemas import JobResearchDraft
from core.model import get_match_model
from core.settings import get_settings
from matching.job_research import fetch_search_results
from matching.models import (
    JDAnalysis,
    JDRequirement,
    JobResearch,
    JobResearchSource,
    RequirementOrigin,
    RequirementPriority,
    ResearchStatus,
)

ABILITY_PATTERN = re.compile(
    r"(?:具备|需要|要求|拥有|强调|注重|较强的?|良好的?)([^，。；;]{2,24}(?:能力|经验|技能))"
)
GENERIC_ABILITY_PATTERN = re.compile(r"([\u4e00-\u9fffA-Za-z]{2,24}(?:能力|经验|技能|基础))")
MARKET_TOOLS = (
    *KNOWN_SKILLS,
    "Stable Diffusion",
    "Midjourney",
    "ComfyUI",
    "Photoshop",
    "Illustrator",
    "Figma",
    "Blender",
    "Maya",
    "AIGC",
    "AI绘图",
)

CAPABILITY_SYNONYMS = {
    "编码": ["编码", "编程", "开发", "代码", "程序设计"],
    "AI绘图": ["AI绘图", "生成式AI", "文生图", "图像生成", "Stable Diffusion", "Midjourney"],
    "数据": ["数据", "SQL", "分析", "统计"],
    "沟通": ["沟通", "协作", "跨团队", "表达"],
    "设计": ["设计", "视觉", "创意", "审美"],
    "算法": ["算法", "数据结构", "建模", "优化"],
}
PROHIBITED_MARKET_TERMS = (
    "周岁",
    "年龄",
    "男女",
    "性别",
    "婚育",
    "户籍",
    "民族",
    "宗教",
    "政治面貌",
    "健康状况",
)


async def research_role(state: dict) -> dict:
    analysis = JDAnalysis.model_validate(state["jd_analysis"])
    settings = get_settings()
    warnings: list[str] = []
    if not settings.job_search_enabled:
        research = _heuristic_research(analysis, [], [], ResearchStatus.DISABLED)
        return {
            "jd_analysis": _augment_analysis(analysis, research).model_dump(mode="json"),
            "job_research": research.model_dump(mode="json"),
            "warnings": ["联网岗位研究已关闭，岗位说明仅根据 JD 生成。"],
        }

    try:
        queries, sources = await fetch_search_results(analysis.role_title, settings)
    except Exception as exc:
        queries, sources = [], []
        warnings.append(f"联网岗位研究失败，已根据 JD 回退：{exc}")

    research = None
    if sources and settings.llm_configured:
        try:
            model = get_match_model(settings).with_structured_output(JobResearchDraft)
            draft = await model.ainvoke(
                [
                    SystemMessage(content=JOB_RESEARCH_SYSTEM_PROMPT),
                    HumanMessage(
                        content=job_research_user_prompt(
                            analysis.role_title,
                            analysis.model_dump_json(),
                            json.dumps(
                                [item.model_dump(mode="json") for item in sources],
                                ensure_ascii=False,
                            ),
                        )
                    ),
                ]
            )
            research = _materialize_research(
                analysis,
                draft,
                queries,
                sources,
                ResearchStatus.COMPLETED,
            )
        except Exception as exc:
            if not settings.allow_heuristic_fallback:
                raise
            warnings.append(f"岗位研究模型总结失败，已使用规则回退：{exc}")

    if research is None:
        status = ResearchStatus.PARTIAL if sources else ResearchStatus.UNAVAILABLE
        research = _heuristic_research(analysis, queries, sources, status)
        if not sources:
            warnings.append("未获取到岗位搜索结果，岗位说明仅根据 JD 生成。")

    augmented = _augment_analysis(analysis, research)
    return {
        "jd_analysis": augmented.model_dump(mode="json"),
        "job_research": research.model_dump(mode="json"),
        "warnings": warnings,
    }


def _materialize_research(
    analysis: JDAnalysis,
    draft: JobResearchDraft,
    queries: list[str],
    sources: list[JobResearchSource],
    status: ResearchStatus,
) -> JobResearch:
    return JobResearch(
        role_title=analysis.role_title,
        role_summary=draft.role_summary.strip() or _role_summary(analysis),
        core_capabilities=_dedupe(draft.core_capabilities)[:12],
        typical_responsibilities=_dedupe(draft.typical_responsibilities)[:10],
        common_tools=_dedupe(draft.common_tools)[:15],
        market_keywords=_dedupe(draft.market_keywords)[:20],
        search_queries=queries,
        sources=sources,
        status=status,
    )


def _heuristic_research(
    analysis: JDAnalysis,
    queries: list[str],
    sources: list[JobResearchSource],
    status: ResearchStatus,
) -> JobResearch:
    searchable = " ".join(
        [analysis.role_title, *analysis.responsibilities]
        + [f"{item.title} {item.snippet}" for item in sources]
    )
    ability_candidates = [
        *ABILITY_PATTERN.findall(searchable),
        *GENERIC_ABILITY_PATTERN.findall(searchable),
    ]
    abilities = [
        cleaned
        for item in ability_candidates
        if (cleaned := _clean_capability(item)) and _safe_market_text(cleaned)
    ]
    tools = [skill for skill in MARKET_TOOLS if skill.casefold() in searchable.casefold()]
    core = _dedupe([*abilities, *analysis.required_skills, *analysis.preferred_skills, *tools])[:12]
    responsibilities = _dedupe(
        [item for item in analysis.responsibilities if _safe_market_text(item)]
        + [
            cleaned
            for source in sources
            for sentence in re.split(r"[。；;]", source.snippet)
            if (cleaned := _clean_responsibility(sentence))
            if _safe_market_text(cleaned)
            if any(
                token in cleaned
                for token in ("负责", "职责", "工作", "完成", "创建", "开发", "设计", "根据需求")
            )
        ]
    )[:10]
    market_keywords = _dedupe([*core, *tools, *analysis.keywords])[:20]
    return JobResearch(
        role_title=analysis.role_title,
        role_summary=_role_summary(analysis, responsibilities, core),
        core_capabilities=core,
        typical_responsibilities=responsibilities,
        common_tools=_dedupe(tools)[:15],
        market_keywords=market_keywords,
        search_queries=queries,
        sources=sources,
        status=status,
    )


def _role_summary(
    analysis: JDAnalysis,
    responsibilities: list[str] | None = None,
    capabilities: list[str] | None = None,
) -> str:
    responsibilities = responsibilities or analysis.responsibilities
    capabilities = capabilities or [*analysis.required_skills, *analysis.preferred_skills]
    responsibility_text = (
        "；".join(item[:100] for item in responsibilities[:3]) or "围绕岗位目标完成专业任务"
    )
    capability_text = "、".join(capabilities[:5]) or "相应的专业能力与协作能力"
    return (
        f"{analysis.role_title}是一个以{responsibility_text}为主要工作内容的岗位，"
        f"通常需要{capability_text}，并将专业方法转化为可交付成果。"
    )[:500]


def _augment_analysis(analysis: JDAnalysis, research: JobResearch) -> JDAnalysis:
    updated = analysis.model_copy(deep=True)
    existing = " ".join(item.text for item in updated.requirements).casefold()
    source_urls = [item.url for item in research.sources[:5]]
    for capability in research.core_capabilities:
        if capability.casefold() in existing:
            continue
        updated.requirements.append(
            JDRequirement(
                text=f"同类岗位常见核心能力：{capability}",
                category=_category(capability),
                priority=RequirementPriority.PREFERRED,
                weight=1.5,
                keywords=_capability_keywords(capability),
                origin=RequirementOrigin.MARKET_RESEARCH,
                source_urls=source_urls,
            )
        )
    updated.preferred_skills = _dedupe([*updated.preferred_skills, *research.common_tools])[:30]
    updated.keywords = _dedupe([*updated.keywords, *research.market_keywords])[:60]
    updated.requirements = updated.requirements[:60]
    return updated


def _capability_keywords(capability: str) -> list[str]:
    output = [capability]
    for marker, synonyms in CAPABILITY_SYNONYMS.items():
        if marker.casefold() in capability.casefold():
            output.extend(synonyms)
    output.extend(skill for skill in KNOWN_SKILLS if skill.casefold() in capability.casefold())
    return _dedupe(output)[:12]


def _category(text: str) -> FactCategory:
    if any(token in text for token in ("学历", "专业背景", "课程", "学校")):
        return FactCategory.EDUCATION
    if any(token in text for token in ("实习", "工作经验", "业务经验")):
        return FactCategory.INTERNSHIP
    if any(token in text for token in ("项目", "落地", "交付", "开发", "编码", "设计")):
        return FactCategory.PROJECT
    if any(token in text for token in ("沟通", "协作", "责任", "学习", "表达")):
        return FactCategory.PERSONAL
    return FactCategory.CAPABILITY


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in items if item and item.strip()))


def _clean_capability(value: str) -> str:
    parts = [item.strip() for item in re.split(r"[,，/]", value) if item.strip()]
    ability_parts = [item for item in parts if item.endswith(("能力", "经验", "技能", "基础"))]
    selected = ability_parts[-1] if ability_parts else value
    return re.sub(r"^(?:具备|需要|要求|拥有|较强的?|良好的?|优秀的?)+", "", selected).strip(
        " 】[，。；"
    )


def _clean_responsibility(value: str) -> str:
    cleaned = " ".join(value.split()).strip(" -•\t")
    for marker in ("职位描述:", "职位描述：", "核心职责】", "岗位职责:", "岗位职责："):
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[1]
    return cleaned[:220].strip()


def _safe_market_text(value: str) -> bool:
    return not any(term in value for term in PROHIBITED_MARKET_TERMS)
