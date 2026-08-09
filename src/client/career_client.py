import httpx


class CareerClientError(RuntimeError):
    pass


class CareerClient:
    def __init__(self, base_url: str, timeout: float = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_settings(self) -> dict:
        return self._request("GET", "/career/settings").json()["settings"]

    def save_settings(self, payload: dict) -> dict:
        return self._request("PUT", "/career/settings", json=payload).json()["settings"]

    def list_answers(self) -> list[dict]:
        return self._request("GET", "/career/answers").json()["answers"]

    def save_answers(self, answers: list[dict]) -> list[dict]:
        return self._request("PUT", "/career/answers", json=answers).json()["answers"]

    def create_campaign(self, payload: dict) -> dict:
        return self._request("POST", "/campaigns", json=payload).json()["campaign"]

    def list_campaigns(self, profile_task_id: str | None = None) -> list[dict]:
        params = {"profile_task_id": profile_task_id} if profile_task_id else None
        return self._request("GET", "/campaigns", params=params).json()

    def discover(self, campaign_id: str, payload: dict) -> list[dict]:
        return self._request("POST", f"/campaigns/{campaign_id}/discover", json=payload).json()[
            "jobs"
        ]

    def list_jobs(self, campaign_id: str | None = None) -> list[dict]:
        if campaign_id:
            return self._request("GET", f"/campaigns/{campaign_id}/jobs").json()["jobs"]
        return self._request("GET", "/jobs").json()["items"]

    def create_batch(self, campaign_id: str, job_ids: list[str], title: str) -> dict:
        return self._request(
            "POST",
            "/tailoring-batches",
            json={"campaign_id": campaign_id, "job_ids": job_ids, "title": title},
        ).json()["batch"]

    def create_resume(
        self,
        job_id: str,
        match_id: str,
        template: str,
        match_version: int | None = None,
    ) -> dict:
        payload = {"match_id": match_id, "template": template}
        if match_version:
            payload["match_version"] = match_version
        return self._request("POST", f"/jobs/{job_id}/resume", json=payload).json()["resume"]

    def list_resumes(self, job_id: str | None = None) -> list[dict]:
        params = {"job_id": job_id} if job_id else None
        return [item["resume"] for item in self._request("GET", "/resumes", params=params).json()]

    def download_resume(self, resume_id: str, format: str) -> bytes:
        return self._request(
            "GET", f"/resumes/{resume_id}/export", params={"format": format}
        ).content

    def download_resume_document(self, resume_id: str, document_key: str) -> bytes:
        return self._request("GET", f"/resumes/{resume_id}/documents/{document_key}").content

    def create_application(self, job_id: str, resume_version_id: str) -> dict:
        return self._request(
            "POST",
            "/applications",
            json={"job_id": job_id, "resume_version_id": resume_version_id},
        ).json()["application"]

    def browser_status(self) -> dict:
        return self._request("GET", "/applications/browser/status").json()["browser"]

    def open_boss(self) -> dict:
        return self._request("POST", "/applications/browser/open-boss").json()["browser"]

    def list_applications(self) -> list[dict]:
        return [item["application"] for item in self._request("GET", "/applications").json()]

    def confirm_application(self, application_id: str, preview_hash: str) -> dict:
        return self._request(
            "POST",
            f"/applications/{application_id}/confirm",
            json={"preview_hash": preview_hash},
        ).json()

    def resume_application(self, application_id: str) -> dict:
        return self._request("POST", f"/applications/{application_id}/resume").json()

    def cancel_application(self, application_id: str) -> dict:
        return self._request("POST", f"/applications/{application_id}/cancel").json()

    def delete_application(self, application_id: str) -> dict:
        return self._request("DELETE", f"/applications/{application_id}").json()

    def dashboard(self) -> dict:
        return self._request("GET", "/tracking/dashboard").json()["dashboard"]

    def create_interview(self, job_id: str, resume_version_id: str) -> dict:
        return self._request(
            "POST",
            "/interviews",
            json={"job_id": job_id, "resume_version_id": resume_version_id},
        ).json()["kit"]

    def delete_campaign(self, campaign_id: str) -> dict:
        return self._request("DELETE", f"/campaigns/{campaign_id}").json()

    def delete_job(self, job_id: str) -> dict:
        return self._request("DELETE", f"/jobs/{job_id}").json()

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
            raise CareerClientError(detail or str(exc)) from exc
