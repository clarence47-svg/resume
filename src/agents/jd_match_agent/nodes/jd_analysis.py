import re
from profile.models import FactCategory

from langchain_core.messages import HumanMessage, SystemMessage

from agents.jd_match_agent.prompts.jd_analysis import (
    JD_ANALYSIS_SYSTEM_PROMPT,
    jd_analysis_user_prompt,
)
from agents.jd_match_agent.schemas import (
    CapabilityDimensionDraft,
    JDAnalysisDraft,
    JDRequirementDraft,
)
from core.model import get_match_model
from core.settings import get_settings
from matching.models import (
    CapabilityDimension,
    JDAnalysis,
    JDRequirement,
    RequirementPriority,
)

PRIORITY_WEIGHTS = {
    RequirementPriority.REQUIRED: 3.0,
    RequirementPriority.PREFERRED: 1.5,
    RequirementPriority.CONTEXT: 0.5,
}
KNOWN_SKILLS = (
    "Python",
    "Java",
    "C++",
    "Go",
    "JavaScript",
    "TypeScript",
    "SQL",
    "FastAPI",
    "Django",
    "Flask",
    "Spring",
    "Vue",
    "React",
    "PostgreSQL",
    "MySQL",
    "Redis",
    "Docker",
    "Kubernetes",
    "Linux",
    "Git",
    "机器学习",
    "深度学习",
    "大模型",
    "数据分析",
    "算法",
)
CAPABILITY_GROUPS = (
    ("编程与开发", ("Python", "Java", "C++", "Go", "JavaScript", "TypeScript", "开发", "编码")),
    ("框架与工程", ("FastAPI", "Django", "Flask", "Spring", "Vue", "React", "架构", "系统")),
    ("数据与存储", ("SQL", "PostgreSQL", "MySQL", "Redis", "数据分析", "数据库", "数据")),
    ("云端与交付", ("Docker", "Kubernetes", "Linux", "Git", "DevOps", "云", "部署", "交付")),
    ("算法与 AI", ("机器学习", "深度学习", "大模型", "算法", "模型", "AIGC", "LLM")),
    ("产品与业务", ("产品", "用户", "需求", "运营", "增长", "商业", "行业", "市场")),
    ("协作与推动", ("沟通", "协作", "项目管理", "推动", "团队", "跨部门", "领导")),
)


async def analyze_jd(state: dict) -> dict:
    settings = get_settings()
    warnings: list[str] = []
    if settings.llm_configured:
        try:
            model = get_match_model(settings).with_structured_output(JDAnalysisDraft)
            draft = await model.ainvoke(
                [
                    SystemMessage(content=JD_ANALYSIS_SYSTEM_PROMPT),
                    HumanMessage(content=jd_analysis_user_prompt(state["jd_text"])),
                ]
            )
        except Exception as exc:
            if not settings.allow_heuristic_fallback:
                raise
            warnings.append(f"JD 模型分析失败，已使用规则回退：{exc}")
            draft = _heuristic_analysis(state["jd_text"])
    else:
        draft = _heuristic_analysis(state["jd_text"])
    analysis = _materialize(draft, state["jd_text"])
    return {"jd_analysis": analysis.model_dump(mode="json"), "warnings": warnings}


def _materialize(draft: JDAnalysisDraft, jd_text: str) -> JDAnalysis:
    requirements = [
        JDRequirement(
            text=item.text.strip(),
            category=item.category,
            priority=item.priority,
            weight=PRIORITY_WEIGHTS[item.priority],
            keywords=_dedupe(item.keywords),
        )
        for item in draft.requirements
        if item.text.strip()
    ]
    if not requirements:
        fallback = _heuristic_analysis(jd_text)
        requirements = [
            JDRequirement(
                text=item.text,
                category=item.category,
                priority=item.priority,
                weight=PRIORITY_WEIGHTS[item.priority],
                keywords=item.keywords,
            )
            for item in fallback.requirements
        ]
    dimensions = _materialize_dimensions(draft.capability_dimensions, requirements, jd_text)
    return JDAnalysis(
        role_title=draft.role_title.strip() or "目标岗位",
        seniority=draft.seniority,
        responsibilities=_dedupe(draft.responsibilities),
        required_skills=_dedupe(draft.required_skills),
        preferred_skills=_dedupe(draft.preferred_skills),
        experience_requirements=_dedupe(draft.experience_requirements),
        education_requirements=_dedupe(draft.education_requirements),
        keywords=_dedupe(draft.keywords),
        requirements=requirements,
        capability_dimensions=dimensions,
    )


def _heuristic_analysis(jd_text: str) -> JDAnalysisDraft:
    lines = [item.strip(" -•\t") for item in jd_text.splitlines() if item.strip()]
    role_title = lines[0][:60] if lines else "目标岗位"
    requirements: list[JDRequirementDraft] = []
    responsibilities: list[str] = []
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    experience: list[str] = []
    education: list[str] = []
    all_keywords = _extract_keywords(jd_text)
    for line in lines[1:] or lines:
        priority = _priority(line)
        category = _category(line)
        keywords = [item for item in all_keywords if item.casefold() in line.casefold()]
        requirements.append(
            JDRequirementDraft(
                text=line[:500], category=category, priority=priority, keywords=keywords
            )
        )
        if "负责" in line or "职责" in line:
            responsibilities.append(line)
        if "经验" in line or re.search(r"\d+\s*年", line):
            experience.append(line)
        if any(token in line for token in ("本科", "硕士", "博士", "学历", "专业")):
            education.append(line)
        target = preferred_skills if priority == RequirementPriority.PREFERRED else required_skills
        target.extend(keywords)
    return JDAnalysisDraft(
        role_title=role_title,
        responsibilities=responsibilities,
        required_skills=_dedupe(required_skills),
        preferred_skills=_dedupe(preferred_skills),
        experience_requirements=experience,
        education_requirements=education,
        keywords=all_keywords,
        requirements=requirements[:40],
        capability_dimensions=_heuristic_dimension_drafts(jd_text, requirements),
    )


def _materialize_dimensions(
    drafts: list[CapabilityDimensionDraft],
    requirements: list[JDRequirement],
    jd_text: str,
) -> list[CapabilityDimension]:
    source = drafts or _heuristic_dimension_drafts(jd_text, requirements)
    output: list[CapabilityDimension] = []
    seen: set[str] = set()
    for draft in source:
        name = draft.name.strip()
        normalized = name.casefold()
        if not name or normalized in seen:
            continue
        seen.add(normalized)
        keywords = _dedupe(draft.keywords or _extract_keywords(draft.description))
        match_tokens = [*keywords, *_extract_keywords(name)]
        requirement_ids = [
            item.id for item in requirements if _dimension_matches_requirement(match_tokens, item)
        ]
        weight = sum(item.weight for item in requirements if item.id in set(requirement_ids)) or 1
        output.append(
            CapabilityDimension(
                name=name,
                description=draft.description.strip(),
                keywords=keywords,
                requirement_ids=requirement_ids,
                weight=weight,
            )
        )
        if len(output) == 6:
            break
    return output


def _heuristic_dimension_drafts(
    jd_text: str,
    requirements: list[JDRequirementDraft] | list[JDRequirement],
) -> list[CapabilityDimensionDraft]:
    dimensions: list[CapabilityDimensionDraft] = []
    for name, triggers in CAPABILITY_GROUPS:
        matched = [token for token in triggers if token.casefold() in jd_text.casefold()]
        if matched:
            dimensions.append(
                CapabilityDimensionDraft(
                    name=name,
                    description=f"岗位对{'、'.join(matched[:4])}相关能力的要求。",
                    keywords=matched,
                )
            )
    categories = {item.category for item in requirements}
    supplements = (
        (FactCategory.PROJECT, "项目落地", ("项目", "落地", "成果")),
        (FactCategory.INTERNSHIP, "岗位实践", ("实习", "工作经验", "岗位")),
        (FactCategory.EDUCATION, "教育背景", ("学历", "专业", "本科", "硕士", "博士")),
    )
    for category, name, triggers in supplements:
        if category in categories and not any(item.name == name for item in dimensions):
            dimensions.append(
                CapabilityDimensionDraft(
                    name=name,
                    description=f"JD 中与{name}相关的要求。",
                    keywords=[token for token in triggers if token in jd_text],
                )
            )
    if not dimensions:
        dimensions.append(
            CapabilityDimensionDraft(
                name="岗位核心要求",
                description="根据当前 JD 的职责与任职要求动态生成。",
                keywords=_extract_keywords(jd_text)[:12],
            )
        )
    return dimensions[:6]


def _dimension_matches_requirement(tokens: list[str], requirement: JDRequirement) -> bool:
    if not tokens:
        return False
    searchable = f"{requirement.text} {' '.join(requirement.keywords)}".casefold()
    return any(token.casefold() in searchable for token in tokens)


def _priority(text: str) -> RequirementPriority:
    if any(token in text for token in ("优先", "加分", "最好", "bonus")):
        return RequirementPriority.PREFERRED
    if any(token in text for token in ("必须", "要求", "熟悉", "掌握", "精通", "具备")):
        return RequirementPriority.REQUIRED
    return RequirementPriority.CONTEXT


def _category(text: str) -> FactCategory:
    if any(token in text for token in ("本科", "硕士", "博士", "学历", "学校", "专业")):
        return FactCategory.EDUCATION
    if any(token in text for token in ("比赛", "竞赛", "奖项")):
        return FactCategory.COMPETITION
    if any(token in text for token in ("实习", "工作经验", "岗位经验")):
        return FactCategory.INTERNSHIP
    if any(token in text for token in ("项目", "开发", "设计", "落地", "系统")):
        return FactCategory.PROJECT
    if any(token in text for token in ("沟通", "协作", "责任", "主动", "学习能力")):
        return FactCategory.PERSONAL
    return FactCategory.CAPABILITY


def _extract_keywords(text: str) -> list[str]:
    found = [skill for skill in KNOWN_SKILLS if skill.casefold() in text.casefold()]
    found.extend(re.findall(r"\b[A-Za-z][A-Za-z0-9+#.\-]{1,30}\b", text))
    return _dedupe(found)[:40]


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in items if item.strip()))
