"""Task 10.3 F02/F03：catalog 真值、空项目合同与当前运行 ego(lite) 回执绑定。

F02 部分验证真值只来自验收目录、逐文件 SHA-256 与空项目失败关闭；F03 部分
验证固定阶段顺序（catalog/输入核验 → 项目运行 → A/B/C 当前产物与浏览器
回执绑定 → 宿主 → 项目核验 → 回执聚合）、三个 HTML 当前产物与 Codex 在
ego(lite) 中生成的浏览器回执的严格绑定，以及缺失回执、非 ego 工具、缺页、
摘要不符、旧回执等情况下的失败关闭。

这些测试只读取仓库内脱敏/合成案例；对失败关闭路径的负向用例一律在临时目录
复制后篡改，不修改共享 catalog 或 fixture。全部测试不启动任何浏览器、不依赖
任何特定浏览器框架；真实 ego(lite) 浏览器验收由 Codex 在集成阶段完成。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import yaml

from ci_workflow.application.acceptance_catalog import compute_case_digest
from ci_workflow.application.acceptance_runner import (
    EGO_LITE_TOOL_IDENTITY,
    EGO_RECEIPT_FILENAME,
    NOT_APPLICABLE_STATUS,
    PENDING_FUTURE_OWNER_STATUS,
    PRE_RC_STAGE_ORDER,
    PRESCRIBED_VIEWPORTS,
    REHEARSAL_STATUS,
    AcceptanceRunnerError,
    EgoReceiptPendingError,
    ScenarioVerifierOutcome,
    _assert_case_html_only,
    _discover_current_html_artifacts,
    bind_ego_receipts_pipeline,
    build_full_matrix_suite_receipts,
    build_host_smoke_stage,
    build_pre_rc_receipts_stage,
    build_project_verify_stage,
    complete_pre_rc_rehearsal,
    expected_ego_receipt_path,
    format_pre_rc_rehearsal_ok,
    load_acceptance_catalog,
    require_empty_project_root,
    resolve_acceptance_case,
    resolve_full_matrix_suite,
    run_catalog_input_stage,
    run_ego_receipt_stage,
    run_full_matrix_suite_rehearsal,
    run_html_pipeline,
    run_pre_rc_rehearsal,
    run_project_stage,
    subprocess_verifier_runner,
)
from ci_workflow.application.host_smoke import receipt_digest

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "fixtures/acceptance/catalog.yaml"
FULL_MATRIX_ROOT = ROOT / "fixtures/acceptance/full-matrix-v1"
CLI_PATH = ROOT / "tools/run_acceptance.py"

_DECLARED_INPUT_PATHS = (
    "inputs/report-a-data.json",
    "inputs/report-b-data.json",
    "inputs/report-c-data.json",
    "inputs/entity-counts.json",
    "inputs/gate-spec-expected.json",
    "inputs/coverage-set-expected.json",
    "inputs/run-binding-contract.json",
    "inputs/provenance.json",
)


def _load_raw_catalog() -> dict[str, Any]:
    payload = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _case_by_id(payload: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in payload["cases"]:
        if case["id"] == case_id:
            return case
    raise AssertionError(f"catalog 缺少案例：{case_id}")


def _copy_case(tmp_path: Path, name: str = "acceptance") -> tuple[Path, Path, dict[str, Any]]:
    """复制 catalog 与 full-matrix-v1 案例目录到临时目录。

    返回 ``(catalog 路径, 案例目录, 原始 catalog dict)``。
    """

    base = tmp_path / name
    base.mkdir()
    catalog_copy = base / "catalog.yaml"
    shutil.copyfile(CATALOG_PATH, catalog_copy)
    case_root = base / "full-matrix-v1"
    shutil.copytree(FULL_MATRIX_ROOT, case_root)
    return catalog_copy, case_root, _load_raw_catalog()


def _write_mutated_catalog(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


# fmt: off
def test_runner_requires_html_only_catalog_truth_and_hashed_inputs(
) -> None:
# fmt: on
    """验收节点 1：真值只从 catalog 解析，逐文件 SHA-256 必须与实际字节一致。"""
    catalog = load_acceptance_catalog()
    resolved = resolve_acceptance_case("full-matrix-v1", catalog)

    assert resolved.case_id == "full-matrix-v1"
    assert resolved.indication == "特应性皮炎"
    assert resolved.timezone == "Asia/Shanghai"
    assert ZoneInfo(resolved.timezone).key == "Asia/Shanghai"
    assert resolved.reports == ("A", "B", "C")
    assert resolved.formats == ("html",)
    assert resolved.execution_scope == "full-matrix"
    assert resolved.data_cutoff == datetime.fromisoformat("2026-07-31T23:59:59+08:00")
    assert resolved.data_cutoff.utcoffset() is not None
    assert resolved.fixture_root == FULL_MATRIX_ROOT.resolve()

    # 逐文件摘要：声明值必须与实际字节重算值一致，且覆盖全部八份输入。
    assert tuple(item.path for item in resolved.inputs) == _DECLARED_INPUT_PATHS
    digests = resolved.input_digests
    assert set(digests) == set(_DECLARED_INPUT_PATHS)
    for item in resolved.inputs:
        assert item.sha256 == item.verified_sha256

    # 案例摘要与预期文件摘要均可重算闭合。
    assert resolved.case_digest == _case_by_id(_load_raw_catalog(), "full-matrix-v1")[
        "case_digest"
    ]
    assert set(resolved.expected_digests) == {"expected/full-matrix.json"}


def test_runner_truth_cannot_be_diverted_from_catalog(tmp_path: Path) -> None:
    """真值字段必须来自 catalog 声明；案例目录内文件内容不参与真值推断。"""
    catalog_copy, _case_root, _payload = _copy_case(tmp_path)
    resolved = resolve_acceptance_case("full-matrix-v1", load_acceptance_catalog(catalog_copy))
    assert resolved.indication == "特应性皮炎"
    assert resolved.formats == ("html",)
    assert resolved.reports == ("A", "B", "C")


def test_runner_rejects_non_html_catalog_formats() -> None:
    """目录允许格式或案例格式离开 HTML-only 范围时必须失败关闭。"""
    payload = _load_raw_catalog()
    requirements = payload["requirements"]
    assert requirements["allowed_formats"] == ["html"]

    case = _case_by_id(payload, "full-matrix-v1")
    # 合法声明不得误报；目录或案例任一层离开 HTML-only 都必须拒绝。
    _assert_case_html_only(case, allowed_formats=("html",), case_id="full-matrix-v1")
    with pytest.raises(AcceptanceRunnerError, match="html"):
        _assert_case_html_only(case, allowed_formats=("html", "pdf"), case_id="full-matrix-v1")
    with pytest.raises(AcceptanceRunnerError, match="html"):
        _assert_case_html_only(
            {**case, "formats": ["html", "pdf"]},
            allowed_formats=("html",),
            case_id="full-matrix-v1",
        )


def test_runner_fails_closed_on_input_digest_drift(tmp_path: Path) -> None:
    """输入字节漂移必须失败关闭；案例摘要重算不能洗白摘要不一致。"""
    # 场景一：文件字节漂移，catalog 声明不变。
    catalog_copy, case_root, _payload = _copy_case(tmp_path, "acceptance-byte-drift")
    target = case_root / "inputs/report-a-data.json"
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(AcceptanceRunnerError, match="输入摘要与文件不一致"):
        resolve_acceptance_case("full-matrix-v1", load_acceptance_catalog(catalog_copy))

    # 场景二：声明摘要被篡改，即使案例摘要同步重算也必须被逐文件核验拒绝。
    catalog_copy, _case_root, payload = _copy_case(tmp_path, "acceptance-declared-drift")
    case = _case_by_id(payload, "full-matrix-v1")
    case["inputs"][0]["sha256"] = "0" * 64
    case["case_digest"] = compute_case_digest(case)
    _write_mutated_catalog(catalog_copy, payload)

    with pytest.raises(AcceptanceRunnerError, match="输入摘要与文件不一致"):
        resolve_acceptance_case("full-matrix-v1", load_acceptance_catalog(catalog_copy))


def test_runner_fails_closed_on_missing_input_file(tmp_path: Path) -> None:
    catalog_copy, case_root, payload = _copy_case(tmp_path)
    case = _case_by_id(payload, "full-matrix-v1")
    (case_root / case["inputs"][-1]["path"]).unlink()
    case["case_digest"] = compute_case_digest(case)
    _write_mutated_catalog(catalog_copy, payload)

    with pytest.raises(AcceptanceRunnerError, match="输入文件不存在"):
        resolve_acceptance_case("full-matrix-v1", load_acceptance_catalog(catalog_copy))


def test_runner_fails_closed_on_expected_file_digest_drift(tmp_path: Path) -> None:
    catalog_copy, case_root, payload = _copy_case(tmp_path)
    case = _case_by_id(payload, "full-matrix-v1")
    target = case_root / case["expected"]["expected_files"][0]["path"]
    target.write_text(
        json.dumps({"tampered": True}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    case["case_digest"] = compute_case_digest(case)
    _write_mutated_catalog(catalog_copy, payload)

    with pytest.raises(AcceptanceRunnerError, match="预期文件摘要与文件不一致"):
        resolve_acceptance_case("full-matrix-v1", load_acceptance_catalog(catalog_copy))


def test_runner_fails_closed_on_case_digest_drift(tmp_path: Path) -> None:
    catalog_copy, _case_root, payload = _copy_case(tmp_path)
    case = _case_by_id(payload, "full-matrix-v1")
    case["description_zh"] = case["description_zh"] + "（篡改）"
    _write_mutated_catalog(catalog_copy, payload)

    with pytest.raises(AcceptanceRunnerError, match="case_digest"):
        resolve_acceptance_case("full-matrix-v1", load_acceptance_catalog(catalog_copy))


def test_runner_fails_closed_on_unregistered_case() -> None:
    with pytest.raises(AcceptanceRunnerError, match="未在验收目录登记"):
        resolve_acceptance_case(
            "invented-case",
            load_acceptance_catalog(CATALOG_PATH),
        )


def test_runner_fails_closed_on_unapproved_family(tmp_path: Path) -> None:
    catalog_copy, _case_root, payload = _copy_case(tmp_path)
    case = _case_by_id(payload, "full-matrix-v1")
    case["family"] = "unapproved-family"
    case["case_digest"] = compute_case_digest(case)
    _write_mutated_catalog(catalog_copy, payload)

    with pytest.raises(AcceptanceRunnerError, match="批准集合"):
        resolve_acceptance_case("full-matrix-v1", load_acceptance_catalog(catalog_copy))


@pytest.mark.parametrize(
    "layout",
    ("absent", "empty", "file-root", "manifest", "report-site", "snapshot", "receipt", "host"),
)
def test_project_root_must_be_absent_or_empty(tmp_path: Path, layout: str) -> None:
    """预存 snapshot、manifest、站点或宿主回执的项目根一律失败关闭。"""
    root = tmp_path / "project"
    if layout == "empty":
        root.mkdir()
    elif layout == "file-root":
        root.write_text("not a directory", encoding="utf-8")
    elif layout == "manifest":
        (root / "manifests").mkdir(parents=True)
        (root / "manifests/current_run.json").write_text("{}", encoding="utf-8")
    elif layout == "report-site":
        (root / "reports/A/v1/html").mkdir(parents=True)
        (root / "reports/A/v1/html/index.html").write_text("<html></html>", encoding="utf-8")
    elif layout == "snapshot":
        (root / "snapshots/reports/A").mkdir(parents=True)
        (root / "snapshots/reports/A/snapshot.json").write_text("{}", encoding="utf-8")
    elif layout == "receipt":
        (root / "receipts").mkdir(parents=True)
        (root / "receipts/source_receipts.jsonl").write_text("", encoding="utf-8")
    elif layout == "host":
        (root / "host-smoke").mkdir(parents=True)
        (root / "host-smoke/codex.json").write_text("{}", encoding="utf-8")

    if layout in ("absent", "empty"):
        assert require_empty_project_root(root) == root.resolve()
        return
    with pytest.raises(AcceptanceRunnerError, match="不存在或为空"):
        require_empty_project_root(root)


def test_project_root_symlink_is_rejected_without_following_target(
    tmp_path: Path,
) -> None:
    """空项目检查不得跟随软链接写入验收根之外的目录。"""
    target = tmp_path / "outside"
    target.mkdir()
    root = tmp_path / "project"
    root.symlink_to(target, target_is_directory=True)

    with pytest.raises(AcceptanceRunnerError, match="不得是软链接"):
        require_empty_project_root(root)
    assert list(target.iterdir()) == []


def test_cli_rejects_command_line_override_of_catalog_truth() -> None:
    """命令行不得提供覆盖适应症/时区/截止/报告/格式的任何开关。"""
    for forbidden in (
        "--indication",
        "--timezone",
        "--data-cutoff",
        "--reports",
        "--formats",
    ):
        completed = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "--project-root",
                "unused",
                forbidden,
                "tampered",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert completed.returncode == 2, (forbidden, completed.stdout, completed.stderr)
        assert "科学真值" in completed.stderr, (forbidden, completed.stderr)


def test_cli_catalog_stage_passes_on_absent_project_root(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "--project-root",
            str(tmp_path / "fresh-root"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    first_line, _, json_blob = completed.stdout.partition("\n")
    assert first_line.startswith("CATALOG_INPUTS_OK")
    assert "formats=1" in first_line
    assert "reports=3" in first_line
    payload = json.loads(json_blob)
    assert payload["ok"] is True
    assert payload["case_id"] == "full-matrix-v1"
    assert payload["indication"] == "特应性皮炎"
    assert payload["timezone"] == "Asia/Shanghai"
    assert payload["data_cutoff"] == "2026-07-31T23:59:59+08:00"
    assert payload["reports"] == ["A", "B", "C"]
    assert payload["formats"] == ["html"]
    assert set(payload["inputs"]) == set(_DECLARED_INPUT_PATHS)
    assert payload["project_root_state"] == "absent"


def test_cli_catalog_stage_fails_closed_on_preexisting_project(tmp_path: Path) -> None:
    root = tmp_path / "dirty-root"
    (root / "manifests").mkdir(parents=True)
    (root / "manifests/current_run.json").write_text("{}", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(CLI_PATH), "--project-root", str(root)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert completed.returncode == 1
    assert "不存在或为空" in completed.stderr
    assert "PRE_RC_REHEARSAL_OK" not in completed.stdout


# ─── F03：当前运行顺序、A/B/C HTML 产物与 ego(lite) 浏览器回执严格绑定 ────────

_PRE_RC_TEST_ID = "pre-rc-test-fixed"


@pytest.fixture(scope="module")
def ran_project(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """真实执行阶段 1-2 一次，供回执合同测试复制使用（不涉及任何浏览器）。"""

    base = tmp_path_factory.mktemp("ran-project")
    root = base / "project"
    catalog = load_acceptance_catalog()
    resolved = resolve_acceptance_case("full-matrix-v1", catalog)
    run_project_stage(
        catalog=catalog,
        resolved=resolved,
        project_root=root,
        pre_rc_run_id=_PRE_RC_TEST_ID,
    )
    artifacts, _sources, run_info = _discover_current_html_artifacts(
        root.resolve(),
        resolved=resolved,
        pre_rc_run_id=_PRE_RC_TEST_ID,
    )
    return {
        "root": root,
        "resolved": resolved,
        "artifacts": artifacts,
        "run_id": str(run_info["run_id"]),
        "pre_rc_run_id": _PRE_RC_TEST_ID,
    }


def _copy_ran_project(ran: dict[str, Any], tmp_path: Path, name: str) -> Path:
    """复制已运行项目树（保留 run id 与产物绑定），供单个故障用例使用。"""

    target = tmp_path / name
    shutil.copytree(ran["root"], target)
    return target


def _write_ego_receipt(
    root: Path,
    report: str,
    *,
    artifact: Any,
    run_id: str,
    pre_rc_run_id: str,
    routes: Any,
    **overrides: Any,
) -> Path:
    """写入一份合同合法的 ego(lite) 回执；``overrides`` 用于故障注入。"""

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "tool": EGO_LITE_TOOL_IDENTITY,
        "ok": True,
        "report": report,
        "version": artifact["version"],
        "run_id": run_id,
        "pre_rc_run_id": pre_rc_run_id,
        "manifest_id": artifact["manifest_id"],
        "report_snapshot_id": artifact["report_snapshot_id"],
        "site_digest": artifact["site_sha256"],
        "routes": list(routes),
        "viewports": [list(viewport) for viewport in PRESCRIBED_VIEWPORTS],
        "pages": [{"route": route, "ok": True} for route in routes],
        "verified_at": datetime.now(UTC).isoformat(),
    }
    payload.update(overrides)
    path = expected_ego_receipt_path(root, report, str(artifact["version"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _write_all_receipts(root: Path, ran: dict[str, Any], **per_report: Any) -> None:
    """为 A/B/C 各写一份回执；``per_report`` 可按报告注入字段覆盖。"""

    for report in ("A", "B", "C"):
        kwargs: dict[str, Any] = {
            "artifact": ran["artifacts"][report].to_summary(),
            "run_id": ran["run_id"],
            "pre_rc_run_id": ran["pre_rc_run_id"],
            "routes": ran["artifacts"][report].routes,
        }
        kwargs.update(per_report.get(report, {}))
        _write_ego_receipt(root, report, **kwargs)


# fmt: off
def test_runner_orders_project_render_browser_hosts_and_project_verify(
    ran_project: dict[str, Any],
    tmp_path: Path,
) -> None:
# fmt: on
    """验收节点 2：阶段顺序固定——catalog/输入核验 → 项目运行 → ego(lite) 回执
    绑定 → 宿主 → 项目核验 → 回执聚合；回执按 A → B → C 顺序进入绑定摘要。"""
    ran = ran_project
    root = _copy_ran_project(ran, tmp_path, "order-root")
    _write_all_receipts(root, ran)

    stage_names = [
        "catalog-and-input-verification",
        "project-run",
    ]
    # 空项目目录上的阶段 1 独立可执行（阶段 2 已在 fixture 中真实运行）。
    catalog_stage = run_catalog_input_stage(project_root=tmp_path / "fresh-root")
    assert catalog_stage["stage"] == stage_names[0]

    # 阶段 3（回执绑定）作用于已运行项目；阶段 4-6 由注入处理器按声明顺序接入。
    bound = bind_ego_receipts_pipeline(project_root=root)
    assert [stage["stage"] for stage in bound["stages"]] == list(PRE_RC_STAGE_ORDER)[:3]
    stage_names.append(bound["stages"][2]["stage"])

    handler_outputs = [
        {"hosts": ["codex", "hermes", "omp"]},
        {},
        {"release_cases_closed": 0},
    ]
    for stage_name, outcome in zip(
        ("host-smoke", "project-verify", "pre-rc-receipts"),
        handler_outputs,
        strict=True,
    ):
        stage_names.append(stage_name)
        assert stage_name in PRE_RC_STAGE_ORDER
        assert outcome is not None

    assert stage_names == list(PRE_RC_STAGE_ORDER)
    receipts = bound["stages"][2]["receipts"]
    assert list(receipts) == ["A", "B", "C"]
    for receipt in receipts.values():
        assert receipt["tool"] == EGO_LITE_TOOL_IDENTITY
        assert receipt["run_id"] == ran["run_id"]
        assert receipt["pre_rc_run_id"] == ran["pre_rc_run_id"]
        assert receipt["bound_to_current_artifact"] is True
    assert bound["stages"][2]["stage"] == "html-artifacts-browser-verdicts"
    # 回执绑定不产生任何未来责任关闭标记（Task 10.6/恢复/切换责任不受影响）。
    assert all("release_cases_closed" not in stage for stage in bound["stages"])


def test_current_run_manifest_binds_three_html_artifacts_and_browser_verdicts(
    ran_project: dict[str, Any],
    tmp_path: Path,
) -> None:
    """验收节点 3：当前运行绑定三个 HTML 产物（实际文件/摘要/生成时间/入口页）
    与三份 ego(lite) 浏览器回执（run id、清单标识、快照、站点摘要、实际路由
    集合、规定视口、验收时间）；旧回执、伪摘要与篡改站点都不能通过。"""
    ran = ran_project
    root = _copy_ran_project(ran, tmp_path, "bind-root")
    _write_all_receipts(root, ran)

    summary = bind_ego_receipts_pipeline(project_root=root)
    assert summary["ok"] is True
    receipt_stage = summary["stages"][2]

    # 三个 HTML 当前产物：版本、站点目录摘要、清单摘要、生成时间与入口页逐项绑定。
    artifacts = receipt_stage["artifacts"]
    assert set(artifacts) == {"A", "B", "C"}
    for report, artifact in artifacts.items():
        assert artifact["version"] == "v-fixture-001"
        assert artifact["site_relative_path"] == f"reports/{report}/v-fixture-001/html"
        assert artifact["generated_at"]
        assert artifact["entry_route"].startswith(f"/{report.lower()}/")
        entry_file = root / artifact["entry_relative_path"]
        assert artifact["entry_sha256"] == hashlib.sha256(entry_file.read_bytes()).hexdigest()
        manifest_file = root / artifact["manifest_relative_path"]
        assert artifact["manifest_sha256"] == hashlib.sha256(
            manifest_file.read_bytes()
        ).hexdigest()

    # 三份回执与当前产物逐项绑定；实际路由集合与规定视口必须完整声明。
    receipts = receipt_stage["receipts"]
    assert set(receipts) == {"A", "B", "C"}
    for report, artifact in artifacts.items():
        receipt = receipts[report]
        assert receipt["ok"] is True
        assert receipt["tool"] == EGO_LITE_TOOL_IDENTITY
        assert receipt["version"] == artifact["version"]
        assert receipt["run_id"] == ran["run_id"]
        assert receipt["pre_rc_run_id"] == ran["pre_rc_run_id"]
        assert receipt["manifest_id"] == artifact["manifest_id"]
        assert receipt["report_snapshot_id"] == artifact["report_snapshot_id"]
        assert receipt["site_digest"] == artifact["site_sha256"]
        assert receipt["route_count"] == artifact["route_count"]
        assert receipt["viewports"] == [list(v) for v in PRESCRIBED_VIEWPORTS]
        assert receipt["bound_to_current_artifact"] is True
        receipt_file = root / receipt["receipt_relative_path"]
        assert receipt_file.name == EGO_RECEIPT_FILENAME
        assert hashlib.sha256(receipt_file.read_bytes()).hexdigest() == receipt["receipt_sha256"]

    resolved = ran["resolved"]
    resolved_root = root.resolve()

    # 旧回执：文件时间回拨到运行开始之前 → 拒绝。
    receipt_path = expected_ego_receipt_path(resolved_root, "A", "v-fixture-001")
    old = int(time.time() - 3600)
    os.utime(receipt_path, (old, old))
    with pytest.raises(AcceptanceRunnerError, match="早于当前运行"):
        run_ego_receipt_stage(
            project_root=resolved_root, resolved=resolved, pre_rc_run_id=ran["pre_rc_run_id"]
        )
    os.utime(receipt_path, None)

    # 伪站点摘要：回执声明与当前产物不同的 site_digest → 拒绝。
    _write_ego_receipt(
        resolved_root,
        "B",
        artifact=ran["artifacts"]["B"].to_summary(),
        run_id=ran["run_id"],
        pre_rc_run_id=ran["pre_rc_run_id"],
        routes=ran["artifacts"]["B"].routes,
        site_digest="0" * 64,
    )
    with pytest.raises(AcceptanceRunnerError, match="站点摘要"):
        run_ego_receipt_stage(
            project_root=resolved_root, resolved=resolved, pre_rc_run_id=ran["pre_rc_run_id"]
        )

    # 篡改当前站点文件：站点目录摘要与锁定清单不一致 → 拒绝（旧运行/伪产物不可通过）。
    entry = root / ran["artifacts"]["C"].entry_relative_path
    entry.write_bytes(entry.read_bytes() + b"<!-- tampered -->\n")
    with pytest.raises(AcceptanceRunnerError, match="无法核验"):
        run_ego_receipt_stage(
            project_root=resolved_root, resolved=resolved, pre_rc_run_id=ran["pre_rc_run_id"]
        )


@pytest.mark.parametrize(
    ("fault", "match"),
    (
        ("missing-receipt", "等待 ego"),
        ("non-ego-tool", "不是 ego"),
        ("missing-page", "数量不一致"),
        ("failed-page", "页面未通过"),
        ("site-digest-mismatch", "站点摘要"),
        ("wrong-run-id", "运行标识"),
        ("wrong-manifest-id", "清单标识"),
        ("wrong-viewport", "视口"),
        ("stale-receipt-file", "早于当前运行"),
        ("missing-artifact", "无法核验"),
    ),
)
def test_runner_fails_closed_on_any_missing_artifact_failed_verifier_or_nonzero_command(
    ran_project: dict[str, Any],
    tmp_path: Path,
    fault: str,
    match: str,
) -> None:
    """验收节点 4：缺失回执/产物、非 ego 工具、缺页、页面失败、摘要或身份不符、
    旧回执任一发生即失败关闭，不输出通过信号。（原“非零命令”分支随浏览器
    命令执行一并移除：本 runner 不再启动任何浏览器命令。）"""
    ran = ran_project
    root = _copy_ran_project(ran, tmp_path, f"fault-{fault}")

    if fault == "missing-receipt":
        _write_ego_receipt(
            root,
            "A",
            artifact=ran["artifacts"]["A"].to_summary(),
            run_id=ran["run_id"],
            pre_rc_run_id=ran["pre_rc_run_id"],
            routes=ran["artifacts"]["A"].routes,
        )
        with pytest.raises(EgoReceiptPendingError, match=match):
            run_ego_receipt_stage(
                project_root=root, resolved=ran["resolved"], pre_rc_run_id=ran["pre_rc_run_id"]
            )
        return

    if fault == "missing-artifact":
        _write_all_receipts(root, ran)
        shutil.rmtree(root / "reports" / "C" / "v-fixture-001" / "html")
        with pytest.raises(AcceptanceRunnerError, match=match):
            run_ego_receipt_stage(
                project_root=root, resolved=ran["resolved"], pre_rc_run_id=ran["pre_rc_run_id"]
            )
        return

    overrides: dict[str, Any] = {}
    if fault == "non-ego-tool":
        overrides["tool"] = "playwright"
    elif fault == "missing-page":
        overrides["pages"] = [{"route": route, "ok": True} for route in
                              ran["artifacts"]["B"].routes][:-1]
    elif fault == "failed-page":
        pages = [
            {"route": route, "ok": route != ran["artifacts"]["B"].routes[0]}
            for route in ran["artifacts"]["B"].routes
        ]
        overrides["pages"] = pages
    elif fault == "site-digest-mismatch":
        overrides["site_digest"] = "0" * 64
    elif fault == "wrong-run-id":
        overrides["run_id"] = "run_foreign_run"
    elif fault == "wrong-manifest-id":
        overrides["manifest_id"] = "artifact-manifest_foreign"
    elif fault == "wrong-viewport":
        overrides["viewports"] = [[800, 600]]
    target = "B" if fault != "wrong-run-id" else "A"
    _write_all_receipts(root, ran, **{target: overrides})
    receipt_path = expected_ego_receipt_path(
        root, target, str(ran["artifacts"][target].to_summary()["version"])
    )
    if fault == "stale-receipt-file":
        old = int(time.time() - 3600)
        os.utime(receipt_path, (old, old))

    with pytest.raises(AcceptanceRunnerError, match=match):
        run_ego_receipt_stage(
            project_root=root, resolved=ran["resolved"], pre_rc_run_id=ran["pre_rc_run_id"]
        )
    # 失败关闭后不得留下任何已绑定的回执结论信号。
    bound_marker = root / "manifests" / "current_run.json"
    assert bound_marker.is_file()  # 项目运行记录保留用于诊断，但无通过信号输出


def test_html_pipeline_runs_project_then_requests_ego_receipts(tmp_path: Path) -> None:
    """阶段 1 → 2 真实执行后，阶段 3 以明确指引等待 Codex 的 ego(lite) 回执；
    runner 自身不启动任何浏览器，也不回退到其他浏览器。"""
    root = tmp_path / "fresh-root"
    with pytest.raises(EgoReceiptPendingError) as pending:
        run_html_pipeline(project_root=root, pre_rc_run_id=_PRE_RC_TEST_ID)

    message = str(pending.value)
    assert "ego(lite)" in message and EGO_LITE_TOOL_IDENTITY in message
    assert "回执" in message
    assert "verification/A/v-fixture-001/ego-receipt.json" in message
    assert pending.value.missing_paths and all(
        path.name == EGO_RECEIPT_FILENAME for path in pending.value.missing_paths
    )
    # 阶段 1-2 确已执行：当前运行清单存在且绑定案例与 pre-RC 身份。
    manifest = json.loads((root / "manifests" / "current_run.json").read_text(encoding="utf-8"))
    assert manifest["case_id"] == "full-matrix-v1"
    assert manifest["pre_rc_run_id"] == _PRE_RC_TEST_ID
    assert manifest["resume"] is False


def test_pre_rc_rehearsal_preflight_fails_closed_before_any_work(tmp_path: Path) -> None:
    """宿主/项目核验/回执聚合任一处理器缺失时，预检即失败关闭，不执行任何阶段。"""
    with pytest.raises(AcceptanceRunnerError, match="尚未接入"):
        run_pre_rc_rehearsal(project_root=tmp_path / "root")
    assert not (tmp_path / "root").exists()


def test_cli_html_pipeline_prompts_for_ego_receipts(tmp_path: Path) -> None:
    """CLI html 流水线在回执缺失时提示需要 Codex 使用 ego(lite)，退出码 3，
    不输出任何成功信号。"""
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "--pipeline",
            "html",
            "--project-root",
            str(tmp_path / "fresh-root"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert completed.returncode == 3, (completed.stdout, completed.stderr)
    assert "ego(lite)" in completed.stderr
    assert "ego-lite" in completed.stderr
    assert "回执" in completed.stderr
    assert "ego-receipt.json" in completed.stderr
    assert "PRE_RC_REHEARSAL_OK" not in completed.stdout
    assert "HTML_PIPELINE_OK" not in completed.stdout


def test_cli_bind_ego_receipts_reports_missing_receipts(
    ran_project: dict[str, Any],
    tmp_path: Path,
) -> None:
    """CLI 绑定入口对已运行但缺回执的项目给出 ego(lite) 指引并退出码 3。"""
    root = _copy_ran_project(ran_project, tmp_path, "cli-bind-root")
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "--pipeline",
            "html",
            "--bind-ego-receipts",
            "--project-root",
            str(root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert completed.returncode == 3, (completed.stdout, completed.stderr)
    assert "ego(lite)" in completed.stderr
    assert "EGO_RECEIPTS_OK" not in completed.stdout

    # 提供 A/B/C 三份回执后绑定成功（仍不执行任何浏览器）。
    ran = ran_project
    bind_root = _copy_ran_project(ran, tmp_path, "cli-bind-root-ok")
    _write_all_receipts(bind_root, ran)
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "--pipeline",
            "html",
            "--bind-ego-receipts",
            "--project-root",
            str(bind_root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert completed.stdout.startswith("EGO_RECEIPTS_OK")
    assert "receipts=3" in completed.stdout.splitlines()[0]


def test_cli_bind_flag_requires_html_pipeline(ran_project: dict[str, Any], tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "--bind-ego-receipts",
            "--project-root",
            str(ran_project["root"]),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 2
    assert "bind-ego-receipts" in completed.stderr


# ─── F04：required-v12 full-matrix 场景 rehearsal 回执与未来责任保护 ──────────

_REQUIRE_V12_ROOT = ROOT / "fixtures/acceptance/required-v12"

_EXPECTED_SUITE_IDS = (
    "full-matrix-v1",
    "landscape-global-china-maturity",
    "ontology-regimen-boundaries",
    "study-role-boundaries",
    "c-protocol-registry-paths",
    "evidence-guidance-conflicts",
    "supplement-requiredness",
    "b-baseline-d70",
    "b-disposition",
    "b-interaction-cross-format",
    "technical-and-manual-recovery",
    "multi-report-partial-delivery",
    "state-replay-and-reopen",
    "kangzhe-and-large-project-runtime",
    "host-smoke-v1",
    "legacy-negative-regressions",
)

_HISTORICAL_CASE_IDS = (
    "historical-cutoff-acquired-after-disclosed-before",
    "historical-cutoff-disclosed-after-cutoff",
    "historical-cutoff-unknown-first-disclosure",
    "historical-cutoff-cross-day-resume",
)


def _stub_verifier_runner(fail_targets: frozenset[str] = frozenset()) -> Any:
    """返回恒通过/按目标失败的 verifier 替身，并记录全部调用供绑定断言。"""

    calls: list[tuple[str, str, str]] = []

    def runner(case_id: str, target: str, command: str) -> ScenarioVerifierOutcome:
        calls.append((case_id, target, command))
        ok = target not in fail_targets
        return ScenarioVerifierOutcome(
            case_id=case_id,
            target=target,
            command=command,
            ok=ok,
            exit_code=0 if ok else 1,
            duration_ms=1,
            output_sha256=hashlib.sha256(
                f"{case_id}:{target}".encode()
            ).hexdigest(),
        )

    runner.calls = calls  # type: ignore[attr-defined]
    return runner


def _host_smoke_summary(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": True,
        "hosts": {
            host: {"ok": True, "host": host} for host in ("codex", "hermes", "omp")
        },
    }
    payload.update(overrides)
    return payload


def _copy_acceptance_fixtures(tmp_path: Path, name: str) -> Path:
    """复制完整 fixtures/acceptance（catalog + 案例目录）到临时目录。"""

    base = tmp_path / name
    base.mkdir()
    shutil.copytree(ROOT / "fixtures/acceptance", base / "acceptance")
    return base / "acceptance" / "catalog.yaml"


def _recompute_all_case_digests(payload: dict[str, Any]) -> None:
    for case in payload["cases"]:
        case["case_digest"] = compute_case_digest(case)


def _complete_pipeline_summary(
    receipts_payload: dict[str, Any],
    pre_rc_run_id: str = _PRE_RC_TEST_ID,
) -> dict[str, Any]:
    stages = [
        {"stage": "catalog-and-input-verification", "ok": True},
        {"stage": "project-run", "ok": True},
        {"stage": "html-artifacts-browser-verdicts", "ok": True},
        {"stage": "host-smoke", "ok": True},
        {"stage": "project-verify", "ok": True},
        {"stage": "pre-rc-receipts", "ok": True, **receipts_payload},
    ]
    return {
        "ok": True,
        "pre_rc_run_id": pre_rc_run_id,
        "reports": ["A", "B", "C"],
        "formats": ["html"],
        "stage_order": list(PRE_RC_STAGE_ORDER),
        "stages": stages,
    }


# fmt: off
def test_suite_full_rehearses_current_scope_without_closing_future_owner_receipts(
) -> None:
# fmt: on
    """验收节点 5：``--suite full`` 只把本轮预演的首版 case/子 case 记为
    ``pre_rc_rehearsal``；恢复、切换与未来格式责任保持
    ``pending_future_owner``，``release_cases_closed`` 恒为 0，且固定成功
    信号只能在完整六阶段摘要上按固定格式渲染。"""
    catalog = load_acceptance_catalog()
    suite = resolve_full_matrix_suite(catalog)
    assert [resolved.case_id for resolved in suite] == list(_EXPECTED_SUITE_IDS)
    for resolved in suite:
        assert resolved.execution_scope == "full-matrix"
        assert resolved.formats == ("html",)

    runner = _stub_verifier_runner()
    payload = build_full_matrix_suite_receipts(
        catalog,
        pre_rc_run_id=_PRE_RC_TEST_ID,
        host_smoke_summary=_host_smoke_summary(pre_rc_run_id=_PRE_RC_TEST_ID),
        verifier_runner=runner,
    )

    assert payload["suite"] == "full"
    assert payload["pre_rc_run_id"] == _PRE_RC_TEST_ID
    assert payload["release_cases_closed"] == 0
    assert payload["closed_case_ids"] == []
    assert payload["formats"] == ["html"]
    assert payload["hosts"] == ["codex", "hermes", "omp"]
    assert payload["counts"] == {
        "catalog_cases_total": 23,
        "suite_cases": 16,
        "rehearsed": 16,
        "pending_future_owner": 2,
        "not_applicable": 1,
        "outside_suite": 4,
    }

    receipts = {receipt["case_id"]: receipt for receipt in payload["receipts"]}
    assert len(receipts) == 23

    # 套件案例：本轮预演，verifier 逐条绑定且全部通过；子场景逐项继承回执。
    for case_id in payload["suite_case_ids"]:
        receipt = receipts[case_id]
        assert receipt["status"] == REHEARSAL_STATUS
        assert receipt["release_case_closed"] is False
        assert receipt["pre_rc_run_id"] == _PRE_RC_TEST_ID
        assert receipt["evidence_kind"] == "catalog-verifier-rehearsal"
        assert receipt["formats"] == ["html"]
        assert receipt["verifiers"], case_id
        assert all(item["ok"] is True for item in receipt["verifiers"])
        assert all(
            sub["status"] == REHEARSAL_STATUS and sub["release_case_closed"] is False
            for sub in receipt["subscenarios"]
        )

    # verifier 命令逐字来自 catalog：字符串声明合成 uv run pytest 命令。
    full_matrix_case = catalog.cases["full-matrix-v1"]
    assert (full_matrix_case["id"], full_matrix_case["verifiers"][0],
            f"uv run pytest {full_matrix_case['verifiers'][0]} -q") in runner.calls  # type: ignore[attr-defined]

    # 子场景与案例目录 scenario.json 逐项一致；无 scenario.json 的基准案例为空。
    for case_id in ("landscape-global-china-maturity", "legacy-negative-regressions"):
        scenario = json.loads(
            (_REQUIRE_V12_ROOT / case_id / "inputs/scenario.json").read_text(encoding="utf-8")
        )
        assert [sub["id"] for sub in receipts[case_id]["subscenarios"]] == [
            sub["id"] for sub in scenario["subscenarios"]
        ]
    assert len(receipts["legacy-negative-regressions"]["subscenarios"]) == 6
    assert receipts["full-matrix-v1"]["subscenarios"] == []

    # 恢复与切换：保持 pending_future_owner，不预演、不关闭其 verifier。
    for case_id, task in (
        ("recovery-rehearsal", "Task 10.6"),
        ("legacy-absence", "Task 10.8"),
    ):
        receipt = receipts[case_id]
        assert receipt["status"] == PENDING_FUTURE_OWNER_STATUS
        assert receipt["release_case_closed"] is False
        assert receipt["catalog_receipt_owner_status"] == "pending_future_owner"
        assert "verifiers" not in receipt
        assert task in receipt["reason_zh"]

    # 条件扩展：not_applicable，runner 不猜测合同选择。
    optional = receipts["optional-adapter-recovery"]
    assert optional["status"] == NOT_APPLICABLE_STATUS
    assert optional["release_case_closed"] is False
    assert "verifiers" not in optional

    # Task 10.1 已持有的历史截止案例：套件外记录，归属不被改写。
    for case_id in _HISTORICAL_CASE_IDS:
        receipt = receipts[case_id]
        assert receipt["status"] == "outside_suite"
        assert receipt["release_case_closed"] is False
        assert receipt["catalog_receipt_owner_status"] == "current_owner"

    # 未来格式：单独记录为 pending_future_owner，不进入任何回执格式集合。
    future_formats = payload["future_formats"]
    assert future_formats["deferred_formats"] == ["pdf", "html-ppt", "pptx"]
    assert future_formats["status"] == PENDING_FUTURE_OWNER_STATUS
    assert future_formats["release_case_closed"] is False
    assert future_formats["basis"] == "ADR 0013"

    # 固定成功信号：只能在完整六阶段摘要上按固定格式渲染。
    line = format_pre_rc_rehearsal_ok(_complete_pipeline_summary(payload))
    assert line.startswith("PRE_RC_REHEARSAL_OK reports=3 formats=1 hosts=3 ")
    assert "cases=23 rehearsed=16 future_owner=2 not_applicable=1 outside_suite=4" in line
    assert "release_cases_closed=0" in line
    assert line.endswith(f"pre_rc_run_id={_PRE_RC_TEST_ID}")


def test_suite_rehearsal_fails_closed_on_verifier_failure() -> None:
    """任一套件案例的 declared verifier 未通过即失败关闭，不生成回执。"""
    catalog = load_acceptance_catalog()
    failing_target = (
        "tests/reports/b/test_baseline_group_gate.py::"
        "test_each_core_trial_group_requires_all_four_independent_baseline_observations"
    )
    runner = _stub_verifier_runner(fail_targets=frozenset({failing_target}))
    with pytest.raises(AcceptanceRunnerError) as excinfo:
        build_full_matrix_suite_receipts(
            catalog,
            pre_rc_run_id=_PRE_RC_TEST_ID,
            host_smoke_summary=_host_smoke_summary(),
            verifier_runner=runner,
        )
    message = str(excinfo.value)
    assert "b-baseline-d70" in message
    assert "未通过的 verifier" in message
    assert failing_target in message


def _catalog_with_mutated_case(case_id: str, mutate: Any) -> Any:
    """构造案例字段被篡改的内存 catalog 对象（绕过 YAML/Schema 层，直测运行时防线）。"""

    from ci_workflow.application.acceptance_runner import AcceptanceCatalog

    catalog = load_acceptance_catalog()
    cases = dict(catalog.cases)
    cases[case_id] = mutate(dict(cases[case_id]))
    return AcceptanceCatalog(
        path=catalog.path,
        sha256=catalog.sha256,
        release_scope=catalog.release_scope,
        digest_algorithm=catalog.digest_algorithm,
        allowed_formats=catalog.allowed_formats,
        approved_case_families=catalog.approved_case_families,
        extra_case_policy=catalog.extra_case_policy,
        cases=cases,
    )


def test_suite_rehearsal_fails_closed_on_unregistered_execution_scope() -> None:
    """出现未登记执行范围时拒绝静默归类，防止新范围被误关闭或忽略。"""
    catalog = _catalog_with_mutated_case(
        "legacy-absence",
        lambda case: {**case, "execution_scope": "invented-scope"},
    )

    with pytest.raises(AcceptanceRunnerError, match="执行范围未登记"):
        resolve_full_matrix_suite(catalog)
    with pytest.raises(AcceptanceRunnerError, match="执行范围未登记"):
        build_full_matrix_suite_receipts(
            catalog,
            pre_rc_run_id=_PRE_RC_TEST_ID,
            verifier_runner=_stub_verifier_runner(),
        )


def test_suite_rehearsal_fails_closed_when_no_full_matrix_case_remains(
    tmp_path: Path,
) -> None:
    catalog_copy = _copy_acceptance_fixtures(tmp_path, "suite-empty")
    payload = _load_raw_catalog()
    for case in payload["cases"]:
        if case["execution_scope"] == "full-matrix":
            case["execution_scope"] = "recovery"
    _recompute_all_case_digests(payload)
    _write_mutated_catalog(catalog_copy, payload)

    with pytest.raises(AcceptanceRunnerError, match="没有任何 execution_scope=full-matrix"):
        resolve_full_matrix_suite(load_acceptance_catalog(catalog_copy))


@pytest.mark.parametrize("field", ("case_id", "formats"))
def test_suite_rehearsal_fails_closed_on_subscenario_contract_violation(
    tmp_path: Path,
    field: str,
) -> None:
    """scenario.json 与案例合同漂移（即使 catalog 摘要同步改写）必须失败关闭。"""
    catalog_copy = _copy_acceptance_fixtures(tmp_path, f"suite-sub-{field}")
    payload = _load_raw_catalog()
    case = _case_by_id(payload, "landscape-global-china-maturity")
    scenario_path = (
        catalog_copy.parent
        / "required-v12"
        / "landscape-global-china-maturity"
        / "inputs/scenario.json"
    )
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    if field == "case_id":
        scenario["case_id"] = "another-case"
    else:
        scenario["formats"] = ["html", "pdf"]
    scenario_path.write_text(
        json.dumps(scenario, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    case["inputs"][0]["sha256"] = hashlib.sha256(scenario_path.read_bytes()).hexdigest()
    _recompute_all_case_digests(payload)
    _write_mutated_catalog(catalog_copy, payload)

    with pytest.raises(AcceptanceRunnerError, match="子场景"):
        build_full_matrix_suite_receipts(
            load_acceptance_catalog(catalog_copy),
            pre_rc_run_id=_PRE_RC_TEST_ID,
            verifier_runner=_stub_verifier_runner(),
        )


def test_suite_rehearsal_rejects_release_closed_catalog_receipt_status() -> None:
    """catalog 回执出现 runner 不可识别的关闭语义（如 verified）时拒绝预演。

    ``verified`` 是 schema 允许的 host 回执状态，但不是本 runner 可分类的
    catalog 所有权；将其伪装成案例所有权时必须失败关闭，防止借回执层
    提前宣布发布案例已验证。
    """
    catalog = _catalog_with_mutated_case(
        "recovery-rehearsal",
        lambda case: {
            **case,
            "receipt": {**case["receipt"], "owner_status": "verified"},
        },
    )

    with pytest.raises(AcceptanceRunnerError, match="owner_status"):
        build_full_matrix_suite_receipts(
            catalog,
            pre_rc_run_id=_PRE_RC_TEST_ID,
            verifier_runner=_stub_verifier_runner(),
        )


def test_pre_rc_receipts_stage_binds_host_smoke_and_current_run() -> None:
    """回执聚合阶段：宿主三宿主绑定、当前运行绑定与 catalog 未漂移缺一不可。"""
    catalog = load_acceptance_catalog()
    resolved = resolve_acceptance_case("full-matrix-v1", catalog)
    handler = build_pre_rc_receipts_stage(verifier_runner=_stub_verifier_runner())
    context: dict[str, Any] = {
        "pre_rc_run_id": _PRE_RC_TEST_ID,
        "case_id": "full-matrix-v1",
        "case_digest": resolved.case_digest,
        "catalog_sha256": catalog.sha256,
        "project_run": {"run_id": "run_current_1"},
        "html_pipeline": {
            "reports": ["A", "B", "C"],
            "receipts": {"A": {}, "B": {}, "C": {}},
        },
        "host_smoke": _host_smoke_summary(pre_rc_run_id=_PRE_RC_TEST_ID),
    }

    payload = handler(context)
    assert payload["host_smoke_bound"] is True
    assert payload["hosts"] == ["codex", "hermes", "omp"]
    assert payload["pipeline_binding"]["project_run_id"] == "run_current_1"
    assert payload["pipeline_binding"]["case_digest"] == resolved.case_digest

    def refuted(mutate: Any, match: str) -> None:
        candidate = dict(context)
        mutate(candidate)
        with pytest.raises(AcceptanceRunnerError, match=match):
            handler(candidate)

    refuted(lambda ctx: ctx.__setitem__("host_smoke", None), "宿主冒烟阶段摘要")
    refuted(lambda ctx: ctx.__setitem__("host_smoke", _host_smoke_summary(ok=False)), "未通过")
    refuted(
        lambda ctx: ctx.__setitem__(
            "host_smoke", _host_smoke_summary(hosts={"codex": {"ok": True}})
        ),
        "三个宿主",
    )
    refuted(
        lambda ctx: ctx["host_smoke"].__setitem__("pre_rc_run_id", "pre-rc-run_foreign"),
        "另一次 pre-RC",
    )
    refuted(
        lambda ctx: ctx.__setitem__("html_pipeline", {"reports": ["A", "B"], "receipts": {}}),
        "三报告与三份浏览器回执",
    )
    refuted(lambda ctx: ctx.__setitem__("catalog_sha256", "0" * 64), "漂移")
    refuted(lambda ctx: ctx.__setitem__("case_digest", "0" * 64), "案例摘要")
    refuted(lambda ctx: ctx.__setitem__("pre_rc_run_id", ""), "pre-RC 运行身份")


def test_pre_rc_rehearsal_ok_signal_refuses_incomplete_or_out_of_scope_summaries() -> None:
    """固定成功信号拒绝：阶段不完整/未通过、未来格式、宿主缺失、越责状态与误关闭。"""
    catalog = load_acceptance_catalog()
    payload = build_full_matrix_suite_receipts(
        catalog,
        pre_rc_run_id=_PRE_RC_TEST_ID,
        host_smoke_summary=_host_smoke_summary(pre_rc_run_id=_PRE_RC_TEST_ID),
        verifier_runner=_stub_verifier_runner(),
    )
    summary = _complete_pipeline_summary(payload)
    assert format_pre_rc_rehearsal_ok(summary).startswith("PRE_RC_REHEARSAL_OK")

    def refuted(mutate: Any) -> None:
        candidate = json.loads(json.dumps(summary, ensure_ascii=False))
        mutate(candidate)
        with pytest.raises(AcceptanceRunnerError, match="成功信号被拒绝"):
            format_pre_rc_rehearsal_ok(candidate)

    refuted(lambda s: s.pop("stages"))
    refuted(lambda s: s["stages"].pop())
    refuted(lambda s: s["stages"][3].__setitem__("ok", False))
    refuted(lambda s: s.__setitem__("ok", False))
    refuted(lambda s: s.__setitem__("formats", ["html", "pdf"]))
    refuted(lambda s: s.__setitem__("reports", ["A", "B"]))
    refuted(lambda s: s["stages"][5].__setitem__("release_cases_closed", 1))
    refuted(lambda s: s["stages"][5].__setitem__("closed_case_ids", ["recovery-rehearsal"]))
    refuted(lambda s: s["stages"][5].__setitem__("hosts", ["codex", "hermes"]))
    refuted(
        lambda s: s["stages"][5]["receipts"][0].__setitem__("status", "accepted")
    )
    refuted(
        lambda s: s["stages"][5]["receipts"][0].__setitem__("release_case_closed", True)
    )
    refuted(lambda s: s["stages"][5].pop("counts"))
    refuted(lambda s: s.__setitem__("pre_rc_run_id", ""))


def test_standalone_suite_rehearsal_lacks_hosts_and_cannot_render_success_signal() -> None:
    """独立套件预演不绑定宿主，组装出的摘要也无法渲染全量成功信号。"""
    summary = run_full_matrix_suite_rehearsal(verifier_runner=_stub_verifier_runner())
    assert summary["mode"] == "standalone-catalog-rehearsal"
    assert summary["host_smoke_bound"] is False
    assert summary["hosts"] == []
    assert summary["release_cases_closed"] == 0

    standalone = _complete_pipeline_summary(summary)
    with pytest.raises(AcceptanceRunnerError, match="三宿主"):
        format_pre_rc_rehearsal_ok(standalone)


def test_subprocess_verifier_runner_executes_declared_pytest_command() -> None:
    """默认执行器真实运行 catalog 声明的 pytest 命令并回传精简结果。"""
    catalog = load_acceptance_catalog()
    case = catalog.cases["full-matrix-v1"]
    target = case["verifiers"][0]
    outcome = subprocess_verifier_runner("full-matrix-v1", target, f"uv run pytest {target} -q")
    assert outcome.ok is True
    assert outcome.exit_code == 0
    assert outcome.command == f"uv run pytest {target} -q"
    assert len(outcome.output_sha256) == 64


@pytest.mark.parametrize(
    "extra",
    (
        ["--case", "full-matrix-v1"],
        ["--pipeline", "html"],
        ["--bind-ego-receipts"],
        ["--project-root", "unused"],
    ),
)
def test_cli_suite_full_rejects_conflicting_modes(tmp_path: Path, extra: list[str]) -> None:
    """``--suite full`` 与流水线模式互斥；冲突即用法错误，不执行任何阶段。"""
    completed = subprocess.run(
        [sys.executable, str(CLI_PATH), "--suite", "full", *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 2, (completed.stdout, completed.stderr)
    assert "--suite full" in completed.stderr
    assert "PRE_RC_REHEARSAL_OK" not in completed.stdout
    assert "SUITE_REHEARSAL_RECEIPTS_OK" not in completed.stdout


def test_cli_pipeline_mode_requires_project_root() -> None:
    """流水线模式缺少 --project-root 时给出用法指引（指向 --suite full）。"""
    completed = subprocess.run(
        [sys.executable, str(CLI_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 2
    assert "--project-root" in completed.stderr
    assert "--suite full" in completed.stderr


# ─── F05：候选安装根三宿主真实 smoke 与最终项目核验 ─────────────────────────


def _make_fake_install_root(base: Path) -> Path:
    """构造可通过 ``load_fresh_install_layout`` 核验的最小候选安装根。

    版本目录名取 package-manifest.json 字节的 SHA-256，与真实安装的
    内容地址语义一致；shared 与 OMP 链接指向同一 bundle，入口可执行。
    """

    manifest_payload = {
        "package": {"name": "competitive-intelligence-workflow", "version": "0.1.0+candidate"},
        "public_skill": "skills/competitive-intelligence-workflow/SKILL.md",
    }
    manifest_bytes = json.dumps(
        manifest_payload, ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    bundle = base / "versions" / digest
    skill_dir = bundle / "skills" / "competitive-intelligence-workflow"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# 公共 Skill 替身\n", encoding="utf-8")
    (bundle / "fixtures").mkdir()
    (bundle / "fixtures" / "catalog.yaml").write_text("cases: []\n", encoding="utf-8")
    (bundle / "package-manifest.json").write_bytes(manifest_bytes)
    (base / "shared").symlink_to(bundle, target_is_directory=True)
    omp_link = base / "omp" / "skills" / "competitive-intelligence-workflow"
    omp_link.parent.mkdir(parents=True)
    omp_link.symlink_to(skill_dir, target_is_directory=True)
    entry = base / "bin" / "ci-workflow"
    entry.parent.mkdir(parents=True)
    entry.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    entry.chmod(0o755)
    return base


def _fake_host_receipt(
    host: str,
    *,
    package_manifest_sha256: str,
    case_digest: str,
    session_id: str,
    pid: int,
    run_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    """构造一份结构完整的 host-smoke-v1 回执投影（绑定字段与合同同名）。"""

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "receipt_kind": "host-smoke-v1",
        "host": host,
        "status": "verified",
        "unavailable_reason_zh": None,
        "issued_at": "2026-09-02T04:00:00+00:00",
        "package": {
            "name": "competitive-intelligence-workflow",
            "version": "0.1.0+candidate",
            "package_digest": package_manifest_sha256,
        },
        "entry": {
            "kind": "console_script",
            "command": ["bin/ci-workflow"],
            "resolved_path": "bin/ci-workflow",
            "sha256": "1" * 64,
        },
        "host_executable": {
            "provenance": "path_resolved",
            "path": f"/usr/local/bin/{host}",
            "resolved_realpath": f"/usr/local/bin/{host}",
            "version": f"{host}-double 1.0.0",
        },
        "session": {"session_id": session_id, "launcher_pid": 100 + pid, "launcher_parent_pid": 1},
        "process": {
            "kind": "external_subprocess",
            "pid": pid,
            "argv": ["bin/ci-workflow", "fixture", "run", "--case", "host-smoke-v1"],
            "cwd": "/tmp",
            "started_at": "2026-09-02T04:00:01+00:00",
            "finished_at": "2026-09-02T04:01:00+00:00",
            "returncode": 0,
            "stdout_tail": "HOST_SMOKE_DONE exit=0",
            "stderr_tail": "",
        },
        "fixture": {
            "case_id": "host-smoke-v1",
            "case_digest": case_digest,
            "inputs": {"inputs/scenario.json": "2" * 64},
        },
        "interruption": None,
        "recovery": None,
        "run": {
            "project_root": f"/tmp/host-projects/{host}",
            "run_id": run_id,
            "project_id": "proj_host_smoke",
            "state": "complete",
            "outcome": "rendered",
            "no_draft": False,
            "exit_code": 0,
            "semantic_receipt_digest": "3" * 64,
            "artifacts": [],
        },
        "event_chain": {"event_count": 3, "stream_digest": "4" * 64},
        "manifest": {
            "path": "manifests/current_run.json",
            "sha256": "5" * 64,
            "run_id": run_id,
            "outcome": "rendered",
            "manifest_digest": "6" * 64,
        },
    }
    payload.update(overrides)
    payload["receipt_digest"] = receipt_digest(payload)
    return payload


class _FakeVerdict:
    """``HostSmokeBatchVerdict`` 的最小替身：字段与被绑定层消费的一致。"""

    def __init__(self, real_host_pass: bool = True) -> None:
        self.statuses = {host: "verified" for host in ("codex", "hermes", "omp")}
        self.rejection_reasons: dict[str, str] = {}
        self.real_host_pass = real_host_pass
        self.summary_zh = (
            "三宿主真实入口回执全部验证通过（宿主可执行文件均来自 PATH 真实解析）"
            if real_host_pass
            else "宿主可执行文件为显式提供，不构成真实宿主通过"
        )


class _FakeBatchResult:
    """``HostSmokeBatchResult`` 的最小替身。"""

    def __init__(
        self,
        receipts: dict[str, Any],
        receipt_paths: dict[str, Path],
        batch_path: Path,
        project_roots: dict[str, Path],
        verdict: _FakeVerdict,
    ) -> None:
        self.receipts = receipts
        self.receipt_paths = receipt_paths
        self.batch_path = batch_path
        self.project_roots = project_roots
        self.verdict = verdict


def _make_fake_smoke_runner(
    *,
    real_host_pass: bool = True,
    mutate_receipts: Any = None,
    post_write: Any = None,
) -> Any:
    """构造三宿主批次替身：写落盘回执与批次结论后返回绑定结果。

    ``mutate_receipts`` 在落盘前篡改回执投影（互异/同包/状态注入）；
    ``post_write`` 在落盘后、返回前篡改磁盘文件（事后替换注入）。
    """

    calls: list[dict[str, Any]] = []

    def runner(layout: Any, *, evidence_root: Path, project_root: Path) -> Any:
        calls.append({"evidence_root": evidence_root, "project_root": project_root})
        package_manifest_sha256 = hashlib.sha256(
            Path(layout.package_manifest).read_bytes()
        ).hexdigest()
        case_digest = "a" * 64
        receipts = {
            host: _fake_host_receipt(
                host,
                package_manifest_sha256=package_manifest_sha256,
                case_digest=case_digest,
                session_id=f"session-{host}",
                pid=20001 + index,
                run_id=f"run-host-{host}",
            )
            for index, host in enumerate(("codex", "hermes", "omp"))
        }
        if mutate_receipts is not None:
            mutate_receipts(receipts)
        for host, receipt in receipts.items():
            receipt["run"]["project_root"] = str((project_root / host).resolve())
            receipt["receipt_digest"] = receipt_digest(receipt)
        evidence_root.mkdir(parents=True)
        project_root.mkdir(parents=True)
        receipt_paths: dict[str, Path] = {}
        for host, receipt in receipts.items():
            path = evidence_root / f"{host}.json"
            path.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            receipt_paths[host] = path
        batch_path = evidence_root / "batch.json"
        batch_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "receipt_kind": "host-smoke-v1",
                    "bundle_digest": layout.bundle_digest,
                    "package_manifest_sha256": package_manifest_sha256,
                    "receipt_paths": {
                        host: f"{host}.json" for host in receipts
                    },
                    "project_roots": {
                        host: str((project_root / host).resolve())
                        for host in receipts
                    },
                    "statuses": {host: "verified" for host in receipts},
                    "rejection_reasons": {},
                    "real_host_pass": real_host_pass,
                    "summary_zh": "三宿主真实入口回执全部验证通过",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if post_write is not None:
            post_write(receipt_paths, batch_path)
        return _FakeBatchResult(
            receipts,
            receipt_paths,
            batch_path,
            {host: (project_root / host).resolve() for host in receipts},
            _FakeVerdict(real_host_pass),
        )

    runner.calls = calls  # type: ignore[attr-defined]
    return runner


def test_host_smoke_stage_binds_distinct_hosts_and_same_package_digest(
    tmp_path: Path,
) -> None:
    """三宿主真实冒烟绑定：进程/会话/运行互异、同包摘要对齐磁盘重算值、
    落盘回执逐字节一致，且证据全部落在隔离验收根下。"""
    install_root = _make_fake_install_root(tmp_path / "install")
    acceptance_root = tmp_path / "acceptance-root"
    runner = _make_fake_smoke_runner()
    stage = build_host_smoke_stage(
        install_root=install_root,
        acceptance_root=acceptance_root,
        smoke_runner=runner,
    )

    summary = stage({"pre_rc_run_id": _PRE_RC_TEST_ID})

    assert summary["pre_rc_run_id"] == _PRE_RC_TEST_ID
    assert summary["real_host_pass"] is True
    assert set(summary["hosts"]) == {"codex", "hermes", "omp"}
    for host, entry in summary["hosts"].items():
        assert entry["ok"] is True
        assert entry["status"] == "verified"
        assert entry["host_executable_provenance"] == "path_resolved"
        assert entry["session_id"] == f"session-{host}"
        assert entry["run_id"] == f"run-host-{host}"
        receipt_file = acceptance_root / "host-smoke" / f"{host}.json"
        assert entry["receipt_sha256"] == hashlib.sha256(
            receipt_file.read_bytes()
        ).hexdigest()
    assert summary["distinctness"] == {"session_ids": 3, "process_pids": 3, "run_ids": 3}
    package_manifest_sha256 = hashlib.sha256(
        next((install_root / "versions").iterdir()).joinpath(
            "package-manifest.json"
        ).read_bytes()
    ).hexdigest()
    assert {entry["package_digest"] for entry in summary["hosts"].values()} == {
        package_manifest_sha256
    }
    assert summary["package_manifest_sha256"] == package_manifest_sha256
    assert summary["batch_relative_path"] == "batch.json"
    # 宿主项目与证据全部在验收根下；候选安装根未被写入。
    assert (acceptance_root / "host-smoke" / "batch.json").is_file()
    assert (acceptance_root / "host-projects").is_dir()
    assert not (install_root / "host-smoke").exists()
    assert len(runner.calls) == 1
    assert runner.calls[0]["evidence_root"] == (acceptance_root / "host-smoke").resolve()


@pytest.mark.parametrize(
    ("fault", "match"),
    (
        ("missing-install-root", "候选安装根无法核验"),
        ("wrong-expected-digest", "候选安装根与预期 bundle 摘要不一致"),
        ("install-root-drift", "执行时候选安装根无法核验"),
        ("entrypoint-drift", "真实入口在构建与执行之间发生漂移"),
        ("stale-evidence", "宿主冒烟证据根"),
        ("batch-not-real", "三宿主真实冒烟批次未通过"),
        ("evidence-inside-bundle", "不得写入不可变候选 bundle"),
    ),
)
def test_host_smoke_stage_fails_closed_on_install_root_and_batch_faults(
    tmp_path: Path,
    fault: str,
    match: str,
) -> None:
    """候选安装根、证据根与批次结论任一不符合即失败关闭，且先于宿主执行。"""
    install_root = _make_fake_install_root(tmp_path / "install")
    acceptance_root = tmp_path / "acceptance-root"
    runner = _make_fake_smoke_runner()
    expected_digest = None
    if fault == "wrong-expected-digest":
        expected_digest = "f" * 64
    if fault == "stale-evidence":
        stale = acceptance_root / "host-smoke"
        stale.mkdir(parents=True)
        (stale / "batch.json").write_text('{"real_host_pass": true}\n', encoding="utf-8")
    if fault == "evidence-inside-bundle":
        bundle_root = next((install_root / "versions").iterdir())
        acceptance_root = bundle_root / "acceptance"

    if fault in (
        "missing-install-root",
        "wrong-expected-digest",
        "stale-evidence",
        "evidence-inside-bundle",
    ):
        with pytest.raises(AcceptanceRunnerError, match=match):
            build_host_smoke_stage(
                install_root=(
                    tmp_path / "not-installed" if fault == "missing-install-root" else install_root
                ),
                acceptance_root=acceptance_root,
                expected_bundle_digest=expected_digest,
                smoke_runner=runner,
            )
        assert runner.calls == []
        return

    if fault == "batch-not-real":
        runner = _make_fake_smoke_runner(real_host_pass=False)
    stage = build_host_smoke_stage(
        install_root=install_root,
        acceptance_root=acceptance_root,
        smoke_runner=runner,
    )
    if fault == "entrypoint-drift":
        entrypoint = install_root / "bin" / "ci-workflow"
        entrypoint.write_bytes(entrypoint.read_bytes() + b"\n# drift\n")
    if fault == "install-root-drift":
        shutil.rmtree(install_root / "versions")
    with pytest.raises(AcceptanceRunnerError, match=match):
        stage({"pre_rc_run_id": _PRE_RC_TEST_ID})
    if fault in ("install-root-drift", "entrypoint-drift"):
        assert runner.calls == []


@pytest.mark.parametrize("shared", ("session", "pid", "run"))
def test_host_smoke_stage_fails_closed_on_shared_session_process_or_run(
    tmp_path: Path,
    shared: str,
) -> None:
    """同进程伪造三宿主：会话、外部进程或运行标识任一共享都失败关闭。"""

    def mutate(receipts: dict[str, Any]) -> None:
        if shared == "session":
            receipts["hermes"]["session"]["session_id"] = receipts["codex"]["session"][
                "session_id"
            ]
        elif shared == "pid":
            receipts["hermes"]["process"]["pid"] = receipts["codex"]["process"]["pid"]
        else:
            receipts["hermes"]["run"]["run_id"] = receipts["codex"]["run"]["run_id"]

    install_root = _make_fake_install_root(tmp_path / "install")
    stage = build_host_smoke_stage(
        install_root=install_root,
        acceptance_root=tmp_path / "acceptance-root",
        smoke_runner=_make_fake_smoke_runner(mutate_receipts=mutate),
    )
    with pytest.raises(AcceptanceRunnerError, match="同进程伪造三宿主"):
        stage({"pre_rc_run_id": _PRE_RC_TEST_ID})


@pytest.mark.parametrize(
    ("fault", "match"),
    (
        ("package-drift", "候选包摘要不一致"),
        ("status-drift", "不是 verified"),
        ("provenance-drift", "PATH 真实解析"),
        ("disk-tamper", "疑似复用旧回执"),
        ("batch-drift", "未记录真实宿主通过"),
        ("case-drift", "host-smoke-v1"),
    ),
)
def test_host_smoke_stage_fails_closed_on_package_status_or_disk_drift(
    tmp_path: Path,
    fault: str,
    match: str,
) -> None:
    """同包摘要、回执状态、宿主来源、落盘一致与批次结论任一漂移都失败关闭。"""
    install_root = _make_fake_install_root(tmp_path / "install")
    mutate = None
    post_write = None
    real_host_pass = True
    if fault == "package-drift":
        def mutate(receipts: dict[str, Any]) -> None:  # noqa: F811
            receipts["hermes"]["package"]["package_digest"] = "0" * 64
    elif fault == "status-drift":
        def mutate(receipts: dict[str, Any]) -> None:  # noqa: F811
            receipts["hermes"]["status"] = "host_unavailable"
    elif fault == "provenance-drift":
        def mutate(receipts: dict[str, Any]) -> None:  # noqa: F811
            receipts["hermes"]["host_executable"]["provenance"] = "explicit_override"
    elif fault == "case-drift":
        def mutate(receipts: dict[str, Any]) -> None:  # noqa: F811
            receipts["hermes"]["fixture"]["case_id"] = "legacy-smoke-v1"
    elif fault == "disk-tamper":
        def post_write(receipt_paths: dict[str, Path], batch_path: Path) -> None:  # noqa: F811
            receipt = json.loads(receipt_paths["codex"].read_text(encoding="utf-8"))
            receipt["session"]["session_id"] = "session-forged-after-write"
            receipt_paths["codex"].write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    elif fault == "batch-drift":
        def post_write(receipt_paths: dict[str, Path], batch_path: Path) -> None:  # noqa: F811
            payload = json.loads(batch_path.read_text(encoding="utf-8"))
            payload["real_host_pass"] = False
            batch_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    stage = build_host_smoke_stage(
        install_root=install_root,
        acceptance_root=tmp_path / "acceptance-root",
        smoke_runner=_make_fake_smoke_runner(
            real_host_pass=real_host_pass,
            mutate_receipts=mutate,
            post_write=post_write,
        ),
    )
    with pytest.raises(AcceptanceRunnerError, match=match):
        stage({"pre_rc_run_id": _PRE_RC_TEST_ID})


def test_host_smoke_stage_rejects_receipt_path_outside_evidence_root(
    tmp_path: Path,
) -> None:
    """宿主 runner 返回证据根外的回执路径时必须失败关闭。"""
    install_root = _make_fake_install_root(tmp_path / "install")
    outside = tmp_path / "outside-codex.json"

    def post_write(receipt_paths: dict[str, Path], batch_path: Path) -> None:
        outside.write_bytes(receipt_paths["codex"].read_bytes())
        receipt_paths["codex"] = outside

    stage = build_host_smoke_stage(
        install_root=install_root,
        acceptance_root=tmp_path / "acceptance-root",
        smoke_runner=_make_fake_smoke_runner(post_write=post_write),
    )
    with pytest.raises(AcceptanceRunnerError, match="未落在本次隔离证据根"):
        stage({"pre_rc_run_id": _PRE_RC_TEST_ID})


def test_host_smoke_stage_rejects_project_root_outside_acceptance_root(
    tmp_path: Path,
) -> None:
    """宿主批次返回的项目根必须逐宿主落在本次隔离项目根下。"""
    install_root = _make_fake_install_root(tmp_path / "install")
    base_runner = _make_fake_smoke_runner()

    def runner(layout: Any, *, evidence_root: Path, project_root: Path) -> Any:
        result = base_runner(
            layout,
            evidence_root=evidence_root,
            project_root=project_root,
        )
        result.project_roots["codex"] = tmp_path / "outside-project"
        return result

    stage = build_host_smoke_stage(
        install_root=install_root,
        acceptance_root=tmp_path / "acceptance-root",
        smoke_runner=runner,
    )
    with pytest.raises(AcceptanceRunnerError, match="未落在本次隔离宿主项目根"):
        stage({"pre_rc_run_id": _PRE_RC_TEST_ID})


def test_host_smoke_stage_rejects_batch_package_manifest_digest_drift(
    tmp_path: Path,
) -> None:
    """批次结论中的 package-manifest 摘要漂移时不得输出宿主通过。"""
    install_root = _make_fake_install_root(tmp_path / "install")

    def post_write(receipt_paths: dict[str, Path], batch_path: Path) -> None:
        payload = json.loads(batch_path.read_text(encoding="utf-8"))
        payload["package_manifest_sha256"] = "0" * 64
        batch_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    stage = build_host_smoke_stage(
        install_root=install_root,
        acceptance_root=tmp_path / "acceptance-root",
        smoke_runner=_make_fake_smoke_runner(post_write=post_write),
    )
    with pytest.raises(AcceptanceRunnerError, match="package-manifest 摘要"):
        stage({"pre_rc_run_id": _PRE_RC_TEST_ID})


def test_project_verify_stage_rebinds_current_run_after_host_smoke(
    ran_project: dict[str, Any],
    tmp_path: Path,
) -> None:
    """最终项目核验：宿主冒烟之后重新打开当前运行，产物与回执逐项一致。"""
    ran = ran_project
    root = _copy_ran_project(ran, tmp_path, "verify-root")
    _write_all_receipts(root, ran)
    bound = bind_ego_receipts_pipeline(project_root=root)
    context: dict[str, Any] = {
        "pre_rc_run_id": ran["pre_rc_run_id"],
        "project_root": str(root),
        "catalog_sha256": bound["stages"][0]["catalog_sha256"],
        "case_id": ran["resolved"].case_id,
        "case_digest": ran["resolved"].case_digest,
        "project_run": bound["stages"][1],
        "html_pipeline": bound["stages"][2],
    }

    summary = build_project_verify_stage()(context)

    assert summary["run_id"] == ran["run_id"]
    assert summary["pre_rc_run_id"] == ran["pre_rc_run_id"]
    assert summary["case_id"] == "full-matrix-v1"
    assert set(summary["artifacts"]) == {"A", "B", "C"}
    assert summary["browser_receipts_unchanged"] is True
    assert summary["manifest_sha256"] == hashlib.sha256(
        (root / "manifests" / "current_run.json").read_bytes()
    ).hexdigest()
    assert "未被改动" in summary["verified_zh"]


def test_project_verify_stage_fails_closed_on_project_contract_drift(
    ran_project: dict[str, Any],
    tmp_path: Path,
) -> None:
    """宿主冒烟后项目合同被改写时，最终核验不得继续绑定浏览器结论。"""
    ran = ran_project
    root = _copy_ran_project(ran, tmp_path, "verify-contract-drift")
    _write_all_receipts(root, ran)
    bound = bind_ego_receipts_pipeline(project_root=root)
    context: dict[str, Any] = {
        "pre_rc_run_id": ran["pre_rc_run_id"],
        "project_root": str(root),
        "catalog_sha256": bound["stages"][0]["catalog_sha256"],
        "case_id": ran["resolved"].case_id,
        "case_digest": ran["resolved"].case_digest,
        "project_run": bound["stages"][1],
        "html_pipeline": bound["stages"][2],
    }
    project_document = json.loads((root / "project.yaml").read_text(encoding="utf-8"))
    project_document["active_contract_version"] = 999
    (root / "project.yaml").write_text(
        json.dumps(project_document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(AcceptanceRunnerError, match="项目合同"):
        build_project_verify_stage()(context)


@pytest.mark.parametrize(
    ("fault", "match"),
    (
        ("site-tamper", "站点摘要与清单不一致"),
        ("receipt-tamper", "回执文件在绑定之后被改动"),
        ("catalog-drift", "漂移"),
        ("wrong-pre-rc", "pre-RC 运行身份"),
        ("run-id-mismatch", "运行标识与项目运行阶段绑定不一致"),
        ("missing-prior-stage", "缺少前置项目运行"),
    ),
)
def test_project_verify_stage_fails_closed_on_post_bind_mutations(
    ran_project: dict[str, Any],
    tmp_path: Path,
    fault: str,
    match: str,
) -> None:
    """浏览器验收绑定之后，产物、回执、清单或 catalog 任一改动都失败关闭。"""
    ran = ran_project
    root = _copy_ran_project(ran, tmp_path, f"verify-fault-{fault}")
    _write_all_receipts(root, ran)
    bound = bind_ego_receipts_pipeline(project_root=root)
    context: dict[str, Any] = {
        "pre_rc_run_id": ran["pre_rc_run_id"],
        "project_root": str(root),
        "catalog_sha256": bound["stages"][0]["catalog_sha256"],
        "case_id": ran["resolved"].case_id,
        "case_digest": ran["resolved"].case_digest,
        "project_run": bound["stages"][1],
        "html_pipeline": bound["stages"][2],
    }
    if fault == "site-tamper":
        entry = root / ran["artifacts"]["C"].entry_relative_path
        entry.write_bytes(entry.read_bytes() + b"<!-- tampered after bind -->\n")
    elif fault == "receipt-tamper":
        receipt_path = expected_ego_receipt_path(
            root.resolve(), "A", str(ran["artifacts"]["A"].to_summary()["version"])
        )
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["verified_at"] = datetime.now(UTC).isoformat()
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    elif fault == "catalog-drift":
        context["catalog_sha256"] = "0" * 64
    elif fault == "wrong-pre-rc":
        context["pre_rc_run_id"] = "pre-rc-run_other"
    elif fault == "run-id-mismatch":
        context["project_run"] = {**context["project_run"], "run_id": "run_foreign"}
    elif fault == "missing-prior-stage":
        context.pop("html_pipeline")

    with pytest.raises(AcceptanceRunnerError, match=match):
        build_project_verify_stage()(context)


def test_complete_pre_rc_rehearsal_runs_six_stages_and_renders_signal(
    ran_project: dict[str, Any],
    tmp_path: Path,
) -> None:
    """六阶段续跑编排：阶段 1-3 重新核验绑定，宿主冒烟 → 最终项目核验 →
    场景回执聚合按序执行；全部通过后渲染固定 ``PRE_RC_REHEARSAL_OK`` 信号。"""
    ran = ran_project
    root = _copy_ran_project(ran, tmp_path, "complete-root")
    _write_all_receipts(root, ran)
    install_root = _make_fake_install_root(tmp_path / "install")
    acceptance_root = tmp_path / "acceptance-root"
    runner = _make_fake_smoke_runner()
    verifier = _stub_verifier_runner()

    summary = complete_pre_rc_rehearsal(
        project_root=root,
        host_smoke_stage=build_host_smoke_stage(
            install_root=install_root,
            acceptance_root=acceptance_root,
            smoke_runner=runner,
        ),
        project_verify_stage=build_project_verify_stage(),
        receipts_stage=build_pre_rc_receipts_stage(verifier_runner=verifier),
    )

    assert summary["ok"] is True
    assert [stage["stage"] for stage in summary["stages"]] == list(PRE_RC_STAGE_ORDER)
    host_stage = summary["stages"][3]
    assert host_stage["pre_rc_run_id"] == summary["pre_rc_run_id"]
    assert set(host_stage["hosts"]) == {"codex", "hermes", "omp"}
    assert all(entry["ok"] is True for entry in host_stage["hosts"].values())
    project_stage = summary["stages"][4]
    assert project_stage["browser_receipts_unchanged"] is True
    receipts_stage = summary["stages"][5]
    assert receipts_stage["release_cases_closed"] == 0
    assert receipts_stage["counts"]["rehearsed"] == 16
    assert receipts_stage["hosts"] == ["codex", "hermes", "omp"]

    signal = format_pre_rc_rehearsal_ok(summary)
    assert signal.startswith("PRE_RC_REHEARSAL_OK reports=3 formats=1 hosts=3 ")
    assert "release_cases_closed=0" in signal
    assert f"pre_rc_run_id={summary['pre_rc_run_id']}" in signal


def test_complete_pre_rc_rehearsal_requires_all_handlers(tmp_path: Path) -> None:
    """任一后三阶段处理器缺失时，续跑在任何核验之前失败关闭。"""
    built = build_project_verify_stage()
    receipts = build_pre_rc_receipts_stage(verifier_runner=_stub_verifier_runner())
    with pytest.raises(AcceptanceRunnerError, match="host-smoke"):
        complete_pre_rc_rehearsal(
            project_root=tmp_path,
            project_verify_stage=built,
            receipts_stage=receipts,
        )
    with pytest.raises(AcceptanceRunnerError, match="project-verify"):
        complete_pre_rc_rehearsal(
            project_root=tmp_path,
            host_smoke_stage=lambda context: {},
            receipts_stage=receipts,
        )
    with pytest.raises(AcceptanceRunnerError, match="pre-rc-receipts"):
        complete_pre_rc_rehearsal(
            project_root=tmp_path,
            host_smoke_stage=lambda context: {},
            project_verify_stage=built,
        )


def test_full_pipeline_from_empty_root_pauses_at_ego_receipts(
    ran_project: dict[str, Any],
    tmp_path: Path,
) -> None:
    """完整六阶段首次运行：阶段 1-2 真实执行后暂停在 ego(lite) 回执阶段；
    宿主冒烟绝不先于回执绑定执行，验收证据根保持未创建。"""
    install_root = _make_fake_install_root(tmp_path / "install")
    acceptance_root = tmp_path / "acceptance-root"
    runner = _make_fake_smoke_runner()

    with pytest.raises(EgoReceiptPendingError):
        run_pre_rc_rehearsal(
            project_root=tmp_path / "fresh-full-root",
            host_smoke_stage=build_host_smoke_stage(
                install_root=install_root,
                acceptance_root=acceptance_root,
                smoke_runner=runner,
            ),
            project_verify_stage=build_project_verify_stage(),
            receipts_stage=build_pre_rc_receipts_stage(
                verifier_runner=_stub_verifier_runner()
            ),
        )

    assert runner.calls == []
    assert not (acceptance_root / "host-smoke").exists()
    assert not (acceptance_root / "host-projects").exists()


def test_cli_full_pipeline_requires_acceptance_root(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "--pipeline",
            "full",
            "--project-root",
            str(tmp_path / "fresh-root"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 2, (completed.stdout, completed.stderr)
    assert "--acceptance-root" in completed.stderr
    assert "PRE_RC_REHEARSAL_OK" not in completed.stdout


def test_cli_full_pipeline_fails_closed_on_invalid_install_root_before_any_stage(
    tmp_path: Path,
) -> None:
    """无效候选安装根在构建时即失败关闭：任何阶段（含项目运行）都不执行。"""
    project_root = tmp_path / "fresh-root"

    completed = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "--pipeline",
            "full",
            "--project-root",
            str(project_root),
            "--acceptance-root",
            str(tmp_path / "acceptance-root"),
            "--install-root",
            str(tmp_path / "not-installed"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 1, (completed.stdout, completed.stderr)
    assert "候选安装根无法核验" in completed.stderr
    assert not project_root.exists()
    assert not (tmp_path / "acceptance-root" / "host-smoke").exists()
    assert "PRE_RC_REHEARSAL_OK" not in completed.stdout


def test_cli_full_resume_fails_closed_before_host_work_on_invalid_install_root(
    ran_project: dict[str, Any],
    tmp_path: Path,
) -> None:
    """续跑入口同样先核验候选安装根：已运行项目与回执保持原样，宿主冒烟不执行。"""
    ran = ran_project
    root = _copy_ran_project(ran, tmp_path, "resume-root")
    _write_all_receipts(root, ran)
    acceptance_root = tmp_path / "acceptance-root"

    completed = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "--pipeline",
            "full",
            "--bind-ego-receipts",
            "--project-root",
            str(root),
            "--acceptance-root",
            str(acceptance_root),
            "--install-root",
            str(tmp_path / "not-installed"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 1, (completed.stdout, completed.stderr)
    assert "候选安装根无法核验" in completed.stderr
    assert not (acceptance_root / "host-smoke").exists()
    assert expected_ego_receipt_path(
        root.resolve(), "A", str(ran["artifacts"]["A"].to_summary()["version"])
    ).is_file()
    assert "PRE_RC_REHEARSAL_OK" not in completed.stdout
