from collections.abc import Iterator

from sqlmodel import Session, create_engine

from .config import settings

# Engine is only created when DATABASE_URL is set, so the API can run without a database.
engine = create_engine(settings.database_url, pool_pre_ping=True) if settings.database_url else None


def get_session() -> Iterator[Session]:
    if engine is None:
        raise RuntimeError("DATABASE_URL is not set")
    with Session(engine) as session:
        yield session
