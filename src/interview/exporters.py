from pathlib import Path

from interview.models import InterviewKit


def export_interview_markdown(kit: InterviewKit, path: Path) -> Path:
    lines = [
        "# 面试准备包",
        "",
        "## 岗位理解",
        kit.role_summary,
        "",
        "## 自我介绍",
        kit.self_introduction,
    ]
    if kit.star_stories:
        lines.extend(["", "## STAR 故事"])
        for story in kit.star_stories:
            lines.extend(
                [
                    f"### {story.title}",
                    f"- 情境：{story.situation}",
                    f"- 任务：{story.task}",
                    f"- 行动：{story.action}",
                    f"- 结果：{story.result}",
                ]
            )
    if kit.likely_questions:
        lines.extend(["", "## 高频问题"])
        for item in kit.likely_questions:
            lines.append(f"### {item.question}")
            lines.extend(f"- {answer}" for answer in item.answer_outline)
    if kit.questions_to_ask:
        lines.extend(["", "## 反问问题"])
        lines.extend(f"- {item}" for item in kit.questions_to_ask)
    if kit.risks_and_gaps:
        lines.extend(["", "## 风险与缺口"])
        lines.extend(f"- {item}" for item in kit.risks_and_gaps)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path
