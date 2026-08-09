from fastapi.testclient import TestClient

from service.service import create_app


def test_browser_status_and_open_boss_when_disabled(test_settings) -> None:
    app = create_app(test_settings)
    with TestClient(app) as client:
        status = client.get("/applications/browser/status")
        assert status.status_code == 200
        assert not status.json()["browser"]["enabled"]

        opened = client.post("/applications/browser/open-boss")
        assert opened.status_code == 409
