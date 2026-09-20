"""Task 9.4 HA01 宿主回执合同：唯一真实运行回执（与 HA09 证据对接）。

``HostReceipt`` 把一次真实宿主冒烟运行绑定到可复核证据：已安装包（名称/
版本/摘要）、fixture 案例与逐文件摘要、真实安装入口、宿主可执行文件/版本
及其 ``path_resolved|explicit|unavailable`` 来源、启动进程与外部子进程
（PID、完整 argv、开始/结束时间、真实退出码）、会话、项目/运行、事件链
（数量与摘要）、no-draft 断言与最终 manifest（路径/摘要/manifest_digest）。

关键证据阻断语义（PRD：缺关键证据不生成草稿）：``state == "blocked"`` 的
回执必须零产物且 ``no_draft`` 为真；``complete / partially_delivered``
必须至少绑定一个站点式 HTML 产物（ADR 0013）。

内容寻址与防篡改：``receipt_digest`` 是除自身外全部字段的规范 JSON
SHA-256（与 ``application.host_smoke.receipt_digest`` 同一算法：排序键、
紧凑分隔符、无结尾换行），构造即校验；``model_copy`` 或手改字段造成的
摘要漂移由 ``verify_content_integrity`` 失败关闭。

同进程伪造、旧回执与 adapter-only JSON 的真实性裁决属于 HA09 验证器
（对照项目当前状态）；本合同在结构层即拒绝：非外部子进程、外部进程与
启动进程同 PID、宿主来源 ``unavailable`` 却声称通过、退出码缺失等。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

HostReceiptHost = Literal["codex", "hermes", "omp"]
HostReceiptStatus = Literal["verified", "host_unavailable"]
# CanonicalProjectState 的终态子集：回执只在运行到达终态时签发。
HostReceiptRunState = Literal["complete", "partially_delivered", "blocked"]
HostRunOutcome = Literal["rendered", "evidence_blocked"]
HostEntryKind = Literal["console_script", "python_module"]
HostExecutableProvenance = Literal["path_resolved", "explicit", "unavailable"]
RECEIPT_KIND = "host-smoke-v1"


class HostReceiptIntegrityError(RuntimeError):
    """宿主回执内容摘要与当前字段不一致（篡改或损坏）。"""


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("宿主回执字段不能为空")
    return normalized


def _sha256_field(value: str) -> str:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("宿主回执摘要必须是小写 SHA-256")
    return value


def _posix_relative(value: str) -> str:
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "\\" in value or value == ".":
        raise ValueError("回执路径必须是 POSIX 相对路径且不得离开所属根目录")
    return _not_blank(value)


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("宿主回执时间必须包含明确时区偏移")
    return value


def _canonical_json(value: object) -> bytes:
    # 与 application.host_smoke.receipt_digest 同一规范化：排序键、紧凑
    # 分隔符、无结尾换行；保证字典路径与 pydantic 路径摘要一致。
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


class HostPackageBinding(BaseModel):
    """已安装包绑定：名称、版本与包内容摘要（重装后旧回执失败关闭）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    version: str
    package_digest: str

    @field_validator("name", "version")
    @classmethod
    def _identity_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("package_digest")
    @classmethod
    def _package_digest_is_sha256(cls, value: str) -> str:
        return _sha256_field(value)


class HostEntryBinding(BaseModel):
    """真实安装入口绑定：控制台脚本或解释器模块入口及其摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: HostEntryKind
    command: tuple[str, ...] = Field(min_length=1)
    resolved_path: str
    sha256: str

    @field_validator("command")
    @classmethod
    def _command_parts_not_blank(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_not_blank(part) for part in value)

    @field_validator("resolved_path")
    @classmethod
    def _resolved_path_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        return _sha256_field(value)


class HostExecutableEvidence(BaseModel):
    """宿主可执行文件证据：来源三态；``unavailable`` 不得携带路径或版本。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provenance: HostExecutableProvenance
    path: str | None = None
    resolved_realpath: str | None = None
    version: str | None = None

    @model_validator(mode="after")
    def _evidence_matches_provenance(self) -> HostExecutableEvidence:
        if self.provenance == "unavailable":
            if any((self.path, self.resolved_realpath, self.version)):
                raise ValueError("宿主不可用证据不得携带可执行文件路径或版本")
            return self
        if not self.path or not self.version:
            raise ValueError("真实宿主证据必须携带可执行文件路径与版本")
        return self


class HostSessionBinding(BaseModel):
    """会话绑定：会话标识与启动进程（及其父进程）PID。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    launcher_pid: int = Field(ge=1)
    launcher_parent_pid: int = Field(ge=1)

    @field_validator("session_id")
    @classmethod
    def _session_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class HostProcessBinding(BaseModel):
    """真实外部子进程绑定；adapter 自报或同进程执行无法满足本结构。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["external_subprocess"]
    pid: int = Field(ge=1)
    argv: tuple[str, ...] = Field(min_length=1)
    cwd: str
    started_at: datetime
    finished_at: datetime
    returncode: int
    stdout_tail: str = ""
    stderr_tail: str = ""

    @field_validator("cwd")
    @classmethod
    def _cwd_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("started_at", "finished_at")
    @classmethod
    def _times_have_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _timeline_is_consistent(self) -> HostProcessBinding:
        if self.finished_at < self.started_at:
            raise ValueError("外部进程结束时间不得早于开始时间")
        return self


class HostFixtureBinding(BaseModel):
    """fixture 案例绑定：案例标识、case digest 与逐文件摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    case_digest: str
    inputs: dict[str, str] = Field(min_length=1)

    @field_validator("case_id")
    @classmethod
    def _case_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("case_digest")
    @classmethod
    def _case_digest_is_sha256(cls, value: str) -> str:
        return _sha256_field(value)

    @field_validator("inputs")
    @classmethod
    def _input_digests_are_sha256(cls, value: dict[str, str]) -> dict[str, str]:
        for digest in value.values():
            _sha256_field(digest)
        return {_posix_relative(path): digest for path, digest in value.items()}


class HostArtifactBinding(BaseModel):
    """回执内逐产物绑定：项目相对入口路径与内容摘要。

    首版真实输出只有站点式 HTML（ADR 0013），非 html 产物绑定失败关闭。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    report: Literal["A", "B", "C"]
    output: Literal["html"]
    entry_relative_path: str
    entry_sha256: str

    @field_validator("entry_relative_path")
    @classmethod
    def _entry_is_project_relative(cls, value: str) -> str:
        return _posix_relative(value)

    @field_validator("entry_sha256")
    @classmethod
    def _entry_digest_is_sha256(cls, value: str) -> str:
        return _sha256_field(value)


class HostRunEvidence(BaseModel):
    """运行终态证据：no-draft 断言、退出码、产物绑定与语义摘要。

    ``state`` 三态决定产物与断言：``blocked`` 必须零产物且 ``no_draft``
    为真（缺关键证据不生成草稿）；``complete / partially_delivered`` 必须
    至少绑定一个站点式 HTML 产物且 ``no_draft`` 为假。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_root: str
    run_id: str
    project_id: str
    state: HostReceiptRunState
    outcome: HostRunOutcome | None
    no_draft: bool
    exit_code: int
    semantic_receipt_digest: str
    artifacts: tuple[HostArtifactBinding, ...]

    @field_validator("project_root", "run_id", "project_id")
    @classmethod
    def _identity_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("semantic_receipt_digest")
    @classmethod
    def _semantic_digest_is_sha256(cls, value: str) -> str:
        return _sha256_field(value)

    @model_validator(mode="after")
    def _state_determines_draft_and_artifacts(self) -> HostRunEvidence:
        if self.state == "blocked":
            if self.artifacts:
                raise ValueError("关键证据阻断的回执必须零产物（不得生成草稿）")
            if not self.no_draft:
                raise ValueError("关键证据阻断的回执必须携带 no-draft 断言")
            if self.outcome != "evidence_blocked":
                raise ValueError("阻断回执的运行结果必须是 evidence_blocked")
        else:
            if not self.artifacts:
                raise ValueError("已交付回执必须至少绑定一个站点式 HTML 产物")
            if self.no_draft:
                raise ValueError("携带产物的回执不得同时声明 no-draft")
            expected_outcome = "rendered" if self.state == "complete" else None
            if self.outcome != expected_outcome:
                raise ValueError("运行结果与终态不一致")
        return self


class HostEventChainBinding(BaseModel):
    """规范事件链绑定：事件数量与流摘要（旧回执对照失败关闭）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_count: int = Field(ge=1)
    stream_digest: str

    @field_validator("stream_digest")
    @classmethod
    def _stream_digest_is_sha256(cls, value: str) -> str:
        return _sha256_field(value)


class HostInterruptionBinding(BaseModel):
    """恢复前的关键证据阻断与 no-draft 负断言。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    project_id: str
    outcome: Literal["evidence_blocked"]
    exit_code: Literal[4]
    no_draft: Literal[True]
    report_file_count: Literal[0]
    manifest_relative_path: str
    manifest_sha256: str
    manifest_digest: str
    event_count: int = Field(ge=1)
    event_stream_digest: str

    @field_validator("run_id", "project_id")
    @classmethod
    def _identity_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("manifest_sha256", "manifest_digest", "event_stream_digest")
    @classmethod
    def _digests_are_sha256(cls, value: str) -> str:
        return _sha256_field(value)

    @field_validator("manifest_relative_path")
    @classmethod
    def _manifest_path_is_relative(cls, value: str) -> str:
        return _posix_relative(value)


class HostRecoveryBinding(BaseModel):
    """用户补件后的显式重开、报告目标重绑与输入摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reason: Literal["user_material_accepted"]
    reopen_event_id: str
    reopen_event_digest: str
    rebind_event_id: str
    rebind_event_digest: str
    input_relative_path: str
    input_sha256: str

    @field_validator("reopen_event_id", "rebind_event_id")
    @classmethod
    def _event_ids_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("reopen_event_digest", "rebind_event_digest", "input_sha256")
    @classmethod
    def _digests_are_sha256(cls, value: str) -> str:
        return _sha256_field(value)

    @field_validator("input_relative_path")
    @classmethod
    def _input_path_is_relative(cls, value: str) -> str:
        return _posix_relative(value)


class HostManifestBinding(BaseModel):
    """最终运行清单绑定：项目相对路径、内容摘要与 manifest 自摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str
    run_id: str
    outcome: HostRunOutcome | None
    manifest_digest: str

    @field_validator("path")
    @classmethod
    def _path_is_project_relative(cls, value: str) -> str:
        return _posix_relative(value)

    @field_validator("sha256", "manifest_digest")
    @classmethod
    def _digests_are_sha256(cls, value: str) -> str:
        return _sha256_field(value)

    @field_validator("run_id")
    @classmethod
    def _run_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class HostReceipt(BaseModel):
    """唯一宿主回执合同；除 ``receipt_digest`` 外全部字段参与内容摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    receipt_kind: Literal["host-smoke-v1"]
    host: HostReceiptHost
    status: HostReceiptStatus
    unavailable_reason_zh: str | None
    issued_at: datetime
    package: HostPackageBinding
    entry: HostEntryBinding
    host_executable: HostExecutableEvidence
    session: HostSessionBinding
    process: HostProcessBinding
    fixture: HostFixtureBinding
    interruption: HostInterruptionBinding | None = None
    recovery: HostRecoveryBinding | None = None
    run: HostRunEvidence
    event_chain: HostEventChainBinding
    manifest: HostManifestBinding
    receipt_digest: str

    @field_validator("unavailable_reason_zh")
    @classmethod
    def _reason_is_chinese_text_or_absent(cls, value: str | None) -> str | None:
        return None if value is None else _not_blank(value)

    @field_validator("issued_at")
    @classmethod
    def _issued_at_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @field_validator("receipt_digest")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        return _sha256_field(value)

    @model_validator(mode="after")
    def _receipt_is_internally_consistent(self) -> HostReceipt:
        unavailable = self.host_executable.provenance == "unavailable"
        expected_status: HostReceiptStatus = (
            "host_unavailable" if unavailable else "verified"
        )
        if self.status != expected_status:
            raise ValueError(
                "宿主来源为 unavailable 却声称通过：status 必须与宿主证据来源一致"
                if self.status == "verified"
                else "真实宿主证据的回执不得标记 host_unavailable"
            )
        if unavailable and self.unavailable_reason_zh is None:
            raise ValueError("host_unavailable 回执必须说明中文不可用原因")
        if not unavailable and self.unavailable_reason_zh is not None:
            raise ValueError("verified 回执不得携带不可用原因")
        if self.process.pid == self.session.launcher_pid:
            raise ValueError("同进程伪造：外部进程与会话启动进程相同")
        entry_command = list(self.entry.command)
        host_command = [str(self.host_executable.path)]
        direct = list(self.process.argv[: len(entry_command)]) == entry_command
        via_host = (
            self.host_executable.provenance != "unavailable"
            and list(self.process.argv[:1]) == host_command
        )
        if not direct and not via_host:
            raise ValueError("外部进程完整 argv 必须以真实安装入口或宿主入口开头")
        if direct and self.process.returncode != self.run.exit_code:
            raise ValueError("直接入口进程退出码与运行退出码不一致")
        if via_host and self.host_executable.provenance == "path_resolved":
            if (
                self.process.returncode != 0
                or "HOST_SMOKE_DONE exit=0" not in self.process.stdout_tail
                or self.interruption is None
                or self.recovery is None
                or self.run.state != "complete"
            ):
                raise ValueError("真实宿主进程未确认公共 Skill 的阻断、补件恢复和验证")
        elif via_host and (
            self.process.returncode != 0
            or "HOST_SMOKE_DONE exit=4" not in self.process.stdout_tail
        ):
            raise ValueError("显式宿主替身未确认公共 Skill 的 no-draft 运行")
        if self.manifest.run_id != self.run.run_id:
            raise ValueError("最终清单与运行证据的运行标识不一致")
        if self.manifest.outcome != self.run.outcome:
            raise ValueError("最终清单与运行证据的结果不一致")
        if self.receipt_digest != self.compute_content_digest(self):
            raise ValueError("宿主回执内容摘要与字段不一致（摘要漂移）")
        return self

    @staticmethod
    def compute_content_digest(receipt: HostReceipt) -> str:
        """按除 ``receipt_digest`` 外全部字段的规范 JSON 计算 SHA-256。"""
        material = receipt.model_dump(mode="json", exclude={"receipt_digest"})
        return hashlib.sha256(_canonical_json(material)).hexdigest()

    def verify_content_integrity(self) -> None:
        """复验当前内容摘要；``model_copy`` 篡改或手改 JSON 在此失败关闭。"""
        expected = self.compute_content_digest(self)
        if self.receipt_digest != expected:
            raise HostReceiptIntegrityError(
                "宿主回执内容摘要与当前字段不一致；回执已被篡改或损坏"
            )


def build_host_receipt(
    *,
    host: HostReceiptHost,
    issued_at: datetime,
    package: HostPackageBinding,
    entry: HostEntryBinding,
    host_executable: HostExecutableEvidence,
    session: HostSessionBinding,
    process: HostProcessBinding,
    fixture: HostFixtureBinding,
    interruption: HostInterruptionBinding | None = None,
    recovery: HostRecoveryBinding | None = None,
    run: HostRunEvidence,
    event_chain: HostEventChainBinding,
    manifest: HostManifestBinding,
    unavailable_reason_zh: str | None = None,
) -> HostReceipt:
    """以完整绑定材料构造回执并派生内容摘要（唯一受支持构造路径）。

    ``status`` 由宿主证据来源确定性推导（``unavailable`` ⇒ ``host_unavailable``），
    调用方不得自报；``receipt_digest`` 在构造时即校验。
    """
    status: HostReceiptStatus = (
        "host_unavailable"
        if host_executable.provenance == "unavailable"
        else "verified"
    )
    draft = HostReceipt.model_construct(
        schema_version="1.0",
        receipt_kind=RECEIPT_KIND,
        host=host,
        status=status,
        unavailable_reason_zh=unavailable_reason_zh,
        issued_at=issued_at,
        package=package,
        entry=entry,
        host_executable=host_executable,
        session=session,
        process=process,
        fixture=fixture,
        interruption=interruption,
        recovery=recovery,
        run=run,
        event_chain=event_chain,
        manifest=manifest,
        receipt_digest="0" * 64,
    )
    return HostReceipt.model_validate(
        draft.model_dump(mode="json", exclude={"receipt_digest"})
        | {"receipt_digest": HostReceipt.compute_content_digest(draft)}
    )
