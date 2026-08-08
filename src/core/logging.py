import logging

from core.settings import Settings, get_settings


def configure_logging(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    logging.basicConfig(
        level=getattr(logging, resolved.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
