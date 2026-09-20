"""Task 9.4 HA09：真实入口三宿主回执绑定与诚实批次结论。

本文件属**源码级合同验证**：经真实安装入口（外部子进程）运行
host-smoke-v1，但宿主可执行文件使用显式测试替身（文件名与宿主名一致的
version 脚本）。替身证明的是回执结构、跨宿主绑定区分与批次拒绝逻辑；
``real_host_pass`` 必须为假——Task 9.5 fresh-install 用 PATH 真实解析的
宿主可执行文件复验前，不得主张真实三宿主通过。
"""

from __future__ import annotations

import stat
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.host_smoke import (
    _EXPECTED_MANIFEST_OUTCOMES,
    HOSTS,
    HostSmokeReceiptError,
    resolve_real_entry,
    run_host_smoke,
    verify_host_smoke_batch,
    verify_host_smoke_receipt,
)
from ci_workflow.hosts.receipt import HostReceipt


def _host_double(directory: Path, host: str) -> Path:
    path = directory / host
    path.write_text(f'#!/bin/sh\necho "{host}-real-smoke-double 1.0.0"\n', encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def test_fixture_outcomes_map_to_real_run_manifest_vocabulary() -> None:
    """案例的 rendered 不是运行清单词汇；成功路径必须映射到 completed。"""
    assert _EXPECTED_MANIFEST_OUTCOMES == {
        "evidence_blocked": "evidence_blocked",
        "rendered": "completed",
    }


@pytest.fixture(scope="module")
def three_host_smoke(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, Any]:
    base = tmp_path_factory.mktemp("real-host-smoke")
    doubles = base / "bin"
    doubles.mkdir()
    entry = resolve_real_entry()
    receipts: dict[str, HostReceipt] = {}
    roots: dict[str, Path] = {}
    for host in HOSTS:
        root = base / f"项目-{host}"
        receipts[host] = run_host_smoke(
            host,
            project_root=root,
            entry=entry,
            host_executable=_host_double(doubles, host),
        )
        roots[host] = root
    return {"receipts": receipts, "roots": roots}


def test_three_receipts_bind_distinct_real_host_entries_sessions_runs_package_and_events(
    three_host_smoke: dict[str, Any],
) -> None:
    """三宿主回执绑定互异的真实入口/会话/运行/包/事件链；显式替身不构成
    真实宿主通过（real_host_pass 必须为假）。"""
    receipts: dict[str, HostReceipt] = three_host_smoke["receipts"]
    roots: dict[str, Path] = three_host_smoke["roots"]

    # 每份回执：唯一合同模型 + 当前项目状态深度验证通过
    for host in HOSTS:
        receipt = receipts[host]
        assert isinstance(receipt, HostReceipt)
        assert HostReceipt.model_validate(receipt.model_dump(mode="json")) is not None
        receipt.verify_content_integrity()
        verify_host_smoke_receipt(receipt, project_root=roots[host])
        assert receipt.host == host
        assert receipt.receipt_kind == "host-smoke-v1"

    # 宿主入口（可执行文件）互异：三宿主不可共享同一可执行文件
    exe_paths = {receipts[host].host_executable.path for host in HOSTS}
    assert len(exe_paths) == len(HOSTS)
    # 会话互异：同进程伪造三宿主在批次层失败关闭
    session_ids = {receipts[host].session.session_id for host in HOSTS}
    assert len(session_ids) == len(HOSTS)
    # 运行互异：三个独立项目目录、三个独立 run_id；project_id 由项目
    # 合同确定性派生，同一 fixture 案例在三宿主下必须一致（合同身份相同）
    run_ids = {receipts[host].run.run_id for host in HOSTS}
    project_ids = {receipts[host].run.project_id for host in HOSTS}
    assert len(run_ids) == len(HOSTS)
    assert len(project_ids) == 1
    assert len({str(roots[host].resolve()) for host in HOSTS}) == len(HOSTS)
    # 外部进程互异：每次冒烟是独立真实子进程
    pids = {receipts[host].process.pid for host in HOSTS}
    assert len(pids) == len(HOSTS)
    # 包绑定一致且是当前安装包内容摘要：三宿主运行的是同一个已安装包
    package_identities = {
        (
            receipts[host].package.name,
            receipts[host].package.version,
            receipts[host].package.package_digest,
        )
        for host in HOSTS
    }
    assert len(package_identities) == 1
    # 事件链互异且均绑定当前项目状态
    stream_digests = {receipts[host].event_chain.stream_digest for host in HOSTS}
    assert len(stream_digests) == len(HOSTS)
    # fixture 绑定一致：三宿主运行的是唯一 catalog 中的同一案例
    case_digests = {receipts[host].fixture.case_digest for host in HOSTS}
    assert len(case_digests) == 1

    verdict = verify_host_smoke_batch(receipts, project_roots=roots)
    assert all(verdict.statuses[host] == "verified" for host in HOSTS)
    # 诚实性：显式替身不构成真实宿主通过；真实三宿主实跑留给 Task 9.5
    assert verdict.real_host_pass is False
    assert "不构成真实宿主通过" in verdict.summary_zh


def test_same_session_batch_is_rejected_for_distinctness_contract(
    three_host_smoke: dict[str, Any],
) -> None:
    """批次拒绝证据：结构合法但共享会话的三份回执必须失败关闭。"""
    import copy

    from ci_workflow.application.host_smoke import receipt_digest

    receipts = three_host_smoke["receipts"]
    roots = three_host_smoke["roots"]
    forged: dict[str, dict[str, Any]] = {}
    for host in HOSTS:
        dumped = copy.deepcopy(receipts[host].model_dump(mode="json"))
        dumped["session"]["session_id"] = "single-forged-session"
        dumped["receipt_digest"] = receipt_digest(dumped)
        forged[host] = dumped
    for host in HOSTS:
        verify_host_smoke_receipt(forged[host], project_root=roots[host])
    with pytest.raises(HostSmokeReceiptError, match="同进程伪造三宿主.*session_id"):
        verify_host_smoke_batch(forged, project_roots=roots)
