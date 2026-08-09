from applications.platforms.base import PlatformAdapter


class GreenhouseAdapter(PlatformAdapter):
    platform = "greenhouse"
    submit_selectors = ('button[type="submit"]', "#submit_app", 'input[type="submit"]')
