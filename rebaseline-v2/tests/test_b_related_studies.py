"""All related studies survive the B query, independently of adopted numeric results."""
import hashlib

import pytest

from ciw2.render.portal import data_b
from ciw2.store.db import DB


def setup(settings):
    settings.ensure_dirs()
    db = DB(settings.db_path)
    pid = db.create_project('特应性皮炎', ['B'])
    return db, pid


def trial(db, pid, name, flag=None, *, native=True, modules=None):
    eid, _ = db.upsert_entity(pid, 'trial', name, attrs={'has_results': flag})
    sid = db.add_source(pid, 'ctgov', f'https://clinicaltrials.gov/api/v2/studies/{name}', 'a' * 64)
    snapshot = hashlib.sha256(f'{sid}:test'.encode()).hexdigest()
    if native:
        db.link(pid, eid, 'ctgov-current', sid, attrs={'snapshot': snapshot,
            'source_id': sid, 'source_digest': 'a' * 64, 'extractor_version': 'test',
            'input_result_modules': ['outcomeMeasuresModule'] if modules is None and flag is True else modules or []})
    return eid, sid, snapshot


def result(db, pid, eid, sid, snapshot):
    return db.add_fact({'project_id': pid, 'entity_id': eid, 'field': 'result.primary.value', 'value': 0,
        'tier': 'critical', 'status': 'verified', 'source_id': sid, 'quote': '0',
        'context': {'source_snapshot': snapshot, 'endpoint': 'Clinical score', 'unit': 'points',
                    'stat_type': 'mean', 'population': 'ITT', 'timepoint': 'Week 16'},
        'extracted_by': 'code:ctgov'})


def test_unpublished_and_unknown_studies_are_not_deleted_by_a_numeric_query(settings):
    db, pid = setup(settings)
    posted = trial(db, pid, 'NCT00000001', True)
    no_results = trial(db, pid, 'NCT00000002', False)
    unknown = trial(db, pid, 'NCT00000003', True, native=False)
    fid = result(db, pid, *posted)
    before = db.query('SELECT * FROM facts')
    data = data_b(db, pid)
    rows = data['study_catalog']['rows']
    assert {r['entity_id'] for r in rows} == {posted[0], no_results[0], unknown[0]}
    assert data['study_catalog']['counts'] == {'all': 3, 'with_results': 1, 'without_results': 1,
                                              'unknown': 1, 'adopted': 1}
    assert next(r for r in rows if r['entity_id'] == no_results[0])['published_results'] is False
    assert next(r for r in rows if r['entity_id'] == unknown[0])['published_results'] is None
    assert {r['id'] for r in data['results']} == {fid} and data['results'][0]['value'] == 0
    assert db.query('SELECT * FROM facts') == before


@pytest.mark.parametrize('bad', ['digest', 'snapshot', 'modules', 'boolean'])
def test_invalid_or_conflicting_publication_evidence_stays_unknown(settings, bad):
    db, pid = setup(settings)
    eid, sid, _snapshot = trial(db, pid, 'NCT00000001', True)
    if bad == 'digest':
        db.execute("UPDATE sources SET digest=? WHERE id=?", ('b' * 64, sid))
    elif bad == 'snapshot':
        db.execute("UPDATE links SET attrs=json_set(attrs,'$.snapshot','forged')")
    elif bad == 'modules':
        db.execute("UPDATE links SET attrs=json_set(attrs,'$.input_result_modules',json('[]'))")
    else:
        db.upsert_entity(pid, 'trial', 'NCT00000001', attrs={'has_results': 'false'})
    row = data_b(db, pid)['study_catalog']['rows'][0]
    assert row['entity_id'] == eid and row['published_results'] is None
    assert data_b(db, pid)['study_catalog']['counts']['unknown'] == 1


def test_scope_filters_trials_but_not_orphans_or_mixed_parent_studies(settings):
    db, pid = setup(settings)
    kept = trial(db, pid, 'NCT00000001', False)[0]
    excluded = trial(db, pid, 'NCT00000002', False)[0]
    mixed = trial(db, pid, 'NCT00000003', False)[0]
    orphan = trial(db, pid, 'NCT00000004', None, native=False)[0]
    a = db.upsert_entity(pid, 'drug', '药物A')[0]
    b = db.upsert_entity(pid, 'drug', '药物B')[0]
    db.set_scope(a, False, '明确背景药物')
    for tid in (excluded, mixed): db.link(pid, a, 'drug-trial', tid)
    db.link(pid, b, 'drug-trial', mixed)
    assert {r['entity_id'] for r in data_b(db, pid)['study_catalog']['rows']} == {kept, mixed, orphan}
