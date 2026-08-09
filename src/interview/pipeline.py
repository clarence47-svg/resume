from interview.exporters import export_interview_markdown
from interview.models import InterviewKit, InterviewQuestion, StarStory
from storage.career_repositories import CareerRepository
from storage.files import FileStorage


class InterviewPipeline:
    def __init__(self, repository: CareerRepository, storage: FileStorage):
        self.repository = repository
        self.storage = storage

    def generate(self, job_id: str, resume_version_id: str) -> InterviewKit:
        job = self.repository.get_job(job_id)
        resume = self.repository.get_resume(resume_version_id)
        evaluation = self.repository.get_evaluation(job_id)
        if job is None or resume is None or resume.job_id != job_id:
            raise KeyError("job_or_resume")
        experiences = [
            item
            for group in (
                resume.document.projects,
                resume.document.internships,
                resume.document.competitions,
            )
            for item in group
        ]
        stories = [_story(item) for item in experiences[:4]]
        kit = InterviewKit(
            job_id=job_id,
            resume_version_id=resume_version_id,
            role_summary=(
                f"目标岗位为 {job.company} 的 {job.title}，重点围绕岗位职责和已匹配能力准备。"
            ),
            self_introduction=resume.document.summary,
            star_stories=stories,
            likely_questions=[
                InterviewQuestion(
                    question=f"请介绍你在“{item.name}”中的具体贡献。",
                    answer_outline=[bullet.content for bullet in item.bullets[:3]]
                    or [item.summary],
                    category="experience",
                )
                for item in experiences[:5]
            ],
            questions_to_ask=[
                "这个岗位入职前三个月最重要的交付目标是什么？",
                "团队如何衡量该岗位的成功？",
                "目前团队在技术或业务上最大的挑战是什么？",
            ],
            risks_and_gaps=evaluation.gaps if evaluation else [],
        )
        path = export_interview_markdown(kit, self.storage.interview_export_path(kit.id))
        self.repository.save_interview_kit(kit, str(path))
        return kit


def _story(item) -> StarStory:
    actions = [bullet.content for bullet in item.bullets]
    return StarStory(
        title=item.name,
        situation=item.summary or f"参与 {item.name}。",
        task=item.role or "承担与目标岗位相关的核心工作。",
        action="；".join(actions[:3]) or "根据项目目标推进关键任务。",
        result=actions[-1] if actions else "形成可复用的项目经验。",
        source_fact_ids=list(
            dict.fromkeys(fact_id for bullet in item.bullets for fact_id in bullet.source_fact_ids)
        ),
    )
