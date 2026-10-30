"""A failed Chinese reading batch has one content-preserving, resumable recovery."""
import json
from copy import deepcopy

import pytest

from ciw.verify.crosscheck import CheckedItem, CrosscheckFailed
from ciw.verify.design_labels import _atoms, _task, enrich_design_labels


def source_rows(count=4):
    return dict(rows=[dict(trial_id=f"trial-{i}", design_excerpts=[dict(topic_id="dose", snippets=[dict(
        text=f"The daily dose is {i + 1} mg.", condition="", cohort_quote="", timeframe="",
        source_id=f"source-{i}", field="arm", criterion_role="unspecified",
        context=f"The daily dose is {i + 1} mg. Full context must stay whole.")])]) for i in range(count)])


def cases(c):
    atoms = _atoms(c)
    keys = sorted(atoms)
    middle = len(keys) // 2
    groups = [atoms, {k: atoms[k] for k in keys[:middle]}, {k: atoms[k] for k in keys[middle:]}]
    return {_task(group).task_id: group for group in groups if group }


def replies(batch, wrong=False):
    out = []
    for k, atom in batch.items():
        dose = atom["text"].split("is ")[1].split(" mg")[0]
        item = dict(clause_id=k, text_zh=f"每日剂量 {999 if wrong else dose} mg。", condition_zh="",
                    cohort_zh="", timeframe_zh="", quote=atom["text"])
        out.append(CheckedItem(item, "verified", (k,), calls=[dict(role="verify", family="glm")]))
    return out


def exhausted(*, error="JSONDecodeError", reason="length", earlier=False):
    calls = [dict(role="extract", family="deepseek", finish_reason=reason, error=error)]
    if earlier:
        calls.insert(0, dict(role="extract", family="deepseek", finish_reason="length", error="JSONDecodeError"))
    return CrosscheckFailed("synthetic completed failure", calls=calls)


def test_exhausted_parent_splits_once_and_keeps_all_original_context(ws, monkeypatch):
    c = source_rows()
    before = deepcopy(c)
    groups, calls = cases(c), []

    def review(task, _roles):
        batch = groups[task.task_id]
        calls.append(len(batch))
        assert all(atom["context"] in task.source_text for atom in batch.values())
        if len(batch) == 4:
            raise exhausted()
        return replies(batch)

    monkeypatch.setattr("ciw.verify.design_labels.crosscheck", review)
    assert not enrich_design_labels(ws, c, {"test": True})
    assert calls == [4, 2, 2]
    assert len(ws.read_stage("research-design-reading")["items"]) == 4
    assert any(r["status"] == "failed" for r in ws.verifications().values())
    for row in c["rows"]:
        for excerpt in row["design_excerpts"]:
            for snippet in excerpt["snippets"]:
                assert snippet.pop("reading")["text_zh"].startswith("每日剂量")
    assert c == before
    assert not enrich_design_labels(ws, source_rows(), {"test": True})
    assert calls == [4, 2, 2]


def test_resume_retains_fixed_children_and_does_not_repeat_the_successful_sibling(ws, monkeypatch):
    c = source_rows()
    groups, calls = cases(c), []
    children = [_task(group).task_id for group in groups.values() if len(group) == 2]
    fail_right = True

    def review(task, _roles):
        batch = groups[task.task_id]
        calls.append(task.task_id)
        if len(batch) == 4:
            raise exhausted()
        if task.task_id == children[1] and fail_right:
            raise exhausted(error="HTTPError", reason=None)
        return replies(batch)

    monkeypatch.setattr("ciw.verify.design_labels.crosscheck", review)
    with pytest.raises(CrosscheckFailed):
        enrich_design_labels(ws, c, {"test": True})
    assert len(ws.read_stage("research-design-reading")["items"]) == 2
    fail_right = False
    assert not enrich_design_labels(ws, source_rows(), {"test": True})
    assert calls == [_task(_atoms(c)).task_id, children[0], children[1], children[1]]
    assert len(ws.read_stage("research-design-reading")["items"]) == 4


@pytest.mark.parametrize("error,reason,earlier", [
    ("HTTPError", None, False), ("HTTPError", None, True),
    ("JSONDecodeError", None, False), ("OSError", None, False),
])
def test_transport_and_non_length_format_failures_never_split(ws, monkeypatch, error, reason, earlier):
    calls = []

    def review(task, _roles):
        calls.append(task.task_id)
        raise exhausted(error=error, reason=reason, earlier=earlier)

    monkeypatch.setattr("ciw.verify.design_labels.crosscheck", review)
    with pytest.raises(CrosscheckFailed):
        enrich_design_labels(ws, source_rows(), {"test": True})
    assert len(calls) == 1
    assert not ws.read_stage("research-design-reading") or not ws.read_stage("research-design-reading").get("items")


def test_a_child_has_no_recursive_split_and_failure_cannot_change_current(ws, monkeypatch):
    calls = []
    current = ws.root / "releases/current.json"
    current.parent.mkdir(exist_ok=True)
    current.write_text('{"release_id":"previous-published"}')
    before = current.read_bytes()

    def review(task, _roles):
        calls.append(task.task_id)
        raise exhausted()

    monkeypatch.setattr("ciw.verify.design_labels.crosscheck", review)
    with pytest.raises(CrosscheckFailed):
        enrich_design_labels(ws, source_rows(), {"test": True})
    assert len(calls) == 2
    assert current.read_bytes() == before


def test_one_large_atom_is_not_cut_or_split(ws, monkeypatch):
    c = source_rows(1)
    snippet = c["rows"][0]["design_excerpts"][0]["snippets"][0]
    snippet["context"] += " source context" * 4000
    calls = []

    def review(task, _roles):
        calls.append(task.task_id)
        assert snippet["context"] in task.source_text
        raise exhausted()

    monkeypatch.setattr("ciw.verify.design_labels.crosscheck", review)
    with pytest.raises(CrosscheckFailed):
        enrich_design_labels(ws, c, {"test": True})
    assert len(calls) == 1


def test_recovered_child_still_requires_the_original_clinical_guard(ws, monkeypatch):
    c = source_rows()
    groups = cases(c)

    def review(task, _roles):
        batch = groups[task.task_id]
        if len(batch) == 4:
            raise exhausted()
        return replies(batch, wrong=True)

    monkeypatch.setattr("ciw.verify.design_labels.crosscheck", review)
    issues = enrich_design_labels(ws, c, {"test": True})
    assert len(issues) == 4
    assert not ws.read_stage("research-design-reading")["items"]
    assert all("reading" not in row["design_excerpts"][0]["snippets"][0] for row in c["rows"])


def test_recovery_uses_real_two_family_crosscheck_and_keeps_failed_raw_cache(ws):
    from ciw.verify.llm import CachedBackend, FakeBackend

    c = source_rows()
    groups = cases(c)
    seen = []
    a, b = FakeBackend("deepseek", "synthetic-a", None), FakeBackend("glm", "synthetic-b", None)

    def respond(system, user, backend):
        batch = next(group for task_id, group in groups.items()
                     if all(k in user for k in group) and
                     sum(k in user for k in _atoms(c)) == len(group))
        seen.append((backend.family, len(batch)))
        if len(batch) == 4 and backend is a:
            backend.receipt = dict(finish_reason="length")
            return ""
        backend.receipt = dict(finish_reason="stop")
        return json.dumps(dict(items=[r.item for r in replies(batch)]))

    a.responder = lambda system, user: respond(system, user, a)
    b.responder = lambda system, user: respond(system, user, b)
    roles = dict(extractor_a=CachedBackend(a, ws), verifier=CachedBackend(b, ws))
    assert not enrich_design_labels(ws, c, roles)
    assert seen == [("deepseek", 4), ("deepseek", 4), ("deepseek", 2), ("glm", 2),
                    ("deepseek", 2), ("glm", 2)]
    with ws.db() as con:
        assert con.execute("select count(*) from llm_cache where response='' ").fetchone()[0] == 2



def test_saved_recovery_records_children_before_any_child_call(ws, monkeypatch):
    c = source_rows()
    groups = cases(c)
    parent = _task(_atoms(c)).task_id

    def review(task, _roles):
        batch = groups[task.task_id]
        if len(batch) == 4:
            raise exhausted()
        saved = ws.read_stage("research-design-reading")
        plan = saved["recoveries"][parent]
        assert plan["parent_clause_ids"] == sorted(_atoms(c))
        assert task.task_id in {child["task_id"] for child in plan["children"]}
        assert set().union(*(set(child["clause_ids"]) for child in plan["children"])) == set(_atoms(c))
        assert ws.verifications()["design-reading:"+parent]["clause_ids"] == sorted(_atoms(c))
        return replies(batch)

    monkeypatch.setattr("ciw.verify.design_labels.crosscheck", review)
    assert not enrich_design_labels(ws, c, {"test": True})


def test_changed_or_corrupt_child_plan_is_not_silently_rebound(ws, monkeypatch):
    c = source_rows()
    parent = _task(_atoms(c)).task_id
    ws.write_stage("research-design-reading", dict(items={}, recoveries={
        parent: dict(parent_clause_ids=sorted(_atoms(c)), children=[dict(task_id="wrong", clause_ids=[])])}))

    def unexpected(*args):
        raise AssertionError("invalid source-bound child plan must fail before a model call")

    monkeypatch.setattr("ciw.verify.design_labels.crosscheck", unexpected)
    with pytest.raises(ValueError, match="不匹配"):
        enrich_design_labels(ws, c, {"test": True})
