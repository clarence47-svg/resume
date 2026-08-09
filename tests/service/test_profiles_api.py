import time

from fastapi.testclient import TestClient

from service.service import create_app


def test_markdown_upload_completes(test_settings) -> None:
    app = create_app(test_settings)
    with TestClient(app) as client:
        response = client.post(
            "/profiles",
            files={
                "files": ("resume.md", "# 项目经历\n\n负责 FastAPI 后端开发。", "text/markdown")
            },
            data={"review_mode": "auto", "title": "测试画像"},
        )
        assert response.status_code == 202
        task_id = response.json()["task_id"]
        task = {}
        for _ in range(100):
            task = client.get(f"/profiles/{task_id}").json()
            if task["status"] in {"completed", "partial_success", "failed_retryable"}:
                break
            time.sleep(0.05)
        assert task["status"] in {"completed", "partial_success"}, task
        result = client.get(f"/profiles/{task_id}/result")
        assert result.status_code == 200
        assert "project_experiences" in result.json()["result"]
        section = client.get(f"/profiles/{task_id}/sections/project_experiences")
        assert section.status_code == 200
        assert "项目经历" in section.text


def test_profile_can_be_deleted_immediately_after_creation(test_settings) -> None:
    app = create_app(test_settings)
    with TestClient(app) as client:
        response = client.post(
            "/profiles",
            files={"files": ("resume.md", "# 项目经历\n测试资料", "text/markdown")},
            data={"review_mode": "auto", "title": "立即删除画像"},
        )
        assert response.status_code == 202
        task_id = response.json()["task_id"]

        deleted = client.delete(f"/profiles/{task_id}")

        assert deleted.status_code == 200, deleted.text
        assert client.get(f"/profiles/{task_id}").status_code == 404
