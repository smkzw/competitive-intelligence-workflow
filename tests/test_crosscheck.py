"""Two-model source review: synthetic production-function cases, not clinical evidence."""
import json

import pytest

from ciw.verify.crosscheck import CrosscheckFailed, ExtractionTask, crosscheck
from ciw.verify.llm import FakeBackend
from ciw.verify.schemas import EventItem

TEXT = "2025年9月12日，司普奇拜单抗注射液（CM310）获批准。"


def task():
    return ExtractionTask("t", "s", TEXT, "抽取里程碑", EventItem,
                          ("product_mention", "event_type"), ("date", "region"), date_fields=("date",))


def item(**kw):
    return dict(product_mention="CM310", event_type="approval", region="中国",
                date="2025-09-12", quote=TEXT, **kw)


def backend(family, items=None, raw=None, seen=None):
    def respond(system, user):
        if seen is not None:
            seen.append((system, user))
        return raw if raw is not None else json.dumps({"items": items or []}, ensure_ascii=False)
    return FakeBackend(family, family, respond)


def roles(a, b):
    return {"extractor_a": a, "verifier": b}


def test_verifier_sees_original_and_candidate_and_is_not_called_blind():
    seen = []
    out = crosscheck(task(), roles(backend("deepseek", [item()]), backend("glm", [item()], seen=seen)))
    assert out[0].status == "verified" and len(out[0].calls) == 2
    assert [c["role"] for c in out[0].calls] == ["extract", "verify"]
    assert TEXT in seen[0][1] and "待核候选" in seen[0][1]


def test_verifier_can_correct_an_invalid_candidate_against_original():
    wrong = dict(item(), date="2024-01-01")
    out = crosscheck(task(), roles(backend("deepseek", [wrong]), backend("glm", [item()])))
    assert out[0].status == "verified" and out[0].item["date"] == "2025-09-12"
    assert "修正" in out[0].note


def test_verifier_adds_a_missing_item_from_the_full_source():
    out = crosscheck(task(), roles(backend("deepseek", []), backend("glm", [item()])))
    assert out[0].status == "verified" and "补充遗漏" in out[0].note


def test_unconfirmed_primary_item_is_not_silently_dropped_or_accepted():
    out = crosscheck(task(), roles(backend("deepseek", [item()]), backend("glm", [])))
    assert out[0].status == "needs_review"


@pytest.mark.parametrize("change", [{"date": "2024-01-01"}, {"quote": "原文不存在的引语"}])
def test_verifier_still_must_pass_source_guards(change):
    out = crosscheck(task(), roles(backend("deepseek", [item()]), backend("glm", [dict(item(), **change)])))
    assert out[0].status == "needs_review"


def test_conflicting_verifier_duplicates_do_not_select_first():
    out = crosscheck(task(), roles(backend("deepseek", [item()]),
                                  backend("glm", [item(), dict(item(), date="2024-01-01")])))
    assert len(out) == 1 and out[0].status == "needs_review" and "冲突" in out[0].note


@pytest.mark.parametrize("raw", ["[]", "{}", '{"items":"not a list"}', '{"items":[{"date":"2025"}]}'])
@pytest.mark.parametrize("role", ["extractor_a", "verifier"])
def test_failed_call_is_not_evidence_of_absence(raw, role):
    models = roles(backend("deepseek", []), backend("glm", []))
    models[role] = backend(models[role].family, raw=raw)
    with pytest.raises(CrosscheckFailed):
        crosscheck(task(), models)


def test_legitimate_empty_source_remains_empty():
    assert crosscheck(task(), roles(backend("deepseek"), backend("glm"))) == []


def test_same_family_or_extra_third_role_is_rejected():
    with pytest.raises(ValueError):
        crosscheck(task(), roles(backend("deepseek"), backend("deepseek")))
    models = roles(backend("deepseek"), backend("glm"))
    models["arbiter"] = backend("qwen")
    with pytest.raises(ValueError):
        crosscheck(task(), models)


def test_invalid_review_gets_one_same_model_repair_with_source_error():
    seen = []
    def review(system, user):
        seen.append(user)
        corrected = len(seen) == 2
        return json.dumps({"items": [item() if corrected else dict(item(), date="2024-01-01")]}, ensure_ascii=False)
    out = crosscheck(task(), roles(backend("deepseek", [item()]), FakeBackend("glm", "glm", review)))
    assert out[0].status == "verified" and len(seen) == 2
    assert "确定性校验错误" in seen[1] and "2024-01-01" in seen[1]
    assert [c["role"] for c in out[0].calls] == ["extract", "verify", "verify_repair"]
    assert {c["family"] for c in out[0].calls} == {"deepseek", "glm"}


def test_repair_is_bounded_and_cannot_adopt_unrequested_new_identities():
    seen = []
    def review(system, user):
        seen.append(user)
        invalid = dict(item(), date="2024-01-01")
        extra = dict(item(), product_mention="Unrelated")
        return json.dumps({"items": [invalid] if len(seen) == 1 else [invalid, extra]}, ensure_ascii=False)
    out = crosscheck(task(), roles(backend("deepseek", [item()]), FakeBackend("glm", "glm", review)))
    assert len(seen) == 2 and len(out) == 1 and out[0].status == "needs_review"


def test_malformed_verifier_json_has_one_format_repair_without_chaining_retries():
    seen = []
    def review(system, user):
        seen.append(user)
        return '{"items": [broken}' if len(seen) == 1 else json.dumps({"items": [dict(item(), date="2024")]})
    out = crosscheck(task(), roles(backend("deepseek", [item()]), FakeBackend("glm", "glm", review)))
    assert len(seen) == 2 and out[0].status == "needs_review"
    assert [c["role"] for c in out[0].calls] == ["extract", "verify", "verify_format_repair"]


@pytest.mark.parametrize('bad', ['', '{"items":[broken}', '{"items":"invalid"}'])
def test_primary_format_failure_has_one_content_cached_recovery_and_real_source_review(ws, bad):
    from ciw.verify.crosscheck import retained_verified
    from ciw.verify.llm import CachedBackend
    seen = []
    def extract(system, user):
        seen.append(user)
        a.receipt = {'response_id': 'a-'+str(len(seen))}
        return bad if len(seen) == 1 else json.dumps({'items': [item()]})
    a = FakeBackend('deepseek', 'deepseek', extract)
    b = backend('glm', [item()])
    b.receipt = {'response_id': 'b-response'}
    models = roles(CachedBackend(a,ws), CachedBackend(b,ws))
    out = crosscheck(task(), models)
    assert out[0].status == 'verified' and len(seen) == 2
    assert TEXT in seen[1] and seen[1] != seen[0]
    assert len(out[0].calls) == 3 and out[0].calls[0]['error']
    assert out[0].calls[1]['format_repair'] and not out[0].calls[1].get('error')
    assert {c['family'] for c in out[0].calls} == {'deepseek','glm'}
    ws.save_verification('event-test', 'verified', dict(task='t', source_id='s',
        item=out[0].item, calls=out[0].calls))
    retained, incomplete = retained_verified(ws, task())
    assert len(retained) == 1 and not incomplete
    assert crosscheck(task(), models)[0].status == 'verified' and len(seen) == 2
    with ws.db() as con:
        assert any(row[0] == bad for row in con.execute('SELECT response FROM llm_cache'))


@pytest.mark.parametrize('malformed', [True, False])
def test_primary_format_recovery_is_bounded_and_network_failure_is_not_retried(malformed):
    seen = []
    def extract(*_):
        seen.append('call')
        if not malformed:
            raise OSError('synthetic transport failure')
        return ''
    def review(*_):
        pytest.fail('No primary candidate, so verification must not run')
    with pytest.raises(CrosscheckFailed) as exc:
        crosscheck(task(), roles(FakeBackend('deepseek','deepseek',extract), FakeBackend('glm','glm',review)))
    assert len(seen) == (2 if malformed else 1)
    assert len(exc.value.calls) == len(seen)
