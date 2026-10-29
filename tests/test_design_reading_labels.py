"""Source-bound Chinese reading points keep the original facts and conditions intact."""
import json
from copy import deepcopy
from unittest.mock import Mock

import pytest

from ciw.verify.llm import FakeBackend


def material():
    snippet = dict(text="eGFR greater than or equal to 40 mL/min/1.73 m2 at screening.",
        condition="Biopsy may be omitted if all of the following apply:", cohort_quote="Relapsed PMN",
        timeframe="Week 24", source_id="s", field="eligibility", criterion_role="inclusion")
    c = dict(rows=[dict(trial_id="t", design_excerpts=[dict(topic_id="topic", label="肾功能", snippets=[snippet])])])
    return c, snippet


def answer(atom):
    return dict(clause_id=atom["clause_id"], text_zh="筛选时 eGFR ≥40 mL/min/1.73 m2。",
        condition_zh="全部满足以下条件时可免活检：", cohort_zh="复发 PMN", timeframe_zh="第24周",
        quote=atom["text"])


def test_checked_chinese_points_are_reusable_without_modifying_scientific_source(ws):
    from ciw.verify.design_labels import _atoms, enrich_design_labels
    c, source = material()
    before = deepcopy(source)
    atoms = _atoms(c)
    reply = Mock(return_value=json.dumps(dict(items=[answer(next(iter(atoms.values())))])))
    roles = dict(extractor_a=FakeBackend("deepseek", "a", reply), verifier=FakeBackend("glm", "b", reply))
    assert not enrich_design_labels(ws, c, roles)
    assert {key:value for key,value in source.items() if key != "reading"} == before
    assert source["reading"]["text_zh"].startswith("筛选时")
    assert source["reading"]["condition_zh"] and source["reading"]["cohort_zh"] == "复发 PMN"
    c2, s2 = material()
    assert not enrich_design_labels(ws, c2, None) and s2 == source and reply.call_count == 2


@pytest.mark.parametrize("field,bad", [("text_zh", "eGFR ≥50 mL/min/1.73 m2。"),
    ("text_zh", "筛选时 eGFR >40 mL/min/1.73 m2。"),
    ("text_zh", "筛选时 eGFR ≥40 mL/min。"),
    ("text_zh", "筛选时 eGFR ≥40 mg/dL/1.73 m2。"),
    ("condition_zh", ""), ("cohort_zh", ""), ("timeframe_zh", "第48周"), ("timeframe_zh", "第24月"),
    ("quote", "eGFR ≥40 mL/min")])
def test_reading_points_cannot_change_threshold_units_or_drop_source_conditions(field, bad):
    from ciw.verify.design_labels import _atoms, _check
    c, _ = material()
    atoms = _atoms(c)
    item = answer(next(iter(atoms.values())))
    item[field] = bad
    assert not _check(item, atoms)[0]


def test_missing_verifier_and_changed_content_never_reuse_a_chinese_point(ws):
    from ciw.verify.design_labels import _atoms, enrich_design_labels
    c, s = material()
    atom = next(iter(_atoms(c).values()))
    roles = dict(extractor_a=FakeBackend("deepseek", "a", lambda *_: json.dumps(dict(items=[answer(atom)]))),
                 verifier=FakeBackend("glm", "b", lambda *_: '{"items":[]}'))
    assert enrich_design_labels(ws, c, roles) and "reading" not in s
    c2, s2 = material()
    s2["text"] = s2["text"].replace("40", "45")
    assert enrich_design_labels(ws, c2, None) and "reading" not in s2


def test_identical_atoms_shared_by_two_themes_need_one_checked_item(ws):
    from ciw.verify.design_labels import _atoms, enrich_design_labels
    c, _ = material()
    duplicate = deepcopy(c["rows"][0]["design_excerpts"][0])
    duplicate["topic_id"] = "other-theme"
    c["rows"][0]["design_excerpts"].append(duplicate)
    atoms = _atoms(c)
    assert len(atoms) == 1
    reply = Mock(return_value=json.dumps(dict(items=[answer(next(iter(atoms.values())))])))
    roles = dict(extractor_a=FakeBackend("deepseek", "a", reply), verifier=FakeBackend("glm", "b", reply))
    assert not enrich_design_labels(ws, c, roles) and reply.call_count == 2
    assert all(e["snippets"][0]["reading"] for e in c["rows"][0]["design_excerpts"])


def test_newline_and_quotes_in_the_exact_source_do_not_break_source_binding(ws):
    from ciw.verify.design_labels import _atoms, enrich_design_labels
    c, snippet = material()
    snippet["text"] = snippet["text"].replace(" at screening.", '\n at "screening".')
    atom = next(iter(_atoms(c).values()))
    def reply(*_):
        return json.dumps(dict(items=[answer(atom)]))
    roles = dict(extractor_a=FakeBackend("deepseek", "a", reply), verifier=FakeBackend("glm", "b", reply))
    assert not enrich_design_labels(ws, c, roles)
    assert snippet["reading"] and '\n at "screening".' in snippet["text"]


def test_short_points_from_multiple_real_sources_are_batched_without_losing_provenance(ws):
    from ciw.verify.design_labels import _atoms, enrich_design_labels
    c,_ = material()
    other=deepcopy(c["rows"][0])
    other["trial_id"]="other"
    other["design_excerpts"][0]["snippets"][0]["source_id"]="second-source"
    c["rows"].append(other)
    atoms=_atoms(c)
    reply=Mock(return_value=json.dumps(dict(items=[answer(a) for a in atoms.values()])))
    roles=dict(extractor_a=FakeBackend("deepseek","a",reply),verifier=FakeBackend("glm","b",reply))
    assert not enrich_design_labels(ws,c,roles) and reply.call_count == 2
    assert {r['source_id'] for r in ws.verifications().values()} == {"s","second-source"}


@pytest.mark.parametrize("unit,valid", [("µg",True),("g",False),("ng",False)])
def test_micro_unit_prefix_cannot_disappear_or_change(unit,valid):
    from ciw.verify.design_labels import _atoms, _check
    c,s=material()
    s.update(text="The daily dose is ≥40 µg.",condition="",cohort_quote="",timeframe="")
    atoms=_atoms(c)
    a=next(iter(atoms.values()))
    item=dict(clause_id=a['clause_id'],text_zh=f"每日剂量 ≥40 {unit}。",condition_zh="",cohort_zh="",timeframe_zh="",
              quote=a['text'])
    assert _check(item,atoms)[0] == valid


def test_large_source_context_is_retained_whole_not_cut_to_the_packing_target():
    from ciw.verify.design_labels import _atoms, _batches, _task
    c,s=material()
    s['context']='Source context ' * 2500
    atoms=_atoms(c)
    batches=list(_batches({key:{**a,'material':json.dumps(a)} for key,a in atoms.items()}))
    assert len(batches)==1
    assert s['context'] in _task(atoms).source_text
