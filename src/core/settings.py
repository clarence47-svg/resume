from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "用户资料六维画像 Agent"
    app_version: str = "0.1.0"
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
    ocr_enabled: bool = True
    allow_heuristic_fallback: bool = True
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
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
