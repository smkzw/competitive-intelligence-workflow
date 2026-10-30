"""A bare, schema-valid singleton is an envelope variation, never a scientific exemption."""
import hashlib
import json

import pytest

from ciw.verify.crosscheck import (
    CrosscheckFailed,
    ExtractionTask,
    crosscheck,
    retained_candidate,
    retained_verified,
)
from ciw.verify.design_clauses import DesignTopicReview, _check
from ciw.verify.endpoint_index import _review_binding
from ciw.verify.llm import CachedBackend, FakeBackend

SOURCE = "Inclusion Criteria:\nAge at least 18 years."
ANCHOR = "Age at least 18 years."


def topic_item():
    return dict(topic_id="age", quote=ANCHOR,
                clauses=[dict(field="eligibility", text=ANCHOR, quote=ANCHOR, criterion_role="inclusion")])


def topic_task():
    topics = {"age": {"kind": "eligibility_threshold"}}
    passages = [("eligibility", SOURCE, "eligibility")]
    return ExtractionTask("singleton-task", "synthetic-source", SOURCE, "Read the age criterion",
        DesignTopicReview, ("topic_id",), ("clauses",), item_check=lambda item: _check(item, topics, passages))


def models(ws, raw, bare_role="verifier"):
    out, seen = {}, []
    for role, family in [("extractor_a", "deepseek"), ("verifier", "glm")]:
        inner = FakeBackend(family, "test-"+family, None)

        def respond(system, user, role=role, inner=inner):
            text = raw if role == bare_role else json.dumps({"items": [topic_item()]})
            inner.receipt = {"response_id": "synthetic-"+hashlib.sha256((system+user+text).encode()).hexdigest()}
            seen.append(role)
            return text

        inner.responder = respond
        out[role] = CachedBackend(inner, ws)
    return out, seen


@pytest.mark.parametrize("role", ["extractor_a", "verifier"])
def test_schema_valid_singleton_keeps_one_exact_item_and_raw_cache(ws, role):
    raw = json.dumps(topic_item())
    roles, seen = models(ws, raw, role)
    result = crosscheck(topic_task(), roles)
    assert len(result) == 1 and result[0].status == "verified"
    assert result[0].item == DesignTopicReview.model_validate(topic_item()).model_dump()
    assert seen == ["extractor_a", "verifier"]
    call = result[0].calls[0 if role == "extractor_a" else 1]
    assert call["response_envelope"] == "single_item" and call["n_items"] == 1
    with ws.db() as con:
        rows = con.execute("SELECT family,response FROM llm_cache ORDER BY family").fetchall()
    assert len(rows) == 2
    assert dict(rows)["deepseek" if role == "extractor_a" else "glm"] == raw


@pytest.mark.parametrize("raw", [
    "{}", "[]", '{"items":{}}',
    json.dumps({"topic_id": "age", "quote": ANCHOR}),
    json.dumps(topic_item() | {"properties": {}}),
    json.dumps(topic_item()) + '\n{"topic_id":"second"}',
])
def test_incomplete_ambiguous_or_multiple_objects_still_fail_closed(ws, raw):
    roles, _ = models(ws, raw)
    with pytest.raises(CrosscheckFailed):
        crosscheck(topic_task(), roles)


def test_singleton_must_still_pass_the_production_clinical_source_check(ws):
    wrong = topic_item()
    wrong["clauses"][0]["text"] = "Age at least 19 years."
    roles, _ = models(ws, json.dumps(wrong))
    result = crosscheck(topic_task(), roles)
    assert len(result) == 1 and result[0].status == "needs_review"
    assert "条款必须逐字" in result[0].note


def test_singleton_verifier_proof_replays_and_does_not_survive_missing_raw_response(ws):
    roles, _ = models(ws, json.dumps(topic_item()))
    task = topic_task()
    checked = crosscheck(task, roles)[0]
    record = dict(task=task.task_id, source_id=task.source_id, item=checked.item,
                  calls=checked.calls, note=checked.note)
    ws.save_verification("design:"+task.task_id+":age", "verified", record)
    before = ws.verifications()
    replayed, incomplete = retained_verified(ws, task)
    assert len(replayed) == 1 and not incomplete and replayed[0].item == checked.item
    assert ws.verifications() == before
    assert retained_candidate(ws, task, record, checked.item)
    binding = _review_binding(ws, {}, checked.note, checked.item, checked.calls[-1],
                              item_model=DesignTopicReview, identity_field="topic_id", require_cache=True)
    assert binding and binding["method"] == "cached_verifier_item"
    with ws.db() as con:
        con.execute("DELETE FROM llm_cache WHERE family='glm'")
    assert retained_verified(ws, task) == ([], True)
    assert _review_binding(ws, {}, checked.note, checked.item, checked.calls[-1],
                           item_model=DesignTopicReview, identity_field="topic_id", require_cache=True) is None
