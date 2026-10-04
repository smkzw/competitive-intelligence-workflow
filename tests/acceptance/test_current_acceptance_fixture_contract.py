"""ci-r24-189：current-v2 当前封闭切片合同（新建版本身份，不重写冻结fixture）。

- 冻结的 `full-matrix-v1`、`fixtures/acceptance/catalog.yaml` 与合成
  `three-report-complete` 字节保持不变（历史 SHA 只读核验）；
- 新 `current-v2` 目录使用既有 catalog/schema/layout API 注册一个显式命名的
  当前候选案例，只更新版本身份，保留全部原始 A/B/C 行、ID、缺失/零值与安全语
  境；旧矩阵绝对坐标视图被拒绝并保存在迁移缺口工件中，不从 x/y 反推任何数值；
- 生产 loader 接受当前切片、拒绝把旧矩阵视图塞回当前输入；
- 真实项目阶段在合成独立上下文探针 seam 下端到端渲染候选 HTML，保持
  `pending_future_owner` 候选状态，不伪造快照锁定、真实评审或 RC 接受。

本套件只使用仓库内脱敏/合成输入。项目阶段会运行现有能力探针（包括
浏览器可用性），不作 Ego 实屏审美、临床或发布接受。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.acceptance_catalog import compute_case_digest
from ci_workflow.application.acceptance_runner import (
    load_acceptance_catalog,
    resolve_acceptance_case,
    run_catalog_input_stage,
    run_project_stage,
)
from ci_workflow.renderers.portal.report_a import load_report_a_data
from ci_workflow.renderers.portal.report_b import (
    ReportBPortalError,
    load_report_b_data,
    report_b_baseline_gate_failures,
)
from ci_workflow.renderers.portal.report_c import load_report_c_data

ROOT = Path(__file__).resolve().parents[2]
FROZEN_ROOT = ROOT / "fixtures" / "acceptance" / "full-matrix-v1"
FROZEN_CATALOG = ROOT / "fixtures" / "acceptance" / "catalog.yaml"
SYNTHETIC_B = (
    ROOT / "fixtures" / "synthetic" / "three-report-complete" / "inputs" / "report-b-data.json"
)
CURRENT_CATALOG = ROOT / "fixtures" / "acceptance" / "current-v2" / "catalog.yaml"
CURRENT_CASE = "current-v2"
CURRENT_ROOT = (
    ROOT / "fixtures" / "acceptance" / "current-v2" / "required-v12" / CURRENT_CASE
)
CURRENT_VERSION = "v2.0.0-current"
CURRENT_SNAPSHOT = "snapshot-current-v2-001"
LEGACY_VIEW_ARTIFACT = CURRENT_ROOT / "migration" / "legacy-matrix-view-rejected.json"
VERSION_PATTERN = re.compile(r"^v[0-9]+(?:\.[0-9]+){0,2}(?:-[a-z0-9][a-z0-9.-]*)?$")
IDENTITY_FIELDS = ("report_version", "report_snapshot_id")
CURRENT_INPUT_NAMES = (
    "report-a-data.json",
    "report-b-data.json",
    "report-c-data.json",
    "entity-counts.json",
    "gate-spec-expected.json",
    "coverage-set-expected.json",
    "run-binding-contract.json",
    "provenance.json",
)
# 历史字节只在只读核验时出现；任何迁移都不得改写它们。
FROZEN_SHA256 = {
    FROZEN_CATALOG: "499d644e76ff0a5f4b3cb3e12e722dd644b39da3684d896d9ee28534874777ca",
    FROZEN_ROOT / "inputs" / "report-b-data.json": (
        "1b18921b6584e37bf8da40b965a1cde9c9b738c0237b76ba2fab58ac5ed16eb9"
    ),
    SYNTHETIC_B: "b8a25df59bce07452f2a06cdc5205ac7b7ea6eb60b0ca64c366ddcb82583ebb8",
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_independent_context_probe(base: Path) -> Path:
    """合成独立上下文探针（测试 seam）：真实执行并返回合法回执，不是真实评审。"""

    probe = base / "independent-context-probe"
    probe.write_text(
        "#!/bin/sh\nprintf '%s\\n' '"
        + json.dumps(
            {
                "schema_version": "1.0",
                "available": True,
                "mechanism": "independent_session",
                "producer_context": "producer-main-run",
                "reviewer_context": "reviewer-synthetic-ri189",
                "invocation_id": "ri189-current-v2-probe-1",
            }
        )
        + "'\n",
        encoding="utf-8",
    )
    os.chmod(probe, 0o700)
    return probe


# ─── 冻结历史：只读字节与目录隔离 ──────────────────────────────────────────


def test_frozen_full_matrix_and_synthetic_sources_remain_byte_stable() -> None:
    for path, expected in FROZEN_SHA256.items():
        assert path.is_file(), f"冻结来源缺失：{path}"
        assert _sha256_file(path) == expected, f"冻结来源字节被改写：{path}"


def test_current_v2_is_an_isolated_slice_not_a_default_catalog_rewrite() -> None:
    default = load_acceptance_catalog()
    assert CURRENT_CASE not in default.cases
    assert "full-matrix-v1" in default.cases
    assert _sha256_file(default.path) == FROZEN_SHA256[FROZEN_CATALOG]


# ─── current-v2 catalog：显式命名案例与封闭版本身份 ────────────────────────


def test_current_v2_catalog_registers_named_case_with_closed_version_identity() -> None:
    catalog = load_acceptance_catalog(CURRENT_CATALOG)
    assert catalog.release_scope == "site_html_v1"
    assert catalog.allowed_formats == ("html",)
    assert CURRENT_CASE in catalog.approved_case_families
    assert CURRENT_CASE in catalog.cases

    resolved = resolve_acceptance_case(CURRENT_CASE, catalog)  # 默认布局推导，无 override
    assert resolved.fixture_root == CURRENT_ROOT.resolve()
    assert resolved.reports == ("A", "B", "C")
    assert resolved.formats == ("html",)
    assert {item.path for item in resolved.inputs} == {
        f"inputs/{name}" for name in CURRENT_INPUT_NAMES
    }
    assert {item.path for item in resolved.expected_files} == {"expected/current-v2.json"}

    case = catalog.cases[CURRENT_CASE]
    assert case["case_digest"] == compute_case_digest(case)
    assert VERSION_PATTERN.fullmatch(CURRENT_VERSION) is not None
    assert case["expected"]["outcome"] == "rendered"
    # 候选切片不得主张快照锁定或已接受状态。
    assert case["expected"]["state"] != "snapshot_locked"
    assert case["receipt"]["owner_status"] == "pending_future_owner"
    assert all(
        state["state"] == "pending_future_owner"
        for state in case["expected"]["report_states"].values()
    )

    for name in (
        "report-a-data.json",
        "report-b-data.json",
        "report-c-data.json",
        "entity-counts.json",
        "gate-spec-expected.json",
        "coverage-set-expected.json",
    ):
        payload = _read_json(CURRENT_ROOT / "inputs" / name)
        for field in IDENTITY_FIELDS:
            if field in payload:
                expected = CURRENT_VERSION if field == "report_version" else CURRENT_SNAPSHOT
                assert payload[field] == expected, f"{name} 的 {field} 未更新版本身份"


def test_current_v2_run_binding_contract_binds_new_identity_and_hashes() -> None:
    catalog = load_acceptance_catalog(CURRENT_CATALOG)
    resolved = resolve_acceptance_case(CURRENT_CASE, catalog)
    binding = _read_json(CURRENT_ROOT / "inputs" / "run-binding-contract.json")
    assert binding["case_id"] == CURRENT_CASE
    assert binding["report_version"] == CURRENT_VERSION
    assert binding["report_snapshot_id"] == CURRENT_SNAPSHOT
    assert binding["indication"] == resolved.indication
    assert binding["reports"] == ["A", "B", "C"]
    assert binding["formats"] == ["html"]
    rules = " ".join(binding["binding_rules_zh"])
    assert CURRENT_CASE in rules
    assert "full-matrix-v1" not in rules, "绑定规则不得再指向冻结案例身份"
    assert binding["input_hashes"], "运行绑定合同必须声明输入摘要"
    for path_text, digest in binding["input_hashes"].items():
        catalog_digest = resolved.input_digests.get(path_text)
        assert catalog_digest == digest, f"绑定摘要与 catalog 真值不一致：{path_text}"


# ─── 原始行/ID 等值与矩阵缺口工件 ──────────────────────────────────────────


def test_current_v2_raw_rows_and_ids_equal_frozen_source_apart_from_identity() -> None:
    for name in ("report-a-data.json", "report-b-data.json", "report-c-data.json"):
        current = _read_json(CURRENT_ROOT / "inputs" / name)
        frozen = _read_json(FROZEN_ROOT / "inputs" / name)
        drop = {"matrix_view"} if name == "report-b-data.json" else set()
        current_body = {k: v for k, v in current.items() if k not in (*IDENTITY_FIELDS, *drop)}
        frozen_body = {k: v for k, v in frozen.items() if k not in (*IDENTITY_FIELDS, *drop)}
        assert current_body == frozen_body, f"{name} 除版本身份/显式矩阵缺口外必须与冻结源一致"
        assert set(frozen) - set(current) == drop
        assert set(current) - set(frozen) == set()


def test_legacy_matrix_view_is_preserved_as_rejected_migration_gap() -> None:
    frozen_b = _read_json(FROZEN_ROOT / "inputs" / "report-b-data.json")
    legacy_view = frozen_b["matrix_view"]
    current_b = _read_json(CURRENT_ROOT / "inputs" / "report-b-data.json")
    assert "matrix_view" not in current_b, "当前输入不得携带未授权的旧矩阵覆盖"

    artifact = _read_json(LEGACY_VIEW_ARTIFACT)
    assert artifact["artifact_kind"] == "rejected-view-migration-gap"
    assert artifact["case_id"] == CURRENT_CASE
    assert artifact["source_case_id"] == "full-matrix-v1"
    assert artifact["source_input_path"] == "inputs/report-b-data.json"
    assert artifact["source_input_sha256"] == FROZEN_SHA256[
        FROZEN_ROOT / "inputs" / "report-b-data.json"
    ]
    assert artifact["source_view_sha256"] == _canonical_sha256(legacy_view)
    assert artifact["preserved_view"] == legacy_view
    assert artifact["legacy_row_count"] == len(legacy_view["comparison_rows"]) == 4
    assert artifact["legacy_row_ids"] == [
        row["row_id"] for row in legacy_view["comparison_rows"]
    ]
    missing = set(artifact["missing_projection_inputs"])
    assert missing == {
        "treatment_projection",
        "control_projection",
        "safety_projection",
        "size_projection",
    }
    reason = " ".join(str(artifact["reason_zh"]).split())
    assert "x_value" in reason and "y_value" in reason
    assert "未推断" in " ".join(str(artifact["not_inferred_zh"]).split())
    assert "科学 owner" in " ".join(str(artifact["next_owner_action_zh"]).split())


# ─── 生产 loader：接受当前切片，拒绝旧矩阵覆盖 ─────────────────────────────


def test_current_v2_loader_accepts_current_slice_and_rejects_legacy_matrix_override(
    tmp_path: Path,
) -> None:
    load_report_a_data(CURRENT_ROOT / "inputs" / "report-a-data.json")
    current_b = load_report_b_data(CURRENT_ROOT / "inputs" / "report-b-data.json")
    assert current_b.matrix_view is None
    assert report_b_baseline_gate_failures(current_b) == ()
    load_report_c_data(CURRENT_ROOT / "inputs" / "report-c-data.json")

    # 冻结源矩阵坐标不满足当前封闭投影合同。
    with pytest.raises(ReportBPortalError):
        load_report_b_data(FROZEN_ROOT / "inputs" / "report-b-data.json")

    # 把保留的旧视图原样塞回当前输入：生产 loader 必须拒绝，不得当作合法覆盖。
    tampered = _read_json(CURRENT_ROOT / "inputs" / "report-b-data.json")
    tampered["matrix_view"] = _read_json(FROZEN_ROOT / "inputs" / "report-b-data.json")[
        "matrix_view"
    ]
    tampered_path = tmp_path / "report-b-data.json"
    tampered_path.write_text(
        json.dumps(tampered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with pytest.raises(ReportBPortalError):
        load_report_b_data(tampered_path)


# ─── 项目阶段：候选 HTML 渲染（合成探针 seam），不伪造接受 ──────────────────


def test_current_v2_project_stage_renders_candidate_html_without_matrix_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = load_acceptance_catalog(CURRENT_CATALOG)
    resolved = resolve_acceptance_case(CURRENT_CASE, catalog)
    project_root = tmp_path / "current-v2-project"
    catalog_stage = run_catalog_input_stage(
        catalog_path=CURRENT_CATALOG, case_id=CURRENT_CASE, project_root=project_root
    )
    assert catalog_stage["case_id"] == CURRENT_CASE
    assert catalog_stage["case_digest"] == resolved.case_digest
    assert catalog_stage["inputs"] == resolved.input_digests
    assert catalog_stage["project_root_state"] == "absent"

    probe = _write_independent_context_probe(tmp_path)
    monkeypatch.setenv("CI_WORKFLOW_INDEPENDENT_CONTEXT_PROBE", str(probe))
    summary = run_project_stage(
        catalog=catalog,
        resolved=resolved,
        project_root=project_root,
        pre_rc_run_id="pre-rc-189-current-v2",
    )
    assert summary["outcome"] == "completed"
    assert summary["case_id"] == CURRENT_CASE
    assert summary["case_digest"] == resolved.case_digest
    assert summary["output_count"] == 3
    assert list(project_root.rglob("*.html")), "候选切片必须产出站点式 HTML"
    actual_manifest = _read_json(project_root / "manifests" / "current_run.json")
    assert actual_manifest["report_states"] == {
        kind: "rendered_unreviewed" for kind in ("A", "B", "C")
    }
    assert actual_manifest["format_states"] == {
        kind: {"html": "generated"} for kind in ("A", "B", "C")
    }
    assert not actual_manifest.get("scientific_review_receipts")
    assert not (project_root / "reports" / "current.json").exists()

    # 旧绝对坐标气泡覆盖不得进入当次产物（底层临床行仍按普通当前渲染器输出）。
    site_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in project_root.rglob("*")
        if path.is_file() and path.suffix in {".js", ".html", ".json", ".css"}
    )
    assert "matrix-apply-teae" not in site_text
    assert '"matrix_view"' not in site_text
    # 候选状态：catalog 期望仍为待未来 owner，未主张快照锁定/发布接受。
    case = catalog.cases[CURRENT_CASE]
    assert case["expected"]["state"] == "pending_future_owner"
    assert case["receipt"]["owner_status"] == "pending_future_owner"
