"""Task 9.5 PK05–PK06：候选 bundle fresh-install、三宿主一致性与归档合同。

默认测试只使用临时构建根和确定性能力覆盖，不读取或修改宿主真实入口。
设置 ``CI_WORKFLOW_RUN_REAL_HOST_TESTS=1`` 后才执行真实 Codex/Hermes/OMP
入口；没有真实宿主时必须明确失败，而不是把适配器 JSON 当作通过证据。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from ci_workflow.application.fresh_install import (
    FreshInstallError,
    FreshInstallLayout,
    install_bundle,
)
from ci_workflow.application.host_smoke import _run_evidence
from ci_workflow.hosts.receipt import HostReceipt
from tools.bundle_contract import FINAL_REQUIRED_CONTENT

ROOT = Path(__file__).resolve().parents[2]
BUILD_TOOL = ROOT / "tools" / "build_bundle.py"
VERIFY_TOOL = ROOT / "tools" / "verify_bundle.py"
RUN_HOST_SMOKE_TOOL = ROOT / "tools" / "run_host_smoke.py"
ARCHIVE_DIR = ROOT / "docs" / "acceptance" / "host-smoke"
ARCHIVE_SCHEMA = ARCHIVE_DIR / "archive-contract.schema.json"
ARCHIVE_INDEX = ARCHIVE_DIR / "archive.json"
INSTALL_GUIDE = ROOT / "docs" / "user-guide" / "install.md"
HOSTS = ("codex", "hermes", "omp")
CAPABILITY_IDS = (
    "project_file_io",
    "script_runtime",
    "http_network",
    "search_browser",
    "login_browser",
    "document_ingestion",
    "ocr",
    "browser_validation",
    "independent_context",
)


@dataclass(frozen=True)
class FreshCandidate:
    bundle: Path
    root: Path
    install_root: Path
    module_root: Path
    entrypoint: Path
    sidecar: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _require_bundle_tools() -> None:
    missing = [
        str(path.relative_to(ROOT)) for path in (BUILD_TOOL, VERIFY_TOOL) if not path.is_file()
    ]
    if missing:
        pytest.skip(f"PK01–PK04 bundle tooling尚未合入：{', '.join(missing)}")
    if shutil.which("zstd") is None:
        pytest.fail("缺少 zstd；无法解包并验证 .tar.zst 候选包")


def _build_candidate(tmp_path_factory: pytest.TempPathFactory) -> FreshCandidate:
    _require_bundle_tools()
    base = tmp_path_factory.mktemp("candidate-bundle")
    dist = base / "dist"
    dist.mkdir()
    bundle = dist / "competitive-intelligence-workflow.tar.zst"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    built = _run(
        [
            sys.executable,
            str(BUILD_TOOL),
            "--output",
            str(dist),
            "--archive-name",
            bundle.name,
        ],
        cwd=ROOT,
        env=env,
    )
    if built.returncode != 0:
        pytest.fail(
            f"候选 bundle 构建失败：\nstdout={built.stdout[-2000:]}\nstderr={built.stderr[-2000:]}"
        )
    assert bundle.is_file(), "构建器未产生 .tar.zst 候选包"

    sidecars = sorted(
        path
        for path in dist.iterdir()
        if path.is_file() and path != bundle and path.suffix in {".sha256", ".sha256sum"}
    )
    assert sidecars, "构建器未产生外部 SHA-256 sidecar"
    digest = _sha256(bundle)
    sidecar = Path(f"{bundle}.sha256")
    assert sidecar in sidecars
    assert digest in re.findall(r"[0-9a-f]{64}", sidecar.read_text(encoding="utf-8")), (
        f"bundle 外部 SHA-256 与实际内容不一致：{sidecar}"
    )

    verified = _run(
        [sys.executable, str(VERIFY_TOOL), "--bundle", str(bundle)],
        cwd=ROOT,
        env=env,
    )
    if verified.returncode != 0 or "BUNDLE_OK" not in verified.stdout:
        pytest.fail(
            "候选 bundle 校验未输出 BUNDLE_OK：\n"
            f"stdout={verified.stdout[-2000:]}\n"
            f"stderr={verified.stderr[-2000:]}"
        )

    layout = install_bundle(bundle, base / "fresh-install")
    assert isinstance(layout, FreshInstallLayout)
    unpack_root = layout.bundle_root
    module_root = unpack_root / "src"
    assert (module_root / "ci_workflow" / "__main__.py").is_file(), (
        "fresh-install 缺少可执行的 ci_workflow 模块"
    )
    return FreshCandidate(
        bundle=bundle,
        root=unpack_root,
        install_root=layout.install_root,
        module_root=module_root,
        entrypoint=layout.entrypoint,
        sidecar=sidecar,
    )


@pytest.fixture(scope="module")
def candidate(tmp_path_factory: pytest.TempPathFactory) -> FreshCandidate:
    return _build_candidate(tmp_path_factory)


def _extract_members(bundle: Path, tmp_path: Path) -> set[str]:
    zstd = shutil.which("zstd")
    if zstd is None:
        pytest.fail("缺少 zstd；无法读取候选包成员")
    raw_tar = tmp_path / "members.tar"
    with raw_tar.open("wb") as stream:
        decompressed = subprocess.run(
            [zstd, "-q", "-d", "--stdout", str(bundle)],
            stdout=stream,
            stderr=subprocess.PIPE,
            check=False,
        )
    if decompressed.returncode != 0:
        pytest.fail(
            "候选 .tar.zst 读取失败："
            f"{decompressed.stderr.decode('utf-8', errors='replace')[-2000:]}"
        )
    listed = subprocess.run(
        ["tar", "-tf", str(raw_tar)],
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode != 0:
        pytest.fail(f"候选 tar 清单读取失败：{listed.stderr[-2000:]}")
    members: set[str] = set()
    for raw_name in listed.stdout.splitlines():
        name = raw_name.strip().removeprefix("./").rstrip("/")
        if name and name != ".":
            members.add(name)
    return members


def _installed_env(module_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONPATH"] = str(module_root)
    env["CI_WORKFLOW_PYTHON"] = sys.executable
    env["CI_WORKFLOW_TEST_MODE"] = "1"
    env["CI_WORKFLOW_CAPABILITY_OVERRIDES"] = json.dumps(
        {capability_id: True for capability_id in CAPABILITY_IDS},
        ensure_ascii=False,
        sort_keys=True,
    )
    return env


def _installed_cli(
    candidate: FreshCandidate,
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    return _run(
        [str(candidate.entrypoint), *args],
        cwd=cwd or candidate.install_root,
        env=env or _installed_env(candidate.module_root),
        timeout=timeout,
    )


def _archive_sample() -> dict[str, Any]:
    checks = {
        "bundle_verified": False,
        "receipts_schema_valid": False,
        "receipts_current": False,
        "path_resolved": False,
        "package_digest_consistent": False,
        "case_digest_consistent": False,
        "semantic_state_consistent": False,
        "process_session_run_distinct": False,
        "no_draft_assertion": False,
        "html_only": True,
    }
    return {
        "schema_version": "1.0",
        "archive_kind": "candidate-bundle-host-smoke",
        "generated_at": "2026-09-01T10:00:00+08:00",
        "bundle": {
            "path": "dist/competitive-intelligence-workflow.tar.zst",
            "sha256": "a" * 64,
            "package_manifest_sha256": "b" * 64,
        },
        "fixture": {"case_id": "host-smoke-v1", "case_digest": "c" * 64},
        "receipts": {host: f"{host}.json" for host in HOSTS},
        "checks": checks,
        "real_host_pass": False,
        "acceptance_status": "pending",
        "summary_zh": "等待三宿主真实回执和独立验收。",
    }


def test_archive_contract_schema_is_closed_and_acceptance_is_fail_closed() -> None:
    assert ARCHIVE_SCHEMA.is_file()
    schema = json.loads(ARCHIVE_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    sample = _archive_sample()
    assert list(validator.iter_errors(sample)) == []

    missing_host = json.loads(json.dumps(sample))
    del missing_host["receipts"]["omp"]
    assert list(validator.iter_errors(missing_host))

    accepted_without_checks = json.loads(json.dumps(sample))
    accepted_without_checks["acceptance_status"] = "accepted"
    assert list(validator.iter_errors(accepted_without_checks))

    accepted_without_real_host = json.loads(json.dumps(sample))
    accepted_without_real_host["acceptance_status"] = "accepted"
    accepted_without_real_host["checks"] = {
        key: True for key in accepted_without_real_host["checks"]
    }
    assert list(validator.iter_errors(accepted_without_real_host))


def test_install_guide_is_chinese_and_declares_html_only_failure_classes() -> None:
    text = INSTALL_GUIDE.read_text(encoding="utf-8")
    for required in (
        "build_bundle.py",
        "verify_bundle.py",
        "install_bundle.py",
        "run_host_smoke.py",
        "--allow-real-host",
        "站点式 HTML",
        "技术或环境问题",
        "本轮遇到技术问题，尚未完成；请恢复环境后重试",
        "关键证据不足",
        "关键证据不足，暂不生成草稿",
        "不生成草稿",
        "不猜测",
        "未公开",
    ):
        assert required in text
    assert "PDF、HTML-PPT 和 PPTX" in text


def test_fresh_bundle_contains_required_paths_and_no_project_outputs(
    candidate: FreshCandidate,
    tmp_path: Path,
) -> None:
    members = _extract_members(candidate.bundle, tmp_path)
    required = {
        *FINAL_REQUIRED_CONTENT,
        "bundle-manifest.json",
        "fixtures/synthetic/host-smoke-v1/inputs/universe.json",
        "fixtures/synthetic/host-smoke-v1/inputs/recovery-report-data.json",
        "schemas/host-receipt.schema.json",
    }
    assert required <= members
    assert (candidate.install_root / "shared").is_symlink()
    assert (candidate.install_root / "shared").resolve() == candidate.root.resolve()
    omp_link = candidate.install_root / "omp" / "skills" / "competitive-intelligence-workflow"
    assert omp_link.is_symlink()
    assert (
        omp_link.resolve()
        == (candidate.root / "skills" / "competitive-intelligence-workflow").resolve()
    )
    assert candidate.entrypoint.is_file()
    assert os.access(candidate.entrypoint, os.X_OK)

    forbidden_directory_names = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        ".artifacts",
        "archives",
        "logs",
        "output",
        "runs",
        "tests",
        "tmp",
    }
    sensitive_basenames = {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        "credentials",
        "credentials.json",
        "credentials.yaml",
        "credentials.yml",
        "secrets",
        "secrets.json",
        "secrets.yaml",
        "secrets.yml",
        "service-account.json",
        "id_rsa",
        "id_ed25519",
        "password",
        "password.txt",
        "api_key",
        "api-key",
        "token",
        "token.txt",
    }
    for member in members:
        path = PurePosixPath(member)
        assert not path.is_absolute(), member
        assert ".." not in path.parts, member
        forbidden_parts = forbidden_directory_names.intersection(path.parts)
        if forbidden_parts:
            assert path in {
                PurePosixPath("contracts/kangzhe/design_specs/tests"),
                PurePosixPath("contracts/kangzhe/design_specs/tests/test_package_load.py"),
            }, member
        assert path.name.lower() not in sensitive_basenames, member
        assert not any(
            token in path.name.lower()
            for token in (
                "credential",
                "secret",
                ".env",
                "access_token",
                "refresh_token",
                "api_key",
                "api-key",
            )
        ), member
        assert not path.name.lower().endswith(
            (".pem", ".key", ".p12", ".pfx", ".secret", ".secrets", ".token", ".tokens")
        ), member

    manifest = json.loads((candidate.root / "package-manifest.json").read_text(encoding="utf-8"))
    assert manifest["package"]["hosts"] == list(HOSTS)
    catalog = yaml.safe_load(
        (candidate.root / "fixtures" / "catalog.yaml").read_text(encoding="utf-8")
    )
    case_root = candidate.root / "fixtures"
    for case in catalog["cases"]:
        case_id = case["id"]
        candidates = (
            case_root / "synthetic" / case_id,
            case_root / "positive" / case_id,
        )
        resolved = next((path for path in candidates if path.is_dir()), None)
        assert resolved is not None, f"catalog 案例未随候选包闭合：{case_id}"
        for item in case["inputs"]:
            assert (resolved / item["path"]).is_file(), (
                f"catalog 案例输入未随候选包闭合：{case_id}/{item['path']}"
            )
    smoke_case = next(case for case in catalog["cases"] if case["id"] == "host-smoke-v1")
    assert smoke_case["outputs"] == ["html"]
    assert smoke_case["case_digest"]


def test_candidate_bundle_closes_final_required_content(
    candidate: FreshCandidate,
    tmp_path: Path,
) -> None:
    """Task 10.6A：默认 allowlist 必须已覆盖 10.6 最终包必需内容，缺一即失败关闭。

    当前设计合同、公开入口和可安装运行时必须随默认候选包闭合。构建器、
    宿主 runner 与 required-v12 验收资料属于开发仓库，不进入用户安装包。
    """

    members = _extract_members(candidate.bundle, tmp_path)
    missing = [path for path in FINAL_REQUIRED_CONTENT if path not in members]
    assert not missing, f"最终必需内容未随候选包闭合：{missing}"


def test_fresh_install_refuses_existing_root_without_mutation(
    candidate: FreshCandidate,
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "existing-install"
    install_root.mkdir()
    sentinel = install_root / "old-entry"
    sentinel.write_text("preserve\n", encoding="utf-8")

    with pytest.raises(FreshInstallError, match="不覆盖"):
        install_bundle(candidate.bundle, install_root)

    assert sentinel.read_text(encoding="utf-8") == "preserve\n"
    assert sorted(path.name for path in install_root.iterdir()) == ["old-entry"]


def test_fresh_install_runs_package_verify_and_no_draft_fixture_without_checkout(
    candidate: FreshCandidate,
) -> None:
    verify = _installed_cli(
        candidate,
        "package",
        "verify",
        "--root",
        str(candidate.root),
    )
    assert verify.returncode == 0, f"stdout={verify.stdout}\nstderr={verify.stderr}"
    assert "PACKAGE_OK" in verify.stdout

    project_root = candidate.install_root.parent / "host-smoke-project"
    smoke = _installed_cli(
        candidate,
        "fixture",
        "run",
        "--case",
        "host-smoke-v1",
        "--reports",
        "A",
        "--outputs",
        "html",
        "--project",
        str(project_root),
    )
    combined = f"{smoke.stdout}\n{smoke.stderr}"
    assert smoke.returncode == 4, combined
    assert "证据不足" in combined
    assert not list((project_root / "reports").rglob("*.html"))
    audit = project_root / "blockers" / "A" / "v1" / "audit.md"
    assert audit.is_file()
    assert "证据不足" in audit.read_text(encoding="utf-8")


def test_fresh_install_host_smoke_recovers_and_verifies_html(
    candidate: FreshCandidate,
) -> None:
    project_root = candidate.install_root.parent / "host-smoke-recovery-project"
    result = _installed_cli(
        candidate,
        "fixture",
        "run",
        "--case",
        "host-smoke-v1",
        "--reports",
        "A",
        "--outputs",
        "html",
        "--project",
        str(project_root),
        "--host-smoke-recovery",
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    record = json.loads((project_root / "state/host-smoke-v1.json").read_text(encoding="utf-8"))
    assert record["initial"]["no_draft"] is True
    assert record["initial"]["report_file_count"] == 0
    assert record["recovery"]["reason"] == "user_material_accepted"
    assert record["final"]["outcome"] == "rendered"
    assert record["final"]["artifact_digests"]
    assert list((project_root / "reports/A").rglob("*.html"))
    current_manifest = json.loads(
        (project_root / "manifests/current_run.json").read_text(encoding="utf-8")
    )
    run_evidence = _run_evidence(
        current_manifest,
        project_root=project_root,
        host="codex",
        returncode=0,
    )
    assert run_evidence.artifacts[0].entry_relative_path.endswith("/html/overview.html")
    assert (project_root / run_evidence.artifacts[0].entry_relative_path).is_file()
    verify = _installed_cli(candidate, "project", "verify", "--root", str(project_root))
    assert verify.returncode == 0, f"{verify.stdout}\n{verify.stderr}"


def test_fresh_install_preflight_is_conformant_and_html_only(
    candidate: FreshCandidate,
) -> None:
    payloads: dict[str, dict[str, Any]] = {}
    for host in HOSTS:
        destination = candidate.install_root.parent / f"preflight-{host}.json"
        result = _installed_cli(
            candidate,
            "capability",
            "preflight",
            "--host",
            host,
            "--reports",
            "A",
            "--outputs",
            "html",
            "--json",
            str(destination),
        )
        assert result.returncode == 0, f"{host}: {result.stdout}\n{result.stderr}"
        payload = json.loads(destination.read_text(encoding="utf-8"))
        assert payload["selection"]["outputs"] == ["html"]
        assert payload["overall_state"] == "ready"
        records = {item["capability_id"]: item for item in payload["capabilities"]}
        for removed in ("native_pdf", "html_ppt_runtime", "ppt_master", "office_renderer"):
            assert removed not in records
        payloads[host] = payload

    def semantic_view(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "selection": payload["selection"],
            "capabilities": [
                {
                    "capability_id": item["capability_id"],
                    "state": item["state"],
                    "required_by": item["required_by"],
                }
                for item in payload["capabilities"]
            ],
            "research": payload["research"],
            "deliveries": payload["deliveries"],
            "overall_state": payload["overall_state"],
            "user_messages": payload["user_messages"],
        }

    views = [semantic_view(payloads[host]) for host in HOSTS]
    assert views[0] == views[1] == views[2]


def test_archived_real_host_receipts_are_complete_when_present() -> None:
    paths = {host: ARCHIVE_DIR / f"{host}.json" for host in HOSTS}
    existing = [path for path in paths.values() if path.is_file()]
    if not existing:
        pytest.skip("真实宿主回执尚未按 Task 9.5 运行；不以缺失回执冒充通过")
    assert len(existing) == len(HOSTS), "宿主回执归档不完整：不得接受部分三宿主结果"
    assert ARCHIVE_INDEX.is_file(), "三宿主回执存在但缺少 archive.json 归档索引"

    archive_schema = json.loads(ARCHIVE_SCHEMA.read_text(encoding="utf-8"))
    archive_validator = Draft202012Validator(
        archive_schema,
        format_checker=FormatChecker(),
    )
    archive = json.loads(ARCHIVE_INDEX.read_text(encoding="utf-8"))
    archive_validator.validate(archive)
    assert archive["receipts"] == {host: f"{host}.json" for host in HOSTS}
    bundle = ROOT / archive["bundle"]["path"]
    assert bundle.is_file()
    assert _sha256(bundle) == archive["bundle"]["sha256"]
    assert archive["acceptance_status"] == "accepted"
    assert archive["real_host_pass"] is True
    assert all(archive["checks"].values())

    schema = json.loads((ROOT / "schemas" / "host-receipt.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    receipts: dict[str, dict[str, Any]] = {}
    for host, path in paths.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        validator.validate(payload)
        model = HostReceipt.model_validate(payload)
        model.verify_content_integrity()
        assert payload["host"] == host
        assert payload["status"] == "verified"
        assert payload["host_executable"]["provenance"] == "path_resolved"
        assert payload["fixture"]["case_id"] == "host-smoke-v1"
        assert payload["interruption"]["outcome"] == "evidence_blocked"
        assert payload["interruption"]["no_draft"] is True
        assert payload["interruption"]["report_file_count"] == 0
        assert payload["recovery"]["reason"] == "user_material_accepted"
        assert payload["run"]["state"] == "complete"
        assert payload["run"]["outcome"] == "rendered"
        assert payload["run"]["no_draft"] is False
        assert payload["run"]["artifacts"]
        receipts[host] = payload

    assert len({receipt["package"]["package_digest"] for receipt in receipts.values()}) == 1
    assert len({receipt["fixture"]["case_digest"] for receipt in receipts.values()}) == 1
    assert len({receipt["run"]["semantic_receipt_digest"] for receipt in receipts.values()}) == 1
    for dotted in (
        ("process", "pid"),
        ("session", "session_id"),
        ("run", "run_id"),
    ):
        values = {receipt[dotted[0]][dotted[1]] for receipt in receipts.values()}
        assert len(values) == len(HOSTS), dotted


def test_real_host_runner_is_executable_only_when_explicitly_enabled(
    candidate: FreshCandidate,
    tmp_path: Path,
) -> None:
    if os.environ.get("CI_WORKFLOW_RUN_REAL_HOST_TESTS") != "1":
        pytest.skip("真实宿主验收需显式设置 CI_WORKFLOW_RUN_REAL_HOST_TESTS=1")
    if not RUN_HOST_SMOKE_TOOL.is_file():
        pytest.fail("缺少 tools/run_host_smoke.py，无法执行真实宿主入口")
    missing_hosts = [host for host in HOSTS if shutil.which(host) is None]
    if missing_hosts:
        pytest.fail(f"未在 PATH 发现真实宿主：{'、'.join(missing_hosts)}")

    env = _installed_env(candidate.module_root)
    env["CI_WORKFLOW_RUN_REAL_HOSTS"] = "1"
    evidence_root = tmp_path / "host-smoke"
    project_root = tmp_path / "projects"
    result = _run(
        [
            sys.executable,
            str(RUN_HOST_SMOKE_TOOL),
            "--allow-real-host",
            "--install-root",
            str(candidate.install_root),
            "--evidence-root",
            str(evidence_root),
            "--project-root",
            str(project_root),
        ],
        cwd=ROOT,
        env=env,
        timeout=900,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert (evidence_root / "batch.json").is_file()
    receipts: dict[str, dict[str, Any]] = {}
    for host in HOSTS:
        receipt_path = evidence_root / f"{host}.json"
        assert receipt_path.is_file()
        receipts[host] = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert len({receipt["package"]["package_digest"] for receipt in receipts.values()}) == 1
    assert len({receipt["fixture"]["case_digest"] for receipt in receipts.values()}) == 1
    assert all(
        receipt["status"] == "verified"
        and receipt["host_executable"]["provenance"] == "path_resolved"
        and receipt["interruption"]["no_draft"] is True
        and receipt["run"]["outcome"] == "rendered"
        and bool(receipt["run"]["artifacts"])
        for receipt in receipts.values()
    )
