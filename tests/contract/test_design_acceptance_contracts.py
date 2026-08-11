from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from tools.design_contract_validation import (
    DesignContractError,
    canonical_json_sha256,
    validate_current_run_acceptance,
    validate_source_pack,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "contracts" / "kangzhe" / "design_specs" / "schemas"
SOURCE_PACK_SCHEMA = SCHEMA_ROOT / "design-source-pack.schema.json"
RUN_MANIFEST_SCHEMA = SCHEMA_ROOT / "design-run-manifest.schema.json"
VERDICT_SCHEMA = SCHEMA_ROOT / "design-verdict.schema.json"

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64
SHA_E = "e" * 64
RUN_STARTED = "2026-08-11T10:00:00+08:00"
RUN_STARTED_NS = int(datetime.fromisoformat(RUN_STARTED).timestamp() * 1_000_000_000)


def _valid_source_pack() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "source_pack_id": "htmlppt-b-crswnp-v1",
        "track": "htmlppt",
        "files": [{"path": "facts.json", "sha256": SHA_A}],
        "tokens": [
            {
                "token_id": "fact-efficacy-001",
                "category": "audience_fact",
                "source_locator": "NCT00000001/results#week24",
                "semantic_role": "第24周主要终点试验组变化值",
                "original_value": -1.2,
                "unit": "分",
                "denominator": "全分析集 n=100",
                "population": "全分析集",
                "arm": "试验组",
                "timepoint": "第24周",
            },
            {"token_id": "page-001", "category": "page_number", "value": 4},
        ],
        "claims": [
            {
                "claim_id": "claim-efficacy-001",
                "value": -1.2,
                "unit": "分",
                "denominator": "全分析集 n=100",
                "normalized_value": "-1.2分（第24周，全分析集，n=100）",
                "source_token_ids": ["fact-efficacy-001"],
            }
        ],
        "occurrences": [
            {
                "claim_id": "claim-efficacy-001",
                "surface": "chart",
                "location_id": "slide-04-chart-01",
                "normalized_value": "-1.2分（第24周，全分析集，n=100）",
            },
            {
                "claim_id": "claim-efficacy-001",
                "surface": "speaker_notes",
                "location_id": "slide-04",
                "normalized_value": "-1.2分（第24周，全分析集，n=100）",
            },
        ],
        "notes": [
            {
                "slide_id": "slide-04",
                "text": "第24周主要终点较基线下降1.2分。",
                "claim_ids": ["claim-efficacy-001"],
                "claim_spans": [
                    {
                        "claim_id": "claim-efficacy-001",
                        "text_span": "第24周主要终点较基线下降1.2分",
                        "normalized_value": "-1.2分（第24周，全分析集，n=100）",
                    }
                ],
            }
        ],
    }


def _file_state(path: str, sha256: str, *, observed_at: str) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": sha256,
        "mtime_ns": RUN_STARTED_NS + 1_000_000_000,
        "inode": 501,
        "observed_at": observed_at,
        "created_by_run_id": "run-20260811-001",
        "pre_run_state": {"exists": False},
    }


def _valid_manifest() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "run_id": "run-20260811-001",
        "run_nonce": "nonce-20260811-001-unique",
        "run_started_at": RUN_STARTED,
        "runner_identity": "workflow-runner",
        "producer_identity": "report-producer",
        "report_snapshot_sha256": SHA_A,
        "design_contract_sha256": SHA_B,
        "source_pack_sha256": SHA_C,
        "artifact": _file_state(
            "outputs/report.html", SHA_D, observed_at="2026-08-11T10:00:02+08:00"
        ),
        "render": _file_state(
            "renders/report-home.png", SHA_E, observed_at="2026-08-11T10:00:03+08:00"
        ),
        "receipts": [
            {
                "receipt_id": "render-receipt-001",
                "run_id": "run-20260811-001",
                "run_nonce": "nonce-20260811-001-unique",
                "design_contract_sha256": SHA_B,
                "source_pack_sha256": SHA_C,
                "issued_at": "2026-08-11T10:00:04+08:00",
            }
        ],
    }


def _valid_verdict(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    bound_manifest = manifest or _valid_manifest()
    return {
        "schema_version": "1.0",
        "run_id": "run-20260811-001",
        "run_nonce": "nonce-20260811-001-unique",
        "manifest_sha256": canonical_json_sha256(bound_manifest),
        "producer_identity": "report-producer",
        "verifier_identity": "independent-visual-verifier",
        "artifact_sha256": SHA_D,
        "render_sha256": SHA_E,
        "issued_at": "2026-08-11T10:00:05+08:00",
        "verdict": "accepted",
        "checks": {
            "current_run": True,
            "real_artifact": True,
            "real_render": True,
            "independent_verifier": True,
            "receipts_current": True,
        },
    }


def _validate_run(manifest: dict[str, Any], verdict: dict[str, Any]) -> None:
    validate_current_run_acceptance(
        manifest,
        verdict,
        manifest_schema_path=RUN_MANIFEST_SCHEMA,
        verdict_schema_path=VERDICT_SCHEMA,
    )


def test_source_pack_preserves_fact_lineage_across_chart_and_speaker_notes() -> None:
    validate_source_pack(_valid_source_pack(), SOURCE_PACK_SCHEMA)


def test_audience_fact_without_denominator_is_rejected() -> None:
    source_pack = _valid_source_pack()
    del source_pack["tokens"][0]["denominator"]
    with pytest.raises(DesignContractError):
        validate_source_pack(source_pack, SOURCE_PACK_SCHEMA)


def test_business_fact_cannot_be_disguised_as_a_page_number() -> None:
    source_pack = _valid_source_pack()
    source_pack["tokens"][0] = {
        "token_id": "fact-efficacy-001",
        "category": "page_number",
        "value": 24,
        "source_locator": "NCT00000001/results#week24",
    }
    with pytest.raises(DesignContractError):
        validate_source_pack(source_pack, SOURCE_PACK_SCHEMA)


def test_claim_must_reference_an_existing_typed_token() -> None:
    source_pack = _valid_source_pack()
    source_pack["claims"][0]["source_token_ids"] = ["missing-token"]
    with pytest.raises(DesignContractError, match="不存在的 token"):
        validate_source_pack(source_pack, SOURCE_PACK_SCHEMA)


def test_speaker_note_claim_must_have_a_matching_note_occurrence() -> None:
    source_pack = _valid_source_pack()
    source_pack["occurrences"] = [source_pack["occurrences"][0]]
    with pytest.raises(DesignContractError, match="speaker_notes"):
        validate_source_pack(source_pack, SOURCE_PACK_SCHEMA)


def test_speaker_note_cannot_introduce_a_claim_absent_from_audience_surfaces() -> None:
    source_pack = _valid_source_pack()
    source_pack["occurrences"] = [source_pack["occurrences"][1]]
    with pytest.raises(DesignContractError, match="受众可见载体"):
        validate_source_pack(source_pack, SOURCE_PACK_SCHEMA)


def test_normalized_value_mismatch_across_surfaces_is_rejected() -> None:
    source_pack = _valid_source_pack()
    source_pack["occurrences"][1]["normalized_value"] = "-1.1分"
    with pytest.raises(DesignContractError, match="归一化值不一致"):
        validate_source_pack(source_pack, SOURCE_PACK_SCHEMA)


def test_current_run_acceptance_binds_new_artifact_render_receipt_and_verifier() -> None:
    manifest = _valid_manifest()
    _validate_run(manifest, _valid_verdict(manifest))


@pytest.mark.parametrize("receipt_field", ["run_id", "run_nonce"])
def test_stale_receipt_from_another_run_is_rejected(receipt_field: str) -> None:
    manifest = _valid_manifest()
    manifest["receipts"][0][receipt_field] = "stale-run-value-0000"
    with pytest.raises(DesignContractError, match="没有绑定当前运行"):
        _validate_run(manifest, _valid_verdict(manifest))


def test_old_receipt_timestamp_is_rejected() -> None:
    manifest = _valid_manifest()
    manifest["receipts"][0]["issued_at"] = "2026-08-10T10:00:04+08:00"
    with pytest.raises(DesignContractError, match="不在当前运行窗口"):
        _validate_run(manifest, _valid_verdict(manifest))


def test_old_artifact_with_only_rewritten_metadata_is_rejected() -> None:
    manifest = _valid_manifest()
    artifact = manifest["artifact"]
    artifact["pre_run_state"] = {
        "exists": True,
        "sha256": artifact["sha256"],
        "mtime_ns": artifact["mtime_ns"],
        "inode": artifact["inode"],
    }
    with pytest.raises(DesignContractError, match="运行前文件内容相同"):
        _validate_run(manifest, _valid_verdict(manifest))


@pytest.mark.parametrize("file_key", ["artifact", "render"])
def test_artifact_or_render_observed_before_run_is_rejected(file_key: str) -> None:
    manifest = _valid_manifest()
    manifest[file_key]["observed_at"] = "2026-08-10T10:00:02+08:00"
    with pytest.raises(DesignContractError, match="不在当前运行窗口"):
        _validate_run(manifest, _valid_verdict(manifest))


def test_file_mtime_before_run_is_rejected_even_when_observation_is_new() -> None:
    manifest = _valid_manifest()
    manifest["render"]["mtime_ns"] = RUN_STARTED_NS - 1
    with pytest.raises(DesignContractError, match="文件修改时间早于当前运行"):
        _validate_run(manifest, _valid_verdict(manifest))


def test_producer_cannot_self_sign_as_independent_verifier() -> None:
    verdict = _valid_verdict()
    verdict["verifier_identity"] = "report-producer"
    with pytest.raises(DesignContractError, match="不能验收自己的产物"):
        _validate_run(_valid_manifest(), verdict)


def test_verdict_must_bind_the_exact_manifest_digest() -> None:
    verdict = _valid_verdict()
    verdict["manifest_sha256"] = SHA_A
    with pytest.raises(DesignContractError, match="运行清单摘要"):
        _validate_run(_valid_manifest(), verdict)


def test_accepted_verdict_cannot_hide_a_failed_check() -> None:
    verdict = _valid_verdict()
    verdict["checks"]["real_render"] = False
    with pytest.raises(DesignContractError, match="未通过的验收项"):
        _validate_run(_valid_manifest(), verdict)


def test_verdict_without_render_digest_is_rejected_by_schema() -> None:
    verdict = copy.deepcopy(_valid_verdict())
    del verdict["render_sha256"]
    with pytest.raises(DesignContractError, match="render_sha256"):
        _validate_run(_valid_manifest(), verdict)


def test_any_manifest_body_change_invalidates_an_existing_verdict_digest() -> None:
    manifest = _valid_manifest()
    verdict = _valid_verdict(manifest)
    manifest["report_snapshot_sha256"] = SHA_E
    with pytest.raises(DesignContractError, match="运行清单摘要"):
        _validate_run(manifest, verdict)


def test_unknown_pre_run_state_cannot_be_hidden_as_null() -> None:
    manifest = _valid_manifest()
    manifest["artifact"]["pre_run_state"] = None
    with pytest.raises(DesignContractError, match="pre_run_state"):
        _validate_run(manifest, _valid_verdict(manifest))


def test_claim_value_must_match_its_source_fact_value_unit_and_denominator() -> None:
    source_pack = _valid_source_pack()
    source_pack["claims"][0]["value"] = 999
    source_pack["claims"][0]["normalized_value"] = "999分（虚构）"
    for occurrence in source_pack["occurrences"]:
        occurrence["normalized_value"] = "999分（虚构）"
    source_pack["notes"][0]["claim_spans"][0]["normalized_value"] = "999分（虚构）"
    with pytest.raises(DesignContractError, match="与来源事实不一致"):
        validate_source_pack(source_pack, SOURCE_PACK_SCHEMA)


def test_claim_cannot_reference_a_structurally_valid_page_number_token() -> None:
    source_pack = _valid_source_pack()
    source_pack["tokens"][0] = {
        "token_id": "fact-efficacy-001",
        "category": "page_number",
        "value": 24,
    }
    with pytest.raises(DesignContractError, match="只能引用 audience_fact"):
        validate_source_pack(source_pack, SOURCE_PACK_SCHEMA)


def test_note_text_cannot_introduce_an_unbound_number() -> None:
    source_pack = _valid_source_pack()
    source_pack["notes"][0]["text"] += " 另一个数值为999。"
    with pytest.raises(DesignContractError, match="未绑定声明的数字"):
        validate_source_pack(source_pack, SOURCE_PACK_SCHEMA)
