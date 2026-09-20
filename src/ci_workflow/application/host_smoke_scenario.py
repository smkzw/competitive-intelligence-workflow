"""host-smoke-v1 的阻断、补件恢复和最终验证场景。"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.application.fixture_runner import (
    _compute_case_digest,
    _get_case_root_base,
    _load_catalog,
    _load_fixture_schema,
    _resolve_case_dir,
    _validate_catalog,
    run_fixture_case,
)
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.run_service import (
    CANONICAL_REPORT_DATA_RELATIVE_PATH,
    CANONICAL_UNIVERSE_RELATIVE_PATH,
    RunContext,
    RunResult,
    run_project,
    validate_run_manifest,
)
from ci_workflow.graph.executor import GraphExecutor
from ci_workflow.graph.recovery import DeliveryContract, PartialDeliveryCoordinator
from ci_workflow.storage.event_store import EventStore

SCENARIO_RECORD_RELATIVE = Path("state/host-smoke-v1.json")


class HostSmokeScenarioError(RuntimeError):
    """候选包宿主场景没有完整走过阻断、恢复或验证。"""


@dataclass(frozen=True)
class HostSmokeScenarioResult:
    run_result: RunResult
    record_path: Path
    record: dict[str, Any]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _completed_result(project_root: Path, case_digest: str) -> RunResult:
    manifest = validate_run_manifest(project_root)
    contract = verify_project_workspace(project_root).contract
    if (
        manifest["outcome"] != "completed"
        or manifest["project_id"] != contract.project_id
        or manifest["contract_version"] != contract.contract_version
        or manifest["case_id"] != "host-smoke-v1"
        or manifest["case_digest"] != case_digest
        or not _report_artifact_digests(manifest)
    ):
        raise HostSmokeScenarioError("恢复完成清单绑定不一致")
    return TypeAdapter(RunResult).validate_python(
        {
            **{
                key: manifest[key]
                for key in (
                    "run_id",
                    "project_id",
                    "contract_version",
                    "outcome",
                    "node_summary",
                    "reused",
                    "outputs",
                    "case_id",
                    "case_digest",
                    "input_hashes",
                )
            },
            "exit_code": 0,
        }
    )


def _report_artifact_digests(manifest: dict[str, Any]) -> dict[str, str]:
    return {
        item["relative_path"]: item["sha256"]
        for item in (*manifest.get("outputs", []), *manifest.get("reused_artifacts", []))
        if item["relative_path"].startswith("reports/")
    }


def run_host_smoke_scenario(
    *,
    project_root: Path,
    catalog_path: Path,
    resume: bool = False,
) -> HostSmokeScenarioResult:
    """在同一项目完成 no-draft 阻断、显式补件重开、HTML 恢复和验证。"""
    project_root = project_root.expanduser().resolve()
    catalog_path = catalog_path.expanduser().resolve()
    cases = _validate_catalog(
        _load_catalog(catalog_path),
        case_root_base=_get_case_root_base(catalog_path),
        schema=_load_fixture_schema(),
    )
    case = cases.get("host-smoke-v1")
    if case is None:
        raise HostSmokeScenarioError("唯一 fixture catalog 未登记 host-smoke-v1")
    recovery_inputs = [item for item in case["inputs"] if item["role"] == "recovery_report_data"]
    if len(recovery_inputs) != 1:
        raise HostSmokeScenarioError("host-smoke-v1 必须声明唯一恢复报告数据")

    record_path = project_root / SCENARIO_RECORD_RELATIVE
    if resume:
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            initial_evidence = record["initial"]
            if record["case_digest"] != _compute_case_digest(case):
                raise ValueError("case drift")
            initial_copy = project_root / "state/host-smoke-v1-initial-manifest.json"
            if _sha256(initial_copy) != initial_evidence["manifest_sha256"]:
                raise ValueError("initial manifest drift")
            initial_manifest = json.loads(initial_copy.read_text(encoding="utf-8"))
            initial_events = EventStore(project_root).read_all()[: initial_evidence["event_count"]]
            recorded = [
                event
                for event in initial_events
                if event.run_id == initial_evidence["run_id"]
                and event.event_type == "run.manifest.recorded"
            ]
            content = {k: v for k, v in initial_manifest.items() if k != "manifest_digest"}
            digest = hashlib.sha256(
                (
                    json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    + "\n"
                ).encode()
            ).hexdigest()
            if (
                len(recorded) != 1
                or recorded[0].payload["manifest_digest"] != digest
                or initial_manifest["run_id"] != initial_evidence["run_id"]
                or initial_manifest["project_id"] != initial_evidence["project_id"]
                or initial_manifest["manifest_digest"] != initial_evidence["manifest_digest"]
                or initial_manifest["outcome"] != "evidence_blocked"
                or any(
                    item["relative_path"].startswith("reports/")
                    for item in initial_manifest["outputs"]
                )
                or initial_evidence["no_draft"] is not True
                or initial_evidence["report_file_count"] != 0
            ):
                raise ValueError("initial evidence drift")
            if (
                EventStore(project_root).stream_digest(
                    through_sequence=initial_evidence["event_count"]
                )
                != initial_evidence["event_stream_digest"]
            ):
                raise ValueError("initial events drift")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise HostSmokeScenarioError("缺失或不一致的恢复证据，不能猜测恢复") from exc
    else:
        if record_path.exists():
            raise HostSmokeScenarioError("已有恢复证据，请使用 --resume")
        initial = run_fixture_case(
            "host-smoke-v1",
            project_root=project_root,
            reports=list(case["reports"]),
            outputs=list(case["outputs"]),
            catalog_path=catalog_path,
        )
        if initial.run_result.outcome != "evidence_blocked" or initial.run_result.exit_code != 4:
            raise HostSmokeScenarioError("host-smoke-v1 初始运行未形成证据不足阻断")
        reports_root = project_root / "reports"
        if reports_root.is_dir() and any(path.is_file() for path in reports_root.rglob("*")):
            raise HostSmokeScenarioError("证据不足阻断后出现报告文件，违反不得生成草稿要求")

        initial_manifest_path = project_root / "manifests/current_run.json"
        initial_manifest = validate_run_manifest(project_root)
        initial_manifest_copy = project_root / "state/host-smoke-v1-initial-manifest.json"
        shutil.copyfile(initial_manifest_path, initial_manifest_copy)
        initial_event_store = EventStore(project_root)
        initial_evidence = {
            "run_id": initial.run_result.run_id,
            "project_id": initial.run_result.project_id,
            "outcome": "evidence_blocked",
            "exit_code": 4,
            "no_draft": True,
            "report_file_count": 0,
            "manifest_relative_path": initial_manifest_copy.relative_to(project_root).as_posix(),
            "manifest_sha256": _sha256(initial_manifest_path),
            "manifest_digest": initial_manifest["manifest_digest"],
            "event_count": len(initial_event_store.read_all()),
            "event_stream_digest": initial_event_store.stream_digest(),
            "contract": verify_project_workspace(project_root).contract.model_dump(mode="json"),
        }

        record = {
            "schema_version": "1.0",
            "case_id": "host-smoke-v1",
            "case_digest": _compute_case_digest(case),
            "initial": initial_evidence,
            "phase": "initial",
        }
        _write_json(record_path, record)

    verification = verify_project_workspace(project_root)
    contract = verification.contract
    if contract.project_id != initial_evidence["project_id"] or contract.model_dump(
        mode="json"
    ) != initial_evidence.get("contract"):
        raise HostSmokeScenarioError("恢复项目绑定不一致")
    universe_input = next(item for item in case["inputs"] if item["role"] == "universe_closure")
    if _sha256(project_root / CANONICAL_UNIVERSE_RELATIVE_PATH) != universe_input["sha256"]:
        raise HostSmokeScenarioError("恢复宇宙输入绑定不一致")
    # 当前协调器按一次运行归约图状态；显式重开事件与被重开的阻断代次
    # 使用同一运行身份，随后新的恢复运行再以独立 run_id 写入清单。
    executor = GraphExecutor(project_root, run_id=initial_evidence["run_id"])
    coordinator = PartialDeliveryCoordinator(executor)
    delivery = DeliveryContract(
        contract_id=contract.project_id,
        contract_version=contract.contract_version,
        reports=tuple(item.value for item in contract.reports),
        optional_formats=tuple(
            sorted(item.value for item in contract.outputs if item.value != "html")
        ),
    )
    now = datetime.now(UTC)
    view, _ = coordinator._validate_coordinator_events()
    prior_reopens = [
        event
        for event in view.project_reopens
        if event.run_id == initial_evidence["run_id"]
        and event.actor_id == "host_smoke_v1"
        and event.payload["guard_evidence"].get("user_material_accepted") is True
    ]
    if len(prior_reopens) > 1:
        raise HostSmokeScenarioError("恢复重开事件不唯一")
    reopen_event = (
        prior_reopens[0]
        if prior_reopens
        else coordinator.reopen_project(
            delivery,
            reason="user_material_accepted",
            actor_id="host_smoke_v1",
            occurred_at=now,
        ).submitted
    )
    if reopen_event is None:
        raise HostSmokeScenarioError("补件后未形成项目显式重开事件")
    coordinator.rebind_report(
        delivery,
        kind="A",
        old_object_id="report_A",
        new_object_id="report_A_v2",
        reason="user_material_accepted",
        actor_id="host_smoke_v1",
        occurred_at=now,
    )
    view, _ = coordinator._validate_coordinator_events()
    matches = [
        event
        for event in view.rebind_events.values()
        if event.payload["kind"] == "A"
        and event.payload["old_object_id"] == "report_A"
        and event.payload["new_object_id"] == "report_A_v2"
        and event.payload["reopen_event_id"] == reopen_event.event_id
        and event.payload["reopen_event_digest"] == reopen_event.event_digest
    ]
    if len(matches) != 1 or view.current_targets["A"] != "report_A_v2":
        raise HostSmokeScenarioError("恢复报告当前绑定不一致")
    rebind_event = matches[0]
    recovery = {
        "reason": "user_material_accepted",
        "reopen_event_id": reopen_event.event_id,
        "reopen_event_digest": reopen_event.event_digest,
        "rebind_event_id": rebind_event.event_id,
        "rebind_event_digest": rebind_event.event_digest,
        "input_relative_path": CANONICAL_REPORT_DATA_RELATIVE_PATH,
        "input_sha256": recovery_inputs[0]["sha256"],
    }
    if "recovery" in record and record["recovery"] != recovery:
        raise HostSmokeScenarioError("恢复事件绑定不一致")
    if "final" in record:
        manifest = validate_run_manifest(project_root)
        if (
            _sha256(project_root / "manifests/current_run.json")
            != record["final"]["manifest_sha256"]
            or manifest["run_id"] != record["final"]["run_id"]
            or manifest["case_digest"] != record["case_digest"]
            or _sha256(project_root / CANONICAL_REPORT_DATA_RELATIVE_PATH)
            != recovery["input_sha256"]
        ):
            raise HostSmokeScenarioError("完成恢复的当前清单或输入绑定不一致")
        result = _completed_result(project_root, record["case_digest"])
        if TypeAdapter(RunResult).validate_python(record["result"]) != result:
            raise HostSmokeScenarioError("完成恢复的结果与当前清单不一致")
        if _report_artifact_digests(manifest) != record["final"][
            "artifact_digests"
        ]:
            raise HostSmokeScenarioError("完成恢复的产物绑定不一致")
        return HostSmokeScenarioResult(result, record_path, record)
    record.update(recovery=recovery, phase="rebound")
    _write_json(record_path, record)

    case_dir = _resolve_case_dir(_get_case_root_base(catalog_path), "host-smoke-v1")
    recovery_source = case_dir / recovery_inputs[0]["path"]
    recovery_target = project_root / CANONICAL_REPORT_DATA_RELATIVE_PATH
    recovery_target.parent.mkdir(parents=True, exist_ok=True)
    if record.get("input_copied"):
        if (
            not recovery_target.is_file()
            or _sha256(recovery_target) != recovery_inputs[0]["sha256"]
        ):
            raise HostSmokeScenarioError("已补件输入摘要不一致")
    else:
        shutil.copyfile(recovery_source, recovery_target)
    if _sha256(recovery_target) != recovery_inputs[0]["sha256"]:
        raise HostSmokeScenarioError("恢复报告数据复制后摘要不一致")

    record.update(input_copied=True, phase="render")
    _write_json(record_path, record)

    universe_path = project_root / CANONICAL_UNIVERSE_RELATIVE_PATH
    input_hashes = {item["path"]: item["sha256"] for item in case["inputs"]}
    current_manifest = json.loads(
        (project_root / "manifests/current_run.json").read_text(encoding="utf-8")
    )
    result = (
        _completed_result(project_root, record["case_digest"])
        if (resume and current_manifest.get("outcome") == "completed")
        else run_project(
            project_root,
            resume=True,
            run_context=RunContext(
                project_root=project_root,
                contract=contract,
                capability_probe=StaticCapabilityProbe(),
                universe_input_path=universe_path,
                report_data_path=recovery_target,
                run_inputs={
                    "case_id": "host-smoke-v1",
                    "case_digest": _compute_case_digest(case),
                    **input_hashes,
                },
            ),
        )
    )
    if result.outcome != "completed" or result.exit_code != 0:
        raise HostSmokeScenarioError("补件恢复后未生成可验证的站点式 HTML")
    final_manifest = validate_run_manifest(project_root)
    if not _report_artifact_digests(final_manifest):
        raise HostSmokeScenarioError("恢复后没有新建或已验证复用的报告产物")
    verify_project_workspace(project_root)
    if final_manifest.get("case_id") != "host-smoke-v1":
        raise HostSmokeScenarioError("恢复后清单未绑定 host-smoke-v1")

    record = {
        "schema_version": "1.0",
        "case_id": "host-smoke-v1",
        "case_digest": _compute_case_digest(case),
        "initial": initial_evidence,
        "recovery": recovery,
        "phase": "completed",
        "input_copied": True,
        "result": json.loads(TypeAdapter(RunResult).dump_json(result)),
        "final": {
            "run_id": result.run_id,
            "outcome": "rendered",
            "exit_code": 0,
            "manifest_sha256": _sha256(project_root / "manifests/current_run.json"),
            "manifest_digest": final_manifest["manifest_digest"],
            "artifact_digests": _report_artifact_digests(final_manifest),
            "project_verified": True,
        },
    }
    record_path = project_root / SCENARIO_RECORD_RELATIVE
    _write_json(record_path, record)
    return HostSmokeScenarioResult(result, record_path, record)
