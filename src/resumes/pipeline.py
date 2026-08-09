from profile.models import ProfileFact

from career.service import CareerService
from matching.models import JDMatchResult
from resumes.ats import audit_resume
from resumes.composition import compose_resume
from resumes.exporters import export_docx, export_html, export_markdown, export_pdf
from resumes.models import ResumeTemplate, ResumeVersion
from resumes.pagination import plan_pages
from resumes.source_documents import write_resume_source_documents
from storage.career_repositories import CareerRepository
from storage.files import FileStorage
from storage.repositories import MatchRepository


class ResumePipeline:
    def __init__(
        self,
        career_repository: CareerRepository,
        match_repository: MatchRepository,
        career_service: CareerService,
        storage: FileStorage,
    ):
        self.career_repository = career_repository
        self.match_repository = match_repository
        self.career_service = career_service
        self.storage = storage

    def build(
        self,
        job_id: str,
        match_id: str,
        template: ResumeTemplate,
        match_version: int | None = None,
    ) -> ResumeVersion:
        job = self.career_repository.get_job(job_id)
        task = self.match_repository.get_task(match_id)
        if job is None or task is None or task.job_id not in {None, job_id}:
            raise KeyError("job_or_match")
        result = (
            self.match_repository.get_version(match_id, match_version)
            if match_version
            else self.match_repository.get_result(match_id)
        )
        if result is None:
            raise RuntimeError("JD 匹配结果尚未生成。")
        result = JDMatchResult.model_validate(result)
        document = compose_resume(result, job, self.career_service.get_settings(), template)
        document = plan_pages(document)
        document.audit = audit_resume(document, job.jd_text)
        version_number = self.career_repository.next_resume_version(job_id)
        paths = self.storage.resume_export_paths(job_id, version_number)
        write_resume_source_documents(
            result,
            [ProfileFact.model_validate(item) for item in task.facts_snapshot],
            paths["documents"],
        )
        export_markdown(document, paths["markdown"])
        export_html(document, paths["html"])
        export_docx(document, paths["docx"])
        pdf = export_pdf(paths["docx"], paths["pdf"], paths["html"])
        resume = ResumeVersion(
            job_id=job_id,
            profile_task_id=job.profile_task_id,
            match_id=match_id,
            match_version=result.version,
            version=version_number,
            template=template,
            document=document,
            markdown_path=str(paths["markdown"]),
            html_path=str(paths["html"]),
            docx_path=str(paths["docx"]),
            pdf_path=str(pdf) if pdf else "",
        )
        self.career_repository.save_resume(resume)
        return resume
