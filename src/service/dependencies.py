from fastapi import Request


def get_repository(request: Request):
    return request.app.state.repository


def get_storage(request: Request):
    return request.app.state.storage


def get_job_runner(request: Request):
    return request.app.state.job_runner


def get_match_repository(request: Request):
    return request.app.state.match_repository


def get_match_job_runner(request: Request):
    return request.app.state.match_job_runner


def get_career_repository(request: Request):
    return request.app.state.career_repository


def get_career_service(request: Request):
    return request.app.state.career_service


def get_job_discovery_pipeline(request: Request):
    return request.app.state.job_discovery_pipeline


def get_batch_tailoring_service(request: Request):
    return request.app.state.batch_tailoring_service


def get_resume_pipeline(request: Request):
    return request.app.state.resume_pipeline


def get_application_pipeline(request: Request):
    return request.app.state.application_pipeline


def get_application_runner(request: Request):
    return request.app.state.application_runner


def get_interview_pipeline(request: Request):
    return request.app.state.interview_pipeline
