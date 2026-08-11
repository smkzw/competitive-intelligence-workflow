from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def open_database(path: Path) -> Iterator[sqlite3.Connection]:
    """以同一约束打开项目科学真源数据库。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(path)
    try:
        database.execute("PRAGMA foreign_keys = ON")
        database.execute("PRAGMA journal_mode = WAL")
        database.execute("PRAGMA synchronous = FULL")
        yield database
        database.commit()
    except BaseException:
        database.rollback()
        raise
    finally:
        database.close()
