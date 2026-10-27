"""交叉核对逻辑（离线 FakeBackend）。"""

import json

import pytest

from ciw.verify.crosscheck import ExtractionTask, crosscheck
from ciw.verify.llm import FakeBackend
from ciw.verify.schemas import EventItem

# 合成测试文本（日期与事件为虚构，仅用于验证核对逻辑，不是证据）
TEXT = (
    "2025年9月12日，康诺亚宣布司普奇拜单抗注射液（CM310）获国家药品监督管理局批准，用于治疗慢性鼻窦炎伴鼻息肉成人患者。"
)


def task():
    return ExtractionTask(
        task_id="t1",
        source_id="s1",
        source_text=TEXT,
        instruction="抽取产品里程碑",
        item_model=EventItem,
        key_fields=("product_mention", "event_type"),
        value_fields=("date", "region"),
    )


def item(**kw):
    base = {
        "product_mention": "CM310",
        "event_type": "approval",
        "region": "中国",
        "date": "2025-09-12",
        "indication": "慢性鼻窦炎伴鼻息肉",
        "detail": "获批",
        "quote": "司普奇拜单抗注射液（CM310）获国家药品监督管理局批准",
    }
    base.update(kw)
    return base


def backend(family, items=None, choice=None, raw=None):
    def respond(system, user):
        if raw is not None:
            return raw
        if "独立核对员" in system:
            return json.dumps({"choice": choice or "neither", "reason": "x"})
        return json.dumps({"items": items or []}, ensure_ascii=False)

    return FakeBackend(family=family, model=family, responder=respond)


def roles(a, b, c):
    return {"extractor_a": a, "extractor_b": b, "arbiter": c}


def test_agreement_is_dual_agreed():
    out = crosscheck(task(), roles(backend("deepseek", [item()]), backend("qwen", [item()]), backend("glm")))
    assert [o.status for o in out] == ["dual_agreed"]
    assert len(out[0].calls) == 2  # 一致时不调用仲裁


def test_disagreement_goes_to_arbiter_and_requires_valid_quote():
    a, b = item(), item(date="2025-09-01")
    out = crosscheck(task(), roles(backend("deepseek", [a]), backend("qwen", [b]), backend("glm", choice="A")))
    assert out[0].status == "arbitrated" and out[0].item["date"] == "2025-09-12"


def test_arbiter_choosing_fabricated_quote_is_needs_review():
    a = item(quote="CM310 于 2024 年获批")  # 原文中不存在
    b = item(date="2025-09-01")
    out = crosscheck(task(), roles(backend("deepseek", [a]), backend("qwen", [b]), backend("glm", choice="A")))
    assert out[0].status == "needs_review"


def test_single_sided_item_needs_arbiter():
    out = crosscheck(
        task(), roles(backend("deepseek", [item()]), backend("qwen", []), backend("glm", choice="neither"))
    )
    assert out[0].status == "needs_review"


def test_broken_json_from_one_model_is_not_silent_agreement():
    out = crosscheck(
        task(), roles(backend("deepseek", [item()]), backend("qwen", raw="not json"), backend("glm", choice="A"))
    )
    assert out[0].status == "arbitrated"
    assert any(c.get("error") for c in out[0].calls)


def test_same_family_is_rejected():
    with pytest.raises(ValueError):
        crosscheck(task(), roles(backend("deepseek"), backend("deepseek"), backend("glm")))


def test_conflicting_duplicate_identity_is_not_first_wins_even_when_other_model_agrees():
    a = item(date="2025-09-01")
    out = crosscheck(
        task(), roles(backend("deepseek", [item(), a]), backend("qwen", [item()]), backend("glm", choice="A"))
    )
    assert len(out) == 1 and out[0].status == "needs_review"
    assert len(out[0].calls) == 2 and "冲突" in out[0].note


@pytest.mark.parametrize("raw", ["[]", "{}", '{"items":"not a list"}', '{"items":[{"date":"2025"}]}'])
def test_invalid_schema_is_not_evidence_of_no_events(raw):
    from ciw.verify.crosscheck import CrosscheckFailed

    with pytest.raises(CrosscheckFailed):
        crosscheck(task(), roles(backend("deepseek", raw=raw), backend("qwen", []), backend("glm")))


def test_two_legitimate_empty_extractions_remain_empty():
    assert crosscheck(task(), roles(backend("deepseek"), backend("qwen"), backend("glm"))) == []
