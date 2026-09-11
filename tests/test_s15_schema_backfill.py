"""A database created before S5 must not 500 on every read.

S5 added `chains.owner_hash`. `create_all()` creates missing tables and never
alters an existing one, so every pre-S5 database answered
`no such column: chains.owner_hash` on every chain read, vault verification,
receipt and idempotent replay — four unrelated-looking console failures with one
cause. Reproduced against a real pre-S5 database, not imagined.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

# The exact pre-S5 shape, taken from a database that actually failed this way.
PRE_S5_CHAINS = """
CREATE TABLE chains (
    chain_id VARCHAR(40) NOT NULL PRIMARY KEY,
    decision VARCHAR(16) NOT NULL,
    confidence FLOAT NOT NULL,
    hypothesis VARCHAR(32) NOT NULL,
    verdict_json TEXT NOT NULL,
    signature TEXT NOT NULL,
    signed_at VARCHAR(40) NOT NULL,
    public_key VARCHAR(80) NOT NULL,
    created_at DATETIME NOT NULL
)
"""


@pytest.fixture()
def pre_s5_db(tmp_path: Path) -> Path:
    path = tmp_path / "pre_s5.db"
    conn = sqlite3.connect(path)
    conn.execute(PRE_S5_CHAINS)
    conn.execute(
        "INSERT INTO chains VALUES ('chn_old', 'DECLINE', 0.9, 'account_takeover',"
        " '{}', 'deadbeef', '2026-01-01T00:00:00+00:00', 'abc', '2026-01-01 00:00:00')"
    )
    conn.commit()
    conn.close()
    return path


def test_the_old_schema_really_did_break(pre_s5_db: Path):
    """Guard the premise: without the backfill this raises."""
    engine = create_engine(f"sqlite:///{pre_s5_db}")
    with engine.begin() as c, pytest.raises(Exception) as exc:
        c.execute(text("SELECT owner_hash FROM chains")).fetchone()
    assert "owner_hash" in str(exc.value)


def test_startup_adds_the_missing_column(pre_s5_db: Path, monkeypatch):
    from app.db import database

    engine = create_engine(f"sqlite:///{pre_s5_db}")
    monkeypatch.setattr(database, "engine", engine)
    database.init_db()

    columns = {c["name"] for c in inspect(engine).get_columns("chains")}
    assert "owner_hash" in columns


def test_the_existing_row_survives_and_belongs_to_nobody(pre_s5_db: Path, monkeypatch):
    """A migrated row must match no owner — unreadable is the safe direction for
    a column that gates tenant access."""
    from app.db import database

    engine = create_engine(f"sqlite:///{pre_s5_db}")
    monkeypatch.setattr(database, "engine", engine)
    database.init_db()

    with engine.begin() as c:
        row = c.execute(text("SELECT chain_id, owner_hash FROM chains")).fetchone()
    assert row[0] == "chn_old"
    assert row[1] in ("", None)


def test_running_it_twice_is_a_no_op(pre_s5_db: Path, monkeypatch):
    from app.db import database

    engine = create_engine(f"sqlite:///{pre_s5_db}")
    monkeypatch.setattr(database, "engine", engine)
    database.init_db()
    database.init_db()  # must not raise "duplicate column name"
    columns = [c["name"] for c in inspect(engine).get_columns("chains")]
    assert columns.count("owner_hash") == 1
