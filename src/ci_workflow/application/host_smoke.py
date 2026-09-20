"""Task 9.4 HA09–HA10：host-smoke-v1 真实入口运行器、宿主回执与失败关闭验证器。

宿主回执与 HA01 的语义回执（``HostSemanticReceipt``）互补：语义回执只承载
三宿主一致的比较面；本模块把一次冒烟运行绑定到可复核的真实证据——已安装
包与真实安装入口、宿主可执行文件/版本、外部子进程、会话、运行、事件链与
最终 manifest（PRD 验收 6/7）。

失败关闭合同：
- 同进程伪造三宿主：单回执的外部进程 pid 等于会话启动进程，或三宿主回执
  共享会话、外部进程或运行标识，一律拒绝；
- 旧回执：manifest 摘要或事件链与项目当前状态不一致即拒绝；
- adapter-only JSON：缺少真实外部进程证据（kind 不是 external_subprocess、
  缺 pid/argv/退出码）或缺回执合同字段，一律拒绝。

诚实性合同：``real_host_pass`` 只有在三宿主回执全部验证通过、且宿主可执行
文件均来自 PATH 真实解析（provenance=path_resolved）时才为真；显式提供或
测试替身不构成真实宿主通过。Task 9.5 fresh-install 复验前不得据此主张
真实宿主通过。
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError

import ci_workflow
from ci_workflow.application.fixture_runner import (
    FixtureCaseError,
    _get_case_root_base,
    _load_catalog,
    _load_fixture_schema,
    _resolve_case_dir,
    _validate_catalog,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.hosts.receipt import (
    HostArtifactBinding,
    HostEntryBinding,
    HostEventChainBinding,
    HostExecutableEvidence,
    HostFixtureBinding,
    HostInterruptionBinding,
    HostManifestBinding,
    HostPackageBinding,
    HostProcessBinding,
    HostReceipt,
    HostReceiptHost,
    HostReceiptIntegrityError,
    HostRecoveryBinding,
    HostRunEvidence,
    HostSessionBinding,
    build_host_receipt,
)
from ci_workflow.storage.event_store import EventStore, EventStoreError
from ci_workflow.storage.manifest_store import ArtifactManifest

HOSTS: tuple[str, ...] = ("codex", "hermes", "omp")
SMOKE_CASE_ID = "host-smoke-v1"
PACKAGE_NAME = "competitive-intelligence-workflow"

_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CATALOG = _ROOT / "fixtures" / "catalog.yaml"
# 安装包根：包内目录随 wheel 分发（fresh-install 定位）；仓库根服务于
# editable 开发安装。宿主回执的 package_digest / Schema 双副本据此定位。
_PACKAGE_ROOT = Path(ci_workflow.__file__).resolve().parent
_PACKAGED_SCHEMA = _PACKAGE_ROOT / "schemas" / "host-receipt.schema.json"
_ROOT_SCHEMA = _ROOT / "schemas" / "host-receipt.schema.json"
_PACKAGE_MANIFEST_CANDIDATES: tuple[Path, ...] = (
    _PACKAGE_ROOT / "package-manifest.json",
    _ROOT / "package-manifest.json",
)
_EXPECTED_EXIT_CODES: dict[str, int] = {"evidence_blocked": 4, "rendered": 0}
_EXPECTED_MANIFEST_OUTCOMES: dict[str, str] = {
    "evidence_blocked": "evidence_blocked",
    "rendered": "completed",
}
_VERSION_PROBE_TIMEOUT_SECONDS = 15
_SMOKE_TIMEOUT_SECONDS = 7200
_TAIL_CHARS = 400
_HOST_COMPLETION_MARKER = "HOST_SMOKE_DONE exit=0"


class HostSmokeError(RuntimeError):
    """真实入口冒烟运行失败或环境证据不成立（诚实失败，不产回执）。"""


class HostSmokeReceiptError(ValueError):
    """宿主回执验证失败关闭：伪造、旧回执或 adapter-only JSON。"""


# ─── 共享工具 ───────────────────────────────────────────────────────────────


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HostSmokeReceiptError("宿主回执必须是有限、可序列化的 JSON") from exc


def receipt_digest(receipt: dict[str, Any]) -> str:
    """回执自摘要：对除 ``receipt_digest`` 外的全部字段做规范化 SHA-256。

    与 ``hosts.receipt.HostReceipt.compute_content_digest`` 同一算法
    （hosts 合同测试按字典路径钉住本函数）；保留为字典路径的等价伙伴。
    """
    return _sha256_bytes(
        _canonical_json({k: v for k, v in receipt.items() if k != "receipt_digest"})
    )


def _host_receipt_schema_validators() -> tuple[Draft202012Validator, ...]:
    """加载回执 JSON Schema 校验器：包内副本必在，根副本存在时一并校验。"""
    paths = [_PACKAGED_SCHEMA]
    if _ROOT_SCHEMA.is_file():
        paths.append(_ROOT_SCHEMA)
    validators: list[Draft202012Validator] = []
    for path in paths:
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            validator = Draft202012Validator(schema)
            Draft202012Validator.check_schema(schema)
        except (OSError, json.JSONDecodeError, JsonSchemaError) as exc:
            raise HostSmokeError(f"无法加载宿主回执 Schema：{path}（{exc}）") from exc
        validators.append(validator)
    return tuple(validators)


def validate_receipt_against_schemas(dumped: dict[str, Any]) -> None:
    """按根/包内双份 host-receipt Schema 校验回执字典；失败关闭。"""
    try:
        for validator in _host_receipt_schema_validators():
            validator.validate(dumped)
    except JsonSchemaValidationError as exc:
        raise HostSmokeReceiptError(
            f"宿主回执不符合 host-receipt Schema：{exc.message}（路径：{list(exc.absolute_path)}）"
        ) from exc


# ─── 真实安装入口解析 ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class RealEntry:
    """已安装包真实入口的解析结果（回执绑定材料）。"""

    kind: Literal["console_script", "python_module"]
    command: tuple[str, ...]
    resolved_path: Path
    sha256: str


def resolve_real_entry(explicit: Path | None = None) -> RealEntry:
    """解析真实安装入口：显式指定优先，其次 PATH/同解释器目录的控制台脚本，
    最后退回当前解释器的 ``-m ci_workflow``（同为已安装包的外部进程入口）。

    注意不把 ``sys.executable`` 先 resolve 再找同级脚本：venv 的 python 常是
    指向系统解释器的符号链接，resolve 会跳出 venv 目录。
    """
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    else:
        found = shutil.which("ci-workflow")
        if found:
            candidates.append(Path(found))
        candidates.append(Path(sys.executable).parent / "ci-workflow")
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return RealEntry(
                kind="console_script",
                command=(str(candidate),),
                resolved_path=candidate,
                sha256=_sha256_bytes(candidate.read_bytes()),
            )
    if explicit is not None:
        raise HostSmokeError(f"指定的真实安装入口不可用：{explicit}")
    # venv 依赖解释器按原路径启动（resolve 后直跑真实二进制会丢失 venv
    # site-packages）；摘要仍按真实文件位置计算，命令按原路径记录。
    interpreter = Path(sys.executable)
    return RealEntry(
        kind="python_module",
        command=(str(interpreter), "-m", "ci_workflow"),
        resolved_path=interpreter.resolve(),
        sha256=_sha256_bytes(interpreter.read_bytes()),
    )


# ─── 宿主可执行文件证据 ────────────────────────────────────────────────────


def resolve_host_executable(
    host: str, *, explicit: Path | None = None
) -> tuple[dict[str, Any], str | None]:
    """解析宿主可执行文件并读取版本，返回 (证据, 不可用原因)。

    可执行文件名必须与宿主名精确一致，否则不构成该宿主的证据；版本经真实
    ``--version`` 子进程读取，任何失败都按宿主不可用处理（失败关闭）。
    返回值始终是合同三态证据：可用时 ``path_resolved|explicit`` 并携带
    路径/版本，不可用时 ``unavailable`` 且三字段为空。
    """
    if explicit is not None:
        path: Path | None = explicit
        provenance = "explicit"
    else:
        found = shutil.which(host)
        path = Path(found) if found else None
        provenance = "path_resolved"
    unavailable = {
        "provenance": "unavailable",
        "path": None,
        "resolved_realpath": None,
        "version": None,
    }
    if path is None:
        return unavailable, f"未在 PATH 上找到宿主 {host} 的可执行文件"
    if path.name != host:
        return unavailable, f"可执行文件名 {path.name} 与宿主 {host} 不一致，不构成宿主证据"
    if not path.is_file() or not os.access(path, os.X_OK):
        return unavailable, f"宿主可执行文件不存在或不可执行：{path}"
    try:
        probe = subprocess.run(
            [str(path), "--version"],
            capture_output=True,
            text=True,
            timeout=_VERSION_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return unavailable, f"无法读取宿主 {host} 版本：{exc}"
    combined = f"{probe.stdout}\n{probe.stderr}"
    first_line = next((line.strip() for line in combined.splitlines() if line.strip()), "")
    if probe.returncode != 0 or not first_line:
        return unavailable, f"宿主 {host} 版本探针失败（退出码 {probe.returncode}）"
    evidence: dict[str, Any] = {
        "provenance": provenance,
        # 记录发现路径（文件名与宿主名一致，可经符号链接定位）；真实路径
        # 另行记录供诊断，验证器只按发现路径做名称绑定。
        "path": str(path.absolute()),
        "resolved_realpath": str(path.resolve()),
        "version": first_line[:200],
    }
    return evidence, None


# ─── fixture catalog 绑定 ──────────────────────────────────────────────────


def _load_smoke_case(
    catalog_path: Path | None,
) -> tuple[dict[str, Any], Path]:
    """完整校验唯一 fixture catalog，返回 (host-smoke-v1 案例, 案例目录)。

    复用 fixture_runner 的 catalog/摘要/逐输入校验与案例摘要实现，保证
    host-smoke 绑定与 fixture 真源使用同一套摘要语义（不复制业务逻辑）。
    """
    resolved = (catalog_path or _DEFAULT_CATALOG).expanduser().resolve()
    try:
        catalog = _load_catalog(resolved)
        cases = _validate_catalog(
            catalog,
            case_root_base=_get_case_root_base(resolved),
            schema=_load_fixture_schema(),
        )
    except FixtureCaseError as exc:
        raise HostSmokeError(f"fixture catalog 校验失败：{exc}") from exc
    case = cases.get(SMOKE_CASE_ID)
    if case is None:
        raise HostSmokeError(f"唯一 fixture catalog 未登记 {SMOKE_CASE_ID} 案例")
    return case, _resolve_case_dir(_get_case_root_base(resolved), SMOKE_CASE_ID)


def _locate_package_manifest() -> Path:
    """从安装入口对应包根定位 package-manifest.json；找不到则诚实失败。

    Codex 裁决：``package.package_digest`` 是当前安装包内
    package-manifest.json **原始字节**的 SHA-256。定位顺序：包内副本
    （随 wheel 分发，Task 9.5 fresh-install 生效）→ 仓库根（editable
    开发安装）。两处都没有时不以版本号代替内容摘要，直接失败关闭。
    """
    for candidate in _PACKAGE_MANIFEST_CANDIDATES:
        if candidate.is_file():
            return candidate
    searched = "、".join(str(candidate) for candidate in _PACKAGE_MANIFEST_CANDIDATES)
    raise HostSmokeError(f"安装包内找不到 package-manifest.json（已检索：{searched}）")


def _installed_package_identity() -> dict[str, str]:
    """已安装包身份：发行版名称/版本 + 包内 package-manifest.json 字节摘要。"""
    try:
        version = metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError as exc:
        raise HostSmokeError(
            "无法确定已安装包版本（真实入口绑定要求已安装发行版）"
        ) from exc
    manifest_path = _locate_package_manifest()
    return {
        "name": PACKAGE_NAME,
        "version": version,
        "package_digest": _sha256_bytes(manifest_path.read_bytes()),
    }


_ADAPTER_BY_HOST: dict[str, str] = {
    "codex": "CodexHostAdapter",
    "hermes": "HermesHostAdapter",
    "omp": "OmpHostAdapter",
}


def _semantic_receipt_digest(host: str, project_root: Path) -> str:
    """由该宿主薄适配器组装语义回执并计算规范摘要。

    摘要在同一项目状态上确定性可复算；能力矩阵等环境相关字段使其只在
    运行时点稳定，验证器不按当前环境重算，只保留结构校验（见验证器注释）。
    惰性导入：验证器路径不触发适配器与能力探针。
    """
    import ci_workflow.hosts as hosts_package

    adapter_cls = getattr(hosts_package, _ADAPTER_BY_HOST[host], None)
    if adapter_cls is None:  # pragma: no cover - 适配器注册表与 HOSTS 同步维护
        raise HostSmokeError(f"缺少宿主 {host} 的薄适配器实现")
    semantic = adapter_cls().build_semantic_receipt(project_root=project_root)
    return _sha256_bytes(
        json.dumps(
            semantic.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


def _run_evidence(
    manifest: dict[str, Any],
    *,
    project_root: Path,
    host: str,
    returncode: int,
) -> HostRunEvidence:
    """由最终 manifest 组装运行终态证据（no-draft 断言与产物绑定）。"""
    outcome = manifest.get("outcome")
    project_id = manifest.get("project_id")
    run_id = manifest.get("run_id")
    if not isinstance(project_id, str) or not project_id:
        raise HostSmokeError("当前清单缺少项目标识")
    if not isinstance(run_id, str) or not run_id:
        raise HostSmokeError("当前清单缺少运行标识")
    semantic_digest = _semantic_receipt_digest(host, project_root)
    if outcome == "evidence_blocked":
        return HostRunEvidence(
            project_root=str(project_root),
            run_id=run_id,
            project_id=project_id,
            state="blocked",
            outcome="evidence_blocked",
            no_draft=True,
            exit_code=returncode,
            semantic_receipt_digest=semantic_digest,
            artifacts=(),
        )
    if outcome != "completed":
        raise HostSmokeError(f"最终 manifest 结果不支持回执绑定：{outcome}")
    artifacts: list[HostArtifactBinding] = []
    for output in (*manifest.get("outputs", []), *manifest.get("reused_artifacts", [])):
        rel_path = output.get("relative_path", "")
        parts = rel_path.split("/")
        if len(parts) < 2 or parts[0] != "reports" or parts[1] not in ("A", "B", "C"):
            continue
        entry_relative_path = rel_path
        entry_sha256 = output.get("sha256", "")
        if rel_path.endswith("/html.manifest.json"):
            manifest_path = project_root / rel_path
            try:
                artifact_manifest = ArtifactManifest.model_validate_json(
                    manifest_path.read_text(encoding="utf-8")
                )
            except (OSError, ValidationError) as exc:
                raise HostSmokeError(
                    f"站点式 HTML 产物清单不可读：{rel_path}"
                ) from exc
            if artifact_manifest.report != parts[1]:
                raise HostSmokeError(f"站点式 HTML 产物清单报告类型不一致：{rel_path}")
            entry_relative_path = (
                f"{artifact_manifest.artifact.relative_path}/overview.html"
            )
            entry_path = project_root / entry_relative_path
            if not entry_path.is_file():
                raise HostSmokeError(f"站点式 HTML 首页不存在：{entry_relative_path}")
            entry_sha256 = _sha256_bytes(entry_path.read_bytes())
        elif "/html/" not in f"/{rel_path}" and not rel_path.endswith("/html"):
            continue
        artifacts.append(
            HostArtifactBinding(
                report=parts[1],
                output="html",
                entry_relative_path=entry_relative_path,
                entry_sha256=entry_sha256,
            )
        )
    if not artifacts:
        raise HostSmokeError("completed 结果缺少可绑定的站点式 HTML 产物")
    return HostRunEvidence(
        project_root=str(project_root),
        run_id=run_id,
        project_id=project_id,
        state="complete",
        outcome="rendered",
        no_draft=False,
        exit_code=returncode,
        semantic_receipt_digest=semantic_digest,
        artifacts=tuple(artifacts),
    )


# ─── 真实入口冒烟运行器 ────────────────────────────────────────────────────


def run_host_smoke(
    host: str,
    *,
    project_root: Path,
    entry: RealEntry | None = None,
    host_executable: Path | None = None,
    session_id: str | None = None,
    catalog_path: Path | None = None,
    resume: bool = False,
    require_external_host_process: bool = False,
    hermes_resume_session: str | None = None,
    hermes_provider: str | None = None,
    hermes_model: str | None = None,
    hermes_reasoning: str | None = None,
) -> HostReceipt:
    """在独立外部子进程中经真实安装入口运行 host-smoke-v1 并组装宿主回执。

    返回唯一 ``HostReceipt`` 合同模型（可直接 ``model_validate`` 复验，并
    通过根/包内双份 host-receipt Schema 自检）；需要 JSON 时由调用方显式
    ``model_dump(mode="json")``。运行结果与 catalog 预期不一致时诚实失败
    （不产回执）；宿主可执行文件证据缺失时产 ``provenance="unavailable"``
    证据块（status 由合同推导为 host_unavailable，不冒充真实宿主通过）。
    """
    if host not in HOSTS:
        raise HostSmokeError(f"未知宿主：{host}（可用：{'、'.join(HOSTS)}）")
    project_root = project_root.expanduser().resolve()
    real_entry = entry if entry is not None else resolve_real_entry()
    case, _case_dir = _load_smoke_case(catalog_path)
    expected_outcome = "rendered" if require_external_host_process else case["expected"]["outcome"]
    expected_exit = _EXPECTED_EXIT_CODES.get(expected_outcome)
    if expected_exit is None:
        raise HostSmokeError(f"host-smoke 案例预期结果不支持冒烟绑定：{expected_outcome}")

    workflow_argv = [
        *real_entry.command,
        "fixture",
        "run",
        "--case",
        SMOKE_CASE_ID,
        "--reports",
        ",".join(case["reports"]),
        "--outputs",
        ",".join(case["outputs"]),
        "--project",
        str(project_root),
    ]
    if catalog_path is not None:
        workflow_argv.extend(["--catalog", str(catalog_path.expanduser().resolve())])
    if resume:
        workflow_argv.append("--resume")

    host_evidence, unavailable_reason = resolve_host_executable(host, explicit=host_executable)
    if require_external_host_process:
        workflow_argv.append("--host-smoke-recovery")
        host_path = host_evidence.get("path")
        if not isinstance(host_path, str):
            raise HostSmokeError(unavailable_reason or f"真实宿主 {host} 不可用")
        skill_path = _ROOT / "skills" / "competitive-intelligence-workflow" / "SKILL.md"
        recovery_instruction = (
            "这是同一项目的恢复运行，不得重新初始化、清空或换目录。"
            "执行候选包fixture运行命令时必须带 --resume，保留 --host-smoke-recovery；"
            "先核验原项目合同、输入和检查点，再续接尚未完成步骤。"
            if resume else "这是新项目运行；首次fixture执行不要带 --resume。"
        )
        prompt = (
            "这是候选包真实宿主验收。请完整读取已安装公共 Skill："
            f"{skill_path}。不要使用源码工程的内部说明，也不要等待额外指令。"
            "请按该 Skill 的「候选包宿主验收」步骤，自行发现并运行已安装入口，"
            f"候选运行入口位于 {real_entry.command[0]}。"
            f"对案例 {SMOKE_CASE_ID} 和项目目录 {project_root} 完成能力预检、"
            "关键证据不足时不生成草稿、补件恢复、站点式 HTML 生成和项目验证。"
            f"{recovery_instruction}"
            "全部成功后最终只回复："
            f"{_HOST_COMPLETION_MARKER}"
        )
        if host == "codex":
            argv = [
                host_path,
                "exec",
                "--skip-git-repo-check",
                "--sandbox",
                "danger-full-access",
                "-C",
                str(_ROOT),
                prompt,
            ]
        elif host == "hermes":
            argv = [
                host_path,
                "chat",
                "-Q",
                "--oneshot",
                "--in",
                str(_ROOT),
                "--run-budget",
                "7200",
                "--max-turns",
                "128",
            ]
            if hermes_resume_session:
                argv.extend(["--resume", hermes_resume_session, "--no-restore-cwd"])
            if hermes_provider:
                argv.extend(["--provider", hermes_provider])
            if hermes_model:
                argv.extend(["--model", hermes_model])
            if hermes_reasoning:
                argv.extend(["--reasoning", hermes_reasoning])
            argv.extend(["-q", prompt])
        else:
            argv = [
                host_path,
                "--print",
                "--no-session",
                "--cwd",
                str(_ROOT),
                "--max-time",
                "120m",
                "--approval-mode",
                "yolo",
                prompt,
            ]
    else:
        argv = workflow_argv

    session = session_id or stable_id(
        "host-smoke-session", host, datetime.now(UTC).isoformat(), os.urandom(8).hex()
    )
    started_at = datetime.now(UTC)
    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=_SMOKE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.communicate()
        raise HostSmokeError("真实入口冒烟运行超时，未产回执") from exc
    finished_at = datetime.now(UTC)
    if process.returncode is None:  # pragma: no cover - communicate 已等待退出
        raise HostSmokeError("外部进程未返回退出码")
    returncode = process.returncode

    manifest_path = project_root / "manifests" / "current_run.json"
    if not manifest_path.is_file():
        raise HostSmokeError(
            "真实入口运行后缺少当前运行清单"
            f"（退出码 {returncode}；stderr 末尾：{stderr[-_TAIL_CHARS:]!r}）"
        )
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HostSmokeError("真实入口运行后当前清单不是有效 JSON") from exc
    if not isinstance(manifest, dict):
        raise HostSmokeError("真实入口运行后当前清单不是对象")
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise HostSmokeError("当前清单缺少运行标识")
    if manifest.get("case_id") != SMOKE_CASE_ID:
        raise HostSmokeError(
            f"当前清单案例绑定不符：期望 {SMOKE_CASE_ID}，实际 {manifest.get('case_id')}"
        )
    expected_manifest_outcome = _EXPECTED_MANIFEST_OUTCOMES.get(expected_outcome)
    if expected_manifest_outcome is None:
        raise HostSmokeError(f"host-smoke 案例结果无法映射到运行清单：{expected_outcome}")
    if manifest.get("outcome") != expected_manifest_outcome:
        raise HostSmokeError(
            "真实入口结果与预期不符："
            f"案例期望 {expected_outcome}（运行清单应为 {expected_manifest_outcome}），"
            f"实际 {manifest.get('outcome')}"
        )
    if require_external_host_process:
        if returncode != 0 or _HOST_COMPLETION_MARKER not in stdout:
            raise HostSmokeError(
                "真实宿主未完成公共 Skill 冒烟："
                f"宿主退出码 {returncode}；stdout 末尾：{stdout[-_TAIL_CHARS:]!r}；"
                f"stderr 末尾：{stderr[-_TAIL_CHARS:]!r}"
            )
    elif returncode != expected_exit:
        raise HostSmokeError(f"真实入口退出码与预期不符：期望 {expected_exit}，实际 {returncode}")

    try:
        events = EventStore(project_root).read_all()
        stream_digest = EventStore(project_root).stream_digest()
    except EventStoreError as exc:
        raise HostSmokeError(f"真实入口运行后事件链不可读：{exc}") from exc

    scenario_record: dict[str, Any] | None = None
    if require_external_host_process:
        scenario_path = project_root / "state/host-smoke-v1.json"
        try:
            loaded = json.loads(scenario_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HostSmokeError("真实宿主没有留下完整的阻断与恢复记录") from exc
        if not isinstance(loaded, dict):
            raise HostSmokeError("真实宿主的阻断与恢复记录不是 JSON 对象")
        scenario_record = loaded

    package_identity = _installed_package_identity()
    run_evidence = _run_evidence(
        manifest,
        project_root=project_root,
        host=host,
        returncode=expected_exit,
    )
    try:
        receipt_model = build_host_receipt(
            host=cast(HostReceiptHost, host),
            issued_at=datetime.now(UTC),
            package=HostPackageBinding(**package_identity),
            entry=HostEntryBinding(
                kind=real_entry.kind,
                command=tuple(real_entry.command),
                resolved_path=str(real_entry.resolved_path),
                sha256=real_entry.sha256,
            ),
            host_executable=HostExecutableEvidence(**host_evidence),
            session=HostSessionBinding(
                session_id=session,
                launcher_pid=os.getpid(),
                launcher_parent_pid=os.getppid(),
            ),
            process=HostProcessBinding(
                kind="external_subprocess",
                pid=process.pid,
                argv=tuple(argv),
                cwd=os.getcwd(),
                started_at=started_at,
                finished_at=finished_at,
                returncode=returncode,
                stdout_tail=stdout[-_TAIL_CHARS:],
                stderr_tail=stderr[-_TAIL_CHARS:],
            ),
            fixture=HostFixtureBinding(
                case_id=SMOKE_CASE_ID,
                case_digest=case["case_digest"],
                inputs={inp["path"]: inp["sha256"] for inp in case["inputs"]},
            ),
            interruption=(
                HostInterruptionBinding(**scenario_record["initial"])
                if scenario_record is not None
                else None
            ),
            recovery=(
                HostRecoveryBinding(**scenario_record["recovery"])
                if scenario_record is not None
                else None
            ),
            run=run_evidence,
            event_chain=HostEventChainBinding(
                event_count=len(events),
                stream_digest=stream_digest,
            ),
            manifest=HostManifestBinding(
                path="manifests/current_run.json",
                sha256=_sha256_bytes(manifest_bytes),
                run_id=manifest.get("run_id", ""),
                outcome=(
                    "evidence_blocked"
                    if expected_outcome == "evidence_blocked"
                    else "rendered"
                ),
                manifest_digest=str(manifest.get("manifest_digest", "")),
            ),
            unavailable_reason_zh=unavailable_reason,
        )
    except ValidationError as exc:
        raise HostSmokeError(f"宿主回执组装失败（绑定材料不满足合同）：{exc}") from exc
    # 返回前自检：合同模型可直接复验，且通过根/包内双份 Schema。
    try:
        receipt_model.verify_content_integrity()
        validate_receipt_against_schemas(receipt_model.model_dump(mode="json"))
    except HostReceiptIntegrityError as exc:
        raise HostSmokeError(f"宿主回执组装失败：{exc}") from exc
    except HostSmokeReceiptError as exc:
        raise HostSmokeError(f"宿主回执组装失败：{exc}") from exc
    return receipt_model


# ─── 回执验证器（失败关闭） ─────────────────────────────────────────────────


def verify_host_smoke_receipt(
    receipt: object,
    *,
    project_root: Path,
    catalog_path: Path | None = None,
) -> None:
    """按 HA09 合同验证宿主回执；任何证据缺口都失败关闭。

    结构层（字段齐全性、回执自摘要、外部子进程、同 PID、argv 前缀、
    状态/来源一致性、no-draft 与产物互斥）由 ``ci_workflow.hosts.receipt``
    的 ``HostReceipt`` 合同失败关闭；本验证器在此基础上对照**项目当前
    状态**裁决真实性：已安装包（含 package_digest）、真实安装入口文件、
    宿主可执行文件、fixture（唯一 catalog 逐文件摘要与 case digest）、
    运行与最终 manifest、事件链（旧回执即被拒绝）与 no-draft 磁盘事实。
    ``semantic_receipt_digest`` 依赖运行时能力矩阵，只在运行时点稳定，
    验证器保留其结构校验、不按当前环境重算。
    """
    if not isinstance(receipt, (dict, HostReceipt)):
        raise HostSmokeReceiptError("宿主回执必须是 JSON 对象（adapter 语义状态不是宿主回执）")

    # R01 结构层：HostReceipt 合同模型（字段、枚举、互斥与自摘要派生）。
    # 模型实例也走 model_dump→model_validate 全量复验，防 model_copy 绕过校验。
    try:
        candidate = receipt.model_dump(mode="json") if isinstance(receipt, HostReceipt) else receipt
        model = HostReceipt.model_validate(candidate)
    except ValidationError as exc:
        raise HostSmokeReceiptError(
            f"宿主回执结构验证失败（伪造/损坏/adapter-only）：{exc}"
        ) from exc

    # R02 内容完整性与双份 JSON Schema（包内副本必校验；根副本存在时一并校验）
    try:
        model.verify_content_integrity()
    except HostReceiptIntegrityError as exc:
        raise HostSmokeReceiptError(f"宿主回执结构验证失败：{exc}") from exc
    dumped = model.model_dump(mode="json")
    validate_receipt_against_schemas(dumped)

    host = model.host

    # R03 已安装包绑定（名称/版本/package_digest 对照当前安装）
    installed = _installed_package_identity_for_verify()
    if (
        model.package.name != installed["name"]
        or model.package.version != installed["version"]
        or model.package.package_digest != installed["package_digest"]
    ):
        raise HostSmokeReceiptError(
            "宿主回执验证失败：包绑定与当前安装的发行版不一致（旧安装回执失败关闭）"
        )

    # R04 真实安装入口文件绑定（磁盘存在 + 摘要一致）
    entry_path = Path(model.entry.resolved_path)
    if not entry_path.is_file():
        raise HostSmokeReceiptError("宿主回执验证失败：真实安装入口文件不存在")
    if _sha256_bytes(entry_path.read_bytes()) != model.entry.sha256:
        raise HostSmokeReceiptError(
            "宿主回执验证失败：真实安装入口摘要与当前文件不一致（重装后旧回执失败关闭）"
        )

    # R05 宿主可执行文件名称绑定（unavailable 三态已由合同校验）
    if model.host_executable.provenance != "unavailable":
        exe_path = Path(str(model.host_executable.path))
        if exe_path.name != host:
            raise HostSmokeReceiptError(
                f"宿主回执验证失败：可执行文件名 {exe_path.name} 与宿主 {host} 不一致"
            )
        if not exe_path.is_file():
            raise HostSmokeReceiptError("宿主回执验证失败：宿主可执行文件不存在")

    # R07 fixture 绑定（唯一 catalog、逐文件摘要、case digest）
    case, case_dir = _load_smoke_case_for_verify(catalog_path)
    if model.fixture.case_id != SMOKE_CASE_ID:
        raise HostSmokeReceiptError("宿主回执验证失败：fixture 未绑定 host-smoke 案例")
    if model.fixture.case_digest != case["case_digest"]:
        raise HostSmokeReceiptError("宿主回执验证失败：fixture case_digest 与唯一 catalog 不一致")
    declared_inputs = {inp["path"]: inp["sha256"] for inp in case["inputs"]}
    if dict(model.fixture.inputs) != declared_inputs:
        raise HostSmokeReceiptError("宿主回执验证失败：fixture 逐文件摘要与唯一 catalog 不一致")
    for rel_path, declared_sha in declared_inputs.items():
        actual = case_dir / rel_path
        if not actual.is_file() or _sha256_bytes(actual.read_bytes()) != declared_sha:
            raise HostSmokeReceiptError(
                f"宿主回执验证失败：fixture 输入文件摘要不匹配：{rel_path}"
            )
    entry_prefix = tuple(model.process.argv[: len(model.entry.command)])
    direct = entry_prefix == model.entry.command
    is_real_host_recovery = (
        not direct and model.host_executable.provenance == "path_resolved"
    )
    expected_outcome = (
        "rendered" if is_real_host_recovery else case["expected"]["outcome"]
    )
    expected_exit = _EXPECTED_EXIT_CODES.get(expected_outcome)
    expected_manifest_outcome = _EXPECTED_MANIFEST_OUTCOMES.get(expected_outcome)
    if expected_exit is None or expected_manifest_outcome is None:
        raise HostSmokeReceiptError("宿主回执验证失败：catalog 预期结果不支持冒烟绑定")
    expected_process_exit = expected_exit if direct else 0
    if model.process.returncode != expected_process_exit:
        raise HostSmokeReceiptError(
            "宿主回执验证失败：外部进程退出码与运行方式不符"
            f"（期望 {expected_process_exit}）"
        )
    expected_marker = _HOST_COMPLETION_MARKER if is_real_host_recovery else "HOST_SMOKE_DONE exit=4"
    if not direct and expected_marker not in model.process.stdout_tail:
        raise HostSmokeReceiptError("宿主回执验证失败：真实宿主未确认公共 Skill 运行")

    # R08 运行与最终 manifest 绑定（对照项目当前状态，旧回执失败关闭）
    resolved_root = project_root.expanduser().resolve()
    if Path(model.run.project_root) != resolved_root:
        raise HostSmokeReceiptError(
            "宿主回执验证失败：回执绑定的项目目录与验证目标不一致"
        )
    manifest_path = resolved_root / "manifests" / "current_run.json"
    if not manifest_path.is_file():
        raise HostSmokeReceiptError("宿主回执验证失败：项目缺少当前运行清单")
    manifest_bytes = manifest_path.read_bytes()
    if _sha256_bytes(manifest_bytes) != model.manifest.sha256:
        raise HostSmokeReceiptError(
            "宿主回执验证失败：旧回执——当前 manifest 摘要与回执不一致"
        )
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HostSmokeReceiptError("宿主回执验证失败：当前清单不是有效 JSON") from exc
    if not isinstance(manifest, dict):
        raise HostSmokeReceiptError("宿主回执验证失败：当前清单不是对象")
    if manifest.get("run_id") != model.run.run_id:
        raise HostSmokeReceiptError(
            "宿主回执验证失败：旧回执——当前 manifest 已属于另一运行"
        )
    if manifest.get("outcome") != expected_manifest_outcome:
        raise HostSmokeReceiptError("宿主回执验证失败：manifest 结果与 catalog 预期不一致")
    if manifest.get("case_id") != SMOKE_CASE_ID:
        raise HostSmokeReceiptError("宿主回执验证失败：manifest 未绑定 host-smoke 案例")
    if manifest.get("case_digest") != case["case_digest"]:
        raise HostSmokeReceiptError("宿主回执验证失败：manifest 案例 digest 与 catalog 不一致")

    # no-draft 断言对照磁盘事实：阻断回执零报告文件；交付回执产物逐一存在且摘要一致
    reports_root = resolved_root / "reports"
    report_files = (
        [p for p in reports_root.rglob("*") if p.is_file()] if reports_root.is_dir() else []
    )
    if model.run.no_draft:
        if report_files:
            raise HostSmokeReceiptError(
                "宿主回执验证失败：no-draft 断言与项目当前状态不一致（存在报告文件）"
            )
    else:
        from ci_workflow.application.run_service import validate_run_manifest

        try:
            validate_run_manifest(resolved_root)
        except (OSError, ValueError, RuntimeError) as exc:
            raise HostSmokeReceiptError("宿主回执验证失败：报告完整产物链校验失败") from exc
        for artifact in model.run.artifacts:
            artifact_path = resolved_root / artifact.entry_relative_path
            if not artifact_path.is_file():
                raise HostSmokeReceiptError(
                    f"宿主回执验证失败：交付产物不存在：{artifact.entry_relative_path}"
                )
            if _sha256_bytes(artifact_path.read_bytes()) != artifact.entry_sha256:
                raise HostSmokeReceiptError(
                    f"宿主回执验证失败：交付产物摘要不一致：{artifact.entry_relative_path}"
                )

    # R09 事件链绑定（对照项目当前事件流，旧回执失败关闭）
    try:
        events = EventStore(resolved_root).read_all()
        current_digest = EventStore(resolved_root).stream_digest()
    except EventStoreError as exc:
        raise HostSmokeReceiptError(f"宿主回执验证失败：事件链不可读：{exc}") from exc
    if model.event_chain.event_count != len(events):
        raise HostSmokeReceiptError(
            "宿主回执验证失败：旧回执——事件链长度与当前项目状态不一致"
        )
    if model.event_chain.stream_digest != current_digest:
        raise HostSmokeReceiptError(
            "宿主回执验证失败：旧回执——事件链摘要与当前项目状态不一致"
        )
    if not any(event.run_id == model.run.run_id for event in events):
        raise HostSmokeReceiptError("宿主回执验证失败：事件流不包含回执声明的运行")
    if is_real_host_recovery:
        if model.interruption is None or model.recovery is None:
            raise HostSmokeReceiptError("宿主回执验证失败：缺少阻断或补件恢复证据")
        scenario_path = resolved_root / "state/host-smoke-v1.json"
        try:
            scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HostSmokeReceiptError("宿主回执验证失败：阻断恢复记录不可读") from exc
        if not isinstance(scenario, dict):
            raise HostSmokeReceiptError("宿主回执验证失败：阻断恢复记录不是对象")
        if scenario.get("initial") != model.interruption.model_dump(mode="json"):
            raise HostSmokeReceiptError("宿主回执验证失败：初始 no-draft 记录与回执不一致")
        if scenario.get("recovery") != model.recovery.model_dump(mode="json"):
            raise HostSmokeReceiptError("宿主回执验证失败：补件恢复记录与回执不一致")
        initial_manifest_path = resolved_root / model.interruption.manifest_relative_path
        if (
            not initial_manifest_path.is_file()
            or _sha256_bytes(initial_manifest_path.read_bytes())
            != model.interruption.manifest_sha256
        ):
            raise HostSmokeReceiptError("宿主回执验证失败：初始阻断清单不存在或摘要漂移")
        if model.interruption.event_count >= len(events):
            raise HostSmokeReceiptError("宿主回执验证失败：恢复事件链没有增长")
        try:
            initial_stream_digest = EventStore(resolved_root).stream_digest(
                through_sequence=model.interruption.event_count
            )
        except EventStoreError as exc:
            raise HostSmokeReceiptError("宿主回执验证失败：初始事件链不可复算") from exc
        if initial_stream_digest != model.interruption.event_stream_digest:
            raise HostSmokeReceiptError("宿主回执验证失败：初始事件链摘要不一致")
        event_by_id = {event.event_id: event for event in events}
        for event_id, event_digest in (
            (model.recovery.reopen_event_id, model.recovery.reopen_event_digest),
            (model.recovery.rebind_event_id, model.recovery.rebind_event_digest),
        ):
            event = event_by_id.get(event_id)
            if event is None or event.event_digest != event_digest:
                raise HostSmokeReceiptError("宿主回执验证失败：显式恢复事件不存在或摘要漂移")
        recovery_input = resolved_root / model.recovery.input_relative_path
        if (
            not recovery_input.is_file()
            or _sha256_bytes(recovery_input.read_bytes()) != model.recovery.input_sha256
        ):
            raise HostSmokeReceiptError("宿主回执验证失败：补件输入不存在或摘要漂移")


def _installed_package_identity_for_verify() -> dict[str, str]:
    try:
        return _installed_package_identity()
    except HostSmokeError as exc:
        raise HostSmokeReceiptError(f"宿主回执验证失败：{exc}") from exc


def _load_smoke_case_for_verify(
    catalog_path: Path | None,
) -> tuple[dict[str, Any], Path]:
    try:
        return _load_smoke_case(catalog_path)
    except HostSmokeError as exc:
        raise HostSmokeReceiptError(f"宿主回执验证失败：{exc}") from exc


# ─── 三宿主批次验证 ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HostSmokeBatchVerdict:
    """三宿主回执批次结论：逐宿主状态、拒绝原因与诚实总结。"""

    statuses: dict[str, str]
    rejection_reasons: dict[str, str]
    real_host_pass: bool
    summary_zh: str


def _dotted(receipt: dict[str, Any], dotted: str) -> Any:
    value: Any = receipt
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def verify_host_smoke_batch(
    receipts: dict[str, Any],
    *,
    project_roots: dict[str, Path],
    catalog_path: Path | None = None,
) -> HostSmokeBatchVerdict:
    """验证三宿主回执并做跨宿主同进程伪造检查；失败关闭。

    宿主可执行文件按文件名与宿主名精确绑定，两宿主共享同一可执行文件在
    单回执校验中已被拒绝；批次层再拒绝共享会话、外部进程或运行标识。
    """
    statuses: dict[str, str] = {}
    rejection_reasons: dict[str, str] = {}
    verified: dict[str, dict[str, Any]] = {}
    for host in HOSTS:
        receipt = receipts.get(host)
        root = project_roots.get(host)
        if receipt is None or root is None:
            statuses[host] = "missing"
            continue
        try:
            verify_host_smoke_receipt(receipt, project_root=root, catalog_path=catalog_path)
        except HostSmokeReceiptError as exc:
            statuses[host] = "rejected"
            rejection_reasons[host] = str(exc)
            continue
        # 统一转字典做状态读取与跨宿主比对（模型与 JSON 两种输入等价）
        dumped_receipt = (
            receipt.model_dump(mode="json") if isinstance(receipt, HostReceipt) else receipt
        )
        receipt_status = dumped_receipt.get("status")
        statuses[host] = receipt_status if isinstance(receipt_status, str) else "unknown"
        if statuses[host] == "verified":
            verified[host] = cast(dict[str, Any], dumped_receipt)

    # 同进程伪造三宿主：任何两份已验证回执共享会话、外部进程或运行标识
    for left, right in itertools.combinations(sorted(verified), 2):
        for dotted in ("session.session_id", "process.pid", "run.run_id"):
            left_value = _dotted(verified[left], dotted)
            right_value = _dotted(verified[right], dotted)
            if left_value is not None and left_value == right_value:
                raise HostSmokeReceiptError(
                    f"宿主回执批次验证失败：同进程伪造三宿主——"
                    f"{left} 与 {right} 的 {dotted} 相同（{left_value}）"
                )

    all_verified = len(verified) == len(HOSTS)
    real_host_pass = all_verified and all(
        _dotted(verified[host], "host_executable.provenance") == "path_resolved"
        for host in HOSTS
    )
    if rejection_reasons:
        detail = "；".join(
            f"{host}={rejection_reasons[host]}" for host in sorted(rejection_reasons)
        )
        summary_zh = f"三宿主回执存在被拒宿主（{detail}）；不得视为通过"
    elif all_verified and real_host_pass:
        summary_zh = "三宿主真实入口回执全部验证通过（宿主可执行文件均来自 PATH 真实解析）"
    elif all_verified:
        summary_zh = (
            "三宿主回执绑定验证通过，但宿主可执行文件为显式提供（测试替身或指定路径），"
            "不构成真实宿主通过；Task 9.5 fresh-install 复验前不得主张真实宿主通过"
        )
    else:
        detail = "、".join(f"{host}={statuses[host]}" for host in HOSTS)
        summary_zh = f"宿主冒烟未完成（{detail}）；不构成任何真实宿主通过主张"
    return HostSmokeBatchVerdict(
        statuses=statuses,
        rejection_reasons=rejection_reasons,
        real_host_pass=real_host_pass,
        summary_zh=summary_zh,
    )
