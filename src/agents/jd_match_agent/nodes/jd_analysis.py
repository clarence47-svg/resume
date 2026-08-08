import re
from profile.models import FactCategory

from langchain_core.messages import HumanMessage, SystemMessage

from agents.jd_match_agent.prompts.jd_analysis import (
    JD_ANALYSIS_SYSTEM_PROMPT,
    jd_analysis_user_prompt,
)
from agents.jd_match_agent.schemas import JDAnalysisDraft, JDRequirementDraft
from core.model import get_match_model
from core.settings import get_settings
from matching.models import JDAnalysis, JDRequirement, RequirementPriority

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
    )


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
    return FactCategory.PROFESSIONAL


def _extract_keywords(text: str) -> list[str]:
    found = [skill for skill in KNOWN_SKILLS if skill.casefold() in text.casefold()]
    found.extend(re.findall(r"\b[A-Za-z][A-Za-z0-9+#.\-]{1,30}\b", text))
    return _dedupe(found)[:40]


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in items if item.strip()))
