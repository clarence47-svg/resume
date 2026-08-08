import uvicorn

from core.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "service.service:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=False,
    )
