from fastapi.testclient import TestClient

from service.service import create_app


def test_career_settings_are_encrypted(test_settings):
    with TestClient(create_app(test_settings)) as client:
        response = client.put(
            "/career/settings",
            json={
                "display_name": "张三",
                "email": "zhangsan@example.com",
                "target_roles": ["Python 开发"],
            },
        )
        assert response.status_code == 200
        row = client.app.state.career_repository.get_settings_payload()
        assert row
        assert "zhangsan@example.com" not in row
        restored = client.get("/career/settings").json()["settings"]
        assert restored["display_name"] == "张三"
