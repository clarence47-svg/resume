from applications.platforms.base import PlatformAdapter


class AshbyAdapter(PlatformAdapter):
    platform = "ashby"
    submit_selectors = ('button[type="submit"]', 'button:has-text("Submit Application")')
