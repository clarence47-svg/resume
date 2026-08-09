from pathlib import Path

from matching.models import (
    JDMatchResult,
    TailoredEducationSection,
    TailoredExperienceSection,
    TailoredTextSection,
)

SECTION_TITLES = {
    "personal_introduction": "个人介绍",
    "professional_introduction": "专业介绍",
    "project_experiences": "项目经历",
    "competition_experiences": "比赛经历",
    "internship_experiences": "实习经历",
    "education_history": "学校履历",
}


def export_match_markdown(result: JDMatchResult, path: Path) -> Path:
    lines = [
        f"# {result.jd_analysis.role_title} · JD 匹配文案",
        "",
        f"- 总匹配度：{result.overall_score:.1f}",
        f"- 版本：v{result.version}",
        f"- 模型：{result.model}",
        f"- 匹配关键词：{'、'.join(result.keyword_coverage.matched) or '无'}",
        f"- 缺失关键词：{'、'.join(result.keyword_coverage.missing) or '无'}",
        "",
        "## 岗位说明",
        "",
        result.job_research.role_summary,
        "",
        f"- 联网研究状态：{result.job_research.status.value}",
        f"- 核心能力：{'、'.join(result.job_research.core_capabilities) or '未识别'}",
        f"- 常见职责：{'；'.join(result.job_research.typical_responsibilities) or '未识别'}",
        f"- 常见工具：{'、'.join(result.job_research.common_tools) or '未识别'}",
        f"- 市场关键词：{'、'.join(result.job_research.market_keywords) or '未识别'}",
        "",
        "### 参考来源",
        "",
    ]
    lines.extend(
        f"- [{source.title}]({source.url})：{source.snippet}"
        for source in result.job_research.sources
    )
    if not result.job_research.sources:
        lines.append("- 未获取到联网搜索来源。")
    lines.extend(
        [
            "",
            "## 匹配分析",
            "",
        ]
    )
    lines.extend(f"- 优势：{item}" for item in result.strengths)
    lines.extend(f"- 缺口：{item}" for item in result.gaps)
    lines.append("")
    for field, title in SECTION_TITLES.items():
        lines.extend(_section(title, getattr(result, field)))
    lines.extend(["## 质量审计", "", f"- 证据覆盖率：{result.audit.evidence_coverage:.0%}"])
    lines.extend(f"- {warning}" for warning in result.audit.warnings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path


def _section(
    title: str, section: TailoredTextSection | TailoredExperienceSection | TailoredEducationSection
) -> list[str]:
    lines = [f"## {title}", "", section.overview.content, ""]
    if isinstance(section, TailoredTextSection):
        lines.extend(f"- {item.content}" for item in section.bullets)
        if section.keywords:
            lines.extend(["", f"关键词：{'、'.join(section.keywords)}"])
    else:
        for entry in section.entries:
            name = getattr(entry, "name", None) or getattr(entry, "institution", "")
            lines.extend(["", f"### {name}", "", entry.tailored_summary.content, ""])
            if hasattr(entry, "organization"):
                lines.extend(
                    [
                        f"- 单位/组织：{entry.organization or '资料未提供'}",
                        f"- 时间：{entry.period or '资料未提供'}",
                        f"- 角色：{entry.role or '资料未提供'}",
                        f"- 核心技术：{'、'.join(entry.technologies) or '资料未提供'}",
                    ]
                )
            else:
                lines.extend(
                    [
                        f"- 学历：{entry.degree or '资料未提供'}",
                        f"- 专业：{entry.major or '资料未提供'}",
                        f"- 时间：{entry.period or '资料未提供'}",
                    ]
                )
            lines.extend(f"- {item.content}" for item in entry.bullets)
    lines.append("")
    return lines
