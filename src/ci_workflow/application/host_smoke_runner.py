"""Task 9.5 PK04：从候选 fresh-install 运行三宿主外部冒烟。

本模块不实现宿主适配器，也不重建回执。每个宿主都调用 Task 9.4 的
``run_host_smoke``，由该函数启动一个真实 ``ci-workflow`` 外部进程并返回
唯一 ``HostReceipt``；本模块只负责隔离环境、逐宿主编排、落盘和批次验证。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ci_workflow.application.fresh_install import (
    FreshInstallError,
    FreshInstallLayout,
    load_fresh_install_layout,
)

if TYPE_CHECKING:
    from ci_workflow.application.host_smoke import HostSmokeBatchVerdict
    from ci_workflow.hosts.receipt import HostReceipt

HOSTS: tuple[str, ...] = ("codex", "hermes", "omp")
RECEIPT_DIRECTORY = Path("docs/acceptance/host-smoke")


class HostSmokeRunnerError(RuntimeError):
    """候选包外部宿主运行失败，或结果无法证明真实宿主通过。"""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise HostSmokeRunnerError(f"无法读取回执绑定文件：{path}") from exc
    return digest.hexdigest()


def _atomic_json_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise HostSmokeRunnerError(f"无法写入宿主冒烟证据：{path}") from exc


def _assert_writable_path(path: Path, *, layout: FreshInstallLayout, label: str) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(layout.bundle_root.resolve())
    except ValueError:
        return resolved
    raise HostSmokeRunnerError(f"{label} 不得写入不可变候选 bundle：{resolved}")


def _prepare_smoke_project(
    project: Path, *, layout: FreshInstallLayout, host: str, catalog: Path, resume: bool,
) -> None:
    # Outside the project: fixture creation requires an empty project directory.
    binding = project.with_name(f".{project.name}.host-smoke-binding.json")
    expected = {
        "schema_version": "1.0", "project_root": str(project.resolve()),
        "host": host, "case_id": "host-smoke-v1", "bundle_digest": layout.bundle_digest,
        "package_manifest_sha256": _sha256(layout.package_manifest),
        "catalog_sha256": _sha256(catalog),
    }
    if project.is_symlink() or (project.exists() and not project.is_dir()):
        raise HostSmokeRunnerError("宿主项目根类型无效")
    if resume:
        if not project.is_dir() or binding.is_symlink() or not binding.is_file():
            raise HostSmokeRunnerError("恢复缺少原项目或候选身份绑定，禁止猜测续接")
        try:
            recorded = json.loads(binding.read_bytes())
        except (OSError, ValueError) as exc:
            raise HostSmokeRunnerError("恢复身份绑定不可读") from exc
        if recorded != expected:
            raise HostSmokeRunnerError("恢复项目、宿主、案例或候选包身份不一致")
        return
    if project.exists() and any(project.iterdir()):
        raise HostSmokeRunnerError(f"宿主项目目录必须为空：{project}")
    if binding.exists() or binding.is_symlink():
        raise HostSmokeRunnerError("已有宿主运行身份绑定；请显式恢复或选择新项目")
    project.mkdir(parents=True, exist_ok=True)
    # Exclusive creation preserves another controller's recovery identity.
    try:
        with binding.open("x", encoding="utf-8") as stream:
            json.dump(expected, stream, ensure_ascii=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise HostSmokeRunnerError("无法建立宿主恢复身份绑定") from exc


@contextmanager
def _candidate_environment(layout: FreshInstallLayout) -> Iterator[None]:
    """令本进程及其每个外部 fixture 子进程使用候选包和隔离入口。"""
    old_cwd = Path.cwd()
    old_environment = os.environ.copy()
    path_entries = [
        str(layout.entrypoint.parent),
        *old_environment.get("PATH", "").split(os.pathsep),
    ]
    os.environ["PATH"] = os.pathsep.join(entry for entry in path_entries if entry)
    # The installed launcher owns its locked runtime. A host controller must
    # not replace it with its own interpreter or inject checkout import paths.
    for name in ("PYTHONPATH", "PYTHONHOME", "CI_WORKFLOW_PYTHON"):
        os.environ.pop(name, None)
    os.environ["CI_WORKFLOW_SHARED_ROOT"] = str(layout.shared_root)
    os.environ["CI_WORKFLOW_OMP_SKILL_LINK"] = str(layout.omp_skill_link)
    try:
        os.chdir(layout.install_root)
        yield
    finally:
        os.chdir(old_cwd)
        os.environ.clear()
        os.environ.update(old_environment)


@dataclass(frozen=True)
class HostSmokeBatchResult:
    """三宿主候选包运行结果；回执仍是唯一 HostReceipt 模型。"""

    layout: FreshInstallLayout
    receipts: dict[str, HostReceipt]
    project_roots: dict[str, Path]
    receipt_paths: dict[str, Path]
    batch_path: Path
    verdict: HostSmokeBatchVerdict


def _receipt_record(receipt: HostReceipt) -> dict[str, Any]:
    # 不通过 model_construct/model_copy 组装回执；磁盘只保存唯一模型的 JSON 投影。
    return receipt.model_dump(mode="json")


def run_installed_single_host_smoke(
    layout: FreshInstallLayout,
    *,
    host: str,
    receipt_path: Path,
    project_root: Path | None = None,
    catalog_path: Path | None = None,
    resume: bool = False,
    hermes_resume_session: str | None = None,
    hermes_provider: str | None = None,
    hermes_model: str | None = None,
    hermes_reasoning: str | None = None,
) -> HostReceipt:
    """从候选安装入口运行一个真实宿主，并只写该宿主的一份回执。"""

    if host not in HOSTS:
        raise HostSmokeRunnerError(f"不支持的宿主：{host}")
    layout.verify_layout()
    destination = _assert_writable_path(
        receipt_path,
        layout=layout,
        label="宿主回执",
    )
    project = _assert_writable_path(
        project_root or layout.install_root / "projects" / host,
        layout=layout,
        label="宿主项目根",
    )
    catalog = (
        (catalog_path or layout.bundle_root / "fixtures" / "catalog.yaml").expanduser().resolve()
    )
    if not catalog.is_file():
        raise HostSmokeRunnerError(f"候选安装缺少唯一 fixture catalog：{catalog}")
    _prepare_smoke_project(project, layout=layout, host=host, catalog=catalog, resume=resume)

    with _candidate_environment(layout):
        from ci_workflow.application.host_smoke import (
            HostSmokeError,
            HostSmokeReceiptError,
            resolve_real_entry,
            run_host_smoke,
            verify_host_smoke_receipt,
        )

        try:
            receipt = run_host_smoke(
                host,
                project_root=project,
                entry=resolve_real_entry(explicit=layout.entrypoint),
                catalog_path=catalog,
                resume=resume and any(project.iterdir()),
                require_external_host_process=True,
                hermes_resume_session=hermes_resume_session,
                hermes_provider=hermes_provider,
                hermes_model=hermes_model,
                hermes_reasoning=hermes_reasoning,
            )
            verify_host_smoke_receipt(
                receipt,
                project_root=project,
                catalog_path=catalog,
            )
        except (HostSmokeError, HostSmokeReceiptError, OSError) as exc:
            raise HostSmokeRunnerError(f"候选包宿主 {host} 运行失败：{exc}") from exc

    _atomic_json_write(destination, _receipt_record(receipt))
    return receipt


def run_installed_host_smoke(
    layout: FreshInstallLayout,
    *,
    evidence_root: Path | None = None,
    project_root: Path | None = None,
    catalog_path: Path | None = None,
    hosts: Sequence[str] = HOSTS,
    host_executables: Mapping[str, Path] | None = None,
    resume: bool = False,
    hermes_resume_session: str | None = None,
    hermes_provider: str | None = None,
    hermes_model: str | None = None,
    hermes_reasoning: str | None = None,
) -> HostSmokeBatchResult:
    """在隔离候选根逐一运行 Codex/Hermes/OMP 的 ``host-smoke-v1``。

    入口、fixture、包清单和宿主可执行文件均由候选环境解析。``host_executables``
    只供合同测试显式注入替身；缺省路径必须由 PATH 真实解析，才能使批次
    ``real_host_pass`` 为真。三次调用复用 Task 9.4 唯一 ``HostReceipt``，不
    在本进程伪造语义 JSON 或回执。
    """
    normalized_hosts = tuple(hosts)
    if normalized_hosts != HOSTS:
        raise HostSmokeRunnerError("候选包真实宿主批次必须按 codex、hermes、omp 全量运行")
    if host_executables is not None and set(host_executables) - set(HOSTS):
        raise HostSmokeRunnerError("宿主替身映射包含未声明宿主")
    layout.verify_layout()
    evidence = _assert_writable_path(
        evidence_root or layout.install_root / RECEIPT_DIRECTORY,
        layout=layout,
        label="宿主验收证据根",
    )
    projects = _assert_writable_path(
        project_root or layout.install_root / "projects",
        layout=layout,
        label="宿主项目根",
    )
    catalog = (
        (catalog_path or layout.bundle_root / "fixtures" / "catalog.yaml").expanduser().resolve()
    )
    if not catalog.is_file():
        raise HostSmokeRunnerError(f"候选安装缺少唯一 fixture catalog：{catalog}")
    if layout.entrypoint.resolve(strict=False).parent != (layout.install_root / "bin").resolve(
        strict=False
    ):
        raise HostSmokeRunnerError("真实入口未位于候选隔离根 bin 目录")

    receipts: dict[str, HostReceipt] = {}
    project_roots: dict[str, Path] = {}
    # Establish/check every recovery identity before any external host starts.
    # A first-host failure must not leave later hosts without a resumable binding.
    for host in normalized_hosts:
        host_project = projects / host
        _prepare_smoke_project(
            host_project, layout=layout, host=host, catalog=catalog, resume=resume,
        )
        project_roots[host] = host_project
    with _candidate_environment(layout):
        # Controller code stays in its own environment; the explicit candidate
        # entry below selects and verifies the independent installed runtime.
        from ci_workflow.application.host_smoke import (
            HostSmokeError,
            HostSmokeReceiptError,
            resolve_real_entry,
            run_host_smoke,
            verify_host_smoke_receipt,
        )

        current_host = "unknown"
        try:
            entry = resolve_real_entry(explicit=layout.entrypoint)
            for host in normalized_hosts:
                current_host = host
                host_project = project_roots[host]
                receipt = run_host_smoke(
                    host,
                    project_root=host_project,
                    entry=entry,
                    host_executable=(host_executables or {}).get(host),
                    catalog_path=catalog,
                    resume=resume and any(host_project.iterdir()),
                    require_external_host_process=True,
                    hermes_resume_session=hermes_resume_session,
                    hermes_provider=hermes_provider,
                    hermes_model=hermes_model,
                    hermes_reasoning=hermes_reasoning,
                )
                # 每一份回执先按当前项目状态深度验证，再进入跨宿主批次比较。
                verify_host_smoke_receipt(
                    receipt,
                    project_root=host_project,
                    catalog_path=catalog,
                )
                receipts[host] = receipt
        except (HostSmokeError, HostSmokeReceiptError, OSError) as exc:
            raise HostSmokeRunnerError(f"候选包宿主 {current_host} 运行失败：{exc}") from exc

        try:
            from ci_workflow.application.host_smoke import verify_host_smoke_batch

            verdict = verify_host_smoke_batch(
                receipts,
                project_roots=project_roots,
                catalog_path=catalog,
            )
        except HostSmokeReceiptError as exc:
            raise HostSmokeRunnerError(f"三宿主批次回执验证失败：{exc}") from exc

    # 只在三份回执各自和批次验证完成后落盘，避免半批次被误认作验收证据。
    evidence.mkdir(parents=True, exist_ok=True)
    receipt_paths: dict[str, Path] = {}
    for host in HOSTS:
        path = evidence / f"{host}.json"
        _atomic_json_write(path, _receipt_record(receipts[host]))
        receipt_paths[host] = path
    batch_path = evidence / "batch.json"
    _atomic_json_write(
        batch_path,
        {
            "schema_version": "1.0",
            "receipt_kind": "host-smoke-v1",
            "bundle_digest": layout.bundle_digest,
            "package_manifest_sha256": _sha256(layout.package_manifest),
            "receipt_paths": {
                host: str(path.relative_to(evidence)) for host, path in receipt_paths.items()
            },
            "project_roots": {host: str(path) for host, path in project_roots.items()},
            "statuses": verdict.statuses,
            "rejection_reasons": verdict.rejection_reasons,
            "real_host_pass": verdict.real_host_pass,
            "summary_zh": verdict.summary_zh,
        },
    )
    return HostSmokeBatchResult(
        layout=layout,
        receipts=receipts,
        project_roots=project_roots,
        receipt_paths=receipt_paths,
        batch_path=batch_path,
        verdict=verdict,
    )


# Task-oriented spelling for callers that describe the operation as a batch run.
run_host_smoke_batch = run_installed_host_smoke


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="在隔离候选 Skill 安装中运行三宿主 host-smoke-v1")
    parser.add_argument(
        "--install-root",
        default=os.environ.get(
            "CI_WORKFLOW_INSTALL_ROOT",
            str(
                Path.home()
                / ".cc-switch"
                / "skills"
                / "clinical-research"
                / "competitive-intelligence-workflow"
            ),
        ),
        help="fresh-install 隔离根",
    )
    parser.add_argument("--host", choices=HOSTS, help="只运行一个宿主")
    parser.add_argument("--case", default="host-smoke-v1", help="固定为 host-smoke-v1")
    parser.add_argument("--receipt", help="单宿主回执输出路径")
    parser.add_argument(
        "--require-external-host-process",
        action="store_true",
        help="要求真实宿主外部进程；单宿主模式必须提供",
    )
    parser.add_argument(
        "--evidence-root",
        help="宿主回执输出目录，默认安装根/docs/acceptance/host-smoke",
    )
    parser.add_argument("--project-root", help="三宿主项目父目录，默认安装根/projects")
    parser.add_argument("--catalog", help="候选包内唯一 fixture catalog.yaml")
    parser.add_argument("--resume", action="store_true", help="从已有 fixture 项目恢复")
    parser.add_argument("--hermes-resume-session", help="Hermes 技术故障后沿用的会话标识")
    parser.add_argument("--hermes-provider", help="Hermes 同会话切换后的提供方")
    parser.add_argument("--hermes-model", help="Hermes 同会话切换后的模型")
    parser.add_argument("--hermes-reasoning", help="Hermes 同会话切换后的推理强度")
    parser.add_argument(
        "--allow-real-host",
        action="store_true",
        help="明确允许启动 Codex/Hermes/OMP 真实入口",
    )
    args = parser.parse_args(argv)
    if not args.allow_real_host and os.environ.get("CI_WORKFLOW_RUN_REAL_HOSTS") != "1":
        print(
            "HOST_SMOKE_BLOCKED 未明确允许真实宿主运行；"
            "请添加 --allow-real-host 或设置 CI_WORKFLOW_RUN_REAL_HOSTS=1",
            file=sys.stderr,
        )
        return 3
    try:
        layout = load_fresh_install_layout(Path(args.install_root))
        if args.host:
            if args.case != "host-smoke-v1":
                raise HostSmokeRunnerError("候选包宿主冒烟案例固定为 host-smoke-v1")
            if not args.require_external_host_process:
                raise HostSmokeRunnerError("单宿主模式必须要求真实宿主外部进程")
            if not args.receipt:
                raise HostSmokeRunnerError("单宿主模式必须指定 --receipt")
            receipt = run_installed_single_host_smoke(
                layout,
                host=args.host,
                receipt_path=Path(args.receipt),
                project_root=Path(args.project_root) if args.project_root else None,
                catalog_path=Path(args.catalog) if args.catalog else None,
                resume=args.resume,
                hermes_resume_session=args.hermes_resume_session,
                hermes_provider=args.hermes_provider,
                hermes_model=args.hermes_model,
                hermes_reasoning=args.hermes_reasoning,
            )
            print(
                "HOST_SMOKE_COMPLETE "
                f"host={args.host} status={receipt.status} receipt={args.receipt}"
            )
            return 0 if receipt.status == "verified" else 3
        result = run_installed_host_smoke(
            layout,
            evidence_root=Path(args.evidence_root) if args.evidence_root else None,
            project_root=Path(args.project_root) if args.project_root else None,
            catalog_path=Path(args.catalog) if args.catalog else None,
            resume=args.resume,
            hermes_resume_session=args.hermes_resume_session,
            hermes_provider=args.hermes_provider,
            hermes_model=args.hermes_model,
            hermes_reasoning=args.hermes_reasoning,
        )
    except (FreshInstallError, HostSmokeRunnerError) as exc:
        print(f"HOST_SMOKE_FAILED {exc}", file=sys.stderr)
        return 2
    print(
        "HOST_SMOKE_COMPLETE "
        f"real_host_pass={str(result.verdict.real_host_pass).lower()} "
        f"batch={result.batch_path}"
    )
    return 0 if result.verdict.real_host_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
