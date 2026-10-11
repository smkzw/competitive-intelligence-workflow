"""Fresh B package wiring for per-fact public-version proofs.

Synthetic quotes exercise the production model only. They do not adopt a
source, rewrite disclosure dates, or settle historical medical meaning.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.fresh_b_research_package import (
    FreshBResearchContent,
    FreshBResearchPackage,
    FreshBResearchPackageError,
    compute_fresh_b_research_content_digest,
)
from ci_workflow.application.fresh_research_primitives import (
    FactPublicVersionProof,
    ResearchFact,
)
from ci_workflow.application.source_research_service import (
    fact_version_material_digest,
)

_B_HELPER_DIR = Path(__file__).resolve().parents[1] / "unit" / "reports" / "b"
if str(_B_HELPER_DIR) not in sys.path:
    sys.path.insert(0, str(_B_HELPER_DIR))

from test_fresh_b_research_package import (  # noqa: E402
    _load,
    _package_payload,
    _with_review,
)

_SOURCE_ID = "source-primary-report"
_SOURCE_URL = "https://journal.example/study-1"
_PUBLIC_DAY = "2026-05-01"
_PUBLIC_INSTANT = "2026-05-01T00:00:00+00:00"
_FUTURE_DAY = "2026-08-15"
_FUTURE_INSTANT = "2026-08-15T00:00:00+00:00"


def _reference(field_path: str, original_text: str, reference_id: str) -> dict[str, object]:
    return {
        "reference_id": reference_id,
        "source_id": _SOURCE_ID,
        "label_zh": "版本证据",
        "locator": {
            "document_role": "主要试验报告",
            "field_path": field_path,
            "url": _SOURCE_URL,
        },
        "original_text": original_text,
    }


def _late_acquired_paper_payload(*, public_day: str = _PUBLIC_DAY) -> dict[str, Any]:
    """B 常规夹具的唯一来源改为晚采集、无最早公开日的论文；事实引文逐字保留。"""
    payload = _package_payload()
    source = payload["sources"][0]
    assert isinstance(source, dict)
    source["first_disclosed_at"] = None
    document = json.loads(str(source["content_text"]))
    document["public_by"] = public_day
    document["version_witness"] = "Version 1 contains every fact quoted in this report"
    document["correction_witness"] = "更正仅改动版权声明，不影响本报告引用的任何事实"
    source["content_text"] = json.dumps(document, ensure_ascii=False)
    return payload


def _proofs(
    payload: dict[str, Any], *, public_instant: str = _PUBLIC_INSTANT
) -> list[dict[str, object]]:
    """为不可用来源上的每个事实构造一份绑定证明；同源兄弟不继承。"""
    source = payload["sources"][0]
    assert isinstance(source, dict)
    content_text = str(source["content_text"])
    document = json.loads(content_text)
    content_sha = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
    proofs: list[dict[str, object]] = []
    for fact in payload["facts"]:
        assert isinstance(fact, dict)
        research_fact = ResearchFact.model_validate(fact)
        proofs.append(
            {
                "fact_id": research_fact.fact_id,
                "fact_material_sha256": fact_version_material_digest(research_fact),
                "source_content_sha256": {_SOURCE_ID: content_sha},
                "public_by": {
                    "state": "reported",
                    "value": public_instant,
                    "precision": "calendar_day",
                    "locator": {
                        "document_role": "主要试验报告",
                        "field_path": "$.public_by",
                        "url": _SOURCE_URL,
                    },
                },
                "public_by_reference": _reference(
                    "$.public_by", str(document["public_by"]), "public-by"
                ),
                "version_references": [
                    _reference(
                        "$.version_witness",
                        str(document["version_witness"]),
                        "version-witness",
                    )
                ],
                "correction_state": "fact_unaffected",
                "correction_references": [
                    _reference(
                        "$.correction_witness",
                        str(document["correction_witness"]),
                        "correction-witness",
                    )
                ],
            }
        )
    return proofs


def _proved_package(*, public_instant: str = _PUBLIC_INSTANT) -> dict[str, Any]:
    payload = _late_acquired_paper_payload(
        public_day=public_instant[:10] if public_instant == _FUTURE_INSTANT else _PUBLIC_DAY
    )
    payload["fact_public_version_proofs"] = _proofs(payload, public_instant=public_instant)
    return payload


def _unused_unavailable_source() -> dict[str, object]:
    return {
        "source_id": "paper-unused",
        "route_id": "primary-trial-report-route",
        "source_type": "primary_trial_report",
        "title": "未被事实引用的晚采集论文",
        "url": "https://journal.example/unused",
        "query_or_identifier": "未引用来源",
        "language": "zh",
        "access_method": "official_page",
        "content_text": "{}",
        "acquired_at": "2026-08-18T12:00:00+08:00",
        "published_at": "2026-05-01T00:00:00+00:00",
        "effective_at": None,
        "first_disclosed_at": None,
        "locator": {
            "document_role": "主要试验报告",
            "field_path": "$",
            "url": "https://journal.example/unused",
        },
    }


def test_b_admits_late_paper_facts_with_exact_fact_proofs(tmp_path: Path) -> None:
    payload = _with_review(_proved_package())
    package = _load(tmp_path, payload)
    paper = package.sources[0]
    assert paper.first_disclosed_at is None
    assert paper.published_at is not None
    assert paper.acquired_at > package.data_cutoff
    assert not paper.is_available_by(package.data_cutoff)
    assert len(package.fact_public_version_proofs) == len(package.facts)
    assert all(
        isinstance(proof, FactPublicVersionProof)
        for proof in package.fact_public_version_proofs
    )
    assert "fact_public_version_proofs" in package.model_dump(mode="json")
    assert package.research_content_digest == compute_fresh_b_research_content_digest(payload)


def test_b_rejects_unproved_sibling_without_inheritance() -> None:
    sibling_id = "fact-eff-easi75-grp-control"
    payload = _proved_package()
    payload["fact_public_version_proofs"] = [
        proof
        for proof in payload["fact_public_version_proofs"]
        if proof["fact_id"] != sibling_id
    ]
    with pytest.raises(ValueError, match=sibling_id):
        FreshBResearchContent.model_validate(payload)


def test_b_rejects_proof_pointing_outside_declared_facts() -> None:
    payload = _proved_package()
    unknown = dict(payload["fact_public_version_proofs"][0])
    unknown["fact_id"] = "fact-unknown"
    payload["fact_public_version_proofs"].append(unknown)
    with pytest.raises(ValueError, match="fact-unknown"):
        FreshBResearchContent.model_validate(payload)


def test_b_rejects_source_bytes_changed_after_proofs() -> None:
    payload = _proved_package()
    source = payload["sources"][0]
    assert isinstance(source, dict)
    document = json.loads(str(source["content_text"]))
    document["late_edit"] = "证明之后追加的段落"
    source["content_text"] = json.dumps(document, ensure_ascii=False)
    with pytest.raises(ValueError, match="来源字节摘要"):
        FreshBResearchContent.model_validate(payload)


def test_b_rejects_wrong_source_content_hash() -> None:
    payload = _proved_package()
    for proof in payload["fact_public_version_proofs"]:
        proof["source_content_sha256"] = {_SOURCE_ID: "0" * 64}
    with pytest.raises(ValueError, match="来源字节摘要"):
        FreshBResearchContent.model_validate(payload)


def test_b_rejects_witness_quote_not_in_source() -> None:
    payload = _proved_package()
    payload["fact_public_version_proofs"][0]["version_references"][0]["original_text"] = (
        "guessed"
    )
    with pytest.raises(ValueError, match="引文不一致"):
        FreshBResearchContent.model_validate(payload)


def test_b_rejects_fact_material_changed_after_proof() -> None:
    payload = _proved_package()
    payload["facts"][0]["raw_value"] = "证明之后改动的原文"
    with pytest.raises(ValueError, match="事实版本材料"):
        FreshBResearchContent.model_validate(payload)


def test_b_rejects_public_witness_after_cutoff() -> None:
    with pytest.raises(ValueError, match="公开日晚于截止"):
        FreshBResearchContent.model_validate(_proved_package(public_instant=_FUTURE_INSTANT))


def test_b_unused_unavailable_source_keeps_source_veto() -> None:
    payload = _proved_package()
    payload["sources"].append(_unused_unavailable_source())
    with pytest.raises(ValueError, match="不得进入当前") as raised:
        FreshBResearchContent.model_validate(payload)
    assert "事实缺少" not in str(raised.value)


def test_legacy_b_digest_omits_empty_proofs() -> None:
    content = FreshBResearchContent.model_validate(_package_payload())
    dumped = content.model_dump(mode="json")
    assert "fact_public_version_proofs" not in dumped
    with_empty = {**dumped, "fact_public_version_proofs": []}
    assert FreshBResearchContent.model_validate(with_empty).model_dump(mode="json") == dumped
    assert compute_fresh_b_research_content_digest(dumped) == (
        compute_fresh_b_research_content_digest(with_empty)
    )


def test_changed_proof_cannot_reuse_old_independent_review(tmp_path: Path) -> None:
    payload = _with_review(_proved_package())
    payload["fact_public_version_proofs"][0]["version_references"][0]["label_zh"] = "新标签"
    with pytest.raises(FreshBResearchPackageError, match="摘要"):
        _load(tmp_path, payload)


def test_accepted_b_package_roundtrip_retains_witnesses_and_scientific_content(
    tmp_path: Path,
) -> None:
    payload = _with_review(_proved_package())
    package = _load(tmp_path, payload)
    dumped = package.model_dump(mode="json")
    reloaded = FreshBResearchPackage.model_validate(dumped)
    assert reloaded.fact_public_version_proofs == package.fact_public_version_proofs
    assert reloaded.research_content_digest == package.research_content_digest
    paper = reloaded.sources[0]
    assert paper.first_disclosed_at is None
    assert paper.published_at == package.sources[0].published_at
    assert paper.acquired_at == package.sources[0].acquired_at
    assert dumped["report_data"] == reloaded.model_dump(mode="json")["report_data"]
    assert reloaded.scientific_review.status == "accepted"
