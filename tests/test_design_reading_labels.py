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


@pytest.mark.parametrize("source,label", [
    ("Investigator's assessment and eGFR ≥40 mL/min.","研究者评估，eGFR ≥40 mL/min。"),
    ("Hemoglobin A1c (HbA1c) <7.5% within 2 years.","2年内 HbA1c <7.5%。"),
    ("After at least 3 months, 24-hour urine collection.","至少3个月后，24小时尿液采集。"),
    ("UPCR ≥3.0 g/g from a 24-hour urine collection or proteinuria ≥3.5 gram per 24 hour [g/24 h].",
     "24小时尿液采集，UPCR ≥3.0 g/g 或蛋白尿 ≥3.5 g/24 h。")])
def test_literal_aliases_and_time_spellings_do_not_force_redundant_chinese(source,label):
    from ciw.verify.design_labels import _atoms, _check
    c,s=material()
    s.update(text=source,condition="",cohort_quote="",timeframe="")
    atoms=_atoms(c)
    atom=next(iter(atoms.values()))
    item=dict(clause_id=atom['clause_id'],text_zh=label,condition_zh="",cohort_zh="",timeframe_zh="",quote=source)
    assert _check(item,atoms)[0]
    if '24-hour' in source:
        assert not _check({**item,'text_zh':label.replace('24小时','12小时')},atoms)[0]


@pytest.mark.parametrize('prefix',['','Original heading: '])
def test_complete_applicability_is_one_reading_point_without_dropping_its_source_predicates(prefix):
    from ciw.verify.design_labels import _atoms
    c,s=material()
    full="Patients may enter based on clinician review of normal function, Marker Q ≥20 U/mL, and negative work-up."
    s.update(text="Marker Q ≥20 U/mL",condition=full,context=prefix+full,cohort_quote="",timeframe="")
    a=next(iter(_atoms(c).values()))
    assert a['text']==prefix+full and not a['condition']
    assert s['text']=="Marker Q ≥20 U/mL" and s['condition']==full


@pytest.mark.parametrize('proof', ['valid','a_only','no_cache','wrong_source','changed_source'])
def test_only_retained_matching_verifier_items_can_be_rechecked_without_more_calls(ws,proof):
    from ciw.verify.design_labels import _atoms, enrich_design_labels
    c,s=material()
    atom=next(iter(_atoms(c).values()))
    item=answer(atom)
    calls=[dict(role='extract',family='deepseek',model='a'),
           dict(role='verify',family='glm',model='b',n_items=1,response_id='synthetic-response')]
    note='核对结果未通过来源校验：旧时间写法规则误拒'
    if proof=='a_only':
        note='主抽取条目未被核对者确认'
        calls=calls[:1]
    ws.save_verification('design-reading:old:'+atom['clause_id'],'needs_review',
        dict(item=item,calls=calls,note=note,source_id='other' if proof=='wrong_source' else atom['source_id']))
    if proof!='no_cache':
        with ws.db() as con:
            con.execute('INSERT INTO llm_cache VALUES (?,?,?,?,?,?,?)',('test-key','b','glm','test-prompt',
                json.dumps(dict(items=[item])),'2026-01-01',json.dumps(dict(response_id='synthetic-response'))))
    if proof=='changed_source':
        s['text']=s['text'].replace('40','45')
    issues=enrich_design_labels(ws,c,None)
    assert bool(issues)==(proof!='valid')
    assert ('reading' in s)==(proof=='valid')
    if proof=='valid':
        record=next(iter(ws.verifications().values()))
        assert record['status']=='verified' and record['item']==item
        assert record['deterministic_recheck']['review_binding']['method']=='cached_verifier_item'


@pytest.mark.parametrize('source,label',[
    ('At screening, Hemoglobin A1c (HbA1c) <7.5%.','HbA1c <8.5%。'),
    ('Protein ≥3.5 gram per 12 hour [g/24 h].','蛋白 ≥3.5 g/24 h。'),
    ('At least 3 months and 24-hour collection.','至少3年，24小时采集。')])
def test_notation_repairs_do_not_erase_changed_values_or_independent_times(source,label):
    from ciw.verify.design_labels import _atoms, _check
    c,s=material()
    s.update(text=source,condition='',cohort_quote='',timeframe='')
    atoms=_atoms(c)
    key=next(iter(atoms))
    item=dict(clause_id=key,text_zh=label,condition_zh='',cohort_zh='',timeframe_zh='',quote=source)
    assert not _check(item,atoms)[0]


def test_literal_condition_and_cohort_already_in_complete_point_are_not_repeated_or_lost():
    from ciw.verify.design_labels import _atoms

    c, s = material()
    full = "Relapsed disease is defined as CR or PR after IST followed by proteinuria ≥3 g/g."
    s.update(text=full, condition="Relapsed disease", cohort_quote="Relapsed disease", context=full, timeframe="")
    before = deepcopy(s)
    atom = next(iter(_atoms(c).values()))
    assert atom["text"] == full and atom["condition"] == "" and atom["cohort_quote"] == ""
    assert s == before
