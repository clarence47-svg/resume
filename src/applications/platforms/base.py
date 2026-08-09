from applications.browser.field_mapper import map_field
from applications.browser.form_detector import detect_form_fields
from applications.browser.safety import detect_blockers
from applications.browser.uploader import upload_resume
from applications.models import ApplicationPreview


class PlatformAdapter:
    platform = "generic"
    submit_selectors = (
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Submit")',
        'button:has-text("提交")',
        'button:has-text("Apply")',
    )

    async def prepare(self, page, job, resume, settings, answers) -> ApplicationPreview:
        await page.goto(job.source_url or job.canonical_url, wait_until="domcontentloaded")
        blockers = await detect_blockers(page)
        fields = [map_field(field, settings, answers) for field in await detect_form_fields(page)]
        await self._fill(page, fields)
        uploaded = await upload_resume(page, resume.docx_path or resume.pdf_path)
        warnings = [] if uploaded else ["未找到简历上传控件或简历文件不存在。"]
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
            fields=fields,
            warnings=warnings,
            blockers=blockers,
            submit_label=await self._submit_label(page),
        )

    async def submit(self, page) -> None:
        for selector in self.submit_selectors:
            target = page.locator(selector)
            if await target.count():
                await target.first.click()
                await page.wait_for_load_state("domcontentloaded")
                return
        raise RuntimeError("未找到明确的提交按钮。")

    async def verify(self, page) -> tuple[str, str, str]:
        text = (await page.locator("body").inner_text()).strip()
        success_lines = [
            line
            for line in text.splitlines()
            if any(
                token in line.casefold()
                for token in (
                    "application submitted",
                    "thank you for applying",
                    "申请已提交",
                    "投递成功",
                    "发送成功",
                )
            )
        ]
        reference = ""
        return (success_lines[0] if success_lines else "", page.url, reference)

    async def _fill(self, page, fields) -> None:
        for field in fields:
            if not field.value or field.sensitive:
                continue
            selector = f'[name="{field.key}"], #{field.key}'
            target = page.locator(selector)
            if await target.count() == 0:
                continue
            element = target.first
            tag = await element.evaluate("element => element.tagName.toLowerCase()")
            if tag == "select":
                try:
                    await element.select_option(label=field.value)
                except Exception:
                    continue
            else:
                await element.fill(field.value)

    async def _submit_label(self, page) -> str:
        for selector in self.submit_selectors:
            target = page.locator(selector)
            if await target.count():
                return (await target.first.inner_text()).strip() or "提交申请"
        return "提交申请"
