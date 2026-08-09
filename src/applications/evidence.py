from datetime import UTC, datetime

from applications.models import ApplicationEvidence


def verified_evidence(
    confirmation_text: str,
    confirmation_url: str,
    application_reference: str = "",
    screenshot_path: str = "",
) -> ApplicationEvidence | None:
    if not any((confirmation_text.strip(), application_reference.strip())):
        return None
    return ApplicationEvidence(
        confirmation_text=confirmation_text.strip(),
        confirmation_url=confirmation_url.strip(),
        application_reference=application_reference.strip(),
        screenshot_path=screenshot_path,
        submitted_at=datetime.now(UTC),
    )
