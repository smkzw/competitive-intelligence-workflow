"""Submission must join source instances, not merely their identifiers."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from contextlib import suppress
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from test_research_package_submission import (
    ROOT,
    _audit_payload,
    _bind_reviewed_universe,
    _project,
    _source_payload,
)

from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.research_package_submission import (
    AUDIT_PACKAGE_PATH,
    REPORT_PACKAGE_PATHS,
    SUBMISSION_MANIFEST_PATH,
    ResearchPackageSubmissionError,
    _assert_source_bindings,
    _capture_source_classification,
    _validate_report_payload,
    load_product_research_submission,
    submit_product_research_package,
)
from ci_workflow.application.source_research_service import (
    SourceCapture,
    compute_research_content_digest,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.research_package import ResearchSource, compute_universe_review_digest


def _persistent_bytes(project: Path) -> dict[str, bytes]:
    # Workspace verification may open SQLite and create ephemeral WAL/SHM
    # coordination files. They are not a submitted research artifact.
    return {
        str(p.relative_to(project)): p.read_bytes()
        for p in project.rglob("*")
        if p.is_file() and not p.name.endswith(("-wal", "-shm"))
    }


@pytest.mark.parametrize(
    "change",
    [
        {"url": "https://example.org/different?id=2"},
        {"title": "不同来源标题"},
        {"content_sha256": "0" * 64},
        {"retrieved_at": "2026-08-18T13:00:00+08:00"},
        {"access_state": "not_accessible", "content_sha256": None},
    ],
)
def test_same_id_mismatch_rejected_before_persistence(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    project = _project(tmp_path)
    source_path, report = _source_payload(tmp_path)
    contract = json.loads((project / "project.yaml").read_text())["project_contract_versions"][0]
    audit = _audit_payload(contract["project_id"], source_path.read_bytes(), report)
    audit["sources"][0].update(change)
    _bind_reviewed_universe(audit)
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(json.dumps(audit))
    before = _persistent_bytes(project)
    with pytest.raises(ResearchPackageSubmissionError, match="来源绑定"):
        submit_product_research_package(
            project, audit_package=audit_path, report_packages={"A": source_path}
        )
    assert not (project / AUDIT_PACKAGE_PATH).exists()
    assert not (project / SUBMISSION_MANIFEST_PATH).exists()
    assert not (project / REPORT_PACKAGE_PATHS["A"]).exists()
    assert before == _persistent_bytes(project)


def _fixture_module(relative_path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location("binding_fixture", ROOT / relative_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=["A", "B", "C"])
def submission_case(tmp_path: Path, request: pytest.FixtureRequest) -> tuple:
    kind = request.param
    cutoff = "2026-09-01" if kind == "C" else "2026-07-31"
    contract = create_project_contract(
        indication="特应性皮炎", reports=[kind], outputs=["html"], cutoff=cutoff
    )
    if kind == "A":
        _, raw = _source_payload(tmp_path)
    elif kind == "B":
        module = _fixture_module("tests/unit/reports/b/test_fresh_b_research_package.py")
        raw = module._with_review(module._package_payload(project_id=contract.project_id))
    else:
        module = _fixture_module("tests/integration/test_fresh_c_research_package.py")
        api = module._module()
        raw = module._ready_package_payload(api)
        content = api.validate_fresh_c_content(raw)
        raw = api.validate_fresh_c_package(
            {**raw, "scientific_review": module._review(api, content.content_digest)}
        ).model_dump(mode="json")
    data = json.dumps(raw, ensure_ascii=False).encode("utf-8")
    payload = _validate_report_payload(kind, data)
    report = payload.model_dump(mode="json")
    report["universe_product_ids"] = list(payload.universe_product_ids)
    audit = _audit_payload(contract.project_id, data, report)
    audit["reports"] = [kind]
    audit["data_cutoff"] = cutoff
    audit["report_payloads"][0].update(report=kind, relative_path=REPORT_PACKAGE_PATHS[kind])
    if kind == "B":
        # Existing synthetic Study-1 primary report, not invented clinical data.
        # A publication must have a real typed verdict even in admission tests.
        source = audit["sources"][0]
        source["linked_trial_ids"] = ["study-1"]
        audit["entities"].append(
            {
                "entity_id": "study-1",
                "entity_type": "trial",
                "name": "Study-1",
                "identity_status": "resolved",
                "disposition": "included",
                "ontology_rule_id": "innovation-therapy-v1",
                "identity_evidence_ids": [source["source_id"]],
            }
        )
        audit["publication_records"] = [
            {
                "publication_id": "pub-study-1",
                "source_id": source["source_id"],
                "product_id": "prod-1",
                "linked_trial_ids": ["study-1"],
                "registry_identifiers": ["Study-1"],
                "title": source["title"],
                "source_url": source["url"],
                "publication_class": "primary_result",
                "model_suggestion": "primary_result",
                "classification_reason": "合成主要报告合同测试",
                "producer_id": "synthetic-producer",
                "producer_context": "synthetic-context",
                "acquisition_disposition": "acquired",
                "affected_reports": ["B"],
                "fetch_attempts": [
                    {
                        "attempt_id": "fetch-study-1",
                        "strategy_id": "publisher-fetch",
                        "route_family": "publisher",
                        "attempted_at": source["retrieved_at"],
                        "result_class": "acquired",
                        "source_id": source["source_id"],
                    }
                ],
            }
        ]
        audit["publication_search_receipts"] = [
            {
                "search_id": "search-study-1",
                "trial_id": "study-1",
                "registry_identifiers": ["Study-1"],
                "route_families": ["publisher", "bibliographic_index"],
                "attempt_ids": ["publisher-search", "index-search"],
                "query_sha256": hashlib.sha256(b"synthetic-study-1").hexdigest(),
                "result": "publications_classified",
                "discovered_publication_ids": ["pub-study-1"],
            }
        ]
        audit["closure"]["candidate_entity_ids"] = ["prod-1", "study-1"]
        audit["closure"]["new_entity_ids_by_round"]["0"] = ["prod-1", "study-1"]
        audit["expansion_receipts"][0]["discovered_entity_ids"] = ["prod-1", "study-1"]
    _bind_reviewed_universe(audit)
    project = create_project_workspace(tmp_path / "project", contract)
    path = tmp_path / "payload.json"
    path.write_bytes(data)
    return kind, project, path, audit


def _submit(case: tuple) -> Any:
    kind, project, path, audit = case
    # Model a new synthetic review, to test payload binding rather than merely
    # reject a stale envelope review digest.
    # Invalid metadata cannot obtain a receipt; still exercise admission.
    with suppress(ValidationError):
        _bind_reviewed_universe(audit)
    audit_path = path.parent / "audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
    return submit_product_research_package(
        project, audit_package=audit_path, report_packages={kind: path}
    )


def test_abc_admit_reload_with_unused_source_and_equivalent_time(submission_case: tuple) -> None:
    _, project, _, audit = submission_case
    extra = deepcopy(audit["sources"][0])
    extra.update(
        source_id="unused-search-instance",
        source_type="registry",
        source_role="official_registry",
        publication_classification="not_applicable",
        linked_trial_ids=[],
        access_state="not_accessible",
        content_sha256=None,
    )
    audit["sources"].append(extra)
    for source in audit["sources"]:
        source["retrieved_at"] = (
            datetime.fromisoformat(source["retrieved_at"]).astimezone(UTC).isoformat()
        )
    assert _submit(submission_case).replayed is False
    assert load_product_research_submission(project).replayed is True


@pytest.mark.parametrize(
    "change",
    [
        {"url": "https://example.org/different?id=2"},
        {"title": "不同来源标题"},
        {"content_sha256": "0" * 64},
        {"retrieved_at": "2026-08-19T13:00:00+08:00"},
        {"published_at": "2020-01-01"},
        {"effective_at": "2020-01-01"},
        {"source_role": "design_document"},
        {"source_type": "secondary"},
        {"publication_classification": "review"},
        {"access_state": "not_accessible", "content_sha256": None},
    ],
)
def test_abc_mismatch_never_persists(submission_case: tuple, change: dict[str, Any]) -> None:
    kind, project, _, audit = submission_case
    audit["sources"][0].update(change)
    if kind == "B" and "url" in change:
        audit["publication_records"][0]["source_url"] = change["url"]
    before = _persistent_bytes(project)
    with pytest.raises(ResearchPackageSubmissionError):
        _submit(submission_case)
    assert before == _persistent_bytes(project)
    assert not (project / AUDIT_PACKAGE_PATH).exists()
    assert not (project / SUBMISSION_MANIFEST_PATH).exists()
    assert not (project / REPORT_PACKAGE_PATHS[kind]).exists()


def test_abc_reload_rechecks_binding_even_with_updated_manifest(submission_case: tuple) -> None:
    _, project, _, audit = submission_case
    _submit(submission_case)
    audit["sources"][0]["title"] = "篡改的来源标题"
    data = json.dumps(audit, ensure_ascii=False).encode("utf-8")
    (project / AUDIT_PACKAGE_PATH).write_bytes(data)
    manifest_path = project / SUBMISSION_MANIFEST_PATH
    manifest = json.loads(manifest_path.read_text())
    manifest["audit_package"]["sha256"] = hashlib.sha256(data).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="独立复核"):
        load_product_research_submission(project)


# Independent expectations, not generated from the implementation's mapping.
@pytest.mark.parametrize(
    "capture_type,expected",
    [
        ("clinical_trial_registry", ("registry", "official_registry", "not_applicable")),
        ("primary_trial_report", ("publication", "primary_publication", "primary_result")),
        ("peer_reviewed_primary_report", ("publication", "primary_publication", "primary_result")),
        (
            "peer_reviewed_primary_report_recovered",
            ("publication", "primary_publication", "primary_result"),
        ),
        ("company_official_disclosure", ("company", "company_disclosure", "not_applicable")),
        ("company_official_result_disclosure", ("company", "company_disclosure", "not_applicable")),
        ("company_regulatory_disclosure", ("company", "company_disclosure", "not_applicable")),
        ("conference_result_official_disclosure", ("conference", "conference", "not_applicable")),
        ("official_conference_primary_result", ("conference", "conference", "not_applicable")),
        ("regulatory_label_or_approval", ("regulatory", "regulatory", "not_applicable")),
        ("regulatory_review", ("regulatory", "regulatory", "not_applicable")),
    ],
)
def test_explicit_document_kind_mapping(capture_type: str, expected: tuple[str, ...]) -> None:
    assert _capture_source_classification(capture_type) == expected


@pytest.mark.parametrize(
    "capture_type",
    [
        "peer_reviewed_publication",
        "peer_reviewed_regulatory_milestone_review",
        "peer_reviewed_evidence_review",
        "publication",
        "secondary",
        "unknown",
    ],
)
def test_ambiguous_types_never_default_to_secondary(capture_type: str) -> None:
    with pytest.raises(ResearchPackageSubmissionError, match="类型未明确"):
        _capture_source_classification(capture_type)


def test_real_fixture_capture_types_are_explicitly_accounted_for() -> None:
    raw = json.loads(
        (ROOT / "fixtures/positive/a-atopic-dermatitis/research-package.json").read_text()
    )
    for item in raw["sources"]:
        if item["source_type"] in {
            "peer_reviewed_publication",
            "peer_reviewed_regulatory_milestone_review",
            "peer_reviewed_evidence_review",
        }:
            with pytest.raises(ResearchPackageSubmissionError, match="类型未明确"):
                _capture_source_classification(item["source_type"])
        else:
            _capture_source_classification(item["source_type"])


def test_normalized_text_not_original_file_hash_and_instance_subset(tmp_path: Path) -> None:
    path, report = _source_payload(tmp_path)
    capture = SourceCapture.model_validate({**report["sources"][0], "content_text": " \n正文\r\n "})
    assert capture.content_text == "正文"
    raw_file = b"%PDF-1.7 raw bytes are not extracted text"
    source = ResearchSource.model_validate(
        {
            **_audit_payload("project", path.read_bytes(), report)["sources"][0],
            "content_sha256": hashlib.sha256(capture.content_text.encode("utf-8")).hexdigest(),
        }
    )
    envelope = SimpleNamespace(sources=(source,))
    payload = SimpleNamespace(sources=(capture,))
    _assert_source_bindings(envelope, payload)
    wrong = source.model_copy(update={"content_sha256": hashlib.sha256(raw_file).hexdigest()})
    with pytest.raises(ResearchPackageSubmissionError, match="规范入库文本摘要"):
        _assert_source_bindings(SimpleNamespace(sources=(wrong,)), payload)
    duplicate = SimpleNamespace(sources=(capture, capture))
    with pytest.raises(ResearchPackageSubmissionError, match="重复"):
        _assert_source_bindings(envelope, duplicate)
    other = capture.model_copy(update={"source_id": "another-instance-same-family"})
    with pytest.raises(ResearchPackageSubmissionError, match="审计包外来源"):
        _assert_source_bindings(envelope, SimpleNamespace(sources=(capture, other)))
    other_source = source.model_copy(update={"source_id": other.source_id})
    _assert_source_bindings(
        SimpleNamespace(sources=(source, other_source)), SimpleNamespace(sources=(capture, other))
    )


@pytest.mark.parametrize(
    "capture_type",
    [
        "peer_reviewed_publication",
        "peer_reviewed_evidence_review",
        "peer_reviewed_regulatory_milestone_review",
        "unknown",
    ],
)
def test_ambiguous_payload_type_rejected_after_valid_digest_binding(
    tmp_path: Path, capture_type: str
) -> None:
    project = _project(tmp_path)
    path, raw = _source_payload(tmp_path)
    project_id = json.loads((project / "project.yaml").read_text())["project_contract_versions"][0][
        "project_id"
    ]
    audit = _audit_payload(project_id, path.read_bytes(), raw)
    # Mutate only synthetic metadata and genuinely recompute both digests, so
    # rejection cannot be explained by a stale scientific or file checksum.
    raw["sources"][0]["source_type"] = capture_type
    raw["scientific_review"]["reviewed_content_digest"] = compute_research_content_digest(raw)
    data = json.dumps(raw, ensure_ascii=False).encode("utf-8")
    _validate_report_payload("A", data)
    path.write_bytes(data)
    audit["report_payloads"][0]["content_sha256"] = hashlib.sha256(data).hexdigest()
    _bind_reviewed_universe(audit)
    before = _persistent_bytes(project)
    with pytest.raises(ResearchPackageSubmissionError, match="类型未明确"):
        _submit(("A", project, path, audit))
    assert _persistent_bytes(project) == before


def test_source_classification_and_url_query_are_bound(tmp_path: Path) -> None:
    path, raw = _source_payload(tmp_path)
    capture = SourceCapture.model_validate(raw["sources"][0])
    source = ResearchSource.model_validate(
        _audit_payload("project", path.read_bytes(), raw)["sources"][0]
    )
    payload = SimpleNamespace(sources=(capture,))
    for changed in [
        {"source_type": "secondary"},
        {"source_role": "registry_history"},
        {"publication_classification": "review"},
        {"url": capture.url + "?record=other"},
    ]:
        with pytest.raises(ResearchPackageSubmissionError, match="来源绑定"):
            _assert_source_bindings(
                SimpleNamespace(sources=(source.model_copy(update=changed),)), payload
            )
    # A second report cannot assign a new title/content to the same source ID.
    for changed in [{"title": "另一个报告的标题"}, {"content_text": "不同报告的原文"}]:
        with pytest.raises(ResearchPackageSubmissionError, match="来源绑定"):
            _assert_source_bindings(
                SimpleNamespace(sources=(source,)),
                SimpleNamespace(sources=(capture.model_copy(update=changed),)),
            )


@pytest.mark.parametrize("field", ["published_at", "effective_at"])
def test_source_dates_bind_using_project_timezone(tmp_path: Path, field: str) -> None:
    path, raw = _source_payload(tmp_path)
    capture = SourceCapture.model_validate(raw["sources"][0]).model_copy(update={
        field: datetime.fromisoformat("2026-07-01T23:30:00+00:00"),
    })
    source = ResearchSource.model_validate({
        **_audit_payload("project", path.read_bytes(), raw)["sources"][0],
        field: "2026-07-02",
    })
    _assert_source_bindings(
        SimpleNamespace(sources=(source,)), SimpleNamespace(sources=(capture,)),
        timezone="Asia/Shanghai",
    )
    for wrong in [None, "2026-07-01"]:
        changed = ResearchSource.model_validate({**source.model_dump(), field: wrong})
        with pytest.raises(ResearchPackageSubmissionError, match=field):
            _assert_source_bindings(
                SimpleNamespace(sources=(changed,)), SimpleNamespace(sources=(capture,)),
                timezone="Asia/Shanghai",
            )


@pytest.mark.parametrize("field", ["published_at", "effective_at"])
def test_calendar_day_does_not_shift_to_previous_day_in_project_timezone(
    tmp_path: Path, field: str,
) -> None:
    path, raw = _source_payload(tmp_path)
    capture = SourceCapture.model_validate({
        **raw["sources"][0], field: "2026-07-01T00:00:00Z",
        "date_precisions": {field: "calendar_day"},
    })
    source = ResearchSource.model_validate({
        **_audit_payload("project", path.read_bytes(), raw)["sources"][0],
        **{
            role: timestamp.astimezone(ZoneInfo("America/Los_Angeles")).date()
            if timestamp is not None else None
            for role in ("published_at", "effective_at")
            for timestamp in (getattr(capture, role),)
        },
        field: "2026-07-01",
    })
    _assert_source_bindings(
        SimpleNamespace(sources=(source,)), SimpleNamespace(sources=(capture,)),
        timezone="America/Los_Angeles",
    )


def test_legacy_review_cannot_admit_new_submission(submission_case: tuple) -> None:
    kind, project, path, audit = submission_case
    audit["closure"]["review_digest_version"] = "1"
    audit["closure"]["reviewed_universe_sha256"] = compute_universe_review_digest(
        **{key: audit[key] for key in (
            "contract_identity", "data_cutoff", "source_policy_id", "source_policy_version",
            "entities", "routes", "expansion_receipts", "closure", "report_payloads",
        )},
    )
    audit_path = path.parent / "audit.json"
    audit_path.write_text(json.dumps(audit))
    before = _persistent_bytes(project)
    with pytest.raises(ResearchPackageSubmissionError, match="来源.*复核.*v2"):
        submit_product_research_package(
            project, audit_package=audit_path, report_packages={kind: path}
        )
    assert before == _persistent_bytes(project)


@pytest.mark.parametrize("change", [None, {"document_role": "different-document", "page": 99}])
def test_source_requires_matching_structured_locator(
    tmp_path: Path, change: dict[str, Any] | None,
) -> None:
    path, raw = _source_payload(tmp_path)
    capture = SourceCapture.model_validate(raw["sources"][0])
    source = ResearchSource.model_validate(
        _audit_payload("project", path.read_bytes(), raw)["sources"][0]
    )
    changed = source.model_copy(update={"locator_detail": change})
    with pytest.raises(ResearchPackageSubmissionError, match="定位"):
        _assert_source_bindings(
            SimpleNamespace(sources=(changed,)), SimpleNamespace(sources=(capture,)),
        )
