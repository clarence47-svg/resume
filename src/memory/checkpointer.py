from pathlib import Path

from core.settings import Settings, get_settings


class CheckpointerManager:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.checkpointer = None
        self._context = None

    async def start(self):
        url = self.settings.checkpoint_url
        if url.startswith("postgresql"):
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            normalized = url.replace("postgresql+psycopg://", "postgresql://", 1)
            self._context = AsyncPostgresSaver.from_conn_string(normalized)
        else:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            raw_path = url.removeprefix("sqlite:///")
            path = Path(raw_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._context = AsyncSqliteSaver.from_conn_string(str(path))
        self.checkpointer = await self._context.__aenter__()
        await self.checkpointer.setup()
        return self.checkpointer

    async def stop(self) -> None:
        if self._context is not None:
            await self._context.__aexit__(None, None, None)
