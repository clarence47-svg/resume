async def detect_blockers(page) -> list[str]:
    text = (await page.locator("body").inner_text()).casefold()
    blockers = []
    if any(token in text for token in ("captcha", "验证码", "人机验证", "cloudflare")):
        blockers.append("captcha")
    if any(token in text for token in ("two-factor", "2fa", "otp", "一次性密码")):
        blockers.append("two_factor")
    password_fields = page.locator('input[type="password"]')
    if await password_fields.count() or any(
        token in page.url.casefold() for token in ("/login", "/signin", "passport")
    ):
        blockers.append("login_maybe_required")
    return blockers
