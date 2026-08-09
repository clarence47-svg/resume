import socket
from contextlib import asynccontextmanager
from urllib.parse import urlsplit, urlunsplit

from applications.browser.safety import detect_blockers
from applications.models import BrowserConnectionStatus
from core.settings import Settings

BOSS_HOME_URL = "https://www.zhipin.com/"


class BrowserRuntime:
    def __init__(self, settings: Settings):
        self.settings = settings

    @asynccontextmanager
    async def connect(self):
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        try:
            browser = await playwright.chromium.connect_over_cdp(
                resolve_cdp_url(self.settings.chrome_cdp_url),
                timeout=self.settings.browser_action_timeout_seconds * 1000,
            )
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            yield context
        finally:
            await playwright.stop()

    async def inspect(self, open_boss: bool = False) -> BrowserConnectionStatus:
        status = BrowserConnectionStatus(
            enabled=self.settings.browser_automation_enabled,
            cdp_url=self.settings.chrome_cdp_url,
        )
        if not status.enabled:
            status.message = "浏览器自动化尚未启用。"
            return status
        try:
            async with self.connect() as context:
                status.connected = True
                browser = context.browser
                status.browser_version = browser.version if browser else ""
                if open_boss:
                    page = await context.new_page()
                    await page.goto(BOSS_HOME_URL, wait_until="domcontentloaded")
                boss_pages = [page for page in context.pages if "zhipin.com" in page.url.casefold()]
                if not boss_pages:
                    status.message = "已连接 Chrome，请打开 BOSS 直聘并完成登录。"
                    return status
                page = boss_pages[-1]
                status.boss_page_open = True
                status.boss_page_url = page.url
                status.blockers = await detect_blockers(page)
                status.boss_logged_in = await _boss_logged_in(page)
                if status.blockers:
                    status.message = "BOSS 页面需要人工处理登录或验证。"
                elif status.boss_logged_in:
                    status.message = "BOSS 直聘已连接并检测到登录状态。"
                else:
                    status.message = "BOSS 页面已打开，请在 Chrome 中登录后重新检测。"
                return status
        except Exception as exc:
            status.message = f"Chrome CDP 连接失败：{exc}"
            return status


async def _boss_logged_in(page) -> bool:
    if any(token in page.url.casefold() for token in ("/login", "passport", "signin")):
        return False
    selectors = (
        ".nav-figure",
        ".user-name",
        ".geek-name",
        '[ka="header-message"]',
        'a[href*="/web/geek/chat"]',
    )
    for selector in selectors:
        locator = page.locator(selector)
        if await locator.count() and await locator.first.is_visible():
            return True
    body_text = (await page.locator("body").inner_text()).casefold()
    has_login_prompt = any(token in body_text for token in ("登录/注册", "登录 boss 直聘"))
    has_member_navigation = "消息" in body_text and "在线简历" in body_text
    return has_member_navigation and not has_login_prompt


def resolve_cdp_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.hostname != "host.docker.internal":
        return url
    try:
        addresses = socket.getaddrinfo(parts.hostname, parts.port or 80, family=socket.AF_INET)
    except OSError:
        return url
    if not addresses:
        return url
    host = addresses[0][4][0]
    netloc = f"{host}:{parts.port}" if parts.port else host
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
