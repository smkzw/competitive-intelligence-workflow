"""工作区：原件 CAS、SQLite（来源、核对账本、LLM 缓存）、阶段产物与 release 指针。"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ciw.models import Source, SourceKind, stable_id

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY, kind TEXT NOT NULL, url TEXT NOT NULL, title TEXT,
  publisher TEXT, published_at TEXT, fetched_at TEXT NOT NULL, sha256 TEXT NOT NULL, ext TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verifications (
  fact_key TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS llm_cache (
  cache_key TEXT PRIMARY KEY, model TEXT NOT NULL, family TEXT NOT NULL,
  prompt_sha TEXT NOT NULL, response TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class Workspace:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        for sub in ("raw/sha256", "captures", "stages", "releases", "logs"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "ciw.sqlite"
        with self.db() as con:
            con.executescript(SCHEMA)
            if "metadata" not in {r[1] for r in con.execute("PRAGMA table_info(llm_cache)")}:
                con.execute("ALTER TABLE llm_cache ADD COLUMN metadata TEXT")

    # ---------- SQLite ----------
    @contextmanager
    def db(self):
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA journal_mode=WAL")
        try:
            yield con
            con.commit()
        finally:
            con.close()

    # ---------- CAS ----------
    def put_raw(self, data: bytes, ext: str) -> tuple[str, Path]:
        sha = hashlib.sha256(data).hexdigest()
        path = self.root / "raw" / "sha256" / sha[:2] / f"{sha}.{ext}"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)
        return sha, path

    def raw_path(self, sha: str, ext: str) -> Path:
        return self.root / "raw" / "sha256" / sha[:2] / f"{sha}.{ext}"

    def record_source(
        self,
        *,
        kind: SourceKind,
        url: str,
        data: bytes,
        ext: str,
        title: str = "",
        publisher: str = "",
        published_at: str | None = None,
        fetched_at: str | None = None,
    ) -> Source:
        sha, _ = self.put_raw(data, ext)
        source = Source(
            source_id=stable_id("src", kind, url, sha),
            kind=kind,
            url=url,
            title=title,
            publisher=publisher,
            published_at=published_at,
            fetched_at=fetched_at or now_iso(),
            sha256=sha,
        )
        with self.db() as con:
            con.execute(
                "INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?,?,?,?)",
                (source.source_id, kind, url, title, publisher, published_at, source.fetched_at, sha, ext),
            )
            stored = con.execute("SELECT title,publisher,published_at,fetched_at FROM sources WHERE source_id=?",
                                 (source.source_id,)).fetchone()
        fields = ("title", "publisher", "published_at", "fetched_at")
        return source.model_copy(update=dict(zip(fields, stored, strict=True)))

    def sources(self) -> list[Source]:
        with self.db() as con:
            rows = con.execute(
                "SELECT source_id, kind, url, title, publisher, published_at, fetched_at, sha256 FROM sources"
            ).fetchall()
        return [
            Source(
                source_id=r[0],
                kind=r[1],
                url=r[2],
                title=r[3] or "",
                publisher=r[4] or "",
                published_at=r[5],
                fetched_at=r[6],
                sha256=r[7],
            )
            for r in rows
        ]

    def read_source(self, source_id: str) -> bytes:
        with self.db() as con:
            row = con.execute("SELECT sha256, ext FROM sources WHERE source_id=?", (source_id,)).fetchone()
        if row is None:
            raise KeyError(source_id)
        return self.raw_path(row[0], row[1]).read_bytes()

    # ---------- 阶段产物 ----------
    def write_stage(self, name: str, payload: Any) -> Path:
        path = self.root / "stages" / f"{name}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        tmp.replace(path)
        return path

    def read_stage(self, name: str) -> Any:
        path = self.root / "stages" / f"{name}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    # ---------- 核对账本 ----------
    def save_verification(self, fact_key: str, status: str, payload: dict[str, Any]) -> None:
        with self.db() as con:
            con.execute(
                "INSERT OR REPLACE INTO verifications VALUES (?,?,?,?)",
                (fact_key, status, json.dumps(payload, ensure_ascii=False, default=str), now_iso()),
            )

    def verifications(self) -> dict[str, dict[str, Any]]:
        with self.db() as con:
            rows = con.execute("SELECT fact_key, status, payload FROM verifications").fetchall()
        return {k: {"status": s, **json.loads(p)} for k, s, p in rows}

    # ---------- release ----------
    @property
    def releases_dir(self) -> Path:
        return self.root / "releases"

    def current_release_dir(self) -> Path | None:
        pointer = self.releases_dir / "current.json"
        if not pointer.exists():
            return None
        rid = json.loads(pointer.read_text(encoding="utf-8"))["release_id"]
        return self.releases_dir / rid

    def set_current(self, release_id: str) -> None:
        pointer = self.releases_dir / "current.json"
        tmp = pointer.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"release_id": release_id, "set_at": now_iso()}), encoding="utf-8")
        tmp.replace(pointer)
