from applications.models import ApplicationPreview

SENSITIVE_TOKENS = (
    "政治",
    "宗教",
    "民族",
    "健康",
    "残疾",
    "婚姻",
    "性别",
    "年龄",
    "身份证",
    "护照",
    "签证",
    "工作许可",
    "sponsorship",
    "veteran",
    "disability",
    "race",
    "gender",
)


def validate_preview(preview: ApplicationPreview) -> list[str]:
    blockers = list(preview.blockers)
    for field in preview.fields:
        label = f"{field.key} {field.label}".casefold()
        if field.sensitive or any(token.casefold() in label for token in SENSITIVE_TOKENS):
            if not field.confirmed:
                blockers.append(f"敏感字段需要用户确认：{field.label}")
        if not field.value and field.source == "unknown":
            blockers.append(f"未知必填字段需要用户处理：{field.label}")
    return list(dict.fromkeys(blockers))
