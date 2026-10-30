"""Historical decisions remain traceable when the event evidence schema grows."""

import json
from copy import deepcopy
from unittest.mock import patch

import pytest
from pydantic import create_model
from test_retained_source_facts import cached_roles

from ciw.sources.captures import extract_events
from ciw.verify.schemas import EventItem, _Item


def old_schema():
    return create_model(
        "EventItem",
        __base__=_Item,
        __doc__=EventItem.__doc__,
        **{k: (f.annotation, deepcopy(f)) for k, f in EventItem.model_fields.items() if k != "detail_quote"},
    )


@pytest.mark.parametrize("proof", ["valid", "missing_response", "wrong_task", "changed_source"])
def test_old_schema_decisions_revalidate_and_keep_unresolved_claims_visible(cfg, resolver, ws, proof):
    folder = ws.root / "captures/docs"
    folder.mkdir()
    source = "MG-K10在中国获批用于慢性鼻窦炎伴鼻息肉。该适应症已在美国获批。"
    path = folder / "legacy.txt"
    path.write_text(source)
    path.with_name("legacy.txt.meta.json").write_text(
        json.dumps({"kind": "company", "url": "https://example.org/news"})
    )
    common = dict(product_mention="MG-K10", event_type="approval", indication="慢性鼻窦炎伴鼻息肉", detail="")
    items = [
        dict(common, region="中国", quote=source.split("。")[0] + "。"),
        dict(common, region="美国", quote="该适应症已在美国获批。"),
    ]
    with (
        patch("ciw.sources.captures.EventItem", old_schema()),
        patch("ciw.sources.captures.validate_event_item", lambda _: (True, "")),
    ):
        before, issues, _ = extract_events(ws, cfg, resolver, cached_roles(ws, items))
    assert len(before) == 2 and not issues
    if proof == "changed_source":
        path.write_text(source + " 来源修订。")
    if proof == "missing_response":
        with ws.db() as con:
            con.execute("DELETE FROM llm_cache WHERE family='glm'")
    if proof == "wrong_task":
        with ws.db() as con:
            for key, payload in con.execute("SELECT fact_key,payload FROM verifications").fetchall():
                row = json.loads(payload)
                row["task"] = "unrelated"
                con.execute("UPDATE verifications SET payload=? WHERE fact_key=?", (json.dumps(row), key))
    ledger = ws.verifications()
    with ws.db() as con:
        cache = con.execute("SELECT * FROM llm_cache ORDER BY cache_key").fetchall()
    after, issues, coverage = extract_events(ws, cfg, resolver, None)
    assert ws.verifications() == ledger
    with ws.db() as con:
        assert cache == con.execute("SELECT * FROM llm_cache ORDER BY cache_key").fetchall()
    if proof == "valid":
        assert {e.region: e.status for e in after} == {"中国": "verified", "美国": "needs_review"}
        assert {e.event_id for e in before} == {e.event_id for e in after}
        assert any(i["kind"] == "event_needs_review" for i in issues)
    else:
        assert not after and issues
    assert coverage[0]["status"] == "partial"


def test_partial_schema_upgrade_keeps_other_old_regions_but_not_a_newly_rejected_identity(cfg, resolver, ws):
    folder = ws.root / "captures/docs"
    folder.mkdir()
    source = "MG-K10在中国和美国获批用于慢性鼻窦炎伴鼻息肉。该适应症在中国获批。"
    path = folder / "legacy.txt"
    path.write_text(source)
    path.with_name("legacy.txt.meta.json").write_text(
        json.dumps({"kind": "company", "url": "https://example.org/news"})
    )
    items = [
        dict(
            product_mention="MG-K10",
            event_type="approval",
            indication="慢性鼻窦炎伴鼻息肉",
            region=region,
            detail="",
            quote=source,
        )
        for region in ["中国", "美国"]
    ]
    with (
        patch("ciw.sources.captures.EventItem", old_schema()),
        patch("ciw.sources.captures.validate_event_item", lambda _: (True, "")),
    ):
        before, _, _ = extract_events(ws, cfg, resolver, cached_roles(ws, items))
    assert len(before) == 2
    pending = dict(items[0], quote="该适应症在中国获批。")
    now, _, _ = extract_events(ws, cfg, resolver, cached_roles(ws, [pending]))
    assert len(now) == 1 and now[0].status == "needs_review"
    ledger = ws.verifications()
    later, issues, coverage = extract_events(ws, cfg, resolver, None)
    assert [(e.region, e.status) for e in later] == [("美国", "verified")]
    assert issues and coverage[0]["status"] == "partial" and ws.verifications() == ledger
