from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from ciw2.store import backup
from ciw2.store.cas import CAS
from ciw2.store.db import DB

RAW = b"raw source bytes for ciw2 backup"
TEXT = "原文纯文本：阿卡迪亚研究".encode()
TABLES = ("projects", "runs", "stages", "agent_steps", "sources", "entities", "links", "facts", "coverage")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seed(root: Path) -> tuple[Path, DB]:
    data = root / "data"
    data.mkdir()
    db = DB(data / "ciw2.sqlite3")
    cas = CAS(data / "cas")
    raw = cas.put(RAW)
    text = cas.put(TEXT)
    pid = db.create_project("特应性皮炎", ["A"], focus="IL-31")
    rid = db.create_run(pid)
    db.set_run(rid, "running")
    db.set_stage(rid, "universe", "succeeded", {"candidates": 2})
    db.log_step(rid, "universe", "universe-global", 1, "assistant", "步骤")
    eid, _ = db.upsert_entity(pid, "drug", "nemolizumab", aliases=["CD14152"], route_id="global:ctgov")
    db.link(pid, eid, "drug-target", "tgt_il31ra", {"phase": "approved"})
    db.add_source(pid, "ctgov", "https://example.org/trial", raw, title="trial", text_digest=text)
    db.add_fact({"project_id": pid, "entity_id": eid, "field": "design.sample_size", "value": 940,
                 "tier": "critical", "status": "verified", "source_id": "src_x", "quote": "940 例",
                 "quote_start": 0, "quote_end": 4, "extracted_by": "code:test"})
    db.log_coverage(rid, "global:ctgov:condition", "global", "AD", "ok", hits=3, new_entities=1)
    return data, db


def _close(db: DB) -> None:
    db._conn.close()


def _rows(path: Path, sql: str) -> list[tuple]:
    with contextlib.closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as conn:
        return list(conn.execute(sql))


def _dump(path: Path) -> dict[str, list[str]]:
    return {table: sorted(repr(row) for row in _rows(path, f"SELECT * FROM {table}")) for table in TABLES}


def _load(backup_dir: Path) -> dict:
    return json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))


def _save(backup_dir: Path, manifest: dict) -> None:
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _leftovers(destination: Path) -> list[str]:
    return sorted(p.name for p in destination.parent.iterdir() if p.name.startswith(f".{destination.name}."))


def test_backup_roundtrip_with_non_ascii_paths(tmp_path):
    data = tmp_path / "数据 目录"
    data.mkdir()
    db = DB(data / "ciw2.sqlite3")
    db.create_project("特应性皮炎", ["A"])
    _close(db)
    out = tmp_path / "备份 输出"
    manifest = backup.create_backup(data, out)
    restored = tmp_path / "恢复 目录"
    assert backup.restore_backup(out, restored) == manifest
    assert _rows(restored / "ciw2.sqlite3", "SELECT indication FROM projects") == [("特应性皮炎",)]


def test_create_backup_snapshots_committed_wal_state_without_touching_source(tmp_path):
    data, db = _seed(tmp_path)
    wal = data / "ciw2.sqlite3-wal"
    assert wal.exists()
    db.execute("BEGIN")
    db.create_project("未提交适应症", ["B"])
    cas_root = data / "cas"
    cas_before = {p.relative_to(data).as_posix(): p.read_bytes() for p in cas_root.rglob("*") if p.is_file()}
    before = (_sha((data / "ciw2.sqlite3").read_bytes()), _sha(wal.read_bytes()))
    manifest = backup.create_backup(data, tmp_path / "backup")
    after = (_sha((data / "ciw2.sqlite3").read_bytes()), _sha(wal.read_bytes()))
    cas_after = {p.relative_to(data).as_posix(): p.read_bytes() for p in cas_root.rglob("*") if p.is_file()}
    assert before == after
    assert cas_before == cas_after
    assert wal.exists()
    snapshot = tmp_path / "backup" / "ciw2.sqlite3"
    assert _rows(snapshot, "SELECT indication FROM projects") == [("特应性皮炎",)]
    assert _rows(snapshot, "SELECT count(*) FROM facts") == [(1,)]
    assert manifest["files"]["ciw2.sqlite3"] == _sha(snapshot.read_bytes())
    db.execute("ROLLBACK")
    assert [row["indication"] for row in db.query("SELECT indication FROM projects")] == ["特应性皮炎"]


def test_create_backup_manifest_is_exact_and_copies_only_referenced_cas(tmp_path):
    data, db = _seed(tmp_path)
    pid = db.one("SELECT id FROM projects")["id"]
    db.add_source(pid, "pubmed", "https://example.org/second", _sha(RAW), text_digest=_sha(RAW))
    CAS(data / "cas").put(b"unreferenced blob")
    (data / "portals").mkdir()
    (data / "portals" / "A.html").write_text("<html></html>", encoding="utf-8")
    (data / "credentials.env").write_text("TOKEN=secret", encoding="utf-8")
    out = tmp_path / "backup"
    manifest = backup.create_backup(data, out)
    raw, text = _sha(RAW), _sha(TEXT)
    assert manifest == {
        "schema_version": "ciw2-backup-v1",
        "files": {
            "ciw2.sqlite3": _sha((out / "ciw2.sqlite3").read_bytes()),
            f"cas/{raw[:2]}/{raw}": raw,
            f"cas/{text[:2]}/{text}": text,
        },
    }
    assert _load(out) == manifest
    assert sorted(p.name for p in out.iterdir()) == ["cas", "ciw2.sqlite3", "manifest.json"]
    assert (out / f"cas/{raw[:2]}/{raw}").read_bytes() == RAW
    assert (out / f"cas/{text[:2]}/{text}").read_bytes() == TEXT


def test_create_backup_accepts_empty_source_set(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    DB(data / "ciw2.sqlite3").create_project("无来源", ["A"])
    out = tmp_path / "backup"
    manifest = backup.create_backup(data, out)
    assert manifest["files"].keys() == {"ciw2.sqlite3"}
    restored = tmp_path / "restored"
    assert backup.restore_backup(out, restored) == manifest
    assert _rows(restored / "ciw2.sqlite3", "SELECT indication FROM projects") == [("无来源",)]
    assert [p.name for p in restored.iterdir()] == ["ciw2.sqlite3"]


def test_create_backup_rejects_missing_blob(tmp_path):
    data, _ = _seed(tmp_path)
    (data / "cas" / _sha(RAW)[:2] / _sha(RAW)).unlink()
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_create_backup_rejects_corrupt_blob(tmp_path):
    data, _ = _seed(tmp_path)
    (data / "cas" / _sha(TEXT)[:2] / _sha(TEXT)).write_bytes(b"tampered")
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()
    assert _leftovers(tmp_path / "backup") == []


@pytest.mark.parametrize("digest", [_sha(RAW).upper(), _sha(RAW)[:63], "", "z" * 64])
def test_create_backup_rejects_malformed_digest_reference(tmp_path, digest):
    data, db = _seed(tmp_path)
    pid = db.one("SELECT id FROM projects")["id"]
    db.add_source(pid, "ctgov", "https://example.org/bad", digest)
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_create_backup_requires_existing_database(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(backup.BackupError):
        backup.create_backup(tmp_path / "empty", tmp_path / "backup")
    with pytest.raises(backup.BackupError):
        backup.create_backup(tmp_path / "missing", tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_create_backup_rejects_existing_empty_destination(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    out.mkdir()
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, out)
    assert list(out.iterdir()) == []


def test_create_backup_rejects_overlapping_destination(tmp_path):
    data, _ = _seed(tmp_path)
    for destination in (data, data / "backup", tmp_path):
        with pytest.raises(backup.BackupError):
            backup.create_backup(data, destination)
    assert not (data / "backup").exists()


def test_create_backup_rejects_symlinked_database(tmp_path):
    data, db = _seed(tmp_path)
    _close(db)
    real = tmp_path / "real.sqlite3"
    (data / "ciw2.sqlite3").rename(real)
    (data / "ciw2.sqlite3").symlink_to(real)
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_create_backup_rejects_symlinked_cas_directory(tmp_path):
    data, _ = _seed(tmp_path)
    moved = tmp_path / "cas-real"
    (data / "cas").rename(moved)
    (data / "cas").symlink_to(moved, target_is_directory=True)
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, tmp_path / "backup")


def test_create_backup_rejects_symlinked_cas_blob_with_identical_bytes(tmp_path):
    data, _ = _seed(tmp_path)
    blob = data / "cas" / _sha(RAW)[:2] / _sha(RAW)
    copy = tmp_path / "blob-copy"
    copy.write_bytes(blob.read_bytes())
    blob.unlink()
    blob.symlink_to(copy)
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, tmp_path / "backup")


def test_create_backup_rejects_symlinked_destination(tmp_path):
    data, _ = _seed(tmp_path)
    link = tmp_path / "backup"
    link.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, link)
    assert not (tmp_path / "elsewhere").exists()


def test_create_backup_copy_failure_publishes_nothing(tmp_path, monkeypatch):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"

    def boom(src, dst):
        raise OSError("injected copy failure")

    monkeypatch.setattr(backup, "_copy_verified", boom)
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, out)
    assert not out.exists()
    assert _leftovers(out) == []


def test_create_backup_publish_failure_publishes_nothing(tmp_path, monkeypatch):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"

    def boom(staging, destination):
        raise OSError("injected publish failure")

    monkeypatch.setattr(backup.os, "rename", boom)
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, out)
    assert not out.exists()
    assert _leftovers(out) == []


def test_backup_restore_roundtrip_preserves_rows_and_cas_bytes(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    restored = tmp_path / "restored"
    manifest = backup.create_backup(data, out)
    assert backup.restore_backup(out, restored) == manifest
    assert _dump(restored / "ciw2.sqlite3") == _dump(data / "ciw2.sqlite3")
    for relative, digest in manifest["files"].items():
        if relative != "ciw2.sqlite3":
            assert _sha((restored / relative).read_bytes()) == digest
    assert _rows(restored / "ciw2.sqlite3", "SELECT value FROM facts") == [("940",)]
    assert sorted(p.name for p in restored.iterdir()) == ["cas", "ciw2.sqlite3"]


def _tampered_schema(manifest: dict) -> dict:
    return {"schema_version": "ciw2-backup-v2", "files": manifest["files"]}


def _tampered_extra_key(manifest: dict) -> dict:
    return {**manifest, "labels": {"x": "y"}}


def _tampered_database_digest(manifest: dict) -> dict:
    return {"schema_version": manifest["schema_version"],
            "files": {**manifest["files"], "ciw2.sqlite3": "0" * 64}}


def _tampered_value_type(manifest: dict) -> dict:
    return {"schema_version": manifest["schema_version"], "files": {**manifest["files"], "ciw2.sqlite3": 1}}


@pytest.mark.parametrize("mutate", [_tampered_schema, _tampered_extra_key, _tampered_database_digest,
                                    _tampered_value_type])
def test_restore_rejects_tampered_manifest(tmp_path, mutate):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    backup.create_backup(data, out)
    _save(out, mutate(_load(out)))
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


@pytest.mark.parametrize("key,value", [
    ("../escape", "0" * 64),
    ("/etc/passwd", "0" * 64),
    ("cas/00/" + "1" * 64, "1" * 64),
    ("portals/A.html", "0" * 64),
    ("cas/" + "1" * 64, "1" * 64),
    ("cas/11/" + "1" * 64 + "/x", "1" * 64),
])
def test_restore_rejects_unsafe_manifest_paths(tmp_path, key, value):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    backup.create_backup(data, out)
    manifest = _load(out)
    manifest["files"][key] = value
    _save(out, manifest)
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_restore_rejects_incomplete_manifest_cas_set(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    backup.create_backup(data, out)
    relative = f"cas/{_sha(TEXT)[:2]}/{_sha(TEXT)}"
    manifest = _load(out)
    del manifest["files"][relative]
    _save(out, manifest)
    (out / relative).unlink()
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_restore_rejects_extra_declared_cas_blob(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    backup.create_backup(data, out)
    extra = b"extra blob"
    digest = _sha(extra)
    relative = f"cas/{digest[:2]}/{digest}"
    (out / relative).parent.mkdir()
    (out / relative).write_bytes(extra)
    manifest = _load(out)
    manifest["files"][relative] = digest
    _save(out, manifest)
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_restore_rejects_declared_file_that_is_absent(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    backup.create_backup(data, out)
    digest = _sha(b"never stored")
    manifest = _load(out)
    manifest["files"][f"cas/{digest[:2]}/{digest}"] = digest
    _save(out, manifest)
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


@pytest.mark.parametrize("damage", ["delete", "corrupt"])
def test_restore_rejects_damaged_backup_blob(tmp_path, damage):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    backup.create_backup(data, out)
    blob = out / f"cas/{_sha(TEXT)[:2]}/{_sha(TEXT)}"
    if damage == "delete":
        blob.unlink()
    else:
        blob.write_bytes(b"corrupt")
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_restore_rejects_symlinked_backup_member(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    backup.create_backup(data, out)
    relative = f"cas/{_sha(TEXT)[:2]}/{_sha(TEXT)}"
    target = tmp_path / "stored-copy"
    target.write_bytes((out / relative).read_bytes())
    (out / relative).unlink()
    (out / relative).symlink_to(target)
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_restore_rejects_symlinked_backup_directory(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    backup.create_backup(data, out)
    link = tmp_path / "backup-link"
    link.symlink_to(out, target_is_directory=True)
    with pytest.raises(backup.BackupError):
        backup.restore_backup(link, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
    parent_link = tmp_path / "parent-link"
    parent_link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(backup.BackupError):
        backup.restore_backup(parent_link / "backup", tmp_path / "restored-via-link")
    assert not (tmp_path / "restored-via-link").exists()



def test_restore_rejects_symlinked_destination(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    backup.create_backup(data, out)
    link = tmp_path / "restored"
    link.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, link)
    assert not (tmp_path / "elsewhere").exists()


def test_restore_rejects_existing_and_overlapping_destination(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    backup.create_backup(data, out)
    existing = tmp_path / "restored"
    existing.mkdir()
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, existing)
    assert list(existing.iterdir()) == []
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, out / "inner")
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, out)


def test_restore_copy_failure_keeps_backup_and_publishes_nothing(tmp_path, monkeypatch):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    manifest = backup.create_backup(data, out)
    before = {relative: _sha((out / relative).read_bytes()) for relative in manifest["files"]}
    manifest_before = _sha((out / "manifest.json").read_bytes())
    real = backup._copy_verified
    calls = {"count": 0}

    def flaky(src, dst):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("injected copy failure")
        return real(src, dst)

    monkeypatch.setattr(backup, "_copy_verified", flaky)
    destination = tmp_path / "restored"
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, destination)
    assert calls["count"] == 2
    assert not destination.exists()
    assert _leftovers(destination) == []
    assert {relative: _sha((out / relative).read_bytes()) for relative in manifest["files"]} == before
    assert _sha((out / "manifest.json").read_bytes()) == manifest_before


def test_restore_publish_failure_keeps_backup_and_publishes_nothing(tmp_path, monkeypatch):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    manifest = backup.create_backup(data, out)
    before = {relative: _sha((out / relative).read_bytes()) for relative in manifest["files"]}

    def boom(staging, destination):
        raise OSError("injected publish failure")

    monkeypatch.setattr(backup.os, "rename", boom)
    destination = tmp_path / "restored"
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, destination)
    assert not destination.exists()
    assert _leftovers(destination) == []
    assert {relative: _sha((out / relative).read_bytes()) for relative in manifest["files"]} == before


def test_backup_and_restore_never_construct_the_application_database(tmp_path, monkeypatch):
    data, db = _seed(tmp_path)
    _close(db)

    def forbidden(self, *args, **kwargs):
        raise AssertionError("DB constructor must not run during backup or restore")

    monkeypatch.setattr(DB, "__init__", forbidden)
    out = tmp_path / "backup"
    manifest = backup.create_backup(data, out)
    restored = tmp_path / "restored"
    assert backup.restore_backup(out, restored) == manifest
    assert _sha((restored / "ciw2.sqlite3").read_bytes()) == manifest["files"]["ciw2.sqlite3"]
    assert _dump(restored / "ciw2.sqlite3") == _dump(data / "ciw2.sqlite3")


def test_create_backup_rejects_symlinked_empty_cas_directory(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    db = DB(data / "ciw2.sqlite3")
    _close(db)
    real_cas = tmp_path / "cas-real"
    real_cas.mkdir()
    (data / "cas").symlink_to(real_cas, target_is_directory=True)
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_restore_rejects_duplicate_manifest_keys(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    manifest = backup.create_backup(data, out)
    path = out / "manifest.json"
    content = path.read_text(encoding="utf-8")
    entry = f'"ciw2.sqlite3": "{manifest["files"]["ciw2.sqlite3"]}"'
    assert content.count(entry) == 1
    path.write_text(content.replace(entry, f"{entry}, {entry}", 1), encoding="utf-8")
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_backup_and_restore_reject_symlinked_destination_parent(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    backup.create_backup(data, out)
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, linked_parent / "new-backup")
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, linked_parent / "restored")
    assert list(real_parent.iterdir()) == []
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, linked_parent / ".." / "dotdot-backup")
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, linked_parent / ".." / "dotdot-restore")
    assert not (tmp_path / "dotdot-backup").exists()
    assert not (tmp_path / "dotdot-restore").exists()


def test_backup_rejects_corrupt_database(tmp_path):
    data, db = _seed(tmp_path)
    _close(db)
    (data / "ciw2.sqlite3").write_bytes(b"not a sqlite database")
    with pytest.raises(backup.BackupError):
        backup.create_backup(data, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_restore_rejects_corrupt_database_with_matching_manifest_hash(tmp_path):
    data, _ = _seed(tmp_path)
    out = tmp_path / "backup"
    manifest = backup.create_backup(data, out)
    corrupt = b"not a sqlite database"
    (out / "ciw2.sqlite3").write_bytes(corrupt)
    manifest["files"]["ciw2.sqlite3"] = _sha(corrupt)
    _save(out, manifest)
    with pytest.raises(backup.BackupError):
        backup.restore_backup(out, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
