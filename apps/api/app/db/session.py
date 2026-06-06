from collections.abc import Iterator
from contextlib import contextmanager
from os import getenv
from typing import Any, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    return getenv("DATABASE_URL", "sqlite:///./careeros.db")


def create_db_engine(database_url: Optional[str] = None) -> Engine:
    url = database_url or get_database_url()
    engine = create_engine(url, future=True)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(database_url: Optional[str] = None) -> sessionmaker[Session]:
    engine = create_db_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
