from collections.abc import Iterator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.settings import Settings, get_settings


class Base(DeclarativeBase):
    pass


def create_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    resolved = settings or get_settings()
    connect_args = (
        {"check_same_thread": False} if resolved.database_url.startswith("sqlite") else {}
    )
    engine = create_engine(resolved.database_url, connect_args=connect_args, pool_pre_ping=True)
    if resolved.database_url.startswith("sqlite"):
        event.listen(
            engine,
            "connect",
            lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
        )
    return sessionmaker(bind=engine, expire_on_commit=False)


SessionFactory = create_session_factory()


def init_db(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    factory = create_session_factory(resolved)
    bind = factory.kw["bind"]
    Base.metadata.create_all(bind)
    _ensure_additive_columns(bind)


def _ensure_additive_columns(engine) -> None:
    inspector = inspect(engine)
    if "match_tasks" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("match_tasks")}
    with engine.begin() as connection:
        if "job_id" not in columns:
            connection.execute(text("ALTER TABLE match_tasks ADD COLUMN job_id VARCHAR(36)"))
        if "batch_id" not in columns:
            connection.execute(text("ALTER TABLE match_tasks ADD COLUMN batch_id VARCHAR(36)"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_match_tasks_job_id ON match_tasks (job_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_match_tasks_batch_id ON match_tasks (batch_id)")
        )


def session_scope(factory: sessionmaker[Session] | None = None) -> Iterator[Session]:
    session = (factory or SessionFactory)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
