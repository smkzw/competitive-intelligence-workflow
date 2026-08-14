"""权威项目合同只读存储测试：持久化、版本化、不可覆盖、resume 不漂移。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from ci_workflow.domain.contracts import ProjectContract, create_project_contract
from ci_workflow.storage.project_contract_store import (
    ProjectContractStore,
    ProjectContractStoreError,
)


def _contract(*, version: int = 1) -> ProjectContract:
    return create_project_contract(
        indication="特应性皮炎",
        reports=["A"],
        outputs=["html"],
        timezone="Asia/Shanghai",
        cutoff="2026-08-10",
        created_at=datetime(2026, 8, 11, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        contract_version=version,
    )


def test_store_persists_and_reloads_without_drift(tmp_path: Path) -> None:
    """真实写入后重读：合同完全一致；resume/重复读取不漂移。"""
    contract = _contract()
    store = ProjectContractStore(tmp_path)
    store.save(contract)
    loaded = store.load_current(contract.project_id)
    assert loaded == contract
    # 重读（同版本）与持久化内容逐字节一致。
    assert store.reload(contract) == contract
    # 再次保存同版本同内容：幂等。
    store.save(contract)


def test_store_versioned_current_is_highest(tmp_path: Path) -> None:
    """当前合同 = 最高版本；refresh 后 load_current 返回新版本，旧版本保留。"""
    store = ProjectContractStore(tmp_path)
    v1 = _contract(version=1)
    store.save(v1)
    v2 = _contract(version=2)
    store.save(v2)
    assert store.load_current(v1.project_id) == v2
    assert store.reload(v1) == v1  # 旧版本仍可读、不漂移


def test_store_rejects_overwrite_conflict(tmp_path: Path) -> None:
    """同一版本不同内容：不可覆盖，必须失败。"""
    store = ProjectContractStore(tmp_path)
    store.save(_contract(version=1))
    conflict = _contract(version=1)
    # 改一个会改变规范内容的字段：indication。
    conflict = ProjectContract.model_validate(
        {**conflict.model_dump(), "indication": "变更适应症"}
    )
    with pytest.raises(ProjectContractStoreError):
        store.save(conflict)


def test_store_missing_current_contract_rejected(tmp_path: Path) -> None:
    """无当前合同：load_current 失败关闭。"""
    store = ProjectContractStore(tmp_path)
    with pytest.raises(ProjectContractStoreError):
        store.load_current("project-missing")


def test_store_rejects_path_escape(tmp_path: Path) -> None:
    """相对路径越界（..）必须失败。"""
    store = ProjectContractStore(tmp_path)
    with pytest.raises(ProjectContractStoreError):
        store._resolve("contracts/../escape.json")
