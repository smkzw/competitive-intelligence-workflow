"""Owner challenges: ancestor links and ambiguous manifests at the backup boundary."""
import json
import sqlite3
import threading

import pytest

from ciw2.store import backup
from ciw2.store.cas import CAS
from ciw2.store.db import DB


def data_at(path):
    path.mkdir(parents=True)
    db=DB(path/'ciw2.sqlite3')
    pid=db.create_project('原资料',['C'])
    digest=CAS(path/'cas').put('来源片段'.encode())
    db.add_source(pid,'web','https://example.org',digest,text_digest=digest)
    return path


@pytest.mark.parametrize('operation',['source_parent','target_parent','restore_parent'])
def test_ancestor_symlink_is_rejected_before_reading_or_publishing(tmp_path,operation):
    real=tmp_path/'real'
    data=data_at(real/'data')
    link=tmp_path/'alias'
    link.symlink_to(real,target_is_directory=True)
    target=tmp_path/'new'
    if operation=='restore_parent':
        backup.create_backup(data,real/'saved')
        call=lambda:backup.restore_backup(link/'saved',target)
    elif operation=='target_parent':
        target=real/'new'
        call=lambda:backup.create_backup(data,link/'new')
    else:call=lambda:backup.create_backup(link/'data',target)
    with pytest.raises(backup.BackupError):call()
    assert not target.exists()


def test_duplicate_manifest_keys_are_not_silently_last_wins(tmp_path):
    data=data_at(tmp_path/'data')
    saved=tmp_path/'saved'
    backup.create_backup(data,saved)
    manifest=saved/'manifest.json'
    old=json.loads(manifest.read_text())
    # Byte-level ambiguity even if the repeated final value happens to be valid.
    manifest.write_text('{"schema_version":"wrong","schema_version":"ciw2-backup-v1","files":'+json.dumps(old['files'])+'}')
    with pytest.raises(backup.BackupError):backup.restore_backup(saved,tmp_path/'restored')
    assert not (tmp_path/'restored').exists()


def test_exclusively_locked_database_does_not_leave_backup_waiting_indefinitely(tmp_path,monkeypatch):
    data=tmp_path/'data'
    data.mkdir()
    writer=sqlite3.connect(data/'ciw2.sqlite3',check_same_thread=False)
    writer.executescript('CREATE TABLE sources(digest TEXT, text_digest TEXT);')
    writer.execute('BEGIN EXCLUSIVE')
    # Always release our synthetic lock, even against the original unbounded implementation.
    release=threading.Timer(0.8,writer.rollback)
    monkeypatch.setattr(backup,'_TIMEOUT',0.05)
    release.start()
    try:
        with pytest.raises(backup.BackupError):backup.create_backup(data,tmp_path/'new')
    finally:
        release.join()
        writer.close()
    assert not (tmp_path/'new').exists()
