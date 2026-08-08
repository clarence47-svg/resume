from pydantic import BaseModel


class ServiceInfo(BaseModel):
    name: str
    version: str
    agent: str = "profile-agent"
    model: str
    llm_configured: bool
    supported_extensions: list[str]


class HealthResponse(BaseModel):
    status: str = "ok"
