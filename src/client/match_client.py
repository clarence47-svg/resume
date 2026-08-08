import httpx


class MatchClientError(RuntimeError):
    pass


class MatchClient:
    def __init__(self, base_url: str, timeout: float = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def create_match(self, profile_task_id: str, jd_text: str, title: str = "") -> dict:
        return self._request(
            "POST",
            "/matches",
            json={"profile_task_id": profile_task_id, "jd_text": jd_text, "title": title},
        ).json()

    def list_matches(self, profile_task_id: str | None = None) -> list[dict]:
        params = {"profile_task_id": profile_task_id} if profile_task_id else None
        return self._request("GET", "/matches", params=params).json()

    def get_task(self, match_id: str) -> dict:
        return self._request("GET", f"/matches/{match_id}").json()

    def get_result(self, match_id: str, version: int | None = None) -> dict:
        params = {"version": version} if version else None
        return self._request("GET", f"/matches/{match_id}/result", params=params).json()["result"]

    def list_versions(self, match_id: str) -> list[dict]:
        return self._request("GET", f"/matches/{match_id}/versions").json()

    def update_draft(self, match_id: str, expected_version: int, updates: list[dict]) -> dict:
        return self._request(
            "PUT",
            f"/matches/{match_id}/draft",
            json={"expected_version": expected_version, "updates": updates},
        ).json()["result"]

    def restore(self, match_id: str, version: int) -> dict:
        return self._request("POST", f"/matches/{match_id}/versions/{version}/restore").json()[
            "result"
        ]

    def regenerate(self, match_id: str) -> dict:
        return self._request("POST", f"/matches/{match_id}/regenerate").json()

    def retry(self, match_id: str) -> dict:
        return self._request("POST", f"/matches/{match_id}/retry").json()

    def download(self, match_id: str, format: str, version: int | None = None) -> bytes:
        params = {"format": format}
        if version:
            params["version"] = version
        return self._request("GET", f"/matches/{match_id}/export", params=params).content

    def delete(self, match_id: str) -> dict:
        return self._request("DELETE", f"/matches/{match_id}").json()

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
            raise MatchClientError(detail or str(exc)) from exc
