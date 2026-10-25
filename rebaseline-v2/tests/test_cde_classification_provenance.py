"""Retain literal registration labels and reject changed claims against the same raw row."""
from dataclasses import replace

import pytest
from test_cde_browser import capture, stream

from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources import cde_browser, cde_review_browser, china_browser


def lookup(settings, monkeypatch, drug_type, classification):
    service = Service(replace(settings, china_ego_space_id=5), llm_factory=lambda _: (ScriptedLLM([]), None))
    pid = service.create_project('适应症', ['A'])
    rc = service.context(pid, service.db.create_run(pid))
    raw = capture(rows=[['1', 'CXSL2600001', '原药联合片', drug_type, '新药', classification,
                         '原企业;', '2026-01-01']])
    monkeypatch.setattr(china_browser, '_invoke', lambda *a, **k: (stream([raw]), True))
    result = cde_browser.browser_search(rc.tool_ctx(), '原药', 'drug_name')
    cde_browser.persist_candidates(rc.tool_ctx(), result, 'source:class')
    return rc


@pytest.mark.parametrize('drug_type,classification', [('治疗用生物制品', '3.3'), ('化药', '2.2'), ('化药', '')])
def test_source_class_labels_reach_candidate_without_innovation_or_approval_inference(settings, monkeypatch,
                                                                                     drug_type, classification):
    rc = lookup(settings, monkeypatch, drug_type, classification)
    drug = rc.db.entities(rc.project_id, 'drug')[0]
    ref = drug['attrs']['cde_acceptance_refs'][0]
    assert ref['drug_type'] == drug_type and ref['registration_class'] == classification
    assert ref['application_type'] == '新药' and drug['in_scope'] is None
    proven = cde_review_browser.proven_acceptance_refs(rc.tool_ctx(), drug)
    assert len(proven) == 1 and proven[0]['registration_class'] == classification
    assert rc.db.current_facts(rc.project_id) == []
    assert not any(key in drug['attrs'] for key in ['innovative', 'biosimilar', 'approved', 'mah'])


@pytest.mark.parametrize('field,value', [('drug_type', '化药'), ('registration_class', '1')])
def test_forged_class_label_does_not_reuse_an_authentic_source_id(settings, monkeypatch, field, value):
    rc = lookup(settings, monkeypatch, '治疗用生物制品', '3.3')
    drug = rc.db.entities(rc.project_id, 'drug')[0]
    ref = drug['attrs']['cde_acceptance_refs'][0]
    ref[field] = value
    assert cde_review_browser.proven_acceptance_refs(rc.tool_ctx(), drug) == []


def test_legacy_reference_without_class_fields_uses_raw_source_not_guessed_defaults(settings, monkeypatch):
    rc = lookup(settings, monkeypatch, '治疗用生物制品', '3.3')
    drug = rc.db.entities(rc.project_id, 'drug')[0]
    for key in ('drug_type', 'registration_class'):
        drug['attrs']['cde_acceptance_refs'][0].pop(key, None)
    proven = cde_review_browser.proven_acceptance_refs(rc.tool_ctx(), drug)
    assert len(proven) == 1 and proven[0]['drug_type'] == '治疗用生物制品'
    assert proven[0]['registration_class'] == '3.3'


def test_refresh_of_same_legacy_source_ref_enriches_in_place_without_duplicate_observation(settings, monkeypatch):
    rc = lookup(settings, monkeypatch, '治疗用生物制品', '3.3')
    drug = rc.db.entities(rc.project_id, 'drug')[0]
    refs = drug['attrs']['cde_acceptance_refs']
    for key in ('drug_type', 'registration_class'):
        refs[0].pop(key, None)
    refs[0]['legacy_note'] = '保留不相关元数据'
    rc.db.upsert_entity(rc.project_id, 'drug', drug['name'], attrs={'cde_acceptance_refs': refs})
    source_id = refs[0]['source_id']
    parsed = cde_review_browser.proven_acceptance_refs(rc.tool_ctx(), rc.db.entities(rc.project_id, 'drug')[0])
    cde_browser.persist_candidates(rc.tool_ctx(), {'source_id': source_id, 'results': parsed}, 'source:refresh')
    after = rc.db.entities(rc.project_id, 'drug')[0]['attrs']['cde_acceptance_refs']
    assert len(after) == 1 and after[0]['registration_class'] == '3.3'
    assert after[0]['drug_type'] == '治疗用生物制品' and after[0]['legacy_note'] == '保留不相关元数据'
