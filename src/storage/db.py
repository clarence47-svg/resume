from collections.abc import Iterator

from sqlalchemy import create_engine
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
    return sessionmaker(bind=engine, expire_on_commit=False)


SessionFactory = create_session_factory()


def init_db(settings: Settings | None = None) -> None:
    resolved = settings or get_settings()
    factory = create_session_factory(resolved)
    bind = factory.kw["bind"]
    Base.metadata.create_all(bind)


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
