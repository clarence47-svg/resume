import re

from applications.models import ApplicationField


async def detect_form_fields(page) -> list[ApplicationField]:
    fields: list[ApplicationField] = []
    locators = page.locator("input, textarea, select")
    for index in range(await locators.count()):
        element = locators.nth(index)
        field_type = (await element.get_attribute("type") or "text").casefold()
        if field_type in {"hidden", "submit", "button", "file"}:
            continue
        name = await element.get_attribute("name") or await element.get_attribute("id") or ""
        label = await _label_for(page, element, name)
        required = await element.get_attribute("required") is not None
        fields.append(
            ApplicationField(
                key=name or f"field_{index}",
                label=label or name or f"字段 {index + 1}",
                value="",
                source="unknown" if required else "optional",
                sensitive=_sensitive(label or name),
            )
        )
    return fields


async def _label_for(page, element, name: str) -> str:
    element_id = await element.get_attribute("id")
    if element_id:
        label = page.locator(f'label[for="{element_id}"]')
        if await label.count():
            return (await label.first.inner_text()).strip()
    aria = await element.get_attribute("aria-label")
    placeholder = await element.get_attribute("placeholder")
    return (aria or placeholder or name).strip()


def _sensitive(value: str) -> bool:
    return bool(
        re.search(
            r"身份证|护照|签证|工作许可|残疾|民族|宗教|性别|婚姻|sponsor|visa|race|gender|disability",
            value,
            re.IGNORECASE,
        )
    )
