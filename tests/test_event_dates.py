import pytest

from ciw.verify.crosscheck import _date_in_quote


@pytest.mark.parametrize(
    "value,quote,ok",
    [
        ("2025-01-03", "Approved 3 January 2025", True),
        ("2025-01-03", "Approved January 3, 2025", True),
        ("2025-01-03", "2025年1月3日获批", True),
        ("2025-01-03", "Approved 2025-01-13", False),
        ("2025-01-03", "Approved January 2025", False),
        ("2025-13-03", "2025-13-03", False),
        ("2025-02-30", "2025-02-30", False),
        ("2025-01", "Approved January 2025", True),
    ],
)
def test_whole_event_date_must_be_supported(value, quote, ok):
    assert _date_in_quote(value, quote) is ok


@pytest.mark.parametrize(
    "evidence,date,kind,ok",
    [
        ("2025年1月3日，公司宣布该药已获批准。", "2025-01-03", "approval", False),
        ("2025年1月3日\n该药在中国获批", "2025-01-03", "approval", False),
        ("该药于2025年1月3日获批准。", "2025-01-03", "approval", True),
        ("The medicine was approved on January 3, 2025.", "2025-01-03", "approval", True),
        ("申请于2024年6月获受理。", "2024-06", "filing", True),
        ("2012年甲公司与乙公司签署合作协议。", "2012", "licensing", True),
        ("The approval is based on earlier study results.", "", "topline", False),
        ("公司宣布III期研究揭盲达到主要终点。", "", "topline", True),
    ],
)
def test_regulatory_date_is_not_a_news_date_and_result_recap_is_not_topline(evidence, date, kind, ok):
    from ciw.verify.events import validate_event_item

    item = dict(event_type=kind, quote=evidence, date=date, event_date_quote=evidence)
    assert validate_event_item(item)[0] is ok


def test_production_inbox_keeps_announcement_date_unaccepted(cfg, resolver, ws):
    import json

    from ciw.sources.captures import extract_events
    from ciw.verify.llm import FakeBackend

    text = "2025年1月3日，公司宣布MG-K10已获批准，用于慢性鼻窦炎伴鼻息肉。"
    folder = ws.root / "captures/docs"
    folder.mkdir()
    (folder / "synthetic.txt").write_text(text)
    (folder / "synthetic.txt.meta.json").write_text(json.dumps({"kind": "company", "url": "https://example.org/news"}))
    item = dict(
        product_mention="MG-K10",
        event_type="approval",
        region="",
        date="2025-01-03",
        indication="慢性鼻窦炎伴鼻息肉",
        quote=text,
        event_date_quote=text,
    )

    def respond(system, user):
        return json.dumps({"choice": "A"} if "独立核对员" in system else {"items": [item]})

    roles = {
        role: FakeBackend(family, family, respond)
        for role, family in [("extractor_a", "deepseek"), ("verifier", "glm")]
    }
    events, queue, _ = extract_events(ws, cfg, resolver, roles)
    assert events[0].status == "needs_review" and queue[0]["kind"] == "event_needs_review"
    saved = ws.verifications()[events[0].event_id]
    assert saved["item"]["event_date_quote"] == text and saved["source_id"] == events[0].source_id


def test_original_contract_year_does_not_date_amended_terms():
    from ciw.verify.events import validate_event_item

    original = "2012年甲乙双方签署合作协议"
    item = dict(event_type="licensing", date="2012", event_date_quote=original,
                quote=original + "，目前已经修订，双方平摊成本与利润。",
                detail="修订后双方平摊成本与利润")
    assert not validate_event_item(item)[0]
    item["detail"] = "双方签署合作协议"
    assert validate_event_item(item)[0]
    item.update(date="2025", event_date_quote="2025年双方修订合作协议",
                quote="2025年双方修订合作协议", detail="双方修订合作协议")
    assert validate_event_item(item)[0]
