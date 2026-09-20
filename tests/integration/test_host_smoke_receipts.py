"""Task 9.4 HA09–HA10：host-smoke-v1 fixture/catalog 合同与宿主回执失败关闭。

- HA10：`host-smoke-v1` 在唯一 fixture catalog 登记，绑定逐文件摘要与
  case digest；经真实安装入口运行后走 A 空宇宙证据阻断路径（不产草稿）。
- HA09：`run_host_smoke` 返回唯一 ``HostReceipt`` 合同模型（通过根/包内
  双份 Schema 自检）；验证器先跑合同内容完整性与 Schema，再对照项目当前
  状态深度验证。同进程伪造三宿主、旧回执、adapter-only JSON 一律失败
  关闭；显式宿主替身不得被表述为真实宿主通过。

本套件属源码级合同验证（source-contract）；Task 9.5 fresh-install 的真实
三宿主实跑验收不在本套件主张范围内。
"""

from __future__ import annotations

import copy
import hashlib
import stat
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.fixture_runner import validate_catalog
from ci_workflow.application.host_smoke import (
    HOSTS,
    SMOKE_CASE_ID,
    HostSmokeError,
    HostSmokeReceiptError,
    receipt_digest,
    resolve_real_entry,
    run_host_smoke,
    verify_host_smoke_batch,
    verify_host_smoke_receipt,
)
from ci_workflow.hosts.receipt import HostReceipt

ROOT = Path(__file__).resolve().parents[2]


def _host_double(directory: Path, host: str) -> Path:
    """显式来源（explicit）的宿主可执行文件替身：文件名与宿主名精确一致。"""
    path = directory / host
    path.write_text(f'#!/bin/sh\necho "{host}-smoke-double 1.0.0"\n', encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture(scope="module")
def smoke_bundle(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """三宿主各一次真实入口冒烟（显式替身、独立会话、独立项目目录）。

    receipts 保存合同模型实例，dumps 保存其 model_dump(mode="json") 字典，
    分别服务模型断言与反例篡改。
    """
    base = tmp_path_factory.mktemp("host-smoke")
    doubles = base / "bin"
    doubles.mkdir()
    entry = resolve_real_entry()
    receipts: dict[str, HostReceipt] = {}
    dumps: dict[str, dict[str, Any]] = {}
    roots: dict[str, Path] = {}
    for host in HOSTS:
        root = base / f"项目-{host}"
        receipt = run_host_smoke(
            host,
            project_root=root,
            entry=entry,
            host_executable=_host_double(doubles, host),
        )
        receipts[host] = receipt
        dumps[host] = receipt.model_dump(mode="json")
        roots[host] = root
    return {"receipts": receipts, "dumps": dumps, "roots": roots, "entry": entry}


# ─── HA10：fixture/catalog 摘要合同 ────────────────────────────────────────


def test_host_smoke_case_registered_with_file_and_case_digests() -> None:
    catalog = validate_catalog(ROOT / "fixtures" / "catalog.yaml")
    cases = {case["id"]: case for case in catalog["cases"]}
    case = cases[SMOKE_CASE_ID]
    assert case["expected"]["outcome"] == "evidence_blocked"
    assert case["reports"] == ["A"]
    assert case["outputs"] == ["html"]
    assert "宿主" in case["description_zh"]
    case_dir = ROOT / "fixtures" / "synthetic" / SMOKE_CASE_ID
    for declared in case["inputs"]:
        actual = hashlib.sha256((case_dir / declared["path"]).read_bytes()).hexdigest()
        assert actual == declared["sha256"]


def test_real_entry_smoke_returns_contract_receipt_fail_closed_without_draft(
    smoke_bundle: dict[str, Any],
) -> None:
    receipt = smoke_bundle["receipts"]["codex"]
    root = smoke_bundle["roots"]["codex"]

    # 唯一合同模型：可直接 model_validate 复验，绑定材料齐备
    assert isinstance(receipt, HostReceipt)
    assert HostReceipt.model_validate(receipt.model_dump(mode="json")) is not None
    assert receipt.host_executable.provenance == "explicit"
    assert receipt.process.kind == "external_subprocess"
    assert receipt.process.pid != receipt.session.launcher_pid
    assert receipt.process.returncode == 4
    assert receipt.run.state == "blocked"
    assert receipt.run.no_draft is True
    assert receipt.run.artifacts == ()
    assert receipt.run.outcome == "evidence_blocked"

    # 验证器同时接受模型实例与 JSON 字典
    verify_host_smoke_receipt(receipt, project_root=root)
    verify_host_smoke_receipt(smoke_bundle["dumps"]["codex"], project_root=root)

    # 关键证据不足：不产任何报告文件，只产中文证据不足说明
    assert not list((root / "reports").rglob("*.html"))
    audit = root / "blockers" / "A" / "v1" / "audit.md"
    assert audit.is_file()
    assert "证据不足" in audit.read_text(encoding="utf-8")


# ─── HA09：诚实批次（显式替身不得冒充真实宿主通过） ────────────────────────


def test_batch_with_explicit_doubles_does_not_claim_real_host_pass(
    smoke_bundle: dict[str, Any],
) -> None:
    verdict = verify_host_smoke_batch(
        smoke_bundle["receipts"], project_roots=smoke_bundle["roots"]
    )
    assert all(verdict.statuses[host] == "verified" for host in HOSTS)
    assert not verdict.real_host_pass
    assert "不构成真实宿主通过" in verdict.summary_zh
    assert "Task 9.5" in verdict.summary_zh


def test_missing_host_executable_is_honest_host_unavailable(
    tmp_path: Path,
) -> None:
    entry = resolve_real_entry()
    receipt = run_host_smoke(
        "codex",
        project_root=tmp_path / "项目",
        entry=entry,
        host_executable=tmp_path / "codex",
    )
    assert receipt.status == "host_unavailable"
    assert receipt.host_executable.provenance == "unavailable"
    assert receipt.host_executable.path is None
    assert receipt.host_executable.version is None
    assert receipt.unavailable_reason_zh
    # 诚实不可用回执自身可通过验证（真实入口与运行证据仍然成立）
    verify_host_smoke_receipt(receipt, project_root=tmp_path / "项目")
    verdict = verify_host_smoke_batch(
        {"codex": receipt}, project_roots={"codex": tmp_path / "项目"}
    )
    assert verdict.statuses["codex"] == "host_unavailable"
    assert verdict.statuses["hermes"] == "missing"
    assert not verdict.real_host_pass
    assert "宿主冒烟未完成" in verdict.summary_zh


# ─── HA09 反例：同进程伪造三宿主 ───────────────────────────────────────────


def test_same_session_three_hosts_forgery_fails_closed(tmp_path: Path) -> None:
    entry = resolve_real_entry()
    doubles = tmp_path / "bin"
    doubles.mkdir()
    receipts: dict[str, HostReceipt] = {}
    roots: dict[str, Path] = {}
    for host in HOSTS:
        root = tmp_path / f"项目-{host}"
        receipts[host] = run_host_smoke(
            host,
            project_root=root,
            entry=entry,
            host_executable=_host_double(doubles, host),
            session_id="forged-single-session",
        )
        roots[host] = root
    # 单回执都成立（真实外部进程各自运行过），但共享会话暴露同进程伪造
    for host in HOSTS:
        verify_host_smoke_receipt(receipts[host], project_root=roots[host])
    with pytest.raises(HostSmokeReceiptError, match="同进程伪造三宿主.*session_id"):
        verify_host_smoke_batch(receipts, project_roots=roots)


def test_shared_external_process_pid_across_hosts_fails_closed(
    smoke_bundle: dict[str, Any],
) -> None:
    codex = smoke_bundle["dumps"]["codex"]
    hermes = copy.deepcopy(smoke_bundle["dumps"]["hermes"])
    # 把 codex 的外部进程记录嫁接给 hermes（其余绑定保持 hermes 自身真源）
    hermes["process"] = copy.deepcopy(codex["process"])
    hermes["receipt_digest"] = receipt_digest(hermes)
    verify_host_smoke_receipt(hermes, project_root=smoke_bundle["roots"]["hermes"])
    with pytest.raises(HostSmokeReceiptError, match="同进程伪造三宿主.*process.pid"):
        verify_host_smoke_batch(
            {"codex": codex, "hermes": hermes},
            project_roots={
                "codex": smoke_bundle["roots"]["codex"],
                "hermes": smoke_bundle["roots"]["hermes"],
            },
        )


def test_self_invoked_process_fails_closed(smoke_bundle: dict[str, Any]) -> None:
    forged = copy.deepcopy(smoke_bundle["dumps"]["codex"])
    forged["process"]["pid"] = forged["session"]["launcher_pid"]
    forged["receipt_digest"] = receipt_digest(forged)
    with pytest.raises(HostSmokeReceiptError, match="同进程伪造"):
        verify_host_smoke_receipt(forged, project_root=smoke_bundle["roots"]["codex"])


# ─── HA09 反例：旧回执 ─────────────────────────────────────────────────────


def test_old_receipt_fails_after_project_moves_on(tmp_path: Path) -> None:
    entry = resolve_real_entry()
    double = _host_double(tmp_path, "codex")
    root = tmp_path / "项目"
    first = run_host_smoke(
        "codex", project_root=root, entry=entry, host_executable=double
    )
    verify_host_smoke_receipt(first, project_root=root)

    second = run_host_smoke(
        "codex", project_root=root, entry=entry, host_executable=double, resume=True
    )
    assert second.run.run_id != first.run.run_id
    verify_host_smoke_receipt(second, project_root=root)

    # 旧回执绑定的 manifest/事件链已与项目当前状态不一致：失败关闭
    with pytest.raises(HostSmokeReceiptError, match="旧回执"):
        verify_host_smoke_receipt(first, project_root=root)


# ─── HA09 反例：adapter-only JSON ──────────────────────────────────────────


def test_adapter_only_json_fails_closed(smoke_bundle: dict[str, Any]) -> None:
    root = smoke_bundle["roots"]["codex"]

    in_process = copy.deepcopy(smoke_bundle["dumps"]["codex"])
    in_process["process"]["kind"] = "in_process_adapter"
    in_process["receipt_digest"] = receipt_digest(in_process)
    with pytest.raises(HostSmokeReceiptError, match="结构验证失败"):
        verify_host_smoke_receipt(in_process, project_root=root)

    no_process = copy.deepcopy(smoke_bundle["dumps"]["codex"])
    del no_process["process"]
    no_process["receipt_digest"] = receipt_digest(no_process)
    with pytest.raises(HostSmokeReceiptError, match="结构验证失败"):
        verify_host_smoke_receipt(no_process, project_root=root)

    # 薄适配器的语义状态 JSON（无回执合同、无进程/运行/manifest 绑定）
    adapter_state = {
        "schema_version": "1.0",
        "host": "codex",
        "canonical_state": "evidence_blocked",
        "primary_status_zh": "项目因关键证据不足暂时无法继续。",
        "minimal_input": {"reports": ["A"], "indication": "多发性骨髓瘤", "outputs": ["html"]},
    }
    with pytest.raises(HostSmokeReceiptError, match="结构验证失败"):
        verify_host_smoke_receipt(adapter_state, project_root=root)

    with pytest.raises(HostSmokeReceiptError, match="JSON 对象"):
        verify_host_smoke_receipt(["adapter", "state"], project_root=root)


# ─── HA09 反例：包与真实入口绑定篡改 ───────────────────────────────────────


def test_package_and_entry_binding_tamper_fails_closed(smoke_bundle: dict[str, Any]) -> None:
    root = smoke_bundle["roots"]["codex"]

    stale_package = copy.deepcopy(smoke_bundle["dumps"]["codex"])
    stale_package["package"]["version"] = "9.9.9"
    stale_package["receipt_digest"] = receipt_digest(stale_package)
    with pytest.raises(HostSmokeReceiptError, match="包绑定与当前安装的发行版不一致"):
        verify_host_smoke_receipt(stale_package, project_root=root)

    stale_digest = copy.deepcopy(smoke_bundle["dumps"]["codex"])
    stale_digest["package"]["package_digest"] = "e" * 64
    stale_digest["receipt_digest"] = receipt_digest(stale_digest)
    with pytest.raises(HostSmokeReceiptError, match="包绑定与当前安装的发行版不一致"):
        verify_host_smoke_receipt(stale_digest, project_root=root)

    reinstalled = copy.deepcopy(smoke_bundle["dumps"]["codex"])
    reinstalled["entry"]["sha256"] = "0" * 64
    reinstalled["receipt_digest"] = receipt_digest(reinstalled)
    with pytest.raises(HostSmokeReceiptError, match="真实安装入口摘要"):
        verify_host_smoke_receipt(reinstalled, project_root=root)

    digest_forged = copy.deepcopy(smoke_bundle["dumps"]["codex"])
    digest_forged["status"] = "host_unavailable"
    with pytest.raises(HostSmokeReceiptError, match="结构验证失败"):
        verify_host_smoke_receipt(digest_forged, project_root=root)


def test_produced_receipts_conform_to_registered_host_receipt_schema(
    smoke_bundle: dict[str, Any],
) -> None:
    import json

    from jsonschema import Draft202012Validator

    schema = json.loads(
        (ROOT / "schemas" / "host-receipt.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    for host in HOSTS:
        validator.validate(smoke_bundle["dumps"][host])


def test_no_draft_assertion_checked_against_disk_fails_closed(tmp_path: Path) -> None:
    entry = resolve_real_entry()
    double = _host_double(tmp_path, "codex")
    root = tmp_path / "项目"
    receipt = run_host_smoke("codex", project_root=root, entry=entry, host_executable=double)
    assert receipt.run.no_draft is True

    planted = root / "reports" / "A" / "v1" / "html" / "index.html"
    planted.parent.mkdir(parents=True, exist_ok=True)
    planted.write_text("<html>伪草稿</html>", encoding="utf-8")
    try:
        with pytest.raises(HostSmokeReceiptError, match="no-draft 断言与项目当前状态不一致"):
            verify_host_smoke_receipt(receipt, project_root=root)
    finally:
        planted.unlink()
    verify_host_smoke_receipt(receipt, project_root=root)


def test_unknown_host_and_missing_catalog_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(HostSmokeError, match="未知宿主"):
        run_host_smoke("claude", project_root=tmp_path / "项目")
    with pytest.raises(HostSmokeError, match="catalog"):
        run_host_smoke(
            "codex",
            project_root=tmp_path / "项目2",
            catalog_path=tmp_path / "missing-catalog.yaml",
        )
