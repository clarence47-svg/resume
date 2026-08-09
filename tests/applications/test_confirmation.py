from types import SimpleNamespace

import pytest

from applications.models import ApplicationPreview, ApplicationStatus
from applications.pipeline import ApplicationPipeline
from applications.preview import compute_preview_hash
from career.encryption import LocalEncryptor
from career.service import CareerService
from job_search.models import JobPlatform
from storage.files import FileStorage


@pytest.mark.asyncio
async def test_application_cannot_submit_without_matching_confirmation_hash(test_settings):
    encryptor = LocalEncryptor(test_settings)
    preview = ApplicationPreview(
        job_id="job-1",
        company="示例公司",
        title="Python 开发",
        platform=JobPlatform.GENERIC,
        job_url="https://example.com/apply",
        resume_version_id="resume-1",
        resume_filename="resume.docx",
    )
    preview.preview_hash = compute_preview_hash(preview)

    class FakeRepository:
        def get_application_row(self, application_id):
            return SimpleNamespace(
                status=ApplicationStatus.AWAITING_CONFIRMATION.value,
                preview_hash=preview.preview_hash,
                encrypted_preview=encryptor.encrypt(preview.model_dump_json()),
            )

    repository = FakeRepository()
    pipeline = ApplicationPipeline(
        repository,
        CareerService(repository, encryptor),
        encryptor,
        FileStorage(test_settings),
        test_settings,
    )
    with pytest.raises(ValueError, match="预览已变化"):
        await pipeline.confirm("application-1", "wrong-hash")
