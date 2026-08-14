"""权威项目合同只读存储：独立于视图上下文的当前合同来源。

``ProjectContractStore`` 持久化、按合同版本不可覆盖地保存 ``ProjectContract``；
``load_current`` 读取当前（最高版本）合同，供视图调用边界重载权威当前合同，
避免"上下文内部自洽"伪造（合同/清单/快照/存储同时改成未来版本仍必须因
权威当前合同不匹配而拒绝）。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path, PurePosixPath

from ci_workflow.domain.contracts import ProjectContract


class ProjectContractStoreError(RuntimeError):
    """权威项目合同存储错误：缺失、冲突或路径越界。"""


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


class ProjectContractStore:
    """项目内版本化、不可覆盖的项目合同存储。

    - ``save`` 按 ``{project_id}/v{contract_version}.json`` 写入规范 JSON；
      同一版本已存在且内容不同则失败（不可覆盖）；
    - ``load_current`` 读取最高合同版本作为当前权威合同；
    - 路径校验拒绝绝对路径与 ``..`` 越界。
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def _contract_dir(self, project_id: str) -> Path:
        return self.project_root / "contracts" / project_id

    def _resolve(self, relative: str) -> Path:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or "\\" in relative:
            raise ProjectContractStoreError("合同存储路径必须是项目内相对路径")
        path = self.project_root.joinpath(*pure.parts).resolve()
        if not path.is_relative_to(self.project_root):
            raise ProjectContractStoreError("合同存储路径离开了项目目录")
        return path

    def save(self, contract: ProjectContract) -> None:
        encoded = _canonical_json(contract.model_dump(mode="json"))
        directory = self._contract_dir(contract.project_id)
        directory.mkdir(parents=True, exist_ok=True)
        relative = f"contracts/{contract.project_id}/v{contract.contract_version}.json"
        path = self._resolve(relative)
        if path.exists():
            if path.read_bytes() != encoded:
                raise ProjectContractStoreError(
                    "同一合同版本对应了不同内容，合同存储不可覆盖"
                )
            return
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def load_current(self, project_id: str) -> ProjectContract:
        """读取当前（最高版本）权威项目合同；缺失或解析失败失败关闭。"""
        directory = self._contract_dir(project_id)
        if not directory.is_dir():
            raise ProjectContractStoreError(
                f"项目合同存储中不存在当前合同：{project_id}"
            )
        versions: list[int] = []
        for entry in directory.iterdir():
            name = entry.name
            if name.startswith("v") and name.endswith(".json"):
                try:
                    versions.append(int(name[1:-5]))
                except ValueError:
                    continue
        if not versions:
            raise ProjectContractStoreError(
                f"项目合同存储中不存在当前合同：{project_id}"
            )
        highest = max(versions)
        path = directory / f"v{highest}.json"
        try:
            payload = json.loads(path.read_bytes())
        except (OSError, json.JSONDecodeError) as error:
            raise ProjectContractStoreError(
                f"当前项目合同读取失败：{project_id}"
            ) from error
        if not isinstance(payload, dict):
            raise ProjectContractStoreError("项目合同根节点必须是对象")
        contract = ProjectContract.model_validate(payload)
        if contract.project_id != project_id:
            raise ProjectContractStoreError("存储路径与合同项目不一致")
        return contract

    def reload(self, contract: ProjectContract) -> ProjectContract:
        """按同一版本重读：resume/重复读取不得漂移。"""
        path = self._resolve(
            f"contracts/{contract.project_id}/v{contract.contract_version}.json"
        )
        if not path.exists():
            raise ProjectContractStoreError(
                f"项目合同版本不存在：{contract.project_id} v{contract.contract_version}"
            )
        try:
            payload = json.loads(path.read_bytes())
        except (OSError, json.JSONDecodeError) as error:
            raise ProjectContractStoreError(
                f"项目合同读取失败：{contract.project_id}"
            ) from error
        if not isinstance(payload, dict):
            raise ProjectContractStoreError("项目合同根节点必须是对象")
        loaded = ProjectContract.model_validate(payload)
        if loaded != contract:
            raise ProjectContractStoreError("重读合同与持久化合同不一致，禁止漂移")
        return loaded
