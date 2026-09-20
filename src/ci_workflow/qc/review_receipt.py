"""R2 独立科学复核的不可变宿主回执合同（scientific-review-v1）。

设计合同（v1.3 §5.4/§13）：独立干净上下文复核不可由生产者自证；宿主无法
创建独立上下文时预检失败（不得主 Agent 自证）。本回执把一次真实发生的
独立科学复核绑定到可验证证据上：

- 生产上下文（``production``）：项目/报告类型/版本/对象/候选快照/候选内容
  摘要/生产者身份/生产者会话/标准版本/门槛结果键/生产完成时间/生产上下文
  摘要（``ScientificQcCurrentContext.context_digest``）；
- 复核上下文（``review``）：复核者身份、宿主可执行文件证据
  （``path_resolved|explicit|unavailable``）、独立宿主会话、真实外部复核
  进程（PID、完整 argv、起止时间、真实退出码）与独立上下文来源声明；
- 内容摘要（``content``）：被复核内容摘要（必须等于生产候选内容摘要）与
  审阅输入摘要；
- review artifact digest（``artifact``）：复核产物的项目相对路径与内容
  摘要（首版只绑定科学质控结论产物）；
- 时间顺序：``produced_at < process.started_at <= process.finished_at <=
  issued_at``（复核不得早于生产完成，签发不得早于复核完成）。

失败关闭（结构层即拒绝，不依赖调用方自觉）：

- ``status`` 由独立上下文证据确定性推导（``build_scientific_review_receipt``
  唯一构造路径），伪造 ``verified`` 状态在模型与 Schema 两层都失败关闭；
- 无独立上下文能力（宿主可执行文件 ``unavailable`` 或声明 ``unavailable``）
  ⇒ ``host_context_unavailable``：必须携带中文原因、不得绑定 review
  artifact、永远无法通过 ``require_verified_review_receipt`` 授权门；
- 同进程伪造（复核进程 PID == 会话启动进程 PID）、生产者自审、同会话
  复核、复核进程失败退出、argv 未绑定宿主可执行文件、时间倒挂、内容摘要
  不一致一律拒绝；
- ``receipt_digest`` 是除自身外全部字段的规范 JSON SHA-256（排序键、紧凑
  分隔符、无结尾换行，与 ``hosts.receipt`` 同一算法），构造即校验；
  ``model_copy`` 或手改 JSON 造成的摘要漂移由 ``verify_content_integrity``
  失败关闭。

三宿主可适配：``host`` 只接受 ``codex|hermes|omp``；回执结构不含宿主私有
字段，宿主差异只体现在运行身份取值。

分层边界：本合同属于科学质控授权链（绑定权威 ``ScientificQcCurrentContext``
并作为复核接受授权门），因此位于 ``qc`` 层；宿主适配层按 Task 9.4 权能
边界不得导入科学真源层，宿主只传递/呈现回执，裁决一律回到本层。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
    model_validator,
)
from pydantic import (
    ValidationError as PydanticValidationError,
)

from ci_workflow.hosts.receipt import (
    HostExecutableEvidence as ReviewExecutableEvidence,
)
from ci_workflow.hosts.receipt import (
    HostProcessBinding as ReviewProcessEvidence,
)
from ci_workflow.hosts.receipt import (
    HostSessionBinding as ReviewHostSession,
)
from ci_workflow.qc.scientific import ScientificQcCurrentContext

ReviewReceiptHost = Literal["codex", "hermes", "omp"]
ReviewReceiptStatus = Literal["verified", "host_context_unavailable"]
ReviewIndependenceProvenance = Literal["external_subprocess_session", "unavailable"]
ReviewExecutableProvenance = Literal["path_resolved", "explicit", "unavailable"]
ReviewArtifactKind = Literal["scientific_qc_verdict"]
REVIEW_RECEIPT_KIND = "scientific-review-v1"


class ScientificReviewReceiptError(ValueError):
    """独立复核回执越界：结构、伪造、绑定或授权门失败关闭。"""


class ScientificReviewReceiptIntegrityError(ScientificReviewReceiptError):
    """回执内容摘要与当前字段不一致（篡改或损坏）。"""


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("独立复核回执字段不能为空")
    return normalized


def _sha256_field(value: str) -> str:
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("独立复核回执摘要必须是小写 SHA-256")
    return value


def _posix_relative(value: str) -> str:
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "\\" in value or value == ".":
        raise ValueError("回执路径必须是 POSIX 相对路径且不得离开所属根目录")
    return _not_blank(value)


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("独立复核回执时间必须包含明确时区偏移")
    return value


def _canonical_json(value: object) -> bytes:
    # 与 hosts.receipt / application.host_smoke 同一规范化：排序键、紧凑
    # 分隔符、无结尾换行；保证字典路径与 pydantic 路径摘要一致。
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


class ReviewProductionContext(BaseModel):
    """生产上下文绑定：复核对象是谁、由谁在哪个会话与哪个门槛下生产。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    report_kind: Literal["A", "B", "C"]
    report_version: str
    report_object_id: str
    candidate_snapshot_id: str
    candidate_content_digest: str
    producer_id: str
    producer_session_id: str
    criteria_version: str
    gate_result_key: str
    produced_at: datetime
    production_context_digest: str

    @field_validator(
        "project_id",
        "report_version",
        "report_object_id",
        "candidate_snapshot_id",
        "producer_id",
        "producer_session_id",
        "criteria_version",
        "gate_result_key",
    )
    @classmethod
    def _identity_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("candidate_content_digest", "production_context_digest")
    @classmethod
    def _digests_are_sha256(cls, value: str) -> str:
        return _sha256_field(value)

    @field_validator("produced_at")
    @classmethod
    def _produced_at_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)


class ReviewContextEvidence(BaseModel):
    """复核上下文：独立宿主会话中的真实外部复核进程与独立性声明。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reviewer_id: str
    host_executable: ReviewExecutableEvidence
    session: ReviewHostSession
    process: ReviewProcessEvidence
    independent_context: ReviewIndependenceProvenance

    @field_validator("reviewer_id")
    @classmethod
    def _reviewer_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class ReviewContentBinding(BaseModel):
    """内容摘要绑定：被复核内容摘要与审阅输入摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reviewed_content_digest: str
    review_input_digest: str

    @field_validator("reviewed_content_digest", "review_input_digest")
    @classmethod
    def _digests_are_sha256(cls, value: str) -> str:
        return _sha256_field(value)


class ReviewArtifactBinding(BaseModel):
    """review artifact 绑定：产物类别、项目相对路径与内容摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_kind: ReviewArtifactKind
    path: str
    artifact_sha256: str

    @field_validator("path")
    @classmethod
    def _path_is_project_relative(cls, value: str) -> str:
        return _posix_relative(value)

    @field_validator("artifact_sha256")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        return _sha256_field(value)


class ScientificReviewReceipt(BaseModel):
    """唯一独立科学复核回执合同；除 ``receipt_digest`` 外全部字段参与内容摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    receipt_kind: Literal["scientific-review-v1"]
    host: ReviewReceiptHost
    status: ReviewReceiptStatus
    unavailable_reason_zh: str | None
    issued_at: datetime
    production: ReviewProductionContext
    review: ReviewContextEvidence
    content: ReviewContentBinding
    artifact: ReviewArtifactBinding | None = None
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
    def _receipt_is_fail_closed(self) -> ScientificReviewReceipt:
        executable_available = self.review.host_executable.provenance != "unavailable"
        independent = self.review.independent_context == "external_subprocess_session"
        if independent != executable_available:
            raise ValueError("独立上下文声明与宿主可执行文件证据矛盾：两者必须同态")
        if independent:
            if self.status != "verified":
                raise ValueError("真实独立上下文证据的回执不得标记 host_context_unavailable")
            if self.unavailable_reason_zh is not None:
                raise ValueError("verified 回执不得携带不可用原因")
            if self.artifact is None:
                raise ValueError("verified 回执必须绑定 review artifact 摘要")
            if self.review.process.returncode != 0:
                raise ValueError("复核进程未成功完成，不得签发 verified 回执")
            if list(self.review.process.argv[:1]) != [self.review.host_executable.path]:
                raise ValueError("复核进程完整 argv 必须以宿主可执行文件开头")
        else:
            if self.status != "host_context_unavailable":
                raise ValueError("无独立上下文能力却声称 verified：独立复核不接受主 Agent 自证")
            if self.unavailable_reason_zh is None:
                raise ValueError("host_context_unavailable 回执必须说明中文不可用原因")
            if self.artifact is not None:
                raise ValueError("无独立上下文的回执不得绑定 review artifact")
        if self.review.process.pid == self.review.session.launcher_pid:
            raise ValueError("同进程伪造：复核进程与会话启动进程相同，不构成独立上下文")
        if self.review.reviewer_id == self.production.producer_id:
            raise ValueError("复核者必须与候选快照生产者是不同身份")
        if self.review.session.session_id == self.production.producer_session_id:
            raise ValueError("复核会话必须与生产会话分离（同会话不构成独立上下文）")
        if self.content.reviewed_content_digest != self.production.candidate_content_digest:
            raise ValueError("内容摘要绑定不一致：复核内容摘要必须等于生产候选内容摘要")
        if not (self.production.produced_at < self.review.process.started_at):
            raise ValueError("时间顺序违例：复核不得早于（或同刻于）生产完成")
        if self.issued_at < self.review.process.finished_at:
            raise ValueError("时间顺序违例：回执签发不得早于复核进程结束")
        if self.receipt_digest != self.compute_content_digest(self):
            raise ValueError("独立复核回执内容摘要与字段不一致（摘要漂移）")
        return self

    @staticmethod
    def compute_content_digest(receipt: ScientificReviewReceipt) -> str:
        """按除 ``receipt_digest`` 外全部字段的规范 JSON 计算 SHA-256。"""
        material = receipt.model_dump(mode="json", exclude={"receipt_digest"})
        return hashlib.sha256(_canonical_json(material)).hexdigest()

    def verify_content_integrity(self) -> None:
        """复验当前内容摘要；``model_copy`` 篡改或手改 JSON 在此失败关闭。"""
        expected = self.compute_content_digest(self)
        if self.receipt_digest != expected:
            raise ScientificReviewReceiptIntegrityError(
                "独立复核回执内容摘要与当前字段不一致；回执已被篡改或损坏"
            )


def build_scientific_review_receipt(
    *,
    host: ReviewReceiptHost,
    issued_at: datetime,
    production: ReviewProductionContext,
    review: ReviewContextEvidence,
    content: ReviewContentBinding,
    artifact: ReviewArtifactBinding | None = None,
    unavailable_reason_zh: str | None = None,
) -> ScientificReviewReceipt:
    """以完整绑定材料构造回执并派生内容摘要（唯一受支持构造路径）。

    ``status`` 由独立上下文证据确定性推导（``unavailable`` ⇒
    ``host_context_unavailable``），调用方不得自报；``receipt_digest`` 在
    构造时即校验。
    """
    status: ReviewReceiptStatus = (
        "host_context_unavailable"
        if review.independent_context == "unavailable"
        or review.host_executable.provenance == "unavailable"
        else "verified"
    )
    draft = ScientificReviewReceipt.model_construct(
        schema_version="1.0",
        receipt_kind=REVIEW_RECEIPT_KIND,
        host=host,
        status=status,
        unavailable_reason_zh=unavailable_reason_zh,
        issued_at=issued_at,
        production=production,
        review=review,
        content=content,
        artifact=artifact,
        receipt_digest="0" * 64,
    )
    return ScientificReviewReceipt.model_validate(
        draft.model_dump(mode="json", exclude={"receipt_digest"})
        | {"receipt_digest": ScientificReviewReceipt.compute_content_digest(draft)}
    )


def require_verified_review_receipt(
    receipt: ScientificReviewReceipt,
    *,
    project_root: Path,
) -> ScientificReviewReceipt:
    """授权门：只有内容完整且 ``verified`` 的回执可以授权独立复核接受。

    无独立上下文能力（``host_context_unavailable``）、伪造状态或摘要漂移
    都在此失败关闭；调用方不得以分离布尔或调用方自报决定替代本门。
    """
    receipt.verify_content_integrity()
    if receipt.status != "verified":
        raise ScientificReviewReceiptError(
            "独立上下文能力缺失：host_context_unavailable 回执不能授权科学复核"
        )
    artifact = receipt.artifact
    if artifact is None:
        raise ScientificReviewReceiptError("verified 回执缺少复核产物绑定")
    project = project_root.expanduser().resolve()
    path = (project / artifact.path).resolve()
    if not path.is_relative_to(project) or not path.is_file():
        raise ScientificReviewReceiptError("复核产物不存在或不在项目目录内")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != artifact.artifact_sha256:
        raise ScientificReviewReceiptError("复核产物实际字节与回执摘要不一致")
    return receipt


def bind_receipt_to_production_context(
    receipt: ScientificReviewReceipt,
    context: ScientificQcCurrentContext,
) -> None:
    """把回执生产上下文逐字绑定到编排层权威 ``ScientificQcCurrentContext``。

    项目/报告类型/版本/对象/候选快照/候选内容摘要/生产者/标准版本/门槛
    结果键必须与当前上下文一致；``production_context_digest`` 必须等于当前
    上下文的 ``context_digest``（覆盖集/合同版本等经上下文摘要间接绑定）。
    任何不一致都以 ``ScientificReviewReceiptError`` 失败关闭。
    """
    production = receipt.production
    bindings: tuple[tuple[object, object, str], ...] = (
        (production.project_id, context.project_id, "项目"),
        (production.report_kind, context.report_kind.value, "报告类型"),
        (production.report_version, context.report_version, "报告版本"),
        (production.report_object_id, context.report_object_id, "报告对象"),
        (production.candidate_snapshot_id, context.candidate_snapshot_id, "候选快照"),
        (
            production.candidate_content_digest,
            context.candidate_content_digest,
            "候选内容摘要",
        ),
        (production.producer_id, context.producer_id, "生产者身份"),
        (production.criteria_version, context.criteria_version, "标准版本"),
        (production.gate_result_key, context.gate_result_key, "门槛结果键"),
        (production.production_context_digest, context.context_digest, "生产上下文摘要"),
    )
    for receipt_value, context_value, label in bindings:
        if receipt_value != context_value:
            raise ScientificReviewReceiptError(f"回执生产上下文{label}与当前权威上下文不一致")


def scientific_review_receipt_schema() -> dict[str, Any]:
    """解析打包的独立复核回执 Schema（Draft 2020-12），失败关闭。

    同时支持两种布局：仓库根 ``schemas/``（Codex 集成时随 ``package-manifest.json``
    清单注册生效）与打包安装布局（``ci_workflow/schemas/``，当前签发的唯一
    随包副本）；两处均缺失时以确定性错误失败关闭。
    """
    candidates: tuple[Path, ...] = (
        Path(__file__).resolve().parents[3] / "schemas" / "scientific-review-receipt.schema.json",
        Path(__file__).resolve().parents[1] / "schemas" / "scientific-review-receipt.schema.json",
    )
    for candidate in candidates:
        try:
            return cast(dict[str, Any], json.loads(candidate.read_text(encoding="utf-8")))
        except FileNotFoundError:
            continue
        except json.JSONDecodeError as error:
            raise ScientificReviewReceiptError(
                f"打包的独立复核回执 Schema 损坏：{candidate}"
            ) from error
    raise ScientificReviewReceiptError(
        "无法定位打包的独立复核回执 Schema（源码树与安装布局均缺失）"
    )


def validate_scientific_review_receipt_payload(
    raw: dict[str, Any],
) -> ScientificReviewReceipt:
    """生产回执验证器：按序执行打包 Schema → Pydantic 模型（含全部语义）。

    任一阶段失败都以确定性的 ``ScientificReviewReceiptError`` 失败关闭，
    绝不让 Schema 违例或伪造状态的载荷进入复核授权路径。
    """
    schema = scientific_review_receipt_schema()
    try:
        Draft202012Validator(schema).validate(raw)
    except JsonSchemaValidationError as error:
        raise ScientificReviewReceiptError(
            f"独立复核回执不符合打包 Schema（scientific-review-receipt）：{error.message}"
        ) from error
    try:
        return ScientificReviewReceipt.model_validate(raw)
    except PydanticValidationError as error:
        raise ScientificReviewReceiptError(f"独立复核回执模型校验失败：{error}") from error
