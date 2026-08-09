from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "一体化智能投简历 Agent"
    app_version: str = "0.3.1"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    profile_model: str = "gpt-4.1-mini"
    match_model: str = ""
    database_url: str = "sqlite:///data/profile-agent.db"
    checkpoint_url: str = "sqlite:///data/langgraph-checkpoints.sqlite"
    data_dir: Path = Path("data")
    service_host: str = "127.0.0.1"
    service_port: int = 8080
    agent_url: str = "http://127.0.0.1:8080"
    max_files: int = Field(default=20, ge=1, le=100)
    max_file_size_mb: int = Field(default=50, ge=1)
    max_total_size_mb: int = Field(default=200, ge=1)
    max_total_pages: int = Field(default=500, ge=1)
    profile_workers: int = Field(default=1, ge=1, le=8)
    match_workers: int = Field(default=1, ge=1, le=8)
    career_workers: int = Field(default=1, ge=1, le=8)
    job_search_enabled: bool = True
    job_search_endpoint: str = "http://www.baidu.com/s"
    job_search_fallback_endpoint: str = "https://www.bing.com/search"
    job_search_max_results: int = Field(default=8, ge=1, le=20)
    job_search_timeout_seconds: float = Field(default=12, ge=1, le=60)
    competition_verification_enabled: bool = True
    competition_verification_min_score: float = Field(default=0.58, ge=0, le=1)
    competition_verification_max_results: int = Field(default=6, ge=1, le=20)
    ocr_enabled: bool = True
    allow_heuristic_fallback: bool = True
    app_encryption_key: str = ""
    chrome_cdp_url: str = "http://host.docker.internal:9222"
    browser_automation_enabled: bool = False
    browser_action_timeout_seconds: float = Field(default=30, ge=5, le=300)
    boss_daily_action_limit: int = Field(default=10, ge=1, le=100)
    boss_action_interval_min_seconds: int = Field(default=90, ge=5, le=3600)
    boss_action_interval_max_seconds: int = Field(default=180, ge=5, le=7200)
    boss_discovery_max_jobs: int = Field(default=10, ge=1, le=50)
    log_level: str = "INFO"

    @computed_field
    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @computed_field
    @property
    def parsed_dir(self) -> Path:
        return self.data_dir / "parsed"

    @computed_field
    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @computed_field
    @property
    def match_exports_dir(self) -> Path:
        return self.exports_dir / "matches"

    @computed_field
    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @computed_field
    @property
    def resumes_dir(self) -> Path:
        return self.data_dir / "resumes"

    @computed_field
    @property
    def applications_dir(self) -> Path:
        return self.data_dir / "applications"

    @computed_field
    @property
    def application_exports_dir(self) -> Path:
        return self.exports_dir / "applications"

    @computed_field
    @property
    def resume_exports_dir(self) -> Path:
        return self.exports_dir / "resumes"

    @computed_field
    @property
    def interview_exports_dir(self) -> Path:
        return self.exports_dir / "interviews"

    @computed_field
    @property
    def encryption_key_path(self) -> Path:
        return self.data_dir / ".encryption-key"

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.profile_model)

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.uploads_dir,
            self.parsed_dir,
            self.exports_dir,
            self.match_exports_dir,
            self.jobs_dir,
            self.resumes_dir,
            self.applications_dir,
            self.resume_exports_dir,
            self.application_exports_dir,
            self.interview_exports_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
