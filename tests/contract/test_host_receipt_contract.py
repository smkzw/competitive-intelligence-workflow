from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast, get_args

import pytest
import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from ci_workflow.application.host_smoke import receipt_digest as smoke_receipt_digest
from ci_workflow.hosts import (
    CanonicalProjectState,
    HostArtifactBinding,
    HostEntryBinding,
    HostEventChainBinding,
    HostExecutableEvidence,
    HostFixtureBinding,
    HostManifestBinding,
    HostPackageBinding,
    HostProcessBinding,
    HostReceipt,
    HostReceiptHost,
    HostReceiptIntegrityError,
    HostReceiptRunState,
    HostRunEvidence,
    HostSessionBinding,
    build_host_receipt,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "host-receipt.schema.json"
PACKAGED_SCHEMA_PATH = (
    ROOT / "src" / "ci_workflow" / "schemas" / "host-receipt.schema.json"
)

SH_A = "a" * 64
SH_B = "b" * 64
SH_C = "c" * 64
SH_D = "d" * 64

ENTRY = HostEntryBinding(
    kind="console_script",
    command=("/opt/venv/bin/ci-workflow",),
    resolved_path="/opt/venv/bin/ci-workflow",
    sha256=SH_A,
)
HOST_EXECUTABLE = HostExecutableEvidence(
    provenance="path_resolved",
    path="/opt/homebrew/bin/codex",
    resolved_realpath="/opt/homebrew/bin/codex",
    version="codex-cli 0.42.0",
)
SESSION = HostSessionBinding(
    session_id="session-7f3k",
    launcher_pid=777,
    launcher_parent_pid=1,
)
PROCESS = HostProcessBinding(
    kind="external_subprocess",
    pid=4242,
    argv=("/opt/venv/bin/ci-workflow", "fixture", "run", "--case", "host-smoke-v1"),
    cwd="/tmp",
    started_at=datetime(2026, 9, 1, 4, 0, 0, tzinfo=UTC),
    finished_at=datetime(2026, 9, 1, 4, 0, 42, tzinfo=UTC),
    returncode=4,
    stdout_tail="",
    stderr_tail="",
)
PACKAGE = HostPackageBinding(
    name="competitive-intelligence-workflow",
    version="0.1.0a0",
    package_digest=SH_B,
)
RUN_BLOCKED = HostRunEvidence(
    project_root="/tmp/项目-codex",
    run_id="run-009",
    project_id="project-a1",
    state="blocked",
    outcome="evidence_blocked",
    no_draft=True,
    exit_code=4,
    semantic_receipt_digest=SH_D,
    artifacts=(),
)
RUN_COMPLETE = HostRunEvidence(
    project_root="/tmp/项目-codex",
    run_id="run-010",
    project_id="project-a1",
    state="complete",
    outcome="rendered",
    no_draft=False,
    exit_code=0,
    semantic_receipt_digest=SH_D,
    artifacts=(
        HostArtifactBinding(
            report="A",
            output="html",
            entry_relative_path="reports/A/v1/html/index.html",
            entry_sha256=SH_C,
        ),
    ),
)
EVENT_CHAIN = HostEventChainBinding(event_count=12, stream_digest=SH_B)
MANIFEST_BLOCKED = HostManifestBinding(
    path="manifests/current_run.json",
    sha256=SH_C,
    run_id="run-009",
    outcome="evidence_blocked",
    manifest_digest=SH_A,
)
MANIFEST_COMPLETE = HostManifestBinding(
    path="manifests/current_run.json",
    sha256=SH_C,
    run_id="run-010",
    outcome="rendered",
    manifest_digest=SH_A,
)
PROCESS_COMPLETE = PROCESS.model_copy(update={"returncode": 0})
MANIFEST_PARTIAL = MANIFEST_COMPLETE.model_copy(update={"outcome": None})


def _smoke_case() -> dict[str, Any]:
    catalog = yaml.safe_load((ROOT / "fixtures" / "catalog.yaml").read_text("utf-8"))
    for case in catalog["cases"]:
        if case["id"] == "host-smoke-v1":
            return cast(dict[str, Any], case)
    raise AssertionError("唯一 fixture catalog 未登记 host-smoke-v1 案例")


SMOKE_CASE = _smoke_case()
FIXTURE_BINDING = HostFixtureBinding(
    case_id="host-smoke-v1",
    case_digest=SMOKE_CASE["case_digest"],
    inputs={item["path"]: item["sha256"] for item in SMOKE_CASE["inputs"]},
)


def _build_receipt(
    *,
    host: str = "codex",
    run: HostRunEvidence = RUN_BLOCKED,
    manifest: HostManifestBinding = MANIFEST_BLOCKED,
    host_executable: HostExecutableEvidence = HOST_EXECUTABLE,
    process: HostProcessBinding = PROCESS,
    unavailable_reason_zh: str | None = None,
) -> HostReceipt:
    return build_host_receipt(
        host=cast(HostReceiptHost, host),
        issued_at=datetime(2026, 9, 1, 4, 1, 0, tzinfo=UTC),
        package=PACKAGE,
        entry=ENTRY,
        host_executable=host_executable,
        session=SESSION,
        process=process,
        fixture=FIXTURE_BINDING,
        run=run,
        event_chain=EVENT_CHAIN,
        manifest=manifest,
        unavailable_reason_zh=unavailable_reason_zh,
    )


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _artifacts_payload() -> list[dict[str, Any]]:
    return [artifact.model_dump(mode="json") for artifact in RUN_COMPLETE.artifacts]


# ─── 正例：唯一回执合同承载 HA09 全部绑定材料 ──────────────────────────────


def test_blocked_receipt_requires_and_allows_zero_artifacts(
    validator: Draft202012Validator,
) -> None:
    receipt = _build_receipt()
    assert receipt.status == "verified"
    assert receipt.run.state == "blocked"
    assert receipt.run.artifacts == ()
    assert receipt.run.no_draft is True
    assert not list(validator.iter_errors(receipt.model_dump(mode="json")))
    receipt.verify_content_integrity()


def test_complete_receipt_requires_at_least_one_site_html_artifact(
    validator: Draft202012Validator,
) -> None:
    receipt = _build_receipt(
        run=RUN_COMPLETE, manifest=MANIFEST_COMPLETE, process=PROCESS_COMPLETE
    )
    assert receipt.run.artifacts
    assert all(artifact.output == "html" for artifact in receipt.run.artifacts)
    assert not list(validator.iter_errors(receipt.model_dump(mode="json")))
    receipt.verify_content_integrity()


def test_partially_delivered_receipt_has_no_catalog_outcome(
    validator: Draft202012Validator,
) -> None:
    partial = RUN_COMPLETE.model_copy(
        update={"state": "partially_delivered", "outcome": None}
    )
    receipt = _build_receipt(
        run=partial, manifest=MANIFEST_PARTIAL, process=PROCESS_COMPLETE
    )
    assert not list(validator.iter_errors(receipt.model_dump(mode="json")))


def test_honest_host_unavailable_receipt_round_trips(
    validator: Draft202012Validator,
) -> None:
    unavailable = HostExecutableEvidence(provenance="unavailable")
    receipt = _build_receipt(
        host="hermes",
        host_executable=unavailable,
        unavailable_reason_zh="未在 PATH 上找到宿主 hermes 的可执行文件",
    )
    assert receipt.status == "host_unavailable"
    assert not list(validator.iter_errors(receipt.model_dump(mode="json")))
    receipt.verify_content_integrity()


def test_receipt_digest_matches_host_smoke_dict_algorithm() -> None:
    """pydantic 合同与 HA09 字典路径对同一内容产生相同摘要（唯一可用合同）。"""
    dumped = _build_receipt().model_dump(mode="json")
    assert smoke_receipt_digest(dumped) == dumped["receipt_digest"]


def test_three_hosts_same_binding_yield_distinct_receipts(
    validator: Draft202012Validator,
) -> None:
    receipts = {host: _build_receipt(host=host) for host in ("codex", "hermes", "omp")}
    for receipt in receipts.values():
        assert not list(validator.iter_errors(receipt.model_dump(mode="json")))
    assert len({receipt.receipt_digest for receipt in receipts.values()}) == 3


def test_root_and_packaged_schema_are_byte_identical_and_valid() -> None:
    root_bytes = SCHEMA_PATH.read_bytes()
    assert root_bytes == PACKAGED_SCHEMA_PATH.read_bytes()
    Draft202012Validator.check_schema(json.loads(root_bytes))


def test_host_receipt_schema_is_registered_in_package_manifest() -> None:
    manifest = json.loads((ROOT / "package-manifest.json").read_text(encoding="utf-8"))
    schemas = manifest["components"]["schemas"]
    assert isinstance(schemas, list)
    assert "schemas/host-receipt.schema.json" in schemas


def test_receipt_run_states_are_canonical_terminal_states() -> None:
    canonical = set(get_args(CanonicalProjectState))
    assert set(get_args(HostReceiptRunState)) <= canonical
    assert "running" not in get_args(HostReceiptRunState)


# ─── 反例：产物/终态/no-draft 断言一致性 ───────────────────────────────────


def test_blocked_receipt_carrying_artifact_fails_closed(
    validator: Draft202012Validator,
) -> None:
    with_artifact = RUN_BLOCKED.model_copy(update={"artifacts": RUN_COMPLETE.artifacts})
    with pytest.raises(ValidationError, match="零产物"):
        _build_receipt(run=with_artifact)
    dumped = _build_receipt().model_dump(mode="json")
    dumped["run"]["artifacts"] = _artifacts_payload()
    assert list(validator.iter_errors(dumped))


def test_complete_receipt_without_artifact_fails_closed(
    validator: Draft202012Validator,
) -> None:
    empty = RUN_COMPLETE.model_copy(update={"artifacts": ()})
    with pytest.raises(ValidationError, match="至少绑定一个站点式 HTML 产物"):
        _build_receipt(
            run=empty, manifest=MANIFEST_COMPLETE, process=PROCESS_COMPLETE
        )
    dumped = _build_receipt(
        run=RUN_COMPLETE, manifest=MANIFEST_COMPLETE, process=PROCESS_COMPLETE
    ).model_dump(mode="json")
    dumped["run"]["artifacts"] = []
    assert list(validator.iter_errors(dumped))


def test_blocked_receipt_without_no_draft_assertion_fails_closed(
    validator: Draft202012Validator,
) -> None:
    drafted = RUN_BLOCKED.model_copy(update={"no_draft": False})
    with pytest.raises(ValidationError, match="no-draft 断言"):
        _build_receipt(run=drafted)
    dumped = _build_receipt().model_dump(mode="json")
    del dumped["run"]["no_draft"]
    assert list(validator.iter_errors(dumped))


def test_blocked_receipt_with_wrong_outcome_fails_closed() -> None:
    wrong = RUN_BLOCKED.model_copy(update={"outcome": "rendered"})
    with pytest.raises(ValidationError, match="evidence_blocked"):
        _build_receipt(run=wrong)


def test_complete_receipt_claiming_no_draft_fails_closed() -> None:
    drafted = RUN_COMPLETE.model_copy(update={"no_draft": True})
    with pytest.raises(ValidationError, match="不得同时声明 no-draft"):
        _build_receipt(
            run=drafted, manifest=MANIFEST_COMPLETE, process=PROCESS_COMPLETE
        )


# ─── 反例：同进程伪造 / adapter-only JSON ─────────────────────────────────


def test_same_process_forgery_fails_closed_at_contract_level() -> None:
    dumped = _build_receipt().model_dump(mode="json")
    dumped["session"]["launcher_pid"] = PROCESS.pid
    dumped["receipt_digest"] = smoke_receipt_digest(dumped)
    with pytest.raises(ValidationError, match="同进程伪造"):
        HostReceipt.model_validate(dumped)


def test_in_process_adapter_kind_fails_closed() -> None:
    dumped = _build_receipt().model_dump(mode="json")
    dumped["process"]["kind"] = "in_process_adapter"
    with pytest.raises(ValidationError):
        HostReceipt.model_validate(dumped)


def test_adapter_only_json_cannot_pose_as_host_receipt(
    validator: Draft202012Validator,
) -> None:
    adapter_only: dict[str, Any] = {
        "schema_version": "1.0",
        "host": "codex",
        "canonical_state": "evidence_blocked",
        "primary_status_zh": "项目因关键证据不足暂时无法继续。",
        "minimal_input": {
            "reports": ["A"],
            "indication": "多发性骨髓瘤",
            "outputs": ["html"],
        },
    }
    assert list(validator.iter_errors(adapter_only))
    with pytest.raises(ValidationError):
        HostReceipt.model_validate(adapter_only)


def test_non_host_identity_cannot_enter_receipt_schema(
    validator: Draft202012Validator,
) -> None:
    dumped = _build_receipt().model_dump(mode="json")
    dumped["host"] = "local"
    assert list(validator.iter_errors(dumped))
    with pytest.raises(ValidationError):
        HostReceipt.model_validate(dumped)


# ─── 反例：宿主来源诚实性 ──────────────────────────────────────────────────


def test_unavailable_provenance_claiming_verified_fails_closed(
    validator: Draft202012Validator,
) -> None:
    unavailable = HostExecutableEvidence(provenance="unavailable")
    dumped = _build_receipt().model_dump(mode="json")
    dumped["host_executable"] = unavailable.model_dump(mode="json")
    with pytest.raises(ValidationError, match="却声称通过"):
        HostReceipt.model_validate(dumped)
    dumped["receipt_digest"] = smoke_receipt_digest(dumped)
    assert list(validator.iter_errors(dumped))


def test_unavailable_evidence_carrying_path_or_version_fails_closed() -> None:
    with pytest.raises(ValidationError, match="不得携带可执行文件路径或版本"):
        HostExecutableEvidence(
            provenance="unavailable",
            path="/opt/homebrew/bin/codex",
            version="codex-cli 0.42.0",
        )


def test_unavailable_receipt_without_chinese_reason_fails_closed() -> None:
    unavailable = HostExecutableEvidence(provenance="unavailable")
    with pytest.raises(ValidationError, match="中文不可用原因"):
        _build_receipt(host_executable=unavailable, unavailable_reason_zh=None)


def test_verified_receipt_with_reason_fails_closed() -> None:
    with pytest.raises(ValidationError, match="不得携带不可用原因"):
        _build_receipt(unavailable_reason_zh="不应出现的原因")


# ─── 反例：退出码 / argv / 时间线 / 绑定一致性 ────────────────────────────


@pytest.mark.parametrize("drop_field", ["run.exit_code", "process.returncode"])
def test_missing_exit_code_fails_closed(
    validator: Draft202012Validator, drop_field: str
) -> None:
    dumped = _build_receipt().model_dump(mode="json")
    section, field = drop_field.split(".")
    del dumped[section][field]
    assert list(validator.iter_errors(dumped))
    with pytest.raises(ValidationError):
        HostReceipt.model_validate(dumped)


def test_process_and_run_exit_code_drift_fails_closed() -> None:
    drifted = PROCESS.model_copy(update={"returncode": 0})
    dumped = _build_receipt().model_dump(mode="json")
    dumped["process"] = drifted.model_dump(mode="json")
    with pytest.raises(ValidationError, match="退出码不一致"):
        HostReceipt.model_validate(dumped)


def test_real_path_resolved_host_cannot_stop_after_blocked_workflow_exit() -> None:
    hosted = PROCESS.model_copy(
        update={
            "argv": ("/opt/homebrew/bin/codex", "exec", "受控冒烟"),
            "returncode": 0,
            "stdout_tail": "HOST_SMOKE_DONE exit=4",
        }
    )
    with pytest.raises(ValidationError, match="阻断、补件恢复和验证"):
        _build_receipt(process=hosted)


def test_real_host_process_without_completion_marker_fails_closed() -> None:
    hosted = PROCESS.model_copy(
        update={
            "argv": ("/opt/homebrew/bin/codex", "exec", "受控冒烟"),
            "returncode": 0,
            "stdout_tail": "未确认",
        }
    )
    with pytest.raises(ValidationError, match="未确认公共 Skill"):
        _build_receipt(process=hosted)


def test_argv_not_prefixed_by_real_entry_fails_closed() -> None:
    foreign = PROCESS.model_copy(
        update={"argv": ("/usr/bin/python3", "-c", "print('x')")}
    )
    dumped = _build_receipt().model_dump(mode="json")
    dumped["process"] = foreign.model_dump(mode="json")
    with pytest.raises(ValidationError, match="真实安装入口或宿主入口开头"):
        HostReceipt.model_validate(dumped)


def test_manifest_run_binding_drift_fails_closed() -> None:
    drifted = MANIFEST_BLOCKED.model_copy(update={"run_id": "run-forged"})
    with pytest.raises(ValidationError):
        _build_receipt(manifest=drifted)


@pytest.mark.parametrize(
    "removed_field",
    [
        "process",
        "event_chain",
        "manifest",
        "entry",
        "package",
        "host_executable",
        "session",
        "run",
        "fixture",
        "receipt_kind",
        "receipt_digest",
    ],
)
def test_missing_binding_sections_fail_schema_closed(
    validator: Draft202012Validator, removed_field: str
) -> None:
    dumped = _build_receipt().model_dump(mode="json")
    del dumped[removed_field]
    assert list(validator.iter_errors(dumped))


def test_fixture_binding_must_carry_per_file_digests() -> None:
    with pytest.raises(ValidationError):
        HostFixtureBinding(case_id="host-smoke-v1", case_digest=SH_B, inputs={})
    dumped = _build_receipt().model_dump(mode="json")
    dumped["fixture"]["inputs"] = {
        item["path"]: "0" * 64 for item in SMOKE_CASE["inputs"]
    }
    with pytest.raises(ValidationError, match="内容摘要与字段不一致"):
        HostReceipt.model_validate(dumped)


def test_event_chain_count_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        HostEventChainBinding(event_count=0, stream_digest=SH_B)


# ─── 反例：摘要漂移与防篡改 ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("section", "tampered"),
    [
        ("session", SESSION.model_copy(update={"session_id": "forged-session"})),
        ("event_chain", EVENT_CHAIN.model_copy(update={"event_count": 999})),
        ("run", RUN_BLOCKED.model_copy(update={"run_id": "run-forged"})),
    ],
)
def test_model_copy_tampering_fails_content_integrity(
    section: str, tampered: object
) -> None:
    receipt = _build_receipt()
    forged = receipt.model_copy(update={section: tampered})
    with pytest.raises(HostReceiptIntegrityError):
        forged.verify_content_integrity()
    receipt.verify_content_integrity()


def test_hand_edited_json_fails_revalidation_with_digest_drift() -> None:
    dumped = _build_receipt().model_dump(mode="json")
    session_edit = deepcopy(dumped)
    session_edit["session"]["session_id"] = "forged-session"
    with pytest.raises(ValidationError, match="摘要漂移"):
        HostReceipt.model_validate(session_edit)
    host_edit = deepcopy(dumped)
    host_edit["host"] = "hermes"
    with pytest.raises(ValidationError, match="摘要漂移"):
        HostReceipt.model_validate(host_edit)


# ─── 反例：格式与路径封闭 ─────────────────────────────────────────────────


def test_non_site_html_artifact_binding_fails_closed() -> None:
    with pytest.raises(ValidationError):
        HostArtifactBinding.model_validate(
            {
                "report": "A",
                "output": "pptx",
                "entry_relative_path": "reports/A/v1/pptx/a.pptx",
                "entry_sha256": SH_A,
            }
        )


def test_uppercase_digest_or_escaping_path_fails_closed() -> None:
    with pytest.raises(ValidationError):
        HostArtifactBinding(
            report="A",
            output="html",
            entry_relative_path="reports/A/v1/html/index.html",
            entry_sha256=SH_A.upper(),
        )
    with pytest.raises(ValidationError):
        HostArtifactBinding(
            report="A",
            output="html",
            entry_relative_path="../outside/index.html",
            entry_sha256=SH_A,
        )
