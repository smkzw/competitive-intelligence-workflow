"""Fresh A package wiring for per-fact public-version proofs.

Synthetic quotes exercise the production model only. They do not adopt a
source, rewrite disclosure dates, or settle historical medical meaning.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.source_research_service import (
    FreshAResearchContent,
    FreshAResearchPackage,
    ResearchFact,
    SourceCapture,
    compute_research_content_digest,
    fact_version_material_digest,
    verify_fact_public_version_evidence,
)

CUTOFF = datetime(2026, 10, 7, 23, 59, 59, tzinfo=UTC)
URL = "https://publisher.example/version-1"
LEGACY_URL = "https://company.example/legacy"


def _paper_text() -> str:
    return json.dumps({
        "product_name": "Synthetic study",
        "other": "99",
        "public_by": "2023-05-04",
        "version": "Version1 includes this table",
        "correction": "Correction changes copyright only, not this table",
    })


def _source(
    source_id: str, url: str, text: str, *, source_type: str,
    acquired_at: str, published_at: str | None, first_disclosed_at: str | None,
    field_path: str,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "route_id": "publisher" if source_id == "paper" else "company",
        "source_type": source_type,
        "title": "Synthetic dated version",
        "url": url,
        "query_or_identifier": "test",
        "language": "en",
        "access_method": "test",
        "media_type": "application/json",
        "content_text": text,
        "acquired_at": acquired_at,
        "published_at": published_at,
        "effective_at": None,
        "first_disclosed_at": first_disclosed_at,
        "locator": {"document_role": "synthetic", "field_path": field_path, "url": url},
    }


def _paper_source(text: str, *, acquired_at: str, published_at: str | None) -> dict[str, Any]:
    return _source(
        "paper", URL, text, source_type="journal_publication", acquired_at=acquired_at,
        published_at=published_at, first_disclosed_at=None, field_path="$",
    )


def _legacy_source() -> dict[str, Any]:
    return _source(
        "legacy", LEGACY_URL, json.dumps({"trial_name": "Synthetic trial"}),
        source_type="company_disclosure", acquired_at="2024-02-02T00:00:00+00:00",
        published_at="2024-01-02T00:00:00+00:00",
        first_disclosed_at="2024-01-02T00:00:00+00:00", field_path="$.trial_name",
    )


def _fact(
    fact_id: str, row_ref: str, source_id: str, field_path: str, original: str, *,
    entity_id: str, entity_type: str, field_id: str, url: str,
) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "row_ref": row_ref,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "canonical_name": original,
        "field_id": field_id,
        "raw_value": original,
        "normalized_value": original,
        "disclosure_state": "reported_value",
        "source_id": source_id,
        "locator": {"document_role": "synthetic", "field_path": field_path, "url": url},
        "original_text": original,
    }


def _product_fact() -> dict[str, Any]:
    return _fact(
        "fact-product", "product:drug-1", "paper", "$.product_name", "Synthetic study",
        entity_id="drug-1", entity_type="drug", field_id="product.name", url=URL,
    )


def _trial_fact(source_id: str = "legacy") -> dict[str, Any]:
    url = LEGACY_URL if source_id == "legacy" else URL
    path = "$.trial_name" if source_id == "legacy" else "$.product_name"
    original = "Synthetic trial" if source_id == "legacy" else "Synthetic study"
    return _fact(
        "fact-trial", "trial:study-1", source_id, path, original,
        entity_id="study-1", entity_type="trial", field_id="trial.name", url=url,
    )


def _sibling_fact() -> dict[str, Any]:
    return _fact(
        "fact-2", "product:drug-1", "paper", "$.other", "99",
        entity_id="drug-1", entity_type="drug", field_id="product.other", url=URL,
    )


def _reference(text: str, field: str) -> dict[str, Any]:
    return {
        "reference_id": field,
        "source_id": "paper",
        "label_zh": "版本证据",
        "locator": {"document_role": "synthetic", "field_path": f"$.{field}", "url": URL},
        "original_text": json.loads(text)[field],
    }


def _proof(text: str, fact: dict[str, Any]) -> dict[str, Any]:
    public_by = _reference(text, "public_by")
    return {
        "fact_id": fact["fact_id"],
        "fact_material_sha256": fact_version_material_digest(ResearchFact.model_validate(fact)),
        "source_content_sha256": {"paper": hashlib.sha256(text.encode()).hexdigest()},
        "public_by": {
            "state": "reported",
            "value": "2023-05-04T00:00:00Z",
            "precision": "calendar_day",
            "locator": public_by["locator"],
        },
        "public_by_reference": public_by,
        "version_references": [_reference(text, "version")],
        "correction_state": "fact_unaffected",
        "correction_references": [_reference(text, "correction")],
    }


def _report() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "report_version": "v1",
        "indication": "合成适应症",
        "data_cutoff": CUTOFF.isoformat(),
        "products": [{
            "id": "drug-1", "name": "Synthetic study", "target": "未核", "modality": "未核",
            "phase": "III", "status": "研究中", "regions": ["全球"], "route": "未核",
            "developer": "未核", "mechanism": "未核", "result_status": "暂无公开关键结果",
        }],
        "trials": [{
            "id": "study-1", "display_id": "STUDY-1", "product_id": "drug-1",
            "name": "Synthetic trial", "phase": "III", "region": "全球",
            "status": "进行中", "role": "研究",
        }],
        "regulatory": [{
            "product_id": "drug-1",
            "track": "未核",
            "event": "未核",
            "date": "未知",
            "status": "未核",
        }],
        "companies": [{
            "product_id": "drug-1", "relationship": "未核", "licensor": "未核",
            "licensee": "未核", "territory": "未核", "transaction": "未核",
        }],
        "patents": [{
            "product_id": "drug-1", "family": "未核", "display_family": "未核",
            "jurisdiction": "未核", "scope": "未核", "expiry": "未知", "exclusivity": "未核",
        }],
        "history": [{
            "product_id": "drug-1", "status": "研究中", "date": "未知", "observation": "未核",
        }],
        "sources": [{
            "source": "合成来源", "scope": "版本证明", "maturity": "候选", "limitation": "机械校验",
        }],
    }


def _package(
    sources: list[dict[str, Any]], facts: list[dict[str, Any]],
    proofs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "indication": "合成适应症",
        "data_cutoff": CUTOFF.isoformat(),
        "report_version": "v1",
        "universe_closed": True,
        "universe_product_ids": ["drug-1"],
        "report_data": _report(),
        "sources": sources,
        "facts": facts,
        "claims": [{
            "claim_id": "claim-1",
            "claim_text": "合成包只验证版本门接线。",
            "claim_kind": "direct_evidence",
            "fact_ids": [fact["fact_id"] for fact in facts],
        }],
        "gate_status": "passed",
    }
    if proofs is not None:
        payload["fact_public_version_proofs"] = proofs
    return payload


def _late_paper(text: str) -> dict[str, Any]:
    return _paper_source(
        text, acquired_at="2026-10-11T00:00:00+00:00", published_at="2023-05-04T00:00:00+00:00",
    )


def test_fresh_a_admits_referenced_fact_without_rewriting_disclosure() -> None:
    text = _paper_text()
    product = _product_fact()
    payload = _package(
        [_late_paper(text), _legacy_source()],
        [product, _trial_fact()],
        [_proof(text, product)],
    )
    content = FreshAResearchContent.model_validate(payload)
    paper = next(source for source in content.sources if source.source_id == "paper")
    legacy = next(source for source in content.sources if source.source_id == "legacy")
    assert paper.first_disclosed_at is None
    assert paper.published_at is not None
    assert paper.acquired_at > content.data_cutoff
    assert not paper.is_available_by(content.data_cutoff)
    assert legacy.is_available_by(content.data_cutoff)
    assert [proof.fact_id for proof in content.fact_public_version_proofs] == ["fact-product"]
    assert "fact_public_version_proofs" in content.model_dump(mode="json")
    with pytest.raises(ValueError):
        FreshAResearchPackage.model_validate(content.model_dump(mode="json"))


def test_fresh_a_rejects_sibling_without_its_own_proof() -> None:
    text = _paper_text()
    product = _product_fact()
    proof = _proof(text, product)
    paper = SourceCapture.model_validate(_late_paper(text))
    verify_fact_public_version_evidence(
        [paper], [ResearchFact.model_validate(product)], [proof], CUTOFF,
    )
    assert paper.first_disclosed_at is None
    assert not paper.is_available_by(CUTOFF)
    payload = _package(
        [_late_paper(text), _legacy_source()],
        [product, _sibling_fact(), _trial_fact()],
        [proof],
    )
    with pytest.raises(ValueError, match="fact-2"):
        FreshAResearchContent.model_validate(payload)
    assert paper.first_disclosed_at is None


def test_wrong_quote_does_not_admit_late_paper() -> None:
    text = _paper_text()
    product = _product_fact()
    proof = _proof(text, product)
    proof["version_references"][0]["original_text"] = "guessed"
    paper = SourceCapture.model_validate(_late_paper(text))
    payload = _package(
        [paper.model_dump(mode="json"), _legacy_source()],
        [product, _trial_fact()],
        [proof],
    )
    with pytest.raises(ValueError, match="引文不一致"):
        FreshAResearchContent.model_validate(payload)
    assert paper.first_disclosed_at is None


def test_publication_date_and_acquisition_do_not_admit_unproved_facts() -> None:
    text = _paper_text()
    paper = SourceCapture.model_validate(_paper_source(
        text, acquired_at="2020-01-01T00:00:00+00:00", published_at="2023-05-04T00:00:00+00:00",
    ))
    assert paper.published_at is not None
    assert paper.acquired_at < CUTOFF
    assert not paper.is_available_by(CUTOFF)
    payload = _package(
        [paper.model_dump(mode="json")],
        [_product_fact(), _trial_fact("paper")],
    )
    with pytest.raises(ValueError, match="首次披露"):
        FreshAResearchContent.model_validate(payload)
    assert paper.first_disclosed_at is None


def test_legacy_package_digest_omits_empty_proofs() -> None:
    legacy = _legacy_source()
    facts = [
        _fact(
            "fact-product", "product:drug-1", "legacy", "$.trial_name", "Synthetic trial",
            entity_id="drug-1", entity_type="drug", field_id="product.name", url=LEGACY_URL,
        ),
        _trial_fact(),
    ]
    content = FreshAResearchContent.model_validate(_package([legacy], facts))
    dumped = content.model_dump(mode="json")
    assert "fact_public_version_proofs" not in dumped
    assert content.sources[0].first_disclosed_at == datetime(2024, 1, 2, tzinfo=UTC)
    with_empty = {**dumped, "fact_public_version_proofs": []}
    assert FreshAResearchContent.model_validate(with_empty).model_dump(mode="json") == dumped
    assert compute_research_content_digest(dumped) == compute_research_content_digest(with_empty)


def test_unused_unavailable_source_keeps_source_veto() -> None:
    text = _paper_text()
    product = _product_fact()
    unused = _source(
        "unused", "https://publisher.example/unused", "{}",
        source_type="journal_publication", acquired_at="2026-10-11T00:00:00+00:00",
        published_at="2023-05-04T00:00:00+00:00", first_disclosed_at=None, field_path="$",
    )
    payload = _package(
        [_late_paper(text), _legacy_source(), unused],
        [product, _trial_fact()],
        [_proof(text, product)],
    )
    with pytest.raises(ValueError, match="不得进入当前快照") as raised:
        FreshAResearchContent.model_validate(payload)
    message = str(raised.value)
    assert "fact-product" not in message
    assert "事实缺少" not in message


def test_consumer_row_change_keeps_version_proof_but_not_report_coverage() -> None:
    text = _paper_text()
    product = _product_fact()
    payload = _package(
        [_late_paper(text), _legacy_source()],
        [product, _trial_fact()],
        [_proof(text, product)],
    )
    FreshAResearchContent.model_validate(payload)
    renamed = copy.deepcopy(payload)
    renamed["facts"][0]["row_ref"] = "another-report:another-row"
    with pytest.raises(ValueError, match="product:drug-1"):
        FreshAResearchContent.model_validate(renamed)


@pytest.mark.parametrize("source_type", [
    "company_disclosure", "regulatory_document", "clinical_trial_registry",
])
def test_paper_proof_does_not_relax_nonpublication_history(source_type: str) -> None:
    text = _paper_text()
    product = _product_fact()
    source = _late_paper(text)
    source["source_type"] = source_type
    payload = _package([source, _legacy_source()], [product, _trial_fact()],
                       [_proof(text, product)])
    with pytest.raises(ValueError, match="论文"):
        FreshAResearchContent.model_validate(payload)


@pytest.mark.parametrize("target", ["fact", "public", "version", "correction"])
def test_exact_quote_with_foreign_locator_url_is_not_bound(target: str) -> None:
    text = _paper_text()
    product = _product_fact()
    proof = _proof(text, product)
    wrong = "https://other.example/unrelated"
    if target == "fact":
        product["locator"]["url"] = wrong
        proof["fact_material_sha256"] = fact_version_material_digest(
            ResearchFact.model_validate(product))
    elif target == "public":
        proof["public_by_reference"]["locator"]["url"] = wrong
        proof["public_by"]["locator"]["url"] = wrong
    else:
        proof[f"{target}_references"][0]["locator"]["url"] = wrong
    payload = _package([_late_paper(text), _legacy_source()],
                       [product, _trial_fact()], [proof])
    with pytest.raises(ValueError, match="URL"):
        FreshAResearchContent.model_validate(payload)


def test_product_submission_reopens_proof_and_preserves_prior_manifest(tmp_path: Path) -> None:
    """Synthetic witnesses through the real submit/reopen path; zero live adoption."""
    from test_research_package_submission import _audit_payload, _bind_reviewed_universe

    from ci_workflow.application.project_service import create_project_workspace
    from ci_workflow.application.research_package_submission import (
        ResearchPackageSubmissionError,
        load_product_research_submission,
        submit_product_research_package,
    )
    from ci_workflow.domain.contracts import create_project_contract
    from ci_workflow.domain.publication import compute_publication_review_digest

    def envelope(report_bytes: bytes, content: dict[str, Any]) -> dict[str, object]:
        audited = _audit_payload(contract.project_id, report_bytes, content)
        audited["data_cutoff"] = "2026-10-07"
        audited["entities"].append({
            "entity_id": "study-1", "entity_type": "trial", "name": "Synthetic trial",
            "identity_status": "resolved", "disposition": "included",
            "ontology_rule_id": "innovation-therapy-v1", "identity_evidence_ids": ["paper"],
        })
        audited["sources"][0]["linked_trial_ids"] = ["study-1"]
        record = {
            "publication_id": "synthetic-pub", "source_id": "paper", "product_id": "drug-1",
            "linked_trial_ids": ["study-1"], "registry_identifiers": ["SYNTHETIC-STUDY"],
            "title": "Synthetic dated version", "source_url": URL,
            "publication_class": "primary_result", "model_suggestion": "primary_result",
            "classification_reason": "合成测试的主要结果分类，不是实际论文裁决",
            "producer_id": "synthetic-producer", "producer_context": "synthetic-producer-context",
            "fetch_attempts": [{"attempt_id": "synthetic-fetch", "strategy_id": "synthetic",
                                "route_family": "publisher", "result_class": "acquired",
                                "attempted_at": content["sources"][0]["acquired_at"],
                                "source_id": "paper"}],
            "acquisition_disposition": "acquired", "affected_reports": ["A"],
            "independent_review_id": "synthetic-publication-review",
            "independent_reviewer_id": "synthetic-other-reviewer",
            "independent_context": "synthetic-clean-context",
        }
        record["reviewed_candidate_sha256"] = compute_publication_review_digest(record)
        audited["publication_records"] = [record]
        audited["publication_search_receipts"] = [{
            "search_id": "synthetic-search", "trial_id": "study-1",
            "registry_identifiers": ["SYNTHETIC-STUDY"],
            "route_families": ["registry_attachment", "bibliographic_index"],
            "attempt_ids": ["synthetic-search-1", "synthetic-search-2"],
            "query_sha256": hashlib.sha256(b"synthetic-query").hexdigest(),
            "result": "publications_classified", "discovered_publication_ids": ["synthetic-pub"],
        }]
        audited["closure"]["candidate_entity_ids"] = ["drug-1", "study-1"]
        audited["closure"]["new_entity_ids_by_round"]["0"] = ["drug-1", "study-1"]
        audited["expansion_receipts"][0]["discovered_entity_ids"] = ["drug-1", "study-1"]
        _bind_reviewed_universe(audited)
        return audited

    text = _paper_text()
    product = _product_fact()
    paper = _late_paper(text)
    paper["source_type"] = "peer_reviewed_primary_report"
    legacy = _legacy_source()
    legacy["source_type"] = "company_official_disclosure"
    payload = _package([paper, legacy], [product, _trial_fact()], [_proof(text, product)])
    payload["indication"] = payload["report_data"]["indication"] = "特应性皮炎"
    payload["data_cutoff"] = payload["report_data"]["data_cutoff"] = (
        "2026-10-07T15:59:59+00:00"
    )
    payload["scientific_review"] = {
        "reviewer_id": "synthetic-independent-reviewer",
        "reviewer_role": "independent_scientific_verifier", "status": "accepted",
        "reviewed_at": "2026-10-11T01:00:00+00:00",
        "reviewed_content_digest": compute_research_content_digest(payload),
        "observations": ["合成测试，不是实际论文的科学接受"],
    }
    contract = create_project_contract(indication="特应性皮炎", reports=["A"],
                                       outputs=["html"], cutoff="2026-10-07")
    project = create_project_workspace(tmp_path / "project", contract)
    report = tmp_path / "report.json"
    report.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    audit_payload = envelope(report.read_bytes(), payload)
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps(audit_payload, ensure_ascii=False), encoding="utf-8")
    submitted = submit_product_research_package(project, audit_package=audit,
                                               report_packages={"A": report})
    assert submitted.authorization_state == "candidate_unreviewed"
    reopened = load_product_research_submission(project)
    assert reopened.replayed
    stored = json.loads(reopened.report_package_paths["A"].read_text())
    assert stored["fact_public_version_proofs"] == payload["fact_public_version_proofs"]
    assert stored["sources"][0]["first_disclosed_at"] is None
    before = {path.relative_to(project): path.read_bytes()
              for path in project.rglob("*") if path.is_file()}
    # A mechanically valid changed label still invalidates independent review;
    # no second manifest or partial replacement may be persisted.
    altered = copy.deepcopy(payload)
    altered["fact_public_version_proofs"][0]["version_references"][0]["label_zh"] = "新标签"
    report.write_text(json.dumps(altered, ensure_ascii=False), encoding="utf-8")
    altered_audit = envelope(report.read_bytes(), altered)
    audit.write_text(json.dumps(altered_audit, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ResearchPackageSubmissionError, match="严格合同"):
        submit_product_research_package(project, audit_package=audit, report_packages={"A": report})
    assert {path.relative_to(project): path.read_bytes()
            for path in project.rglob("*") if path.is_file()} == before
