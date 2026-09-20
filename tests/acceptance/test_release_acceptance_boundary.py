"""发布接受边界回归：rendered_unreviewed 预览路径不得产生可接受后继。

合同来源：v1.3 发布接受边界与 R2 checkpoint
``checkpoint_20260905_r2_bc_science_wiring.md``：report-data /
``rendered_unreviewed`` 快捷路径仅限开发预览，不得生成可被科学、视觉或
发布（RC）接受的后继；运行清单缺少报告状态记录时必须失败关闭。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_visual_acceptance as _va

from ci_workflow.application.acceptance_boundary import (
    ACCEPTED_ORIGIN_REPORT_STATES,
    PREVIEW_ONLY_REPORT_STATES,
    AcceptanceBoundaryError,
    require_accepted_origin_report_states,
)
from ci_workflow.application.real_source_acceptance import _verify_runtime_bindings
from ci_workflow.application.run_service import (
    RunContext,
    run_project,
    validate_run_manifest,
)
from ci_workflow.application.visual_acceptance import (
    VisualAcceptanceError,
    accept_visual_artifact,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.storage.event_store import EventStore
from ci_workflow.storage.manifest_store import ArtifactManifest

ROOT = Path(__file__).resolve().parents[2]
_PREVIEW_REPORT_DATA = (
    ROOT / "fixtures" / "positive" / "b-pnh" / "inputs" / "report-data.json"
)


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _prepare_preview_b_project(tmp_path: Path) -> tuple[Path, ArtifactManifest, Path, Path, Path]:
    """经真实管线运行 report-data 预览路径并准备完整视觉验收证据。

    输入复用 b-pnh fixture 的报告数据包，但去掉调用方自述的
    ``report_snapshot_id``：预览路径由渲染器自行锁定快照。该项目的当前
    运行报告状态是 ``rendered_unreviewed``：只可用于开发预览，任何视觉
    验收尝试都必须失败关闭。
    """

    report_data = _load(_PREVIEW_REPORT_DATA)
    report_data.pop("report_snapshot_id", None)
    contract = create_project_contract(
        indication="阵发性睡眠性血红蛋白尿",
        reports=["B"],
        outputs=["html"],
        timezone="Asia/Shanghai",
        cutoff="2026-07-31",
        created_at=datetime.fromisoformat("2026-08-30T09:00:00+08:00"),
    )
    from ci_workflow.application.project_service import create_project_workspace

    project = create_project_workspace(tmp_path / "b-preview-boundary", contract)
    data_path = project / "evidence" / "library" / "report-data.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(report_data, ensure_ascii=False), encoding="utf-8")
    from ci_workflow.application.capability_preflight import StaticCapabilityProbe

    result = run_project(
        project,
        capability_probe=StaticCapabilityProbe(),
        run_context=RunContext(
            project_root=project,
            contract=contract,
            report_data_path=data_path,
        ),
    )
    assert result.outcome == "completed"
    run_manifest = validate_run_manifest(project)
    assert run_manifest["report_states"] == {"B": "rendered_unreviewed"}
    output = next(
        row
        for row in run_manifest["outputs"]
        if str(row["relative_path"]).endswith("html.manifest.json")
    )
    candidate_path = project / str(output["relative_path"])
    candidate = ArtifactManifest.model_validate(_load(candidate_path))

    from ci_workflow.domain.enums import ReportKind
    from ci_workflow.qc.browser import load_locked_sitemap_source
    from ci_workflow.storage.snapshot_store import compute_locked_snapshot

    source = load_locked_sitemap_source(project, ReportKind.B, candidate.report_version)
    snapshot_sha256 = compute_locked_snapshot(
        kind="report",
        report="B",
        manifest=source.snapshot.model_dump(mode="json"),
    ).sha256
    plan = _va._plan(candidate, source.snapshot, snapshot_sha256)
    plan_path = project / "reviews" / "visual-plan.json"
    evidence_path = project / "reviews" / "render-evidence.json"
    verdict_path = project / "reviews" / "visual-verdict.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    now = max(datetime.now(UTC), candidate.artifact.modified_at.astimezone(UTC))
    evidence = _va._evidence(
        candidate, _va.visual_contract_digest(plan), now + timedelta(seconds=1)
    )
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
    verdict = _va._verdict(
        candidate,
        _va.visual_contract_digest(plan),
        _va.visual_contract_digest(evidence),
        now + timedelta(seconds=2),
    )
    verdict_path.write_text(json.dumps(verdict, ensure_ascii=False), encoding="utf-8")
    return project, candidate, plan_path, evidence_path, verdict_path


def _assert_no_accepted_successor(project: Path) -> None:
    """断言没有写入任何已接受继承清单，也没有进入 passed/delivery_ready。"""

    artifact_dir = project / "manifests" / "artifacts"
    if artifact_dir.is_dir():
        for path in artifact_dir.glob("*.json"):
            payload = _load(path)
            assert payload.get("status") != "accepted"
            assert payload.get("supersedes_manifest_id") is None
    events = EventStore(project).read_all()
    for event in events:
        if event.event_type != "graph.transition.accepted":
            continue
        if event.payload.get("family") != "format_artifact":
            continue
        assert event.payload.get("to_state") not in {"passed", "delivery_ready"}


def test_visual_acceptance_rejects_rendered_unreviewed_preview_run(
    tmp_path: Path,
) -> None:
    """预览运行（rendered_unreviewed）即使证据齐全也不得获得视觉接受后继。"""

    project, candidate, plan_path, evidence_path, verdict_path = _prepare_preview_b_project(
        tmp_path
    )
    with pytest.raises(VisualAcceptanceError, match="rendered_unreviewed"):
        accept_visual_artifact(
            project,
            version=candidate.report_version,
            visual_plan_path=plan_path,
            render_evidence_path=evidence_path,
            verification_reference_path=verdict_path,
        )
    _assert_no_accepted_successor(project)


# ─── 真实来源精确验收的报告状态绑定 ────────────────────────────────────────


def _bindings_run_manifest(report_states: object) -> dict[str, object]:
    payload: dict[str, object] = {}
    if report_states is not None:
        payload["report_states"] = report_states
    return payload


def test_exact_acceptance_fails_closed_without_report_states() -> None:
    """运行清单缺少 report_states 时必须失败关闭，不得以字节链替代科学来源。"""

    with pytest.raises(Exception, match="report_states") as excinfo:
        _verify_runtime_bindings(
            _bindings_run_manifest(None),  # type: ignore[arg-type]
            report="B",
            manifest=SimpleNamespace(report_snapshot_id="report-snapshot-x"),
            manifest_digest="a" * 64,
        )
    assert not isinstance(excinfo.value, AssertionError)


def test_exact_acceptance_rejects_rendered_unreviewed_state() -> None:
    """rendered_unreviewed 是开发预览状态，精确验收必须点名拒绝。"""

    with pytest.raises(Exception, match="rendered_unreviewed"):
        _verify_runtime_bindings(
            _bindings_run_manifest({"B": "rendered_unreviewed"}),  # type: ignore[arg-type]
            report="B",
            manifest=SimpleNamespace(report_snapshot_id="report-snapshot-x"),
            manifest_digest="a" * 64,
        )


def test_exact_acceptance_rejects_caller_declared_state() -> None:
    """未在合同词表中声明的调用方自述状态不可作为接受来源。"""

    with pytest.raises(Exception, match="caller-asserted"):
        _verify_runtime_bindings(
            _bindings_run_manifest({"B": "caller-asserted-accepted"}),  # type: ignore[arg-type]
            report="B",
            manifest=SimpleNamespace(report_snapshot_id="report-snapshot-x"),
            manifest_digest="a" * 64,
        )


def test_exact_acceptance_rejects_missing_report_entry() -> None:
    """report_states 缺少当前报告条目与缺失整体同样失败关闭。"""

    with pytest.raises(Exception, match="report_states"):
        _verify_runtime_bindings(
            _bindings_run_manifest({"A": "snapshot_locked"}),  # type: ignore[arg-type]
            report="B",
            manifest=SimpleNamespace(report_snapshot_id="report-snapshot-x"),
            manifest_digest="a" * 64,
        )


def test_exact_acceptance_rejects_malformed_report_states() -> None:
    """report_states 不是对象时必须失败关闭。"""

    with pytest.raises(Exception, match="report_states"):
        _verify_runtime_bindings(
            _bindings_run_manifest("rendered_unreviewed"),  # type: ignore[arg-type]
            report="B",
            manifest=SimpleNamespace(report_snapshot_id="report-snapshot-x"),
            manifest_digest="a" * 64,
        )


def test_exact_acceptance_accepts_scientific_candidate_state() -> None:
    """新鲜来源科学候选状态（scientifically_reviewed_rendered_candidate）可接受。"""

    _verify_runtime_bindings(
        _bindings_run_manifest({"B": "scientifically_reviewed_rendered_candidate"}),  # type: ignore[arg-type]
        report="B",
        manifest=SimpleNamespace(report_snapshot_id="report-snapshot-x"),
        manifest_digest="a" * 64,
    )


def test_exact_acceptance_accepts_snapshot_locked_state() -> None:
    """已锁定报告快照状态（snapshot_locked）可接受。"""

    _verify_runtime_bindings(
        _bindings_run_manifest({"B": "snapshot_locked"}),  # type: ignore[arg-type]
        report="B",
        manifest=SimpleNamespace(report_snapshot_id="report-snapshot-x"),
        manifest_digest="a" * 64,
    )


# ─── 类型化边界合同词表 ───────────────────────────────────────────────────


def test_boundary_vocabulary_is_typed_and_disjoint() -> None:
    """接受来源状态与仅限预览状态是封闭词表，且互不相交。"""

    assert frozenset(
        {"scientifically_reviewed_rendered_candidate", "snapshot_locked"}
    ) == ACCEPTED_ORIGIN_REPORT_STATES
    assert frozenset(
        {"rendered_unreviewed", "recovery_required", "evidence_blocked"}
    ) == PREVIEW_ONLY_REPORT_STATES
    assert not ACCEPTED_ORIGIN_REPORT_STATES & PREVIEW_ONLY_REPORT_STATES


def test_boundary_require_returns_verified_states() -> None:
    """通过校验时返回逐报告的核验状态映射。"""

    verified = require_accepted_origin_report_states(
        {"report_states": {"B": "scientifically_reviewed_rendered_candidate"}},
        reports=("B",),
    )
    assert verified == {"B": "scientifically_reviewed_rendered_candidate"}


def test_boundary_require_checks_every_declared_report() -> None:
    """多报告验收必须逐报告核验，任一预览状态都失败关闭。"""

    with pytest.raises(AcceptanceBoundaryError, match="rendered_unreviewed"):
        require_accepted_origin_report_states(
            {
                "report_states": {
                    "B": "scientifically_reviewed_rendered_candidate",
                    "C": "rendered_unreviewed",
                }
            },
            reports=("B", "C"),
        )


def test_boundary_require_fails_closed_on_missing_record() -> None:
    """缺少 report_states 记录与预览状态同样失败关闭。"""

    with pytest.raises(AcceptanceBoundaryError, match="report_states"):
        require_accepted_origin_report_states({}, reports=("B",))


def test_boundary_require_fails_closed_on_non_mapping_record() -> None:
    """report_states 不是对象时失败关闭。"""

    with pytest.raises(AcceptanceBoundaryError, match="report_states"):
        require_accepted_origin_report_states(
            {"report_states": ["snapshot_locked"]}, reports=("B",)
        )
