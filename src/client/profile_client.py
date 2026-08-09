from pathlib import Path
from typing import BinaryIO

import httpx


class ProfileClientError(RuntimeError):
    pass


class ProfileClient:
    def __init__(self, base_url: str, timeout: float = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def create_profile(self, files, title: str = "") -> dict:
        payload = []
        opened: list[BinaryIO] = []
        try:
            for file in files:
                if isinstance(file, (str, Path)):
                    handle = Path(file).open("rb")
                    opened.append(handle)
                    payload.append(("files", (Path(file).name, handle)))
                else:
                    payload.append(("files", (file.name, file.getvalue(), file.type)))
            return self._request(
                "POST",
                "/profiles",
                files=payload,
                data={"title": title},
            ).json()
        finally:
            for handle in opened:
                handle.close()

    def list_profiles(self) -> list[dict]:
        return self._request("GET", "/profiles").json()

    def get_task(self, task_id: str) -> dict:
        return self._request("GET", f"/profiles/{task_id}").json()

    def get_facts(self, task_id: str) -> dict:
        return self._request("GET", f"/profiles/{task_id}/facts").json()

    def update_facts(self, task_id: str, facts: list[dict]) -> dict:
        return self._request("PUT", f"/profiles/{task_id}/facts", json={"facts": facts}).json()

    def resume(self, task_id: str) -> dict:
        return self._request("POST", f"/profiles/{task_id}/resume").json()

    def regenerate(self, task_id: str) -> dict:
        return self._request("POST", f"/profiles/{task_id}/regenerate").json()

    def retry(self, task_id: str) -> dict:
        return self._request("POST", f"/profiles/{task_id}/retry").json()

    def get_result(self, task_id: str) -> dict:
        return self._request("GET", f"/profiles/{task_id}/result").json()["result"]

    def download(self, task_id: str, format: str) -> bytes:
        return self._request(
            "GET", f"/profiles/{task_id}/export", params={"format": format}
        ).content

    def download_section(self, task_id: str, section_name: str) -> bytes:
        return self._request("GET", f"/profiles/{task_id}/sections/{section_name}").content

    def delete(self, task_id: str) -> dict:
        return self._request("DELETE", f"/profiles/{task_id}").json()

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            detail = ""
            if getattr(exc, "response", None) is not None:
                detail = exc.response.text
            raise ProfileClientError(detail or str(exc)) from exc
