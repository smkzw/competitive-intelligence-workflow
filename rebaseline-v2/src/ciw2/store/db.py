"""SQLite 单库。表设计原则：
- sources / facts 只追加；修正产生新行并以 supersedes 指向旧行。
- 运行轨迹（runs / stages / agent_steps）完整落库，平台可直接展示进度。
- 不保存任何凭据。
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  indication TEXT NOT NULL,
  indication_aliases TEXT NOT NULL DEFAULT '[]',
  reports TEXT NOT NULL,            -- JSON ["A","B","C"]
  request_text TEXT NOT NULL DEFAULT '',
  focus TEXT NOT NULL DEFAULT '',   -- 用户关注点原话
  cutoff_date TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  status TEXT NOT NULL,             -- queued|running|succeeded|failed|cancelled
  error TEXT,
  created_at TEXT NOT NULL,
  finished_at TEXT
);
CREATE TABLE IF NOT EXISTS stages (
  run_id TEXT NOT NULL REFERENCES runs(id),
  name TEXT NOT NULL,
  status TEXT NOT NULL,             -- pending|running|succeeded|failed|skipped
  output_json TEXT,
  error TEXT,
  started_at TEXT,
  finished_at TEXT,
  PRIMARY KEY (run_id, name)
);
CREATE TABLE IF NOT EXISTS agent_steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT,
  stage TEXT,
  skill TEXT,
  step INTEGER,
  role TEXT,
  content TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  kind TEXT NOT NULL,               -- ctgov|chinadrugtrials|nmpa|cde|pubmed|pmc|fda|ema|conference|wechat|company|web
  url TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  digest TEXT NOT NULL,             -- CAS sha256 of raw bytes
  text_digest TEXT,                 -- CAS sha256 of extracted plain text
  published_date TEXT,
  fetched_at TEXT NOT NULL,
  meta TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_sources_project ON sources(project_id, kind);
CREATE TABLE IF NOT EXISTS entities (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  type TEXT NOT NULL,               -- drug|company|trial|target
  name TEXT NOT NULL,
  name_zh TEXT,
  aliases TEXT NOT NULL DEFAULT '[]',
  attrs TEXT NOT NULL DEFAULT '{}',
  in_scope INTEGER,                 -- 1 纳入 0 排除 NULL 待定
  scope_reason TEXT,
  found_by TEXT NOT NULL DEFAULT '[]', -- 发现路线 route_id 列表
  created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_entities ON entities(project_id, type, name);
CREATE TABLE IF NOT EXISTS links (
  project_id TEXT NOT NULL,
  src TEXT NOT NULL,
  rel TEXT NOT NULL,                -- drug-trial|drug-target|drug-company|trial-sponsor
  dst TEXT NOT NULL,
  attrs TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (project_id, src, rel, dst)
);
CREATE TABLE IF NOT EXISTS facts (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  field TEXT NOT NULL,
  value TEXT NOT NULL,              -- JSON
  tier TEXT NOT NULL,               -- critical|standard
  status TEXT NOT NULL,             -- verified|unverified|conflict|unknown
  source_id TEXT,
  quote TEXT,
  quote_start INTEGER,
  quote_end INTEGER,
  context TEXT NOT NULL DEFAULT '{}', -- 人群/组/时间点/统计对象/分母等语义
  extracted_by TEXT NOT NULL,       -- code:<parser> | llm:<model>
  supersedes TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_facts_entity ON facts(project_id, entity_id, field);
CREATE INDEX IF NOT EXISTS ix_facts_supersedes ON facts(supersedes);
CREATE TABLE IF NOT EXISTS coverage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  route_id TEXT NOT NULL,
  region TEXT NOT NULL,             -- china|global
  query TEXT NOT NULL,
  status TEXT NOT NULL,             -- ok|failed|blocked|skipped
  hits INTEGER NOT NULL DEFAULT 0,
  new_entities INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class DB:
    """线程安全的轻量封装（单用户平台：一个写锁足够）。"""

    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                yield self._conn
                self._conn.execute("COMMIT")
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, tuple(params)).fetchall()]

    def one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: Iterable[Any] = ()) -> None:
        with self._lock:
            self._conn.execute(sql, tuple(params))

    # ---- projects / runs -------------------------------------------------
    def create_project(
        self,
        indication: str,
        reports: list[str],
        request_text: str = "",
        focus: str = "",
        cutoff_date: str | None = None,
        aliases: list[str] | None = None,
    ) -> str:
        pid = new_id("prj")
        self.execute(
            "INSERT INTO projects VALUES (?,?,?,?,?,?,?,?)",
            (pid, indication, json.dumps(aliases or [], ensure_ascii=False),
             json.dumps(reports), request_text, focus, cutoff_date, now()),
        )
        return pid

    def project(self, pid: str) -> dict[str, Any] | None:
        row = self.one("SELECT * FROM projects WHERE id=?", (pid,))
        if row:
            row["reports"] = json.loads(row["reports"])
            row["indication_aliases"] = json.loads(row["indication_aliases"])
        return row

    def create_run(self, project_id: str) -> str:
        rid = new_id("run")
        self.execute("INSERT INTO runs VALUES (?,?,?,?,?,?)", (rid, project_id, "queued", None, now(), None))
        return rid

    def set_run(self, run_id: str, status: str, error: str | None = None) -> None:
        finished = now() if status in {"succeeded", "failed", "cancelled"} else None
        self.execute("UPDATE runs SET status=?, error=?, finished_at=? WHERE id=?",
                     (status, error, finished, run_id))

    def set_stage(self, run_id: str, name: str, status: str, output: Any = None,
                  error: str | None = None) -> None:
        out = json.dumps(output, ensure_ascii=False) if output is not None else None
        existing = self.one("SELECT 1 FROM stages WHERE run_id=? AND name=?", (run_id, name))
        if existing is None:
            self.execute("INSERT INTO stages VALUES (?,?,?,?,?,?,?)",
                         (run_id, name, status, out, error,
                          now() if status == "running" else None,
                          now() if status in {"succeeded", "failed", "skipped"} else None))
        else:
            finished = now() if status in {"succeeded", "failed", "skipped"} else None
            self.execute(
                "UPDATE stages SET status=?, output_json=COALESCE(?, output_json), error=?, "
                "started_at=COALESCE(started_at, CASE WHEN ?='running' THEN ? END), finished_at=? "
                "WHERE run_id=? AND name=?",
                (status, out, error, status, now(), finished, run_id, name),
            )

    def stage_output(self, run_id: str, name: str) -> Any:
        row = self.one("SELECT output_json FROM stages WHERE run_id=? AND name=? AND status='succeeded'",
                       (run_id, name))
        return json.loads(row["output_json"]) if row and row["output_json"] else None

    def log_step(self, run_id: str | None, stage: str | None, skill: str, step: int, role: str,
                 content: Any) -> None:
        text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        self.execute(
            "INSERT INTO agent_steps (run_id, stage, skill, step, role, content, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (run_id, stage, skill, step, role, text[:20000], now()),
        )

    # ---- sources / entities / facts -------------------------------------
    def add_source(self, project_id: str, kind: str, url: str, digest: str, title: str = "",
                   text_digest: str | None = None, published_date: str | None = None,
                   meta: dict[str, Any] | None = None) -> str:
        existing = self.one("SELECT id FROM sources WHERE project_id=? AND url=? AND digest=?",
                            (project_id, url, digest))
        if existing:
            return existing["id"]
        sid = new_id("src")
        self.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sid, project_id, kind, url, title, digest, text_digest, published_date, now(),
             json.dumps(meta or {}, ensure_ascii=False)),
        )
        return sid

    def upsert_entity(self, project_id: str, type_: str, name: str, *, name_zh: str | None = None,
                      aliases: list[str] | None = None, attrs: dict[str, Any] | None = None,
                      route_id: str | None = None) -> tuple[str, bool]:
        """返回 (entity_id, 是否新建)。同名实体合并别名、属性与发现路线。"""
        row = self.one("SELECT * FROM entities WHERE project_id=? AND type=? AND name=?",
                       (project_id, type_, name))
        if row is None:
            eid = new_id(type_[:3])
            self.execute(
                "INSERT INTO entities VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (eid, project_id, type_, name, name_zh,
                 json.dumps(sorted(set(aliases or [])), ensure_ascii=False),
                 json.dumps(attrs or {}, ensure_ascii=False), None, None,
                 json.dumps([route_id] if route_id else []), now()),
            )
            return eid, True
        merged_aliases = sorted(set(json.loads(row["aliases"])) | set(aliases or []))
        merged_attrs = {**json.loads(row["attrs"]), **(attrs or {})}
        found_by = json.loads(row["found_by"])
        if route_id and route_id not in found_by:
            found_by.append(route_id)
        self.execute(
            "UPDATE entities SET name_zh=COALESCE(?, name_zh), aliases=?, attrs=?, found_by=? WHERE id=?",
            (name_zh, json.dumps(merged_aliases, ensure_ascii=False),
             json.dumps(merged_attrs, ensure_ascii=False), json.dumps(found_by), row["id"]),
        )
        return row["id"], False

    def set_scope(self, entity_id: str, in_scope: bool | None, reason: str) -> None:
        val = None if in_scope is None else int(in_scope)
        self.execute("UPDATE entities SET in_scope=?, scope_reason=? WHERE id=?", (val, reason, entity_id))

    def link(self, project_id: str, src: str, rel: str, dst: str, attrs: dict[str, Any] | None = None) -> None:
        self.execute(
            "INSERT OR REPLACE INTO links VALUES (?,?,?,?,?)",
            (project_id, src, rel, dst, json.dumps(attrs or {}, ensure_ascii=False)),
        )

    def entities(self, project_id: str, type_: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM entities WHERE project_id=?"
        params: list[Any] = [project_id]
        if type_:
            sql += " AND type=?"
            params.append(type_)
        rows = self.query(sql + " ORDER BY name", params)
        for r in rows:
            r["aliases"] = json.loads(r["aliases"])
            r["attrs"] = json.loads(r["attrs"])
            r["found_by"] = json.loads(r["found_by"])
        return rows

    def add_fact(self, fact: dict[str, Any]) -> str:
        fid = fact.get("id") or new_id("fct")
        self.execute(
            "INSERT INTO facts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fid, fact["project_id"], fact["entity_id"], fact["field"],
             json.dumps(fact["value"], ensure_ascii=False), fact["tier"], fact["status"],
             fact.get("source_id"), fact.get("quote"), fact.get("quote_start"), fact.get("quote_end"),
             json.dumps(fact.get("context") or {}, ensure_ascii=False), fact["extracted_by"],
             fact.get("supersedes"), now()),
        )
        return fid

    def current_facts(self, project_id: str, entity_id: str | None = None) -> list[dict[str, Any]]:
        """未被后续版本取代的事实。"""
        sql = ("SELECT * FROM facts f WHERE project_id=? AND NOT EXISTS "
               "(SELECT 1 FROM facts g WHERE g.supersedes=f.id)")
        params: list[Any] = [project_id]
        if entity_id:
            sql += " AND entity_id=?"
            params.append(entity_id)
        rows = self.query(sql + " ORDER BY entity_id, field", params)
        for r in rows:
            r["value"] = json.loads(r["value"])
            r["context"] = json.loads(r["context"])
        return rows

    def log_coverage(self, run_id: str, route_id: str, region: str, query: str, status: str,
                     hits: int = 0, new_entities: int = 0, note: str | None = None) -> None:
        self.execute(
            "INSERT INTO coverage (run_id, route_id, region, query, status, hits, new_entities, note, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, route_id, region, query, status, hits, new_entities, note, now()),
        )
