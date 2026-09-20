"""独立科学复核签发入口：真实执行证据是 ``scientific-review-v1`` 回执的
唯一签发来源（Astra P1-1 裁决修复）。

本入口供**独立复核宿主会话**（不得是生产者会话）重复调用：

1. 绑定现有请求：只接受运行时发布的权威生产上下文
   （``reload_production_context``）与唯一科学复核请求
   （``state/scientific_review/<kind>/review_request.json``，含请求摘要
   核验）；请求与当前候选上下文不一致即拒绝；
2. 真实 reviewer/producer 分离：复核者身份、复核会话与请求中的生产者
   身份/会话逐字比较，相同即在**任何执行前**失败关闭；
3. runner/host 执行证据：``review.process`` 只能来自本入口真实启动的
   外部复核子进程（PID、完整 argv、起止时间、退出码、输出尾部），
   argv 必须以宿主可执行文件开头；宿主可执行文件不可用、进程失败退出、
   进程时间出现在未来（注入时钟裁决）一律拒绝签发；
4. 正式 verdict 字节：回执只绑定通过打包 Schema/模型/语义校验、且与
   当前权威上下文一致的接受结论实际文件字节（``accepted_verdict_from_receipt``
   复核结论绑定、时间窗与有效期）；
5. 真实签发记录：回执落盘的同时写入同源签发记录
   （``state/scientific_review/<kind>/issuance.json``，含记录摘要）；
   ``verify_receipt_issuance`` 把回执与记录逐字段交叉核验，只有自洽
   JSON、没有真实签发记录的伪造回执（含测试进程内手工构造的自洽回执）
   一律失败关闭。

失败关闭边界：不引入 PKI、签名服务或第二套回执体系；签发记录复用既有
回执类型字段并按 ``hosts.receipt`` 同一规范化算法计算摘要。分层边界：
授权裁决仍属 ``qc.review_receipt`` 与 ``scientific_review_transition``；
本模块只做真实执行接线，绝不放宽任何既有授权门。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Final

from pydantic import ValidationError as PydanticValidationError

from ci_workflow.application.scientific_review_transition import (
    ScientificReviewTransitionError,
    accepted_verdict_from_receipt,
    load_scientific_review_receipt,
    reload_production_context,
    scientific_review_receipt_path,
    scientific_review_request_path,
)
from ci_workflow.capabilities.scientific_qc import (
    ScientificQcBoundaryError,
    validate_scientific_qc_verdict_payload,
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
from ci_workflow.qc.review_receipt import (
    ReviewArtifactBinding,
    ReviewContentBinding,
    ReviewContextEvidence,
    ReviewProductionContext,
    ReviewReceiptHost,
    ScientificReviewReceipt,
    build_scientific_review_receipt,
)

REVIEW_ISSUANCE_RECORD_KIND: Final = "scientific-review-issuance-v1"
_DEFAULT_TIMEOUT_SECONDS: Final = 3600.0
_STDOUT_TAIL_CHARS: Final = 2000
_VERSION_PROBE_TIMEOUT_SECONDS: Final = 30.0

ReviewClock = Callable[[], datetime]


class ReviewIssuanceError(ValueError):
    """独立复核签发入口失败关闭：绑定、分离、执行或结论核验不通过。"""


@dataclass(frozen=True)
class ExternalProcessResult:
    """一次真实外部进程运行的结果证据。"""

    pid: int
    argv: tuple[str, ...]
    cwd: str
    started_at: datetime
    finished_at: datetime
    returncode: int
    stdout_tail: str = ""
    stderr_tail: str = ""


ReviewProcessRunner = Callable[[tuple[str, ...], str, float], ExternalProcessResult]


@dataclass(frozen=True)
class ReviewIssuanceOutcome:
    """一次成功签发的回执与真实签发记录落盘位置。"""

    receipt: ScientificReviewReceipt
    receipt_path: Path
    record_path: Path


def run_external_process(
    argv: tuple[str, ...], cwd: str, timeout: float
) -> ExternalProcessResult:
    """生产运行器：真实启动外部复核子进程并捕获运行证据。"""

    started_at = datetime.now(UTC)
    try:
        process = subprocess.Popen(
            argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except OSError as error:
        raise ReviewIssuanceError(f"复核进程启动失败：{error}") from error
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        process.kill()
        process.communicate()
        raise ReviewIssuanceError("复核进程超时未结束，拒绝签发") from error
    finished_at = datetime.now(UTC)
    return ExternalProcessResult(
        pid=process.pid,
        argv=tuple(argv),
        cwd=cwd,
        started_at=started_at,
        finished_at=finished_at,
        returncode=process.returncode if process.returncode is not None else -1,
        stdout_tail=(stdout or b"").decode("utf-8", errors="replace")[
            -_STDOUT_TAIL_CHARS:
        ],
        stderr_tail=(stderr or b"").decode("utf-8", errors="replace")[
            -_STDOUT_TAIL_CHARS:
        ],
    )


def _system_clock() -> datetime:
    return datetime.now(UTC)


def _launcher_parent_pid(pid: int) -> int:
    try:
        output = subprocess.run(
            ("ps", "-o", "ppid=", "-p", str(pid)),
            capture_output=True,
            timeout=10.0,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as error:
        raise ReviewIssuanceError(f"无法查询宿主会话启动进程的父进程：{error}") from error
    if output.returncode != 0:
        raise ReviewIssuanceError("无法查询宿主会话启动进程的父进程（ps 失败）")
    text = (output.stdout or b"").decode("utf-8", errors="replace").strip()
    if not text.isdigit() or int(text) < 1:
        raise ReviewIssuanceError("宿主会话启动进程的父进程标识无效")
    return int(text)


def _current_host_session(session_id: str) -> ReviewHostSession:
    """从当前进程推导宿主会话绑定：启动进程为本进程真实父进程。"""

    launcher_pid = os.getppid()
    return ReviewHostSession(
        session_id=session_id,
        launcher_pid=launcher_pid,
        launcher_parent_pid=_launcher_parent_pid(launcher_pid),
    )


def _probe_version(executable: str, run: ReviewProcessRunner) -> str:
    result = run(
        (executable, "--version"), os.getcwd(), _VERSION_PROBE_TIMEOUT_SECONDS
    )
    if result.returncode != 0:
        raise ReviewIssuanceError(
            f"宿主可执行文件版本探测失败（退出码 {result.returncode}）"
        )
    lines = result.stdout_tail.strip().splitlines()
    if not lines or not lines[0].strip():
        raise ReviewIssuanceError("宿主可执行文件版本探测输出为空")
    return lines[0].strip()


def resolve_host_executable(
    host: ReviewReceiptHost,
    *,
    explicit_path: str | None = None,
    runner: ReviewProcessRunner | None = None,
) -> ReviewExecutableEvidence:
    """解析宿主可执行文件证据：显式路径或 PATH 真实解析，版本真实探测。"""

    run = runner if runner is not None else run_external_process
    if explicit_path is not None:
        path = Path(explicit_path).expanduser()
        if not path.is_file():
            raise ReviewIssuanceError(f"宿主可执行文件不存在：{explicit_path}")
        resolved = str(path.resolve())
        return ReviewExecutableEvidence(
            provenance="explicit",
            path=explicit_path,
            resolved_realpath=resolved,
            version=_probe_version(resolved, run),
        )
    discovered = shutil.which(host)
    if discovered is None:
        raise ReviewIssuanceError(
            f"宿主可执行文件在 PATH 中不可用：{host}；无独立上下文能力，拒绝签发"
        )
    resolved = str(Path(discovered).resolve())
    return ReviewExecutableEvidence(
        provenance="path_resolved",
        path=discovered,
        resolved_realpath=resolved,
        version=_probe_version(resolved, run),
    )


def _validated_kind(report_kind: str) -> str:
    if report_kind not in ("A", "B", "C"):
        raise ReviewIssuanceError(
            f"独立复核签发入口只适用于 A/B/C 类报告：{report_kind!r}"
        )
    return report_kind


def _canonical_json_bytes(value: object) -> bytes:
    # 与 hosts.receipt / qc.review_receipt / scientific_review_transition
    # 同一规范化：排序键、紧凑分隔符、无结尾换行。
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _body_digest(body: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(body) + b"\n").hexdigest()


def _read_request_body(project_root: Path, kind: str) -> tuple[dict[str, Any], str]:
    path = project_root / scientific_review_request_path(kind)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReviewIssuanceError("科学复核请求缺失或损坏，拒绝签发") from error
    if not isinstance(raw, dict):
        raise ReviewIssuanceError("科学复核请求必须是 JSON 对象")
    digest = raw.pop("request_digest", None)
    body = {key: value for key, value in raw.items()}
    if not isinstance(digest, str) or digest != _body_digest(body):
        raise ReviewIssuanceError("科学复核请求摘要漂移：请求已被篡改或损坏")
    return body, digest


def _load_published_request(
    project_root: Path,
    kind: str,
    context_digest: str,
) -> tuple[ReviewProductionContext, str, str]:
    body, digest = _read_request_body(project_root, kind)
    scientific_context = body.get("scientific_context")
    if (
        not isinstance(scientific_context, dict)
        or scientific_context.get("context_digest") != context_digest
    ):
        raise ReviewIssuanceError("科学复核请求不属于当前候选上下文，拒绝签发")
    try:
        production = ReviewProductionContext.model_validate(body.get("production"))
    except PydanticValidationError as error:
        raise ReviewIssuanceError("科学复核请求中的生产身份无效") from error
    review_input_digest = body.get("review_input_digest")
    if not isinstance(review_input_digest, str):
        raise ReviewIssuanceError("科学复核请求缺少审阅输入摘要")
    return production, review_input_digest, digest


def review_issuance_record_path(report_kind: str) -> PurePosixPath:
    """真实签发记录的确定性项目相对路径。"""

    kind = _validated_kind(report_kind)
    return PurePosixPath("state") / "scientific_review" / kind / "issuance.json"


def _bind_formal_verdict(
    project_root: Path, verdict_relative_path: str
) -> ReviewArtifactBinding:
    pure = PurePosixPath(verdict_relative_path)
    if (
        pure.is_absolute()
        or ".." in pure.parts
        or "\\" in verdict_relative_path
        or verdict_relative_path == "."
    ):
        raise ReviewIssuanceError("复核结论路径必须是项目内 POSIX 相对路径")
    path = project_root / pure
    if not path.is_file():
        raise ReviewIssuanceError(f"复核结论产物不存在：{verdict_relative_path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReviewIssuanceError("复核结论产物不可读或不是有效 JSON") from error
    if not isinstance(raw, dict):
        raise ReviewIssuanceError("复核结论产物必须是 JSON 对象")
    try:
        validate_scientific_qc_verdict_payload(raw)
    except ScientificQcBoundaryError as error:
        raise ReviewIssuanceError(f"正式质控结论验证失败：{error}") from error
    return ReviewArtifactBinding(
        artifact_kind="scientific_qc_verdict",
        path=verdict_relative_path,
        artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def issue_review_receipt(
    *,
    project_root: Path,
    report_kind: str,
    reviewer_id: str,
    review_session_id: str,
    host: ReviewReceiptHost,
    host_executable: ReviewExecutableEvidence,
    review_argv: Sequence[str],
    verdict_relative_path: str,
    session: ReviewHostSession | None = None,
    runner: ReviewProcessRunner | None = None,
    clock: ReviewClock | None = None,
) -> ReviewIssuanceOutcome:
    """运行真实独立复核进程并签发绑定现有请求的正式回执（唯一签发入口）。

    ``runner``/``clock``/``session`` 是测试 seam；生产路径必须使用默认
    真实实现。任何绑定、分离、执行、结论或落盘前核验失败都不产生回执。
    """

    kind = _validated_kind(report_kind)
    run = runner if runner is not None else run_external_process
    now = clock if clock is not None else _system_clock
    root = project_root.expanduser().resolve()

    try:
        context = reload_production_context(root, kind)
    except ScientificReviewTransitionError as error:
        raise ReviewIssuanceError(f"权威生产上下文未就绪：{error}") from error
    production, review_input_digest, request_digest = _load_published_request(
        root, kind, context.context_digest
    )

    if reviewer_id == production.producer_id:
        raise ReviewIssuanceError(
            "复核者与生产者身份相同：生产者自审不构成独立复核，拒绝签发"
        )
    if review_session_id == production.producer_session_id:
        raise ReviewIssuanceError(
            "复核会话与生产者会话相同：同会话复核不构成独立上下文，拒绝签发"
        )
    if session is not None and session.session_id != review_session_id:
        raise ReviewIssuanceError("复核会话标识与会话绑定不一致，拒绝签发")

    if host_executable.provenance == "unavailable" or not host_executable.path:
        raise ReviewIssuanceError("宿主可执行文件不可用：无独立上下文能力，拒绝签发")
    argv = (host_executable.path, *(str(part) for part in review_argv))
    if len(argv) < 2:
        raise ReviewIssuanceError("请提供宿主可执行文件之后的复核命令参数")

    result = run(argv, str(root), _DEFAULT_TIMEOUT_SECONDS)
    issued_at = now()
    if result.returncode != 0:
        raise ReviewIssuanceError(
            f"复核进程失败退出（退出码 {result.returncode}），拒绝签发"
        )
    if result.started_at > issued_at or result.finished_at > issued_at:
        raise ReviewIssuanceError("复核进程时间出现在未来：拒绝签发")

    artifact = _bind_formal_verdict(root, verdict_relative_path)
    resolved_session = (
        session if session is not None else _current_host_session(review_session_id)
    )
    try:
        receipt = build_scientific_review_receipt(
            host=host,
            issued_at=issued_at,
            production=production,
            review=ReviewContextEvidence(
                reviewer_id=reviewer_id,
                host_executable=host_executable,
                session=resolved_session,
                process=ReviewProcessEvidence(
                    kind="external_subprocess",
                    pid=result.pid,
                    argv=result.argv,
                    cwd=result.cwd,
                    started_at=result.started_at,
                    finished_at=result.finished_at,
                    returncode=result.returncode,
                    stdout_tail=result.stdout_tail,
                    stderr_tail=result.stderr_tail,
                ),
                independent_context="external_subprocess_session",
            ),
            content=ReviewContentBinding(
                reviewed_content_digest=production.candidate_content_digest,
                review_input_digest=review_input_digest,
            ),
            artifact=artifact,
        )
    except (PydanticValidationError, ValueError) as error:
        raise ReviewIssuanceError(f"独立复核回执构造被拒绝：{error}") from error

    try:
        accepted_verdict_from_receipt(project_root=root, context=context, receipt=receipt)
    except ScientificReviewTransitionError as error:
        raise ReviewIssuanceError(f"复核结论不能授权签发：{error}") from error

    receipt_path = root / scientific_review_receipt_path(kind)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_payload = receipt.model_dump(mode="json")
    record: dict[str, Any] = {
        "record_kind": REVIEW_ISSUANCE_RECORD_KIND,
        "report_kind": kind,
        "request_digest": request_digest,
        "receipt_digest": receipt.receipt_digest,
        "host": receipt_payload["host"],
        "reviewer_id": receipt_payload["review"]["reviewer_id"],
        "issued_at": receipt_payload["issued_at"],
        "process": receipt_payload["review"]["process"],
        "artifact": receipt_payload["artifact"],
    }
    record["record_digest"] = _body_digest(record)
    record_path = root / review_issuance_record_path(kind)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(_canonical_json_bytes(record) + b"\n")
    receipt_path.write_bytes(_canonical_json_bytes(receipt_payload) + b"\n")
    return ReviewIssuanceOutcome(
        receipt=receipt, receipt_path=receipt_path, record_path=record_path
    )


def verify_receipt_issuance(
    project_root: Path,
    report_kind: str,
    *,
    checked_at: datetime | None = None,
) -> ScientificReviewReceipt:
    """授权前的真实签发核验：回执必须与真实签发记录逐字段一致。

    只有自洽 JSON、没有真实签发记录；记录被篡改；回执在签发后被替换；
    请求已为其他候选重新发布——全部失败关闭。通过核验时返回完整验证的
    回执；调用方仍须执行 ``qc`` 层授权门与本项目的候选绑定核验。
    """

    kind = _validated_kind(report_kind)
    root = project_root.expanduser().resolve()
    record_path = root / review_issuance_record_path(kind)
    if not record_path.is_file():
        raise ReviewIssuanceError(
            "真实签发记录缺失：只有自洽 JSON、没有经签发入口的回执不被接受"
        )
    try:
        raw = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReviewIssuanceError("真实签发记录不可读或不是有效 JSON") from error
    if not isinstance(raw, dict) or raw.get("record_kind") != REVIEW_ISSUANCE_RECORD_KIND:
        raise ReviewIssuanceError("真实签发记录类别无效")
    digest = raw.pop("record_digest", None)
    body = {key: value for key, value in raw.items()}
    if not isinstance(digest, str) or digest != _body_digest(body):
        raise ReviewIssuanceError("真实签发记录摘要漂移：记录已被篡改或损坏")

    _, current_request_digest = _read_request_body(root, kind)
    if raw.get("request_digest") != current_request_digest:
        raise ReviewIssuanceError("签发记录不属于当前候选的科学复核请求")

    try:
        receipt = load_scientific_review_receipt(root, kind)
    except ScientificReviewTransitionError as error:
        raise ReviewIssuanceError(f"回执验证失败：{error}") from error
    payload = receipt.model_dump(mode="json")
    expected: tuple[tuple[str, object], ...] = (
        ("receipt_digest", receipt.receipt_digest),
        ("report_kind", kind),
        ("host", payload["host"]),
        ("reviewer_id", payload["review"]["reviewer_id"]),
        ("issued_at", payload["issued_at"]),
        ("process", payload["review"]["process"]),
        ("artifact", payload["artifact"]),
    )
    for field, value in expected:
        if raw.get(field) != value:
            raise ReviewIssuanceError(
                f"真实签发记录与回执的 {field} 不一致：回执可能已被替换"
            )
    verified_at = _system_clock() if checked_at is None else checked_at
    if verified_at.tzinfo is None or verified_at.utcoffset() is None:
        raise ReviewIssuanceError("签发核验时间必须包含明确时区")
    if verified_at < receipt.issued_at:
        raise ReviewIssuanceError("签发核验时间早于回执签发时间")
    context = reload_production_context(root, kind)
    try:
        verdict = accepted_verdict_from_receipt(
            project_root=root, context=context, receipt=receipt
        )
    except ScientificReviewTransitionError as error:
        raise ReviewIssuanceError(f"回执不能授权当前候选：{error}") from error
    if verdict.valid_until <= verified_at:
        raise ReviewIssuanceError("科学质控接受结论在签发核验时已失效")
    return receipt


__all__ = [
    "ExternalProcessResult",
    "ReviewClock",
    "ReviewIssuanceError",
    "ReviewIssuanceOutcome",
    "ReviewProcessRunner",
    "issue_review_receipt",
    "resolve_host_executable",
    "review_issuance_record_path",
    "run_external_process",
    "verify_receipt_issuance",
]
