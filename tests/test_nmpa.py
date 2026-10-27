"""Public certificate fields are product licences, not guessed indication approvals."""

import base64
import json
from urllib.parse import urlencode

import pytest

from ciw.sources.nmpa.parser import parse_detail


def certificate(category="境外生产药品"):
    record = base64.b64encode(b"id=" + b"a" * 32 + b"&itemId=" + b"b" * 32).decode()
    rows = (
        [
            ["注册证号", "国药准字SJ20200001"],
            ["产品名称（中文）", "度普利尤单抗注射液"],
            ["产品名称（英文）", "Dupilumab Injection"],
            ["发证日期", "2026-10-01"],
            ["生产厂商（英文）", "Manufacturer"],
            ["上市许可持有人英文名称", "Holder"],
        ]
        if category == "境外生产药品"
        else [["批准文号", "国药准字SJ20200001"], ["产品名称", "度普利尤单抗注射液"], ["批准日期", "2020-06-17"]]
    )
    return {
        "url": "https://datasearch.nmpa.gov.cn/datasearch/search-info.html?" + urlencode({"nmpa": record}),
        "category": category,
        "registration_number": "国药准字SJ20200001",
        "heading": category + "——“国药准字SJ20200001”基本信息",
        "rows": rows,
        "observed_at": "2026-10-27T00:00:00+00:00",
    }


def test_foreign_certificate_does_not_turn_issue_date_into_first_approval():
    raw = certificate()
    parsed = parse_detail(raw, registration_number=raw["registration_number"], category=raw["category"])
    assert parsed["approval_date"] is None and parsed["issue_date"] == "2026-10-01"
    assert parsed["holder_name"] == "Holder" and parsed["manufacturer_name"] == "Manufacturer"


@pytest.mark.parametrize("change", ["wrong_number", "wrong_host", "duplicate_label", "empty_product"])
def test_certificate_must_match_exact_official_record(change):
    raw = certificate()
    if change == "wrong_number":
        raw["rows"][0][1] = "国药准字SJ20200002"
    if change == "wrong_host":
        raw["url"] = raw["url"].replace("datasearch.nmpa.gov.cn", "example.org")
    if change == "duplicate_label":
        raw["rows"].append(raw["rows"][0])
    if change == "empty_product":
        raw["rows"] = [r for r in raw["rows"] if not r[0].startswith("产品名称")]
    with pytest.raises(ValueError):
        parse_detail(raw, registration_number="国药准字SJ20200001", category=raw["category"])


def test_nmpa_inbox_enters_release_as_registry_without_models(cfg, seeded_ws):
    from ciw.pipeline import run
    from ciw.release import load_release

    folder = seeded_ws.root / "captures/nmpa"
    folder.mkdir()
    raw = certificate("境内生产药品")
    (folder / "certificate-test.json").write_text(json.dumps(raw, ensure_ascii=False))
    doc = load_release(run(cfg, seeded_ws, offline=True, log=lambda *_: None).release_path)
    event = next(e for e in doc["events"] if e["status"] == "registry")
    assert (event["product_id"], event["event_type"], event["date"]) == ("dupilumab", "approval", "2020-06-17")
    assert event["indication"] == ""  # a certificate cannot prove the CRSwNP indication
    assert event["source_id"] in {s["source_id"] for s in doc["sources"]}
    assert next(c for c in doc["coverage"] if c["source"] == "nmpa")["status"] == "ok"
