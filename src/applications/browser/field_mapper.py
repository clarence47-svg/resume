from applications.models import ApplicationField
from career.models import AnswerBankEntry, AnswerStatus, CareerSettings


def map_field(
    field: ApplicationField,
    settings: CareerSettings,
    answers: list[AnswerBankEntry],
) -> ApplicationField:
    label = f"{field.key} {field.label}".casefold()
    mapping = (
        (("name", "姓名", "名字"), settings.display_name, "career_settings"),
        (("email", "邮箱"), settings.email, "career_settings"),
        (("phone", "mobile", "电话", "手机"), settings.phone, "career_settings"),
        (("city", "location", "城市", "地点"), settings.city, "career_settings"),
        (("address", "地址"), settings.address, "career_settings"),
        (("linkedin",), settings.linkedin_url, "career_settings"),
        (("github",), settings.github_url, "career_settings"),
        (("portfolio", "个人网站"), settings.portfolio_url, "career_settings"),
    )
    for tokens, value, source in mapping:
        if value and any(token in label for token in tokens):
            field.value = str(value)
            field.source = source
            field.confirmed = not field.sensitive
            return field
    for answer in answers:
        if answer.status != AnswerStatus.CONFIRMED:
            continue
        if answer.question_key.casefold() in label or answer.question.casefold() in label:
            field.value = answer.answer
            field.source = f"answer_bank:{answer.id}"
            field.confirmed = not field.sensitive
            return field
    return field
