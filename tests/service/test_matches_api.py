import time

from fastapi.testclient import TestClient

from service.service import create_app


def _wait(client: TestClient, path: str, completed: set[str]) -> dict:
    task = {}
    for _ in range(200):
        task = client.get(path).json()
        if task["status"] in completed:
            break
        time.sleep(0.05)
    return task


def _create_profile(client: TestClient) -> str:
    response = client.post(
        "/profiles",
        files={
            "files": (
                "resume.md",
                "# 专业介绍\n熟练使用 Python 和 FastAPI。\n"
                "# 项目经历\n使用 Python 完成后端系统开发。",
                "text/markdown",
            )
        },
        data={"review_mode": "auto", "title": "测试画像"},
    )
    profile_id = response.json()["task_id"]
    task = _wait(
        client,
        f"/profiles/{profile_id}",
        {"completed", "partial_success", "failed_retryable"},
    )
    assert task["status"] in {"completed", "partial_success"}, task
    return profile_id


def _create_match(client: TestClient, profile_id: str) -> str:
    response = client.post(
        "/matches",
        json={
            "profile_task_id": profile_id,
            "title": "后端岗位匹配",
            "jd_text": "后端工程师\n任职要求：熟悉 Python 和 FastAPI。\n有 Docker 经验优先。",
        },
    )
    assert response.status_code == 202, response.text
    match_id = response.json()["match_id"]
    task = _wait(
        client,
        f"/matches/{match_id}",
        {"completed", "partial_success", "failed_retryable"},
    )
    assert task["status"] in {"completed", "partial_success"}, task
    return match_id


def test_match_api_versions_edit_restore_and_exports(test_settings) -> None:
    app = create_app(test_settings)
    with TestClient(app) as client:
        profile_id = _create_profile(client)
        match_id = _create_match(client, profile_id)
        result = client.get(f"/matches/{match_id}/result").json()["result"]
        unit = result["personal_introduction"]["overview"]
        edit = client.put(
            f"/matches/{match_id}/draft",
            json={
                "expected_version": result["version"],
                "updates": [{"unit_id": unit["id"], "content": f"{unit['content']}，突出岗位价值"}],
            },
        )
        assert edit.status_code == 200, edit.text
        assert edit.json()["result"]["version"] == 2
        restore = client.post(f"/matches/{match_id}/versions/1/restore")
        assert restore.status_code == 200
        assert restore.json()["result"]["version"] == 3
        versions = client.get(f"/matches/{match_id}/versions").json()
        assert [item["version"] for item in versions] == [3, 2, 1]
        for export_format in ("json", "md", "docx"):
            response = client.get(f"/matches/{match_id}/export", params={"format": export_format})
            assert response.status_code == 200
            assert response.content


def test_list_matches_includes_current_version(test_settings) -> None:
    app = create_app(test_settings)
    with TestClient(app) as client:
        profile_id = _create_profile(client)
        match_id = _create_match(client, profile_id)

        response = client.get("/matches")

        assert response.status_code == 200, response.text
        task = next(item for item in response.json() if item["id"] == match_id)
        assert task["profile_task_id"] == profile_id
        assert task["current_version"] == 1


def test_match_edit_rejects_unsupported_skill(test_settings) -> None:
    app = create_app(test_settings)
    with TestClient(app) as client:
        profile_id = _create_profile(client)
        match_id = _create_match(client, profile_id)
        result = client.get(f"/matches/{match_id}/result").json()["result"]
        unit = result["personal_introduction"]["overview"]
        response = client.put(
            f"/matches/{match_id}/draft",
            json={
                "expected_version": result["version"],
                "updates": [{"unit_id": unit["id"], "content": "精通 Docker 容器平台"}],
            },
        )
        assert response.status_code == 422


def test_deleting_profile_cascades_match(test_settings) -> None:
    app = create_app(test_settings)
    with TestClient(app) as client:
        profile_id = _create_profile(client)
        match_id = _create_match(client, profile_id)
        response = client.delete(f"/profiles/{profile_id}")
        assert response.status_code == 200
        assert client.get(f"/matches/{match_id}").status_code == 404


def test_match_can_be_deleted_immediately_after_creation(test_settings) -> None:
    app = create_app(test_settings)
    with TestClient(app) as client:
        profile_id = _create_profile(client)
        response = client.post(
            "/matches",
            json={
                "profile_task_id": profile_id,
                "title": "立即删除匹配",
                "jd_text": "后端工程师\n任职要求：熟悉 Python 和 FastAPI。",
            },
        )
        assert response.status_code == 202, response.text
        match_id = response.json()["match_id"]

        deleted = client.delete(f"/matches/{match_id}")

        assert deleted.status_code == 200, deleted.text
        assert client.get(f"/matches/{match_id}").status_code == 404
