"""1007 冻结 PMC 对象可用见证：真实 actual v2 固定装置上的构建与复核闭环。

正例只读取冻结的 ``.artifacts/1007-pmc-object-witness-v2`` 并导入调用方隔离
CAS；固定装置缺失时整批显式跳过，绝不以合成数据冒充真实通过。负例对冻结
字节做一致性改写以触碰各拒绝边界；这是对本模块封闭性的验证，不是对官方
来源的指控。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.sources.connectors.pmc_object_availability import (
    PmcObjectAvailabilityError,
    PmcObjectAvailabilityWitness,
    build_pmc_object_witness,
    verify_pmc_object_availability,
)
from ci_workflow.storage.content_store import ContentAddressedStore

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2] / ".artifacts" / "1007-pmc-object-witness-v2"
)

def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")


def _http_instant(text: str) -> datetime:
    parsed = parsedate_to_datetime(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AssertionError("固定装置的 HTTP 时间必须带时区")
    return parsed.astimezone(UTC)


def _records() -> list[dict[str, Any]]:
    if not (FIXTURE_ROOT / "actual.json").is_file():
        pytest.skip("冻结 actual v2 固定装置不存在；不以合成数据冒充真实通过")
    actual = json.loads((FIXTURE_ROOT / "actual.json").read_text(encoding="utf-8"))
    records = actual["records"]
    assert len(records) == 2, "actual v2 固定装置必须恰好包含两个对象"
    return records


def _first_record() -> dict[str, Any]:
    return _records()[0]


def _state(record: dict[str, Any]) -> dict[str, Any]:
    metadata_name = str(record["metadata"]["relative_path"])
    xml_name = str(record["xml"]["relative_path"])
    metadata_json = json.loads((FIXTURE_ROOT / metadata_name).read_text(encoding="utf-8"))
    return {
        "metadata_bytes": (FIXTURE_ROOT / metadata_name).read_bytes(),
        "xml_bytes": (FIXTURE_ROOT / xml_name).read_bytes(),
        "metadata_receipt_bytes": (FIXTURE_ROOT / f"{metadata_name}.receipt.json").read_bytes(),
        "xml_receipt_bytes": (FIXTURE_ROOT / f"{xml_name}.receipt.json").read_bytes(),
        "pmcid": str(metadata_json["pmcid"]),
        "version": int(metadata_json["version"]),
        "xml_last_modified": _http_instant(str(record["xml"]["headers"]["Last-Modified"])),
    }


def _build_from(
    tmp_path: Path, state: dict[str, Any], cas: str = "cas"
) -> tuple[ContentAddressedStore, PmcObjectAvailabilityWitness]:
    store = ContentAddressedStore(tmp_path / cas)
    witness = build_pmc_object_witness(
        store,
        metadata_bytes=state["metadata_bytes"],
        xml_bytes=state["xml_bytes"],
        metadata_receipt_bytes=state["metadata_receipt_bytes"],
        xml_receipt_bytes=state["xml_receipt_bytes"],
    )
    return store, witness


def _edit_receipt(
    state: dict[str, Any], which: str, mutate: Callable[[dict[str, Any]], None]
) -> None:
    receipt = json.loads(state[f"{which}_receipt_bytes"])
    mutate(receipt)
    state[f"{which}_receipt_bytes"] = _json_bytes(receipt)


def _store_metadata(state: dict[str, Any], payload: dict[str, Any]) -> None:
    """回写元数据字节并一致地重绑元数据回执的校验和字段。"""
    raw = _json_bytes(payload)
    state["metadata_bytes"] = raw

    def mutate(receipt: dict[str, Any]) -> None:
        receipt["sha256"] = hashlib.sha256(raw).hexdigest()
        receipt["bytes"] = len(raw)
        receipt["headers"]["Content-Length"] = str(len(raw))
        receipt["headers"]["ETag"] = (
            f'"{hashlib.md5(raw, usedforsecurity=False).hexdigest()}"'
        )

    _edit_receipt(state, "metadata", mutate)


def _edit_metadata_json(state: dict[str, Any], **changes: object) -> None:
    payload = json.loads(state["metadata_bytes"])
    for key, value in changes.items():
        if value is _MISSING:
            payload.pop(key, None)
        else:
            payload[key] = value
    _store_metadata(state, payload)


class _Missing:
    """哨兵：删除字段而不是写入占位值。"""


_MISSING = _Missing()


def _store_xml(state: dict[str, Any], xml: bytes) -> None:
    """回写 XML 字节并一致地重绑 XML 回执与元数据 xml_url 的校验和标签。"""
    md5 = hashlib.md5(xml, usedforsecurity=False).hexdigest()
    state["xml_bytes"] = xml

    def mutate(receipt: dict[str, Any]) -> None:
        receipt["sha256"] = hashlib.sha256(xml).hexdigest()
        receipt["bytes"] = len(xml)
        receipt["headers"]["Content-Length"] = str(len(xml))
        receipt["headers"]["ETag"] = f'"{md5}"'
        receipt["url"] = receipt["url"].split("?md5=")[0] + f"?md5={md5}"
        receipt["response_url"] = receipt["response_url"].split("?md5=")[0] + f"?md5={md5}"

    _edit_receipt(state, "xml", mutate)
    payload = json.loads(state["metadata_bytes"])
    payload["xml_url"] = payload["xml_url"].split("?md5=")[0] + f"?md5={md5}"
    _store_metadata(state, payload)


def _rewrite_identity(
    state: dict[str, Any], *, pmcid: str | None = None, version: int | None = None
) -> None:
    """一致改写元数据与两份回执中的 PMCID/版本标签；XML 字节保持不变。"""
    payload = json.loads(state["metadata_bytes"])
    old_segment = f"{payload['pmcid']}.{payload['version']}"
    new_version = version if version is not None else payload["version"]
    new_segment = f"{pmcid or payload['pmcid']}.{new_version}"
    payload["pmcid"] = pmcid or payload["pmcid"]
    payload["version"] = new_version
    payload["xml_url"] = payload["xml_url"].replace(old_segment, new_segment)
    _store_metadata(state, payload)

    def mutate(receipt: dict[str, Any]) -> None:
        receipt["relative_path"] = receipt["relative_path"].replace(old_segment, new_segment)
        receipt["url"] = receipt["url"].replace(old_segment, new_segment)
        receipt["response_url"] = receipt["response_url"].replace(old_segment, new_segment)

    _edit_receipt(state, "metadata", mutate)
    _edit_receipt(state, "xml", mutate)


def _expect_reject(tmp_path: Path, state: dict[str, Any], match: str) -> None:
    with pytest.raises(PmcObjectAvailabilityError, match=match):
        _build_from(tmp_path, state)


def test_actual_v2_builds_and_proves_availability_by_pinned_clock(tmp_path: Path) -> None:
    for record in _records():
        state = _state(record)
        store, witness = _build_from(tmp_path, state)
        assert witness.pmcid == state["pmcid"]
        assert witness.version == state["version"]
        assert witness.doi == record["doi"]
        assert witness.license_code == record["license_code"]
        assert witness.is_retracted is False
        assert witness.is_manuscript is False
        assert witness.pmid is not None and witness.pmid.isdigit()
        assert witness.xml_last_modified == state["xml_last_modified"]
        assert witness.xml_asset.media_type == "application/xml"
        assert witness.metadata_asset.media_type == "application/json"
        assert witness.xml_receipt_asset.media_type == "application/json"
        # 同一隔离 CAS 内重复导入：同字节同地址，见证完全一致。
        assert _build_from(tmp_path, state)[1] == witness
        # 截止恰等于固定对象时钟：接受并返回精确重开字节。
        assert (
            verify_pmc_object_availability(store, witness, witness.xml_last_modified)
            == state["xml_bytes"]
        )
        later = verify_pmc_object_availability(
            store, witness, witness.xml_last_modified + timedelta(days=1)
        )
        assert later == state["xml_bytes"]
        with pytest.raises(PmcObjectAvailabilityError, match="截止"):
            verify_pmc_object_availability(
                store, witness, witness.xml_last_modified - timedelta(seconds=1)
            )
        with pytest.raises(PmcObjectAvailabilityError, match="时区偏移"):
            naive = witness.xml_last_modified.replace(tzinfo=None)
            verify_pmc_object_availability(store, witness, naive)


def test_wrong_metadata_doi_rejected(tmp_path: Path) -> None:
    state = _state(_first_record())
    _edit_metadata_json(state, doi="10.1111/not-the-linked-article")
    _expect_reject(tmp_path, state, "身份")


def test_wrong_pmcid_identity_rejected(tmp_path: Path) -> None:
    state = _state(_first_record())
    _rewrite_identity(state, pmcid="PMC99999999")
    _expect_reject(tmp_path, state, "身份")


def test_wrong_version_identity_rejected(tmp_path: Path) -> None:
    state = _state(_first_record())
    _rewrite_identity(state, version=2)
    _expect_reject(tmp_path, state, "pmc-version")


def test_entity_declaration_rejected(tmp_path: Path) -> None:
    state = _state(_first_record())
    xml = state["xml_bytes"].replace(
        b'"JATS-archivearticle1-4-mathml3.dtd">',
        b'"JATS-archivearticle1-4-mathml3.dtd" [<!ENTITY amplify "expanded">]>',
        1,
    )
    assert xml != state["xml_bytes"]
    _store_xml(state, xml)
    _expect_reject(tmp_path, state, "实体")


def test_altered_xml_bytes_rejected(tmp_path: Path) -> None:
    state = _state(_first_record())
    state["xml_bytes"] += b" "
    _expect_reject(tmp_path, state, "摘要")


def test_altered_metadata_bytes_rejected(tmp_path: Path) -> None:
    state = _state(_first_record())
    state["metadata_bytes"] += b" "
    _expect_reject(tmp_path, state, "摘要")


def test_altered_receipt_field_rejected(tmp_path: Path) -> None:
    state = _state(_first_record())
    _edit_receipt(state, "xml", lambda receipt: receipt.update(sha256="0" * 64))
    _expect_reject(tmp_path, state, "摘要")
    fresh = _state(_first_record())
    _edit_receipt(fresh, "metadata", lambda receipt: receipt.update(status=404))
    _expect_reject(tmp_path, fresh, "HTTP 200")


def test_wrong_md5_query_and_etag_rejected(tmp_path: Path) -> None:
    real_md5 = hashlib.md5(
        _state(_first_record())["xml_bytes"], usedforsecurity=False
    ).hexdigest()
    # md5 查询标签整体一致地改写，但实际字节不变：摘要矛盾必须封闭拒绝。
    state = _state(_first_record())
    wrong = "f" * 32
    assert wrong != real_md5

    def relabel(receipt: dict[str, Any]) -> None:
        receipt["url"] = receipt["url"].split("?md5=")[0] + f"?md5={wrong}"
        receipt["response_url"] = receipt["response_url"].split("?md5=")[0] + f"?md5={wrong}"

    _edit_receipt(state, "xml", relabel)
    payload = json.loads(state["metadata_bytes"])
    payload["xml_url"] = payload["xml_url"].split("?md5=")[0] + f"?md5={wrong}"
    _store_metadata(state, payload)
    _expect_reject(tmp_path, state, "MD5")
    # ETag 与实际字节 MD5 不同。
    fresh = _state(_first_record())
    _edit_receipt(
        fresh, "xml", lambda receipt: receipt["headers"].update(ETag=f'"{wrong}"')
    )
    _expect_reject(tmp_path, fresh, "ETag")
    # 多部分上传 ETag 不是单部分 MD5。
    multipart = _state(_first_record())
    _edit_receipt(
        multipart,
        "xml",
        lambda receipt: receipt["headers"].update(ETag=f'"{real_md5}-2"'),
    )
    _expect_reject(tmp_path, multipart, "单部分")


def test_clock_violations_rejected(tmp_path: Path) -> None:
    # 对象时钟晚于响应 Date：晚时钟拒绝。
    state = _state(_first_record())
    _edit_receipt(
        state,
        "xml",
        lambda receipt: receipt["headers"].update(
            **{"Last-Modified": "Mon, 12 Oct 2026 10:00:00 GMT"}
        ),
    )
    _expect_reject(tmp_path, state, "晚于响应")
    # 缺失 Last-Modified 头。
    missing = _state(_first_record())

    def remove_clock(receipt: dict[str, Any]) -> None:
        receipt["headers"].pop("Last-Modified")

    _edit_receipt(missing, "xml", remove_clock)
    _expect_reject(tmp_path, missing, "回执头")
    # 畸形时钟。
    malformed = _state(_first_record())
    _edit_receipt(
        malformed,
        "xml",
        lambda receipt: receipt["headers"].update(**{"Last-Modified": "not-a-http-date"}),
    )
    _expect_reject(tmp_path, malformed, "HTTP时间")
    # 缺少时区偏移的本地时钟。
    naive = _state(_first_record())
    _edit_receipt(
        naive,
        "xml",
        lambda receipt: receipt.update(request_started_at="2026-10-11T15:58:29.943920"),
    )
    _expect_reject(tmp_path, naive, "时区偏移")
    # 元数据回执的 Date 头同样必须可解析。
    bad_date = _state(_first_record())
    _edit_receipt(
        bad_date,
        "metadata",
        lambda receipt: receipt["headers"].update(**{"Date": "not-a-http-date"}),
    )
    _expect_reject(tmp_path, bad_date, "HTTP时间")


def test_malicious_xml_receipt_urls_rejected(tmp_path: Path) -> None:
    state = _state(_first_record())
    md5 = hashlib.md5(state["xml_bytes"], usedforsecurity=False).hexdigest()
    base = (
        f"https://pmc-oa-opendata.s3.amazonaws.com/{state['pmcid']}.{state['version']}"
        f"/{state['pmcid']}.{state['version']}.xml?md5={md5}"
    )
    cases = [
        (base.replace("pmc-oa-opendata.s3.amazonaws.com", "evil.example.com"), "官方"),
        (base.replace("https://", "https://user:pass@"), "官方"),
        (base.replace("s3.amazonaws.com", "s3.amazonaws.com:8443"), "官方"),
        (base + "&x=1", "md5"),
        (base.split("?md5=")[0], "md5"),
        (base[:-32] + "z" * 32, "md5"),
        (base + "#fragment", "片段"),
        (base.replace(f"/{state['pmcid']}.{state['version']}/", "/other/", 1), "路径"),
    ]
    for mutant, expected in cases:
        fresh = _state(_first_record())

        def mutate(receipt: dict[str, Any], address: str = mutant) -> None:
            receipt["url"] = address
            receipt["response_url"] = address

        _edit_receipt(fresh, "xml", mutate)
        _expect_reject(tmp_path, fresh, expected)


def test_malicious_metadata_addresses_rejected(tmp_path: Path) -> None:
    def readdress(receipt: dict[str, Any], address: str) -> None:
        receipt["url"] = address
        receipt["response_url"] = address

    hostile = _state(_first_record())
    _edit_receipt(
        hostile,
        "metadata",
        lambda receipt: readdress(
            receipt, "https://evil.example.com/metadata/PMC10202800.1.json"
        ),
    )
    _expect_reject(tmp_path, hostile, "官方")
    wrong_path = _state(_first_record())
    _edit_receipt(
        wrong_path,
        "metadata",
        lambda receipt: readdress(
            receipt, "https://pmc-oa-opendata.s3.amazonaws.com/metadata/PMC99999999.1.json"
        ),
    )
    _expect_reject(tmp_path, wrong_path, "路径")
    queried = _state(_first_record())
    _edit_receipt(
        queried,
        "metadata",
        lambda receipt: readdress(
            receipt,
            "https://pmc-oa-opendata.s3.amazonaws.com/metadata/PMC10202800.1.json?x=1",
        ),
    )
    _expect_reject(tmp_path, queried, "查询")
    wrong_bucket = _state(_first_record())
    payload = json.loads(wrong_bucket["metadata_bytes"])
    payload["xml_url"] = payload["xml_url"].replace("s3://pmc-oa-opendata", "s3://other-bucket")
    _store_metadata(wrong_bucket, payload)
    _expect_reject(tmp_path, wrong_bucket, "bucket")
    https_xml_url = _state(_first_record())
    payload = json.loads(https_xml_url["metadata_bytes"])
    payload["xml_url"] = payload["xml_url"].replace("s3://pmc-oa-opendata", "https://pmc-oa-opendata")
    _store_metadata(https_xml_url, payload)
    _expect_reject(tmp_path, https_xml_url, "bucket")
    unmapped_md5 = _state(_first_record())
    payload = json.loads(unmapped_md5["metadata_bytes"])
    payload["xml_url"] = payload["xml_url"].split("?md5=")[0] + "?md5=" + "f" * 32
    _store_metadata(unmapped_md5, payload)
    _expect_reject(tmp_path, unmapped_md5, "映射")


def test_http_contract_violations_rejected(tmp_path: Path) -> None:
    state = _state(_first_record())
    _edit_receipt(state, "xml", lambda receipt: receipt.update(status=404))
    _expect_reject(tmp_path, state, "HTTP 200")
    mismatched = _state(_first_record())

    def diverge(receipt: dict[str, Any]) -> None:
        receipt["response_url"] = receipt["url"] + "x"

    _edit_receipt(mismatched, "xml", diverge)
    _expect_reject(tmp_path, mismatched, "响应地址")
    inverted = _state(_first_record())

    def invert(receipt: dict[str, Any]) -> None:
        receipt["request_started_at"], receipt["response_completed_at"] = (
            receipt["response_completed_at"],
            receipt["request_started_at"],
        )

    _edit_receipt(inverted, "xml", invert)
    _expect_reject(tmp_path, inverted, "晚于完成时刻")
    wrong_length = _state(_first_record())
    _edit_receipt(
        wrong_length,
        "xml",
        lambda receipt: receipt["headers"].update(**{"Content-Length": "123"}),
    )
    _expect_reject(tmp_path, wrong_length, "Content-Length")


def test_cas_tamper_traversal_and_forgery_rejected(tmp_path: Path) -> None:
    store, witness = _build_from(tmp_path, _state(_first_record()), cas="cas-xml-tamper")
    # 同一版本在 CAS 内的字节被改动：复核必须按摘要漂移失败。
    xml_path = store.project_root / witness.xml_asset.relative_path
    xml_path.write_bytes(xml_path.read_bytes() + b" ")
    with pytest.raises(PmcObjectAvailabilityError, match="篡改"):
        verify_pmc_object_availability(store, witness, witness.xml_last_modified)
    # 回执资产同样不得被替换。
    store, witness = _build_from(
        tmp_path, _state(_first_record()), cas="cas-receipt-tamper"
    )
    receipt_path = store.project_root / witness.xml_receipt_asset.relative_path
    receipt_path.write_bytes(receipt_path.read_bytes() + b" ")
    with pytest.raises(PmcObjectAvailabilityError, match="篡改"):
        verify_pmc_object_availability(store, witness, witness.xml_last_modified)
    # CAS 越界路径在读取前即被拒绝。
    store, witness = _build_from(tmp_path, _state(_first_record()), cas="cas-traversal")
    escaped = witness.model_copy(
        update={
            "xml_asset": witness.xml_asset.model_copy(
                update={"relative_path": "../escape.bin"}
            )
        }
    )
    with pytest.raises(PmcObjectAvailabilityError, match="绑定"):
        verify_pmc_object_availability(store, escaped, witness.xml_last_modified)
    # 伪造见证字段不得被信任：重开派生结果与提交见证必须逐字段一致。
    forged_pmcid = witness.model_copy(update={"pmcid": "PMC99999999"})
    with pytest.raises(PmcObjectAvailabilityError, match="不一致"):
        verify_pmc_object_availability(
            store, forged_pmcid, witness.xml_last_modified + timedelta(days=1)
        )
    backdated = witness.model_copy(
        update={"xml_last_modified": witness.xml_last_modified - timedelta(days=30)}
    )
    with pytest.raises(PmcObjectAvailabilityError, match="不一致"):
        verify_pmc_object_availability(
            store, backdated, witness.xml_last_modified + timedelta(days=1)
        )
    relabeled = witness.model_copy(update={"license_code": "public domain"})
    with pytest.raises(PmcObjectAvailabilityError, match="不一致"):
        verify_pmc_object_availability(
            store, relabeled, witness.xml_last_modified + timedelta(days=1)
        )


def test_bad_flags_rejected_and_strict_flags_recorded(tmp_path: Path) -> None:
    state = _state(_first_record())
    _edit_metadata_json(state, is_retracted=0)
    _expect_reject(tmp_path, state, "布尔")
    manuscript = _state(_first_record())
    _edit_metadata_json(manuscript, is_manuscript="false")
    _expect_reject(tmp_path, manuscript, "布尔")
    blank_license = _state(_first_record())
    _edit_metadata_json(blank_license, license_code="  ")
    _expect_reject(tmp_path, blank_license, "许可")
    # 严格布尔按官方元数据原样记录；记录不是推断许可或科学接受。
    retracted = _state(_first_record())
    _edit_metadata_json(retracted, is_retracted=True)
    _, witness = _build_from(tmp_path, retracted)
    assert witness.is_retracted is True
    assert witness.is_manuscript is False
    assert witness.license_code == "CC BY"


def test_metadata_last_modified_cannot_substitute_object_clock(tmp_path: Path) -> None:
    state = _state(_first_record())
    _edit_receipt(
        state,
        "metadata",
        lambda receipt: receipt["headers"].update(
            **{"Last-Modified": "Mon, 01 Jan 2001 00:00:00 GMT"}
        ),
    )
    store, witness = _build_from(tmp_path, state)
    between = datetime(2026, 6, 1, tzinfo=UTC)
    with pytest.raises(PmcObjectAvailabilityError, match="截止"):
        verify_pmc_object_availability(store, witness, between)
    assert (
        verify_pmc_object_availability(store, witness, witness.xml_last_modified)
        == state["xml_bytes"]
    )


@pytest.mark.parametrize("case", ["xml_media", "metadata_media", "blank_query"])
def test_owner_http_contract_counterexamples(tmp_path: Path, case: str) -> None:
    state = _state(_first_record())
    if case in {"xml_media", "metadata_media"}:
        which = "xml" if case == "xml_media" else "metadata"
        _edit_receipt(state, which, lambda r: r["headers"].update(
            **{"Content-Type": "text/html"}))
        message = "媒体"
    else:
        def suffix(receipt: dict[str, Any]) -> None:
            receipt["url"] += "&unexpected="
            receipt["response_url"] += "&unexpected="
        _edit_receipt(state, "xml", suffix)
        metadata = json.loads(state["metadata_bytes"])
        metadata["xml_url"] += "&unexpected="
        _store_metadata(state, metadata)
        message = "md5"
    _expect_reject(tmp_path, state, message)


def test_actual_server_and_client_clocks_remain_independent(tmp_path: Path) -> None:
    # Initial owner Date<=client-completion assertion was too strict: the two
    # captured servers are 0.36/0.21s ahead. No invented timestamp or tolerance.
    for record in _records():
        state = _state(record)
        receipt = json.loads(state["xml_receipt_bytes"])
        server_date = _http_instant(receipt["headers"]["Date"])
        client_completed = datetime.fromisoformat(receipt["response_completed_at"])
        assert server_date > client_completed
        assert state["xml_last_modified"] <= min(server_date, client_completed)
        store, witness = _build_from(tmp_path, state)
        assert (
            verify_pmc_object_availability(store, witness, client_completed) == state["xml_bytes"]
        )


@pytest.mark.parametrize("case", ["valid", "wrong_media", "extra_query", "changed_xml", "cutoff"])
def test_portable_synthetic_contract_without_external_fixture(tmp_path: Path, case: str) -> None:
    """Mandatory contract tests on fresh checkout; explicitly not real-source evidence."""
    xml = (b'<article><front><article-meta><article-id pub-id-type="pmcid">PMC1</article-id>'
        b'<article-id pub-id-type="pmid">1</article-id>'
        b'<article-id pub-id-type="doi">10.1/test</article-id>'
        b'<article-version article-version-type="pmc-version">1</article-version>'
        b'<title-group><article-title>Synthetic only</article-title></title-group>'
        b'</article-meta></front><body><p>Synthetic contract.</p></body></article>')
    md5 = hashlib.md5(xml, usedforsecurity=False).hexdigest()
    base = "pmc-oa-opendata.s3.amazonaws.com"
    xml_url = f"https://{base}/PMC1.1/PMC1.1.xml?md5={md5}"
    metadata = _json_bytes({"pmcid": "PMC1", "version": 1, "pmid": 1,
        "doi": "10.1/test", "is_retracted": False, "is_manuscript": False,
        "license_code": "synthetic-no-license", "xml_url": xml_url.replace(
            f"https://{base}", "s3://pmc-oa-opendata")})
    def receipt(raw: bytes, url: str, extension: str, media: str) -> bytes:
        return _json_bytes({"url": url, "response_url": url, "status": 200,
            "request_started_at": "2026-01-02T00:00:00+00:00",
            "response_completed_at": "2026-01-02T00:00:01+00:00",
            "relative_path": f"PMC1.1.{extension}", "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "headers": {"Content-Type": media,
                "Content-Length": str(len(raw)), "Date": "Fri, 02 Jan 2026 00:00:00 GMT",
                "Last-Modified": "Thu, 01 Jan 2026 00:00:00 GMT",
                "ETag": '"'+hashlib.md5(raw, usedforsecurity=False).hexdigest()+'"'}})
    state = {"metadata_bytes": metadata, "xml_bytes": xml,
        "metadata_receipt_bytes": receipt(metadata, f"https://{base}/metadata/PMC1.1.json",
            "json", "application/json"),
        "xml_receipt_bytes": receipt(xml, xml_url, "xml", "application/xml")}
    if case == "wrong_media":
        _edit_receipt(state, "xml", lambda r: r["headers"].update(**{"Content-Type": "text/html"}))
    elif case == "extra_query":
        def extra(r: dict[str, Any]) -> None:
            r["url"] += "&empty="
            r["response_url"] += "&empty="
        _edit_receipt(state, "xml", extra)
    elif case == "changed_xml":
        state["xml_bytes"] += b" "
    if case in {"wrong_media", "extra_query", "changed_xml"}:
        with pytest.raises(PmcObjectAvailabilityError):
            _build_from(tmp_path, state)
    else:
        store, witness = _build_from(tmp_path, state)
        if case == "cutoff":
            with pytest.raises(PmcObjectAvailabilityError):
                verify_pmc_object_availability(store, witness,
                    witness.xml_last_modified - timedelta(seconds=1))
        else:
            assert verify_pmc_object_availability(store, witness,
                witness.xml_last_modified) == xml
