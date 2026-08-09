from types import SimpleNamespace

import pytest

from applications.browser.runtime import BrowserRuntime, resolve_cdp_url
from applications.platforms.boss import BossAdapter
from job_search.models import JobPlatform


class FakeLocator:
    def __init__(self, page, selector: str, exists: bool = False):
        self.page = page
        self.selector = selector
        self.exists = exists

    @property
    def first(self):
        return self

    async def count(self) -> int:
        return int(self.exists)

    async def is_visible(self) -> bool:
        return self.exists

    async def inner_text(self) -> str:
        return self.page.body_text

    async def fill(self, value: str) -> None:
        self.page.filled_message = value

    async def click(self) -> None:
        self.page.clicked_selectors.append(self.selector)
        if "发送" in self.selector or "btn-send" in self.selector:
            self.page.body_text = f"聊天记录\n{self.page.filled_message}"


class FakePage:
    def __init__(self) -> None:
        self.url = "https://www.zhipin.com/job_detail/demo.html"
        self.body_text = "岗位详情"
        self.filled_message = ""
        self.clicked_selectors: list[str] = []

    async def goto(self, url: str, **kwargs) -> None:
        del kwargs
        self.url = url

    def locator(self, selector: str) -> FakeLocator:
        exists = selector in {"body", "textarea", 'button:has-text("发送")'}
        return FakeLocator(self, selector, exists)

    async def wait_for_timeout(self, milliseconds: int) -> None:
        del milliseconds


@pytest.mark.asyncio
async def test_boss_adapter_previews_and_sends_greeting() -> None:
    adapter = BossAdapter()
    page = FakePage()
    greeting = "您好，我有 Python 和 FastAPI 项目经验，希望进一步沟通。"
    resume = SimpleNamespace(
        id="resume-1",
        docx_path="/tmp/resume.docx",
        pdf_path="",
        document=SimpleNamespace(
            application_materials=SimpleNamespace(boss_greeting=greeting),
            projects=[SimpleNamespace(name="项目 A")],
            competitions=[],
            internships=[],
        ),
    )
    job = SimpleNamespace(
        id="job-1",
        company="示例公司",
        title="Python 开发",
        platform=JobPlatform.BOSS,
        source_url=page.url,
        canonical_url=page.url,
    )

    preview = await adapter.prepare(
        page,
        job,
        resume,
        SimpleNamespace(display_name="测试用户"),
        [],
    )

    assert preview.action_kind == "boss_greeting"
    assert preview.message_preview == greeting
    assert "再次人工确认" in preview.delivery_note

    await adapter.submit(page)
    confirmation, _, _ = await adapter.verify(page)
    assert page.filled_message == greeting
    assert confirmation == "BOSS 招呼语已发送"


@pytest.mark.asyncio
async def test_browser_status_reports_disabled_without_connecting(test_settings) -> None:
    settings = test_settings.model_copy(update={"browser_automation_enabled": False})
    result = await BrowserRuntime(settings).inspect()
    assert not result.enabled
    assert not result.connected


def test_resolve_cdp_url_uses_ipv4_for_docker_hostname(monkeypatch) -> None:
    monkeypatch.setattr(
        "applications.browser.runtime.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("192.168.65.254", 9222))],
    )
    assert resolve_cdp_url("http://host.docker.internal:9222") == ("http://192.168.65.254:9222")
