from applications.browser.safety import detect_blockers
from applications.models import ApplicationPreview
from applications.platforms.base import PlatformAdapter


class BossAdapter(PlatformAdapter):
    platform = "boss"
    start_chat_selectors = (
        'button:has-text("立即沟通")',
        'button:has-text("继续沟通")',
        'a:has-text("立即沟通")',
        'a:has-text("继续沟通")',
        ".btn-startchat",
    )
    message_input_selectors = (
        "textarea",
        '[contenteditable="true"]',
        ".chat-input textarea",
        ".chat-input-textarea",
    )
    submit_selectors = ('button:has-text("发送")', ".btn-send")

    def __init__(self) -> None:
        self.message = ""

    async def prepare(self, page, job, resume, settings, answers) -> ApplicationPreview:
        del answers
        await page.goto(job.source_url or job.canonical_url, wait_until="domcontentloaded")
        blockers = await detect_blockers(page)
        self.message = resume.document.application_materials.boss_greeting.strip()
        warnings = []
        if not self.message:
            warnings.append("当前简历版本没有 BOSS 招呼语，不能创建发送预览。")
        if not settings.display_name:
            warnings.append("建议先在求职设置中填写姓名。")
        return ApplicationPreview(
            job_id=job.id,
            company=job.company,
            title=job.title,
            platform=job.platform,
            job_url=page.url,
            resume_version_id=resume.id,
            resume_filename=(resume.docx_path or resume.pdf_path).split("/")[-1],
            selected_experiences=[
                item.name
                for group in (
                    resume.document.projects,
                    resume.document.competitions,
                    resume.document.internships,
                )
                for item in group
            ],
            warnings=warnings,
            blockers=blockers,
            submit_label="发送 BOSS 招呼语",
            action_kind="boss_greeting",
            message_preview=self.message,
            delivery_note="确认后仅发送招呼语；HR 索要简历时需再次人工确认附件发送。",
        )

    async def submit(self, page) -> None:
        if not self.message:
            raise RuntimeError("BOSS 招呼语为空。")
        input_locator = await self._message_input(page)
        if input_locator is None:
            for selector in self.start_chat_selectors:
                target = page.locator(selector)
                if await target.count() and await target.first.is_visible():
                    await target.first.click()
                    await page.wait_for_timeout(1200)
                    break
            input_locator = await self._message_input(page)
        if input_locator is None:
            raise RuntimeError("未找到 BOSS 沟通输入框，请在浏览器中检查登录和岗位状态。")
        await input_locator.fill(self.message)
        for selector in self.submit_selectors:
            target = page.locator(selector)
            if await target.count() and await target.first.is_visible():
                await target.first.click()
                await page.wait_for_timeout(1200)
                return
        raise RuntimeError("未找到 BOSS 消息发送按钮。")

    async def verify(self, page) -> tuple[str, str, str]:
        text = (await page.locator("body").inner_text()).strip()
        fingerprint = self.message[:24]
        if fingerprint and fingerprint in text:
            return ("BOSS 招呼语已发送", page.url, "")
        return await super().verify(page)

    async def _message_input(self, page):
        for selector in self.message_input_selectors:
            target = page.locator(selector)
            if await target.count() and await target.first.is_visible():
                return target.first
        return None
