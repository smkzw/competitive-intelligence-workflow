"""report-data 预览快照合同：调用方声明不被信任，预览自锁定且不可接受。

合同来源：v1.3 发布接受边界与 R2 重基线工作项（2026-09-05）：

- 调用方在 report-data 中声明的 ``report_snapshot_id`` 若在项目快照库中
  不存在，则该声明不被信任：预览路径按真实数据字节确定性自锁定快照；
- 已锁定后的运行保持 ``rendered_unreviewed``，不得进入视觉、真实来源或
  RC 接受（``require_accepted_origin_report_states`` 必须逐报告失败关闭）；
- 声明的快照在项目中存在但字节不可信或身份不一致时，仍保持失败关闭；
- 覆盖单报告（B/C 直连 report-data）与 three-report-complete 多报告路径。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.acceptance_boundary import (
    AcceptanceBoundaryError,
    require_accepted_origin_report_states,
)
from ci_workflow.application.fixture_runner import run_fixture_case
from ci_workflow.application.run_service import (
    RunContext,
    run_project,
    validate_run_manifest,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.storage.snapshot_store import ReportSnapshotManifest, compute_locked_snapshot

ROOT = Path(__file__).resolve().parents[2]

_B_REPORT_DATA = ROOT / "fixtures" / "positive" / "b-pnh" / "inputs" / "report-data.json"
_C_REPORT_DATA = (
    ROOT / "fixtures" / "positive" / "c-atopic-dermatitis" / "inputs" / "report-data.json"
)
_THREE_REPORT_DECLARED_SNAPSHOT_ID = "snapshot-three-report-complete-001"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _prepare_preview_project(
    tmp_path: Path,
    *,
    name: str,
    data_path: Path,
    indication: str,
    cutoff: str,
    created_at: str,
    reports: list[str],
) -> tuple[Path, str]:
    """按真实 fixture 数据建立预览项目，保留调用方自述的快照声明。"""

    report_data = _load(data_path)
    declared_snapshot_id = str(report_data["report_snapshot_id"])
    contract = create_project_contract(
        indication=indication,
        reports=reports,
        outputs=["html"],
        timezone="Asia/Shanghai",
        cutoff=cutoff,
        created_at=datetime.fromisoformat(created_at),
    )
    from ci_workflow.application.project_service import create_project_workspace

    project = create_project_workspace(tmp_path / name, contract)
    target = project / "evidence" / "library" / "report-data.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report_data, ensure_ascii=False), encoding="utf-8")
    run_project(
        project,
        run_context=RunContext(
            project_root=project,
            contract=contract,
            report_data_path=target,
        ),
    )
    return project, declared_snapshot_id


def _artifact_manifest(project: Path, report: str) -> tuple[Any, dict[str, Any]]:
    manifest = validate_run_manifest(project)
    output = next(
        row
        for row in manifest["outputs"]
        if str(row["relative_path"]).endswith("html.manifest.json")
        and f"/{report}/" in str(row["relative_path"])
    )
    artifact = json.loads((project / str(output["relative_path"])).read_text(encoding="utf-8"))
    return artifact, manifest


def _assert_self_locked_preview_snapshot(
    project: Path,
    report: str,
    declared_snapshot_id: str,
) -> None:
    """预览产物必须绑定项目内真实自锁定快照，且运行保持不可接受状态。"""

    artifact, run_manifest = _artifact_manifest(project, report)
    locked_snapshot_id = str(artifact["report_snapshot_id"])
    # 调用方声明未被信任：产物绑定的是自锁定快照，不是声明的幽灵标识。
    assert locked_snapshot_id != declared_snapshot_id
    snapshot_path = project / "snapshots" / "reports" / report / f"{locked_snapshot_id}.json"
    assert snapshot_path.is_file()
    payload = _load(snapshot_path)
    assert payload["project_id"] == artifact["project_id"]
    assert payload["report_version"] == artifact["report_version"]
    # 自锁定快照与产物字节绑定：同一规范算法重算身份一致。
    recomputed = compute_locked_snapshot(
        kind="report",
        report=report,  # type: ignore[arg-type]
        manifest=payload,
    )
    assert recomputed.snapshot_id == locked_snapshot_id
    # 运行保持 rendered_unreviewed，任何接受来源核验都必须失败关闭。
    report_states = run_manifest["report_states"]
    assert report_states == {report: "rendered_unreviewed"}
    with pytest.raises(AcceptanceBoundaryError, match="rendered_unreviewed"):
        require_accepted_origin_report_states(run_manifest, reports=(report,))  # type: ignore[arg-type]


def test_single_b_preview_ignores_snapshot_declaration_missing_from_project(
    tmp_path: Path,
) -> None:
    """单报告 B：声明的快照不在项目内时不被信任，预览自锁定并保持不可接受。"""

    project, declared = _prepare_preview_project(
        tmp_path,
        name="b-preview-snapshot-contract",
        data_path=_B_REPORT_DATA,
        indication="阵发性睡眠性血红蛋白尿",
        cutoff="2026-07-31",
        created_at="2026-08-30T09:00:00+08:00",
        reports=["B"],
    )
    _assert_self_locked_preview_snapshot(project, "B", declared)


def test_single_c_preview_ignores_snapshot_declaration_missing_from_project(
    tmp_path: Path,
) -> None:
    """单报告 C：声明的快照不在项目内时不被信任，预览自锁定并保持不可接受。"""

    project, declared = _prepare_preview_project(
        tmp_path,
        name="c-preview-snapshot-contract",
        data_path=_C_REPORT_DATA,
        indication="中重度特应性皮炎",
        cutoff="2026-08-30",
        created_at="2026-08-30T09:00:00+08:00",
        reports=["C"],
    )
    _assert_self_locked_preview_snapshot(project, "C", declared)


def test_three_report_complete_preview_self_locks_snapshots_and_stays_unreviewed(
    tmp_path: Path,
) -> None:
    """three-report-complete：A/B/C 全部自锁定快照并保持 rendered_unreviewed。"""

    result = run_fixture_case(
        "three-report-complete",
        project_root=tmp_path / "三报告预览",
        reports=["A", "B", "C"],
        outputs=["html"],
    )
    assert result.run_result.outcome == "completed"
    run_manifest = validate_run_manifest(tmp_path / "三报告预览")
    assert run_manifest["report_states"] == {
        "A": "rendered_unreviewed",
        "B": "rendered_unreviewed",
        "C": "rendered_unreviewed",
    }
    for report in ("B", "C"):
        artifact, _ = _artifact_manifest(tmp_path / "三报告预览", report)
        assert artifact["report_snapshot_id"] != _THREE_REPORT_DECLARED_SNAPSHOT_ID, (
            f"{report} 类预览产物不得信任声明但项目中不存在的快照标识"
        )
        snapshot_path = (
            tmp_path
            / "三报告预览"
            / "snapshots"
            / "reports"
            / report
            / f"{artifact['report_snapshot_id']}.json"
        )
        assert snapshot_path.is_file()
    with pytest.raises(AcceptanceBoundaryError, match="rendered_unreviewed"):
        require_accepted_origin_report_states(
            run_manifest,
            reports=("A", "B", "C"),
        )


def _write_declared_snapshot_file(
    project: Path,
    declared_snapshot_id: str,
    encoded: bytes,
) -> None:
    snapshot_dir = project / "snapshots" / "reports" / "B"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / f"{declared_snapshot_id}.json").write_bytes(encoded)


def _run_b_preview_with_declared_snapshot(
    tmp_path: Path,
    *,
    name: str,
    declared_snapshot_id: str,
) -> Any:
    report_data = _load(_B_REPORT_DATA)
    report_data["report_snapshot_id"] = declared_snapshot_id
    contract = create_project_contract(
        indication="阵发性睡眠性血红蛋白尿",
        reports=["B"],
        outputs=["html"],
        timezone="Asia/Shanghai",
        cutoff="2026-07-31",
        created_at=datetime.fromisoformat("2026-08-30T09:00:00+08:00"),
    )
    from ci_workflow.application.project_service import create_project_workspace

    project = create_project_workspace(tmp_path / name, contract)
    target = project / "evidence" / "library" / "report-data.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report_data, ensure_ascii=False), encoding="utf-8")
    return project, RunContext(
        project_root=project,
        contract=contract,
        report_data_path=target,
    )


def test_declared_snapshot_with_unbound_identity_fails_closed(tmp_path: Path) -> None:
    """声明的快照存在但内容身份与声明不一致：保持失败关闭，不回退预览。"""

    declared = "snapshot-declared-unbound-001"
    project, run_context = _run_b_preview_with_declared_snapshot(
        tmp_path, name="b-unbound-snapshot", declared_snapshot_id=declared
    )
    impostor = ReportSnapshotManifest(
        schema_version="1.0",
        project_id=str(run_context.contract.project_id),
        contract_version=run_context.contract.contract_version,
        report="B",
        report_version="v-fixture-b-pnh-001",
        data_cutoff=datetime.fromisoformat("2026-07-31T00:00:00+08:00"),
        evidence_snapshot_id="evidence-impostor",
        claim_snapshot_id="claim-impostor",
        coverage_set_id="coverage-impostor",
        claim_ids=("claim-impostor-1",),
        created_at=datetime.now(UTC),
    )
    _write_declared_snapshot_file(project, declared, impostor.model_dump_json().encode("utf-8"))
    result = run_project(project, run_context=run_context)
    assert result.outcome == "failed"
    assert not list((project / "reports" / "B").rglob("html.manifest.json"))


def test_declared_snapshot_with_corrupt_bytes_fails_closed(tmp_path: Path) -> None:
    """声明的快照存在但字节损坏：保持失败关闭，不得静默换用自锁定快照。"""

    declared = "snapshot-declared-corrupt-001"
    project, run_context = _run_b_preview_with_declared_snapshot(
        tmp_path, name="b-corrupt-snapshot", declared_snapshot_id=declared
    )
    _write_declared_snapshot_file(project, declared, b"{ not valid json")
    result = run_project(project, run_context=run_context)
    assert result.outcome == "failed"
    assert not list((project / "reports" / "B").rglob("html.manifest.json"))
