import time

from fastapi.testclient import TestClient

from service.service import create_app


def test_match_uses_immutable_profile_snapshot(test_settings) -> None:
    app = create_app(test_settings)
    with TestClient(app) as client:
        profile_response = client.post(
            "/profiles",
            files={
                "files": (
                    "resume.md",
                    "# 专业介绍\n使用 Python 开发服务。",
                    "text/markdown",
                )
            },
            data={"review_mode": "auto", "title": "快照画像"},
        )
        profile_id = profile_response.json()["task_id"]
        for _ in range(100):
            profile_task = client.get(f"/profiles/{profile_id}").json()
            if profile_task["status"] in {"completed", "partial_success"}:
                break
            time.sleep(0.05)
        match_response = client.post(
            "/matches",
            json={
                "profile_task_id": profile_id,
                "jd_text": "Python 工程师\n任职要求：熟悉 Python 服务开发。",
            },
        )
        match_id = match_response.json()["match_id"]
        snapshot_before = list(app.state.match_repository.get_task(match_id).facts_snapshot)
        app.state.repository.replace_facts(profile_id, [])
        assert app.state.match_repository.get_task(match_id).facts_snapshot == snapshot_before
