"""Offline get_unit/put_unit must match non-PDF CAS bytes and leave receipts unchanged."""
from __future__ import annotations

import json

import pytest

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.recovery import get_unit, put_unit
from ciw2.service import Service
from ciw2.sources import http
from ciw2.sources.http import register_text

URL = 'https://example.org/unit-source.html'
OTHER = 'https://example.org/unrelated.json'
ABSENT = 'https://example.org/not-registered'
TEXT = 'visible source text'
RAW = b'raw-html-bytes-differ-from-text'
KEY = 'nonpdf-unit'
RESULT = {'facts': [{'field': 'kept'}]}
METADATA = {'missing_digest', 'invalid_digest', 'invalid_text_digest', 'empty_text_digest', 'absent_text_digest'}
BYTES = {'remove_raw', 'corrupt_raw', 'remove_text', 'corrupt_text'}
MISS = BYTES | {'missing_digest', 'invalid_digest', 'invalid_text_digest', 'empty_text_digest'}
CASES = (
    'reuse', 'unrelated', 'absent_url', 'absent_text_digest',
    'remove_raw', 'corrupt_raw', 'remove_text', 'corrupt_text',
    'missing_digest', 'invalid_digest', 'invalid_text_digest', 'empty_text_digest',
)


def _world(settings):
    scripted = ScriptedLLM([])
    service = Service(settings, llm_factory=lambda _: (scripted, None))
    project_id = service.create_project('fixture', ['A'])
    return service.context(project_id, service.db.create_run(project_id)), scripted


def _cas_path(rc, digest: str):
    return rc.cas.root / digest[:2] / digest


def _files(rc):
    root = rc.cas.root
    found = []
    for path in root.rglob('*'):
        if path.is_file():
            found.append((path.relative_to(root).as_posix(), path.read_bytes()))
    return sorted(found)


def _stages(rc):
    return rc.db.query(
        'SELECT name, status, output_json, error FROM stages WHERE run_id=? ORDER BY name', (rc.run_id,))


def _rows(rc):
    return rc.db.query('SELECT * FROM sources WHERE project_id=? ORDER BY rowid', (rc.project_id,))


def _steps(rc):
    return rc.db.query('SELECT role, content FROM agent_steps WHERE run_id=? ORDER BY id', (rc.run_id,))


def _mutate(rc, case: str, sid: str, raw_digest: str, text_digest: str) -> None:
    raw_path = _cas_path(rc, raw_digest)
    text_path = _cas_path(rc, text_digest)
    if case == 'remove_raw':
        raw_path.unlink()
    elif case == 'corrupt_raw':
        raw_path.write_bytes(b'corrupt-raw')
    elif case == 'remove_text':
        text_path.unlink()
    elif case == 'corrupt_text':
        text_path.write_bytes(b'corrupt-text')
    elif case == 'missing_digest':
        rc.db.execute('UPDATE sources SET digest=? WHERE id=?', ('', sid))
    elif case == 'invalid_digest':
        rc.db.execute('UPDATE sources SET digest=? WHERE id=?', ('not-a-sha256', sid))
    elif case == 'invalid_text_digest':
        rc.db.execute('UPDATE sources SET text_digest=? WHERE id=?', ('not-a-sha256', sid))
    elif case == 'empty_text_digest':
        rc.db.execute('UPDATE sources SET text_digest=? WHERE id=?', ('', sid))
    elif case == 'absent_text_digest':
        rc.db.execute('UPDATE sources SET text_digest=NULL WHERE id=?', (sid,))
    else:
        raise AssertionError(case)


@pytest.mark.parametrize('case', CASES)
def test_nonpdf_unit_reuse_requires_actual_cas_bytes(settings, monkeypatch, tmp_path, case):
    """Production get_unit/put_unit on an isolated DB; scripted model and fetch stay unused."""
    fetch_calls: list[object] = []

    def forbidden_fetch(*args, **kwargs):
        fetch_calls.append((args, kwargs))
        raise AssertionError('network fetch')

    monkeypatch.setattr(http, 'fetch', forbidden_fetch)
    assert settings.data_dir == tmp_path / 'data'
    assert RAW != TEXT.encode()
    rc, scripted = _world(settings)
    assert rc.cas.root == settings.cas_dir
    sid = register_text(rc.tool_ctx(), kind='web', url=URL, text=TEXT, raw=RAW)
    row = rc.db.one('SELECT digest, text_digest FROM sources WHERE id=?', (sid,))
    assert row['digest'] != row['text_digest']
    assert _cas_path(rc, row['digest']).read_bytes() == RAW
    assert _cas_path(rc, row['text_digest']).read_bytes() == TEXT.encode()
    if case in METADATA:
        _mutate(rc, case, sid, row['digest'], row['text_digest'])
    if case == 'absent_url':
        put_unit(rc, KEY, RESULT, urls=[ABSENT])
    else:
        put_unit(rc, KEY, RESULT, source_ids=[sid])
    if case in BYTES:
        _mutate(rc, case, sid, row['digest'], row['text_digest'])
    if case == 'unrelated':
        register_text(rc.tool_ctx(), kind='web', url=OTHER, text='other text', raw=b'other raw')
    stages, files, rows, steps = _stages(rc), _files(rc), _rows(rc), _steps(rc)
    found = get_unit(rc, KEY)
    assert [item['output_json'].encode() for item in _stages(rc)] == [item['output_json'].encode() for item in stages]
    assert _files(rc) == files and _rows(rc) == rows
    assert scripted.calls == [] and fetch_calls == []
    if case in MISS:
        assert found is None and _steps(rc) == steps
        return
    assert found == RESULT
    after = _steps(rc)
    assert after[:-1] == steps and after[-1]['role'] == 'cache'
    assert json.loads(after[-1]['content']) == {'reused_stage': KEY}
