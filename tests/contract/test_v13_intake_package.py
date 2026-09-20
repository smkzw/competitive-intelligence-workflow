from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from ci_workflow.application.intake import (
    YaozhAccessRecord,
    YaozhAskAlreadyAnswered,
    build_public_intake,
    record_yaozh_answer,
)
from ci_workflow.domain.research_package import (
    ResearchPackage,
    ResearchPackageValidationError,
    ResearchSource,
    compute_universe_review_digest,
)
from ci_workflow.graph.typed_skills import V13_SKILL_GRAPH


def _package_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.3",
        "package_id": "rp-1",
        "contract_identity": {
            "project_id": "project-1",
            "indication": "特应性皮炎",
            "contract_version": "1.3",
        },
        "reports": ["A", "B"],
        "data_cutoff": "2026-09-04",
        "source_policy_id": "source-policy-v1",
        "source_policy_version": "1.1",
        "producer_id": "research-worker-1",
        "producer_context": "producer-context-1",
        "entities": [
            {
                "entity_id": "product-1",
                "entity_type": "product",
                "name": "示例药物",
                "aliases": ["示例别名"],
                "identity_status": "resolved",
                "disposition": "included",
                "ontology_rule_id": "innovation-therapy-v1",
                "identity_evidence_ids": ["src-1"],
            }
        ],
        "sources": [
            {
                "source_id": "src-1",
                "title": "官方登记结果",
                "source_role": "official_registry",
                "source_type": "registry",
                "url": "https://clinicaltrials.gov/study/NCT00000001",
                "locator": "Results, Table 1",
                "content_sha256": "a" * 64,
                "retrieved_at": "2026-09-04T10:00:00+00:00",
                "access_state": "available",
                "publication_classification": "not_applicable",
            }
        ],
        "routes": [
            {
                "route_id": "global-registry",
                "region": "global",
                "strategy_id": "registry-by-indication",
                "result_class": "completed",
                "attempt_ids": ["attempt-1"],
                "source_ids": ["src-1"],
            },
            {
                "route_id": "china-registry",
                "region": "china",
                "strategy_id": "registry-by-indication-cn",
                "result_class": "completed",
                "attempt_ids": ["attempt-2"],
                "source_ids": ["src-1"],
            },
        ],
        "expansion_receipts": [
            {
                "receipt_id": "exp-alias",
                "dimension": "alias",
                "round_id": "0",
                "strategy_id": "alias-reverse-search-0",
                "route_ids": ["global-registry"],
                "attempt_ids": ["attempt-exp-alias"],
                "input_entity_ids": ["product-1"],
                "discovered_entity_ids": ["product-1"],
                "source_ids": ["src-1"],
                "query_sha256": "a" * 64,
                "result_class": "success_with_evidence",
            },
            {
                "receipt_id": "exp-target",
                "dimension": "target",
                "round_id": "0",
                "strategy_id": "target-reverse-search-0",
                "route_ids": ["global-registry"],
                "attempt_ids": ["attempt-exp-target"],
                "input_entity_ids": ["product-1"],
                "discovered_entity_ids": [],
                "source_ids": [],
                "query_sha256": "b" * 64,
                "result_class": "searched_no_evidence",
                "diagnostic": "靶点反向扩展无新增实体",
            },
            {
                "receipt_id": "exp-company",
                "dimension": "company",
                "round_id": "1",
                "strategy_id": "company-reverse-search-1",
                "route_ids": ["china-registry"],
                "attempt_ids": ["attempt-exp-company"],
                "input_entity_ids": ["product-1"],
                "discovered_entity_ids": [],
                "source_ids": [],
                "query_sha256": "c" * 64,
                "result_class": "searched_no_evidence",
                "diagnostic": "企业反向扩展无新增实体",
            },
            {
                "receipt_id": "exp-trial",
                "dimension": "trial",
                "round_id": "1",
                "strategy_id": "trial-reverse-search-1",
                "route_ids": ["china-registry"],
                "attempt_ids": ["attempt-exp-trial"],
                "input_entity_ids": ["product-1"],
                "discovered_entity_ids": [],
                "source_ids": [],
                "query_sha256": "d" * 64,
                "result_class": "searched_no_evidence",
                "diagnostic": "试验反向扩展无新增实体",
            },
            {
                "receipt_id": "exp-alias-2",
                "dimension": "alias",
                "round_id": "2",
                "strategy_id": "alias-reverse-search-2",
                "route_ids": ["global-registry"],
                "attempt_ids": ["attempt-exp-alias-2"],
                "input_entity_ids": ["product-1"],
                "discovered_entity_ids": [],
                "source_ids": [],
                "query_sha256": "e" * 64,
                "result_class": "searched_no_evidence",
                "diagnostic": "别名复核无新增实体",
            },
            {
                "receipt_id": "exp-target-2",
                "dimension": "target",
                "round_id": "2",
                "strategy_id": "target-reverse-search-2",
                "route_ids": ["china-registry"],
                "attempt_ids": ["attempt-exp-target-2"],
                "input_entity_ids": ["product-1"],
                "discovered_entity_ids": [],
                "source_ids": [],
                "query_sha256": "f" * 64,
                "result_class": "searched_no_evidence",
                "diagnostic": "靶点复核无新增实体",
            },
        ],
        "closure": {
            "closed": True,
            "global_route_ids": ["global-registry"],
            "china_route_ids": ["china-registry"],
            "alias_expansion_receipts": ["exp-alias", "exp-alias-2"],
            "target_expansion_receipts": ["exp-target", "exp-target-2"],
            "company_expansion_receipts": ["exp-company"],
            "trial_expansion_receipts": ["exp-trial"],
            "independent_review_id": "review-1",
            "independent_reviewer_id": "independent-reviewer-1",
            "independent_context": "clean-context-review-1",
            "candidate_entity_ids": ["product-1"],
            "excluded_entity_ids": [],
            "new_entity_ids_by_round": {"0": ["product-1"], "1": [], "2": []},
            "convergence_round_ids": ["1", "2"],
        },
        "extraction_candidates": [
            {
                "candidate_id": "candidate-1",
                "source_id": "src-1",
                "locator": "Results, Table 1, row 1",
                "field": "result",
                "value": "1",
            }
        ],
        "recovery_rounds": [
            {
                "round_number": 1,
                "strategy_id": "alternate-registry",
                "strategy_kind": "identifier-recovery",
                "target_gap_ids": ["gap-1"],
                "route_ids": ["global-registry"],
                "source_ids": [],
                "information_gain": "no-new-evidence",
            },
            {
                "round_number": 2,
                "strategy_id": "alternate-publication",
                "strategy_kind": "publication-recovery",
                "target_gap_ids": ["gap-1"],
                "route_ids": ["china-registry"],
                "source_ids": [],
                "information_gain": "no-new-evidence",
            },
        ],
        "gap_strategies": [
            {
                "gap_id": "gap-1",
                "required": True,
                "recovery_required": True,
                "status": "resolved",
                "strategy_ids": ["alternate-registry", "alternate-publication"],
            }
        ],
        "metadata": {"origin": "autonomous-research", "redaction_version": "1"},
    }
    _bind_reviewed_universe(payload)
    return payload


def _bind_reviewed_universe(payload: dict[str, object]) -> None:
    closure = payload["closure"]
    assert isinstance(closure, dict)
    closure["reviewed_universe_sha256"] = compute_universe_review_digest(
        contract_identity=payload["contract_identity"],  # type: ignore[arg-type]
        data_cutoff=payload["data_cutoff"],  # type: ignore[arg-type]
        source_policy_id=str(payload["source_policy_id"]),
        source_policy_version=str(payload["source_policy_version"]),
        entities=payload["entities"],  # type: ignore[arg-type]
        routes=payload["routes"],  # type: ignore[arg-type]
        expansion_receipts=payload["expansion_receipts"],  # type: ignore[arg-type]
        closure=closure,
        report_payloads=payload.get("report_payloads", []),  # type: ignore[arg-type]
    )


def test_source_publication_classification_matches_source_type() -> None:
    payload = _package_payload()
    sources = payload["sources"]
    assert isinstance(sources, list)
    source = sources[0]
    assert isinstance(source, dict)

    source["publication_classification"] = "primary_result"
    with pytest.raises(ValidationError, match="非论文来源"):
        ResearchPackage.model_validate(payload)

    source["source_role"] = "primary_publication"
    source["source_type"] = "publication"
    source["publication_classification"] = "not_applicable"
    with pytest.raises(ValidationError, match="论文来源"):
        ResearchPackage.model_validate(payload)


def test_yaozh_source_is_explicit_commercial_database_on_the_approved_domain() -> None:
    source = ResearchSource.model_validate(
        {
            "source_id": "yaozh-capture-1",
            "title": "药智企业版管线页",
            "source_role": "commercial_database",
            "source_type": "secondary",
            "url": "https://vip.yaozh.com/database/pipeline",
            "locator": "产品详情摘要",
            "content_sha256": "a" * 64,
            "retrieved_at": "2026-09-06T09:00:00+08:00",
            "publication_classification": "not_applicable",
            "access_state": "available",
            "limitations": ["仅用于线索与交叉核验"],
        }
    )

    assert source.source_role == "commercial_database"
    for change in (
        {"source_type": "regulatory"},
        {"url": "https://example.com/database/pipeline"},
        {"source_role": "official_registry", "source_type": "registry"},
        {"source_role": "regulatory", "source_type": "regulatory"},
        {"source_role": "specified_secondary"},
    ):
        with pytest.raises(ValidationError):
            ResearchSource.model_validate({**source.model_dump(mode="json"), **change})


def test_yaozh_observation_and_receipt_schemas_match_models() -> None:
    from ci_workflow.application.yaozh_access import (
        YaozhRouteAccessReceipt,
        YaozhSessionObservation,
    )

    samples = (
        (
            "yaozh-session-observation.schema.json",
            YaozhSessionObservation,
            {
                "schema_version": "1.0",
                "project_id": "project-1",
                "answer_digest": "a" * 64,
                "observed_at": "2026-09-05T21:00:00+08:00",
                "host": "omp",
                "observer_id": "omp-browser-adapter",
                "origin": "https://vip.yaozh.com",
                "technical_state": "captcha_required",
                "page_marker_sha256": "b" * 64,
            },
        ),
        (
            "yaozh-route-access-receipt.schema.json",
            YaozhRouteAccessReceipt,
            {
                "schema_version": "1.0",
                "project_id": "project-1",
                "route_id": "yaozh-optional-browser",
                "answer_digest": "a" * 64,
                "observation_digest": "b" * 64,
                "observed_at": "2026-09-05T21:00:00+08:00",
                "host": "omp",
                "technical_state": "captcha_required",
                "result_class": "access_blocked",
                "user_action_zh": "请自行完成验证。",
                "blocks_core_research": False,
                "credential_fields_allowed": False,
            },
        ),
    )
    root = Path(__file__).resolve().parents[2]
    for filename, model, sample in samples:
        schema = json.loads((root / "schemas" / filename).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(sample)
        assert model.model_validate(sample).model_dump(mode="json") == sample


def test_publication_source_requires_formal_registry_bound_verdict() -> None:
    payload = _package_payload()
    entities = payload["entities"]
    sources = payload["sources"]
    assert isinstance(entities, list)
    assert isinstance(sources, list)
    entities.append(
        {
            "entity_id": "trial-1",
            "entity_type": "trial",
            "name": "NCT00000001",
            "identity_status": "resolved",
            "disposition": "included",
            "ontology_rule_id": "innovation-therapy-v1",
            "identity_evidence_ids": ["src-1"],
        }
    )
    sources.append(
        {
            "source_id": "src-pub-1",
            "title": "Primary result",
            "source_role": "primary_publication",
            "source_type": "publication",
            "url": "https://doi.org/10.1000/example",
            "locator": "full text",
            "content_sha256": None,
            "retrieved_at": "2026-09-04T10:00:00+00:00",
            "linked_trial_ids": ["trial-1"],
            "publication_classification": "primary_result",
            "access_state": "not_accessible",
        }
    )
    _bind_reviewed_universe(payload)

    with pytest.raises(ValidationError, match="正式 publication verdict"):
        ResearchPackage.model_validate(payload)

    payload["publication_records"] = [
        {
            "publication_id": "pub-1",
            "source_id": "src-pub-1",
            "product_id": "product-1",
            "linked_trial_ids": ["trial-1"],
            "registry_identifiers": ["NCT00000001"],
            "title": "Primary result",
            "source_url": "https://doi.org/10.1000/example",
            "publication_class": "primary_result",
            "model_suggestion": "primary_result",
            "classification_reason": "登记关联的主要结果论文",
            "producer_id": "publication-worker-1",
            "producer_context": "publication-context-1",
            "fetch_attempts": [
                {
                    "attempt_id": "fetch-1",
                    "strategy_id": "publisher-full-text",
                    "route_family": "publisher",
                    "attempted_at": "2026-09-04T10:00:00+00:00",
                    "result_class": "access_or_permission_blocked",
                    "diagnostic": "出版社要求机构权限",
                },
                {
                    "attempt_id": "fetch-2",
                    "strategy_id": "repository-full-text",
                    "route_family": "open_repository",
                    "attempted_at": "2026-09-04T10:05:00+00:00",
                    "result_class": "searched_no_evidence",
                    "diagnostic": "开放仓储未找到全文",
                },
            ],
            "acquisition_disposition": "manual_required",
            "blocking_fields": ["b_core_efficacy_endpoint"],
            "affected_reports": ["B"],
        }
    ]
    with pytest.raises(ValidationError, match="publication 检索回执"):
        ResearchPackage.model_validate(payload)

    payload["publication_search_receipts"] = [
        {
            "search_id": "publication-search-trial-1",
            "trial_id": "trial-1",
            "registry_identifiers": ["NCT00000001"],
            "route_families": ["registry_attachment", "bibliographic_index"],
            "attempt_ids": ["publication-search-registry-1", "publication-search-index-1"],
            "query_sha256": "d" * 64,
            "result": "publications_classified",
            "discovered_publication_ids": ["pub-1"],
        }
    ]
    ResearchPackage.model_validate(payload)
    schema = json.loads(
        (Path(__file__).resolve().parents[2] / "schemas/research-package.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []


def test_trial_without_publication_source_still_requires_search_receipt() -> None:
    payload = _package_payload()
    entities = payload["entities"]
    assert isinstance(entities, list)
    entities.append(
        {
            "entity_id": "trial-no-publication",
            "entity_type": "trial",
            "name": "NCT00000002",
            "identity_status": "resolved",
            "disposition": "included",
            "ontology_rule_id": "innovation-therapy-v1",
            "identity_evidence_ids": ["src-1"],
        }
    )
    _bind_reviewed_universe(payload)
    with pytest.raises(ValidationError, match="publication 检索回执"):
        ResearchPackage.model_validate(payload)

    payload["publication_search_receipts"] = [
        {
            "search_id": "publication-search-trial-no-publication",
            "trial_id": "trial-no-publication",
            "registry_identifiers": ["NCT00000002"],
            "route_families": ["registry_attachment", "bibliographic_index"],
            "attempt_ids": ["registry-search-no-publication", "index-search-no-publication"],
            "query_sha256": "e" * 64,
            "result": "searched_no_linked_publication",
            "discovered_publication_ids": [],
            "diagnostic": "登记附件与文献索引均未发现关联结果论文。",
        }
    ]
    ResearchPackage.model_validate(payload)


def test_public_intake_asks_for_missing_report_types_with_native_options() -> None:
    request = build_public_intake("特应性皮炎")
    assert request.reports == ()
    assert request.ask is not None
    assert [option.code for option in request.ask.options] == ["A", "B", "C"]
    assert all(option.explanation_zh for option in request.ask.options)


def test_public_intake_accepts_one_sentence_and_historical_cutoff() -> None:
    request = build_public_intake(
        "请做特应性皮炎的 A、B 竞品调研",
        reports=("A", "B"),
        historical_cutoff="2024-12-31",
    )
    assert request.reports == ("A", "B")
    assert str(request.historical_cutoff) == "2024-12-31"
    assert request.autonomous_research is True


def test_public_intake_removes_request_grammar_from_indication() -> None:
    request = build_public_intake("请做特应性皮炎的竞品调研", reports=("A",))
    assert request.indication == "特应性皮炎"


def test_yaozh_answer_is_recorded_once_without_credentials() -> None:
    first = record_yaozh_answer("project-1", "available")
    assert first.ask_count == 1
    assert first.route_enabled is True
    with pytest.raises(YaozhAskAlreadyAnswered):
        record_yaozh_answer("project-1", "skipped", existing=first)

    with pytest.raises(ValidationError):
        YaozhAccessRecord.model_validate(
            {
                **first.model_dump(mode="json"),
                "answer": "session_expired",
                "route_enabled": False,
            }
        )


def test_research_package_rejects_absolute_locator_and_ambiguous_identity() -> None:
    payload = _package_payload()
    payload["sources"] = [dict(payload["sources"][0], locator="/Users/secret/file.pdf")]  # type: ignore[index]
    with pytest.raises((ValidationError, ResearchPackageValidationError)):
        ResearchPackage.model_validate(payload)

    payload = _package_payload()
    payload["entities"] = [dict(payload["entities"][0], identity_status="ambiguous")]  # type: ignore[index]
    with pytest.raises((ValidationError, ResearchPackageValidationError)):
        ResearchPackage.model_validate(payload)


def test_research_package_rejects_secret_like_metadata_and_accepts_strict_payload() -> None:
    payload = _package_payload()
    package = ResearchPackage.model_validate(payload)
    assert package.schema_version == "1.3"
    assert package.contract_identity.project_id == "project-1"

    payload = _package_payload()
    payload["metadata"] = {"access_token": "Bearer abc"}
    with pytest.raises((ValidationError, ResearchPackageValidationError)):
        ResearchPackage.model_validate(payload)


def test_research_package_json_schema_matches_model_recovery_fields() -> None:
    payload = _package_payload()
    schema = json.loads(
        (Path(__file__).resolve().parents[2] / "schemas/research-package.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []


def test_product_handoff_requires_exact_report_payload_bindings() -> None:
    payload = _package_payload()
    package = ResearchPackage.model_validate(payload)
    with pytest.raises(ResearchPackageValidationError, match="载荷"):
        package.assert_product_handoff_ready()

    payload["report_payloads"] = [
        {
            "report": "A",
            "relative_path": "evidence/library/a-research-package.json",
            "content_sha256": "b" * 64,
            "content_schema_version": "1.0",
            "universe_product_ids": ["product-1"],
        },
        {
            "report": "B",
            "relative_path": "evidence/library/b-research-package.json",
            "content_sha256": "c" * 64,
            "content_schema_version": "1.0",
            "universe_product_ids": ["product-1"],
        },
    ]
    _bind_reviewed_universe(payload)
    ResearchPackage.model_validate(payload).assert_product_handoff_ready()

    payload["report_payloads"][0]["relative_path"] = (  # type: ignore[index]
        "evidence/library/b-research-package.json"
    )
    with pytest.raises((ValidationError, ResearchPackageValidationError), match="规范"):
        ResearchPackage.model_validate(payload)


def test_typed_v13_graph_has_public_entry_and_independent_reviewer() -> None:
    assert V13_SKILL_GRAPH.public_entry_id == "competitive-intelligence-workflow"
    assert "scientific-qc" in V13_SKILL_GRAPH.node_ids
    assert (
        V13_SKILL_GRAPH.node("scientific-qc").independent_acceptor
        == "clean-context-scientific-review"
    )
    assert all(edge.source in V13_SKILL_GRAPH.node_ids for edge in V13_SKILL_GRAPH.edges)
    assert all(edge.target in V13_SKILL_GRAPH.node_ids for edge in V13_SKILL_GRAPH.edges)
    assert V13_SKILL_GRAPH.node("scientific-qc").input_types == (
        "ReportKind",
        "ReportView",
    )
