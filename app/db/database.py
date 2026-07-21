from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = settings.database_url
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        # In-memory SQLite needs a single shared connection (StaticPool),
        # else each session gets its own empty database.
        if ":memory:" in url or url == "sqlite://":
            return create_engine(
                url, connect_args=connect_args, poolclass=StaticPool, future=True
            )
        return create_engine(url, connect_args=connect_args, future=True)
    return create_engine(url, future=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create tables if they don't exist (idempotent). Alembic replaces this in prod."""
    from app.db import models  # noqa: F401 — register mappers

    Base.metadata.create_all(engine)
