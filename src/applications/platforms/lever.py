from applications.platforms.base import PlatformAdapter


class LeverAdapter(PlatformAdapter):
    platform = "lever"
    submit_selectors = ('button[type="submit"]', ".template-btn-submit", 'input[type="submit"]')
