from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import make_url
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
            return create_engine(url, connect_args=connect_args, poolclass=StaticPool, future=True)
        return create_engine(url, connect_args=connect_args, future=True)
    return create_engine(url, future=True)


engine = _make_engine()


def _sqlite_database_path() -> Path | None:
    """The SQLite data file for permission hardening, if this URL has one."""
    if not settings.database_url.startswith("sqlite"):
        return None
    database = make_url(settings.database_url).database
    if not database or database == ":memory:":
        return None
    return Path(database).resolve()


def _secure_sqlite_files() -> None:
    """Keep the database and its WAL siblings owner-readable only."""
    path = _sqlite_database_path()
    if path is None or os.name != "posix":
        return
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        try:
            if candidate.exists():
                os.chmod(candidate, 0o600)
        except OSError:
            # Actual database access still reports a concrete failure later;
            # do not conceal it while establishing connection pragmas.
            pass


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record) -> None:
    """WAL and a busy timeout on every SQLite connection (S12).

    Without WAL a reader blocks a writer, and without a busy timeout a
    concurrent write fails immediately with "database is locked" rather than
    waiting. On stage that is a verdict that never comes back.
    """
    if not settings.database_url.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    try:
        # An in-memory database cannot use WAL; the timeout still applies.
        if ":memory:" not in settings.database_url and settings.database_url != "sqlite://":
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
    finally:
        cursor.close()
    _secure_sqlite_files()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Prepare SQLite locally, or verify a migrated non-SQLite schema.

    SQLite remains the self-contained demo path and supports the narrowly scoped
    legacy-column backfill below. Postgres must be migrated before the service
    starts; application startup never races other replicas by issuing DDL.
    """
    from app.db import models  # noqa: F401 — register mappers

    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)
        _add_missing_columns()
        _secure_sqlite_files()
        return
    _assert_schema_current()


def _assert_schema_current() -> None:
    """Fail closed when a non-SQLite database was not migrated to this model."""
    inspector = inspect(engine)
    missing: list[str] = []
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            missing.append(table.name)
            continue
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        absent = {column.name for column in table.columns} - existing
        if absent:
            missing.append(f"{table.name} missing {', '.join(sorted(absent))}")
    if missing:
        raise RuntimeError(
            "Database schema is not current; run `alembic upgrade head` before starting "
            "the service. Missing: " + "; ".join(missing)
        )


def database_ready() -> bool:
    """A readiness probe that performs a real round trip to the database."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - readiness must not leak a DSN
        return False


def _add_missing_columns() -> None:
    """Add columns that exist on the model but not yet in the table.

    `create_all` creates missing TABLES and never touches a table that already
    exists, so S5 adding `owner_hash` to `chains` left every database created
    before it unreadable: `no such column: chains.owner_hash` on every chain
    read, every vault verification, every receipt and every idempotent replay.
    In the console that surfaced as four unrelated-looking failures.

    S5 was careful about the JSON side of that migration — `Verdict` gained its
    new fields with "" defaults so pre-S5 rows still parse — and missed the SQL
    column beside it. The S6 restart proof passed because its volume was created
    fresh and so never met an old schema.

    This is not a migration framework and does not pretend to be one: it only
    ADDs columns, never drops, renames, backfills or reorders, and it is a
    hackathon's worth of safety rather than Alembic. Adding a column with a
    default is the only schema change this project has actually needed, and
    doing it here means reusing an existing volume on demo day is survivable
    instead of fatal. Anything beyond that still wants Alembic.

    A row migrated this way gets `owner_hash=""`, which matches no owner, so old
    chains become unreadable rather than readable by everyone — the safe
    direction for a column that gates tenant access.
    """
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            if not (column.nullable or column.default is not None or column.server_default):
                # No safe value to give existing rows; refuse rather than guess.
                raise RuntimeError(
                    f"{table.name}.{column.name} is missing and has no default; "
                    "this needs a real migration, not an automatic ADD COLUMN"
                )
            ddl = f"ALTER TABLE {table.name} ADD COLUMN {column.name} {column.type.compile(engine.dialect)}"
            default = getattr(column.default, "arg", None)
            if isinstance(default, str):
                ddl += f" DEFAULT '{default}'"
            elif default is not None and not callable(default):
                ddl += f" DEFAULT {default}"
            with engine.begin() as connection:
                connection.execute(text(ddl))
