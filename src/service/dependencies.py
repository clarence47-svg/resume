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
