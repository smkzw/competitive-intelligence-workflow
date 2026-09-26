from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, Never, cast

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from ci_workflow import __version__
from ci_workflow.application.capability_preflight import (
    CapabilitySelection,
    RuntimeCapabilityProbe,
    persist_capability_matrix,
    run_capability_preflight,
    selection_from_project,
)
from ci_workflow.application.project_service import (
    ProjectWorkspaceError,
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.domain.contracts import create_project_contract

EXPECTED_INTERNAL_SKILLS = {
    "intake-preflight",
    "ontology-universe",
    "source-routing",
    "ingestion-identity",
    "extraction-normalization",
    "identity-conflict",
    "coverage-gates",
    "analysis-a",
    "analysis-b",
    "analysis-c",
    "scientific-qc",
    "visual-design-director",
    "render-deliver",
    "visual-package-qc",
    "correction-refresh",
}
EXPECTED_CLI_CATALOG = [
    "package verify",
    "project create",
    "project verify",
    "project run",
    "project share",
    "project accept-visual",
    "capability preflight",
    "fixture run",
    "review issue",
    "research submit",
    "research capture",
    "research fetch-ctgov",
    "publication unavailable",
    "yaozh answer",
    "yaozh observe",
    "yaozh check",
]
VALID_REPORTS = {"A", "B", "C"}
VALID_OUTPUTS = {"html"}
PUBLIC_SKILL_TRIGGER = "竞品调研"
HISTORICAL_INTERNAL_SKILLS = {"monitoring"}
HISTORICAL_SCHEMA_PATHS = {
    "schemas/monitoring-change-candidate.schema.json",
    "schemas/ppt-master-job.schema.json",
    "schemas/pptx-confirmation.schema.json",
    "schemas/pptx-source-pack.schema.json",
}


class ContractError(ValueError):
    """可直接转换为用户可读错误的合同异常。"""


class ChineseArgumentParser(argparse.ArgumentParser):
    """将 argparse 的固定交互文案收口为中文。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self._positionals.title = "命令"
        self._optionals.title = "选项"
        self.add_argument("-h", "--help", action="help", help="显示帮助并退出")

    def format_help(self) -> str:
        return super().format_help().replace("usage:", "用法:", 1)

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法:", 1)

    def error(self, message: str) -> Never:
        if message.startswith("the following arguments are required:"):
            missing = message.split(":", 1)[1].strip()
            detail = f"缺少必填参数：{missing}"
        elif "invalid choice:" in message:
            detail = "参数值不在允许范围内，请查看 --help"
        elif message.startswith("unrecognized arguments:"):
            unknown = message.split(":", 1)[1].strip()
            detail = f"无法识别的参数：{unknown}"
        else:
            detail = "参数不符合要求，请查看 --help"
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}：参数错误：{detail}\n")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"缺少文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"文件不是有效的 JSON：{path}（{exc.msg}）") from exc
    if not isinstance(value, dict):
        raise ContractError(f"文件顶层必须是对象：{path}")
    return cast(dict[str, Any], value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_digest(path: Path, expected: str) -> None:
    if not path.is_file():
        raise ContractError(f"缺少清单绑定文件：{path}")
    actual = _sha256(path)
    if actual != expected:
        raise ContractError(f"文件摘要不一致：{path}")


def _skill_frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ContractError(f"缺少 Skill：{path}") from exc
    if not text.startswith("---\n"):
        raise ContractError(f"Skill 缺少 YAML 元数据：{path}")
    try:
        _, raw, body = text.split("---\n", 2)
        value = yaml.safe_load(raw)
    except (ValueError, yaml.YAMLError) as exc:
        raise ContractError(f"Skill 元数据无法读取：{path}") from exc
    if not isinstance(value, dict) or not body.strip():
        raise ContractError(f"Skill 元数据或正文为空：{path}")
    if set(value) != {"name", "description"}:
        raise ContractError(f"Skill 元数据只能包含 name 和 description：{path}")
    if "TODO" in text:
        raise ContractError(f"Skill 仍含模板占位内容：{path}")
    return cast(dict[str, Any], value)


def _verify_asset_manifests(root: Path) -> None:
    brand = _load_json(root / "assets/brand/manifest.json")
    _verify_digest(root / "assets/brand" / str(brand["file"]), str(brand["sha256"]))
    _verify_digest(root / str(brand["source"]), str(brand["sha256"]))

    portal = _load_json(root / "assets/portal/manifest.json")
    portal_files = cast(dict[str, dict[str, Any]], portal["files"])
    portal_root = root / "assets/portal"
    echarts_source = root / str(portal.get("echarts_source", ""))
    for relative_path, record in portal_files.items():
        if not isinstance(record, dict):
            raise ContractError(f"门户资源清单条目无效：{relative_path}")
        asset_path = (
            echarts_source if relative_path == "echarts.min.js" else portal_root / relative_path
        )
        _verify_digest(asset_path, str(record["sha256"]))
    echarts = _load_json(root / "assets/third-party/echarts/manifest.json")
    echarts_root = root / "assets/third-party/echarts"
    _verify_digest(echarts_root / str(echarts["bundle"]), str(echarts["bundle_sha256"]))
    _verify_digest(
        echarts_root / str(echarts["license_file"]),
        str(echarts["license_sha256"]),
    )


def _verify_kangzhe_contract(root: Path) -> None:
    manifest = _load_json(root / "contracts/kangzhe/manifest.json")
    runtime = cast(dict[str, Any], manifest["runtime"])
    files = cast(dict[str, str], runtime["files"])
    contract_root = root / "contracts/kangzhe"
    for relative_path, expected in files.items():
        _verify_digest(contract_root / relative_path, expected)


def verify_package(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = _load_json(root / "package-manifest.json")
    schema = _load_json(root / "schemas/package-manifest.schema.json")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(manifest)
    except (SchemaError, ValidationError) as exc:
        raise ContractError(f"安装包清单不符合合同：{exc.message}") from exc

    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    except (FileNotFoundError, tomllib.TOMLDecodeError, KeyError) as exc:
        raise ContractError("无法读取 pyproject.toml 中的项目版本") from exc
    package = cast(dict[str, Any], manifest["package"])
    if package["name"] != project["name"] or package["version"] != project["version"]:
        raise ContractError("安装包名称或版本与 pyproject.toml 不一致")
    if package["cli_version"] != __version__:
        raise ContractError("安装包声明的 CLI 版本与实际模块不一致")
    if package.get("release_scope") != "site_html_v1":
        raise ContractError("安装包 release_scope 必须是 site_html_v1")
    if package.get("formats") != ["html"]:
        raise ContractError("安装包首版格式必须严格为 html")

    public_path = root / str(manifest["public_skill"])
    if _skill_frontmatter(public_path)["name"] != PUBLIC_SKILL_TRIGGER:
        raise ContractError("公开 Skill 触发词不符合安装合同")
    public_agent = _load_json_or_yaml(public_path.parent / "agents/openai.yaml")
    public_interface = cast(dict[str, Any], public_agent.get("interface", {}))
    if "$competitive-intelligence-workflow" not in str(public_interface.get("default_prompt", "")):
        raise ContractError("公开 Skill 默认提示未绑定自身 Skill")

    internal_items = cast(list[dict[str, Any]], manifest["internal_skills"])
    declared_ids = {str(item["id"]) for item in internal_items}
    if declared_ids != EXPECTED_INTERNAL_SKILLS:
        raise ContractError("内部 Skill 集合与冻结合同不一致")
    actual_ids = {path.parent.name for path in (root / "skills/_internal").glob("*/SKILL.md")}
    unexpected_ids = actual_ids - EXPECTED_INTERNAL_SKILLS - HISTORICAL_INTERNAL_SKILLS
    if not EXPECTED_INTERNAL_SKILLS.issubset(actual_ids) or unexpected_ids:
        raise ContractError("安装包中的内部 Skill 目录与冻结合同不一致")
    for item in internal_items:
        skill_id = str(item["id"])
        skill_path = root / str(item["path"])
        if _skill_frontmatter(skill_path)["name"] != skill_id:
            raise ContractError(f"内部 Skill 名称与清单不一致：{skill_id}")
        agent = _load_json_or_yaml(skill_path.parent / "agents/openai.yaml")
        interface = cast(dict[str, Any], agent.get("interface", {}))
        if f"${skill_id}" not in str(interface.get("default_prompt", "")):
            raise ContractError(f"内部 Skill 默认提示未绑定自身 Skill：{skill_id}")
        policy = cast(dict[str, Any], agent.get("policy", {}))
        if policy.get("allow_implicit_invocation") is not False:
            raise ContractError(f"内部 Skill 必须关闭隐式调用：{skill_id}")

    components = cast(dict[str, list[str]], manifest["components"])
    for paths in components.values():
        for relative_path in paths:
            if not (root / relative_path).exists():
                raise ContractError(f"清单声明的组件不存在：{relative_path}")
    declared_schema = set(components["schemas"])
    actual_schema = {
        path.relative_to(root).as_posix() for path in root.glob("schemas/**/*.schema.json")
    } | {path.relative_to(root).as_posix() for path in root.glob("contracts/**/*.schema.json")}
    missing_schema = declared_schema - actual_schema
    extra_schema = actual_schema - declared_schema - HISTORICAL_SCHEMA_PATHS
    if missing_schema or extra_schema:
        raise ContractError("Schema 清单与安装包实际 v1 文件不一致")
    declared_migrations = set(components["migrations"])
    actual_migrations = {
        path.relative_to(root).as_posix() for path in (root / "migrations").glob("*.sql")
    }
    if (
        len(components["migrations"]) != len(declared_migrations)
        or declared_migrations != actual_migrations
    ):
        raise ContractError("Migration 清单与安装包实际文件不一致")

    cli = cast(dict[str, Any], manifest["cli"])
    if cli["catalog"] != EXPECTED_CLI_CATALOG:
        raise ContractError("CLI 目录与冻结合同不一致")

    _verify_asset_manifests(root)
    _verify_kangzhe_contract(root)
    return manifest


def _load_json_or_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise ContractError(f"无法读取界面元数据：{path}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"界面元数据顶层必须是对象：{path}")
    return cast(dict[str, Any], value)


def _split_choices(raw: str, valid: set[str], label: str) -> list[str]:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    if not values:
        raise ContractError(f"请至少选择一项{label}")
    if len(values) != len(set(values)):
        raise ContractError(f"{label}不能重复")
    invalid = [value for value in values if value not in valid]
    if invalid:
        raise ContractError(f"不支持的{label}：{'、'.join(invalid)}")
    return values


def _atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _create_project(args: argparse.Namespace) -> int:
    reports = (
        _split_choices(args.reports, VALID_REPORTS, "报告类型")
        if args.reports
        else []
    )
    outputs = _split_choices(args.outputs, VALID_OUTPUTS, "交付格式")
    try:
        indication = args.indication
        cutoff = args.cutoff
        if args.request:
            from ci_workflow.application.intake import build_public_intake

            intake = build_public_intake(
                args.request,
                reports=cast(Any, tuple(reports)) if reports else None,
                historical_cutoff=cutoff,
            )
            if intake.ask is not None:
                print(
                    "ASK_REQUIRED "
                    + json.dumps(
                        intake.ask.model_dump(mode="json"),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                )
                return 6
            indication = intake.indication
            cutoff = intake.historical_cutoff
        elif not reports:
            raise ContractError("使用 --indication 创建项目时必须指定 --reports")
        contract = create_project_contract(
            indication=indication,
            reports=reports,
            outputs=outputs,
            timezone=args.timezone,
            cutoff=cutoff,
        )
        root = create_project_workspace(Path(args.root), contract)
    except (ValueError, ProjectWorkspaceError) as exc:
        raise ContractError(str(exc)) from exc
    print(f"PROJECT_CREATED 项目已创建：{root}")
    return 0


def _verify_project(args: argparse.Namespace) -> int:
    try:
        verification = verify_project_workspace(Path(args.root))
    except ProjectWorkspaceError as exc:
        raise ContractError(str(exc)) from exc
    print(
        "PROJECT_OK 项目可继续使用："
        f"{verification.project_root}；合同版本 "
        f"{verification.contract.contract_version}"
    )
    return 0


def _project_share_handler(args: argparse.Namespace) -> int:
    from ci_workflow.application.latest_delivery import read_current_delivery
    from ci_workflow.application.share_export import (
        ShareViewSelection,
        export_current_html_share,
    )

    project = Path(args.root)
    try:
        current = read_current_delivery(project)
        if current is None:
            raise ValueError("当前交付不存在，不能从旧HTML生成分享包")
        reports = _split_choices(args.reports, VALID_REPORTS, "报告类型")
        if args.view_config:
            payload = _load_json(Path(args.view_config))
            if (
                set(payload) != {"schema_version", "selections"}
                or payload["schema_version"] != "1.0"
            ):
                raise ValueError("分享视图配置版本或字段不符合合同")
            if not isinstance(payload["selections"], list):
                raise ValueError("分享视图配置selections必须为列表")
            selections = tuple(ShareViewSelection.model_validate(item)
                               for item in payload["selections"])
            if {item.report for item in selections} != set(reports):
                raise ValueError("分享视图配置的报告集合与--reports不一致")
        else:
            selections = tuple(
                ShareViewSelection(
                    report=cast(Literal["A", "B", "C"], report),
                    revision=current.revision,
                )
                for report in reports
            )
        receipt = export_current_html_share(
            project, Path(args.output), selections=selections,
        )
    except (OSError, ValueError, ProjectWorkspaceError) as error:
        raise ContractError(str(error)) from error
    print(
        f"SHARE_READY revision={receipt.current_revision} reports="
        f"{','.join(receipt.reports)} sha256={receipt.sha256} output={receipt.output}"
    )
    return 0


def _package_verify(args: argparse.Namespace) -> int:
    manifest = verify_package(Path(args.root))
    package = cast(dict[str, Any], manifest["package"])
    print(f"PACKAGE_OK version={package['version']} stage={package['build_stage']}")
    return 0


def _capability_preflight(args: argparse.Namespace) -> int:
    source_routes = tuple(
        _split_choices(
            args.source_routes,
            {"public-http", "public-browser", "authenticated-browser"},
            "来源访问方式",
        )
    )
    if bool(args.project) == bool(args.reports):
        raise ContractError("请在项目目录和内联报告选择中任选一种，不要同时填写")
    try:
        if args.project:
            project_root = Path(args.project)
            selection = selection_from_project(
                project_root,
                source_routes=cast(Any, source_routes),
                needs_document_ingestion=True,
                needs_ocr=args.require_ocr,
            )
        else:
            reports = _split_choices(args.reports, VALID_REPORTS, "报告类型")
            requested_outputs = _split_choices(args.outputs or "html", VALID_OUTPUTS, "交付格式")
            outputs = ["html", *(item for item in requested_outputs if item != "html")]
            selection = CapabilitySelection(
                reports=cast(Any, tuple(reports)),
                outputs=cast(Any, tuple(outputs)),
                source_routes=cast(Any, source_routes),
                needs_document_ingestion=True,
                needs_ocr=args.require_ocr,
            )
            project_root = Path.cwd()
        matrix = run_capability_preflight(
            selection,
            host=args.host,
            probe=RuntimeCapabilityProbe(
                independent_context_probe=(
                    Path(args.independent_context_probe)
                    if args.independent_context_probe
                    else None
                )
            ),
            project_root=project_root,
        )
    except (ValueError, ProjectWorkspaceError) as exc:
        raise ContractError(str(exc)) from exc
    if args.json:
        receipt_path = Path(args.json)
        _atomic_json_write(receipt_path, matrix.model_dump(mode="json"))
    else:
        receipt_path = persist_capability_matrix(project_root, matrix)
    print(f"能力预检完成 PREFLIGHT_COMPLETE；结果已保存：{receipt_path}")
    for message in matrix.user_messages:
        print(message)
    return 0 if matrix.overall_state == "ready" else 5


def _project_run_handler(args: argparse.Namespace) -> int:
    from ci_workflow.application.capability_preflight import RuntimeCapabilityProbe
    from ci_workflow.application.run_service import (
        ContractConfigError,
        EvidenceBlockedError,
        RendererUnavailableError,
        RunError,
        run_project,
    )

    try:
        result = run_project(
            Path(args.root),
            resume=args.resume,
            require_bound_submission=True,
            capability_host=args.host,
            capability_probe=RuntimeCapabilityProbe(
                independent_context_probe=(
                    Path(args.independent_context_probe)
                    if args.independent_context_probe
                    else None
                )
            ),
        )
    except ContractConfigError as exc:
        raise ContractError(str(exc)) from exc
    except RendererUnavailableError as exc:
        print(f"RENDERER_UNAVAILABLE {exc}", file=sys.stderr)
        return 3
    except EvidenceBlockedError as exc:
        print(f"EVIDENCE_BLOCKED {exc}", file=sys.stderr)
        return 4
    except RunError as exc:
        print(f"RUN_FAILED {exc}", file=sys.stderr)
        return 2

    if result.outcome == "evidence_blocked":
        print(
            "项目因关键证据不足暂时无法继续。\n"
            f"运行标识：{result.run_id}\n"
            "请查看项目目录中的「证据不足说明」了解详情。"
        )
        return 4
    elif result.outcome == "capability_blocked":
        print(
            "当前执行环境缺少本次研究或 HTML 交付所需能力，项目已安全暂停。\n"
            f"运行标识：{result.run_id}\n"
            "请查看项目目录中的能力预检说明，恢复后从同一项目继续。"
        )
        return 5
    elif result.outcome == "failed":
        print(f"本轮运行遇到技术问题，未能完成。\n运行标识：{result.run_id}")
        return 2
    elif result.outcome == "running":
        print(f"项目已启动，证据采集工作正在进行中。\n运行标识：{result.run_id}")
        return 0
    elif result.outcome == "awaiting_user":
        print(
            "项目正在等待一次性补充关键公开资料。\n"
            f"运行标识：{result.run_id}\n"
            "请查看项目目录中的「需要补充的公开资料」清单。"
        )
        return 6
    elif result.outcome == "recovery_required":
        print(
            "补充资料已核验，受影响报告需要按项目中的重抽取任务重建科学载荷后"
            "重新 research submit；当前未发布旧载荷报告。\n"
            f"运行标识：{result.run_id}"
        )
        return 7
    else:
        print(f"项目运行完成。运行标识：{result.run_id}")
        return 0


def _research_capture_handler(args: argparse.Namespace) -> int:
    from ci_workflow.storage.content_store import ContentAddressedStore, ContentIntegrityError
    from ci_workflow.storage.source_derivation import SourceDerivationError, capture_source_text

    root = Path(args.root)
    try:
        verify_project_workspace(root)
        source = Path(args.input)
        if source.is_symlink() or not source.is_file():
            raise ContractError("来源必须是普通文件，不能是符号链接")
        text, receipt = capture_source_text(root, source.read_bytes(), media_type=args.media_type)
        payload = json.dumps(
            {"content_text": text, "media_type": args.media_type,
             "text_derivation": receipt.model_dump(mode="json")},
            ensure_ascii=False, sort_keys=True,
        ).encode("utf-8")
        blob = ContentAddressedStore(root).put_bytes(payload, media_type="application/json")
    except (SourceDerivationError, ContentIntegrityError, ProjectWorkspaceError) as error:
        raise ContractError(str(error)) from error
    except OSError as error:
        raise ContractError("来源文件或项目存储不可访问；未完成来源捕获") from error
    print(json.dumps({"capture_path": blob.relative_path, "sha256": blob.sha256}, sort_keys=True))
    return 0


def _research_fetch_ctgov_handler(args: argparse.Namespace) -> int:
    from ci_workflow.sources.connectors.ctgov_fetch import (
        derive_ctgov_records,
        fetch_ctgov_condition,
    )
    from ci_workflow.storage.content_store import ContentAddressedStore, ContentIntegrityError
    from ci_workflow.storage.source_derivation import SourceDerivationError

    root = Path(args.root)
    try:
        verify_project_workspace(root)
        result = fetch_ctgov_condition(
            root, args.condition, page_size=args.page_size, max_pages=args.max_pages,
        )
        store = ContentAddressedStore(root)
        entries: list[dict[str, object]] = []
        projection = "not_attempted"
        if result.pagination_complete:
            try:
                records = derive_ctgov_records(root, result)
            except SourceDerivationError:
                projection = "invalid_record"
            else:
                projection = "complete"
                for record in records:
                    payload = json.dumps({
                        "content_text": record.content_text, "media_type": "application/json",
                        "text_derivation": record.text_derivation.model_dump(mode="json"),
                    }, ensure_ascii=False, sort_keys=True).encode("utf-8")
                    captured = store.put_bytes(payload, media_type="application/json")
                    entry = record.model_dump(
                        mode="json", exclude={"content_text", "text_derivation"},
                    )
                    entries.append({
                        **entry, "capture_path": captured.relative_path, "sha256": captured.sha256,
                    })
        receipt = {
            "schema_version": "1.0",
            "acquisition": result.model_dump(mode="json", exclude={"studies"}),
            "projection_status": projection,
            "records": entries,
            "limitation": "仅获取当前公开记录；历史版本重建、竞品闭包及独立科学复核尚未完成",
        }
        blob = store.put_bytes(
            json.dumps(receipt, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            media_type="application/json",
        )
    except (OSError, ValueError, ContentIntegrityError, ProjectWorkspaceError) as error:
        raise ContractError("CT.gov来源获取或项目存储校验失败；不能视为无数据") from error
    print(json.dumps({
        "capture_path": blob.relative_path, "sha256": blob.sha256,
        "status": result.status, "projection_status": projection,
        "records": len(entries), "universe_closed": False,
    }, sort_keys=True))
    return 0 if result.pagination_complete and projection == "complete" else 7


def _research_semantic_review_handler(args: argparse.Namespace) -> int:
    """发射/提交 B 报告语义复核工作项（P3.7 流程接线）。"""
    import hashlib
    import json

    from ci_workflow.application.semantic_review_task import (
        SemanticReviewTask,
        build_semantic_review_task,
        store_semantic_adjudications,
        validate_semantic_review_submission,
    )
    from ci_workflow.renderers.portal.report_b import (
        ReportBPortalData,
        semantic_review_buckets_for,
        semantic_review_domain_inputs,
    )

    root = Path(args.root)
    data_path = Path(args.report_data)
    try:
        verification = verify_project_workspace(root)
    except ProjectWorkspaceError as error:
        raise ContractError(str(error)) from error
    try:
        data = ReportBPortalData.model_validate(
            json.loads(data_path.read_text(encoding="utf-8")),
        )
    except (OSError, ValueError) as error:
        raise ContractError(f"B 载荷无法解析：{error}") from error

    domain_inputs = semantic_review_domain_inputs(data)
    pools = [
        (records, semantic_review_buckets_for(domain, records))
        for domain, records in sorted(domain_inputs.items())
    ]
    pairs: list[Any] = []
    for records, buckets in pools:
        pairs.extend(
            build_semantic_review_task(
                verification.contract.project_id, records, buckets=buckets,
            ).pairs,
        )
    from ci_workflow.application.semantic_review_task import semantic_policy_identity

    task = SemanticReviewTask(
        task_id=f"semantic-review-{len(pairs)}",
        project_id=verification.contract.project_id,
        policy_version=semantic_policy_identity(),
        pairs=tuple(pairs),
    )

    if args.emit:
        work_item = root / "state/work-items/semantic-review.json"
        work_item.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(
            task.model_dump(mode="json"), ensure_ascii=False,
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        if work_item.exists():
            if work_item.is_symlink() or not work_item.is_file():
                raise ContractError("语义复核工作项必须是普通文件")
            if work_item.read_bytes() != encoded:
                try:
                    SemanticReviewTask.model_validate_json(work_item.read_bytes())
                except ValueError as error:
                    raise ContractError("已有语义复核工作项损坏，拒绝覆盖") from error
        work_item.write_bytes(encoded)
        print(json.dumps({
            "work_item": work_item.relative_to(root).as_posix(),
            "pair_count": len(pairs),
            "state": task.state,
        }, ensure_ascii=False))
        return 0

    # --submit：宿主提交经四重绑定验证后写入项目级渲染注入状态。
    if not args.submission:
        raise ContractError("--submit 需要 --submission 指向已批准归并 JSON")
    submission_path = Path(args.submission)
    try:
        payloads = json.loads(submission_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ContractError(f"提交文件无法解析：{error}") from error
    if not isinstance(payloads, list):
        raise ContractError("提交必须是已批准归并的 JSON 数组")
    try:
        validated = validate_semantic_review_submission(
            payloads, task,
            records=[record for records, _buckets in pools for record in records],
            buckets=[bucket for _records, buckets in pools for bucket in buckets],
        )
    except ValueError as error:
        raise ContractError(f"语义归并提交被拒绝：{error}") from error
    digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
    store_semantic_adjudications(
        root,
        report="B",
        payload_digest=digest,
        project_id=verification.contract.project_id,
        task_id=task.task_id,
        adjudications=validated,
    )
    print(json.dumps({
        "stored": "state/semantic-adjudications.json",
        "adjudication_count": len(validated),
        "payload_sha256": digest,
    }, ensure_ascii=False))
    return 0


def _research_fetch_pubmed_handler(args: argparse.Namespace) -> int:
    from ci_workflow.sources.connectors.pubmed_fetch import fetch_pubmed_results
    from ci_workflow.storage.content_store import ContentAddressedStore, ContentIntegrityError

    root = Path(args.root)
    try:
        verify_project_workspace(root)
        result = fetch_pubmed_results(
            root, args.term, page_size=args.page_size, max_pages=args.max_pages,
        )
    except ProjectWorkspaceError as error:
        raise ContractError(str(error)) from error
    except ValueError as error:
        raise ContractError(f"PubMed 检索参数不符合要求：{error}") from error
    try:
        store = ContentAddressedStore(root)
        receipt = {
            "schema_version": "1.0",
            "acquisition": result.model_dump(mode="json", exclude={"records"}),
            "record_count": len(result.records),
            "records": [
                {
                    "pmid": record.pmid,
                    "title": record.title,
                    "publication_types": list(record.publication_types),
                }
                for record in result.records
            ],
            "limitation": (
                "仅获取PubMed当前公开记录；论文—试验关系判定、竞品闭包及独立科学复核尚未完成"
            ),
        }
        blob = store.put_bytes(
            json.dumps(receipt, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            media_type="application/json",
        )
    except (OSError, ContentIntegrityError) as error:
        raise ContractError("PubMed获取回执无法写入项目存储；不能视为无数据") from error
    print(json.dumps({
        "capture_path": blob.relative_path, "sha256": blob.sha256,
        "status": result.status, "pagination_complete": result.pagination_complete,
        "records": len(result.records), "total_count": result.total_count,
        "universe_closed": False,
    }, sort_keys=True))
    return 0 if result.pagination_complete else 7


def _research_submit_handler(args: argparse.Namespace) -> int:
    from ci_workflow.application.research_package_submission import (
        ResearchPackageSubmissionError,
        submit_product_research_package,
    )

    report_packages = {
        report: Path(value)
        for report, value in (("A", args.a_package), ("B", args.b_package), ("C", args.c_package))
        if value is not None
    }
    try:
        result = submit_product_research_package(
            Path(args.root),
            audit_package=Path(args.package),
            report_packages=cast(Any, report_packages),
        )
    except (ResearchPackageSubmissionError, ProjectWorkspaceError) as exc:
        raise ContractError(str(exc)) from exc
    state = "RESEARCH_PACKAGE_REPLAYED" if result.replayed else "RESEARCH_PACKAGE_ACCEPTED"
    print(f"{state} 研究资料已通过严格校验并绑定：{result.manifest_path}")
    return 0


def _publication_unavailable_handler(args: argparse.Namespace) -> int:
    from ci_workflow.application.publication_manual_gate import (
        PublicationManualGateError,
        mark_publication_files_unavailable,
    )

    manifest = _load_json(Path(args.root) / "manifests/current_run.json")
    gate = manifest.get("manual_supply_gate")
    if not isinstance(gate, dict) or not isinstance(gate.get("snapshot_id"), str):
        raise ContractError("当前项目没有等待响应的 publication 补件门")
    sufficient = args.official_evidence == "sufficient"
    try:
        updated = mark_publication_files_unavailable(
            Path(args.root),
            snapshot_id=gate["snapshot_id"],
            official_evidence_sufficient=sufficient,
            limitation_zh=args.limitation,
        )
    except PublicationManualGateError as error:
        raise ContractError(str(error)) from error
    outcome = "带限制继续" if updated.limitation_zh else "转为证据不足交付"
    print(f"PUBLICATION_UNAVAILABLE_RECORDED 已记录一次性回答：{outcome}")
    return 0


def _yaozh_answer_handler(args: argparse.Namespace) -> int:
    from ci_workflow.application.yaozh_access import (
        YaozhAccessError,
        answer_yaozh_access,
    )

    try:
        outcome = answer_yaozh_access(Path(args.root), args.answer)
    except YaozhAccessError as exc:
        raise ContractError(str(exc)) from exc
    state = "YAOZH_ANSWER_REPLAYED" if outcome.replayed else "YAOZH_ANSWER_RECORDED"
    detail = (
        "药智网访问条件此前已记录，本次为幂等重放，本项目不再询问。"
        if outcome.replayed
        else "药智网访问条件已记录，本项目不再询问。"
    )
    print(
        f"{state} {detail}\n"
        f"回答：{outcome.record.answer}；{outcome.decision.rationale_zh}\n"
        f"记录文件：{outcome.record_path}"
    )
    return 0


def _yaozh_check_handler(args: argparse.Namespace) -> int:
    from ci_workflow.application.yaozh_access import YaozhAccessError, check_yaozh_runtime_access

    try:
        result = check_yaozh_runtime_access(Path(args.root), host=args.host)
    except YaozhAccessError as error:
        raise ContractError(str(error)) from error
    print(result.model_dump_json())
    return 0


def _yaozh_observe_handler(args: argparse.Namespace) -> int:
    from ci_workflow.application.yaozh_access import (
        YaozhAccessError,
        YaozhSessionObservation,
        persist_yaozh_route_access_receipt,
    )

    try:
        observation = YaozhSessionObservation.model_validate(_load_json(Path(args.observation)))
        outcome = persist_yaozh_route_access_receipt(Path(args.root), observation)
    except (ValueError, YaozhAccessError) as exc:
        raise ContractError("药智会话观察不符合无凭据合同") from exc
    state = "YAOZH_ROUTE_RECEIPT_REPLAYED" if outcome.replayed else "YAOZH_ROUTE_RECEIPT_RECORDED"
    print(f"{state} {outcome.receipt.technical_state}：{outcome.receipt.user_action_zh}")
    return 0


def _visual_acceptance_handler(args: argparse.Namespace) -> int:
    from ci_workflow.application.visual_acceptance import (
        VisualAcceptanceError,
        accept_visual_artifact,
    )

    try:
        result = accept_visual_artifact(
            Path(args.root),
            report=args.report,
            version=args.version,
            visual_plan_path=Path(args.visual_plan),
            render_evidence_path=Path(args.render_evidence),
            verification_reference_path=Path(args.verification_reference),
            beautification_round=args.beautification_round,
        )
    except VisualAcceptanceError as exc:
        raise ContractError(str(exc)) from exc
    print(
        "视觉验收已完成："
        f"{result.manifest.report} 类报告 {result.manifest.report_version} "
        f"已写入接受清单 {result.stored_manifest_path}；"
        f"已完成独立视觉复核，可进入交付流程（运行 {result.acceptance_run_id}）"
    )
    return 0


def _fixture_run_handler(args: argparse.Namespace) -> int:
    from ci_workflow.application.fixture_runner import (
        FixtureCaseError,
        run_fixture_case,
    )
    from ci_workflow.application.run_service import (
        EvidenceBlockedError,
        RendererUnavailableError,
        RunError,
    )

    try:
        reports = _split_choices(args.reports, VALID_REPORTS, "报告类型")
        outputs = _split_choices(args.outputs, VALID_OUTPUTS, "输出格式")
        catalog_path = (
            Path(args.catalog).expanduser()
            if args.catalog
            else Path(__file__).resolve().parents[2] / "fixtures/catalog.yaml"
        )
        if args.host_smoke_recovery:
            if args.case != "host-smoke-v1":
                raise ContractError("完整宿主冒烟只允许 host-smoke-v1")
            from ci_workflow.application.host_smoke_scenario import run_host_smoke_scenario

            try:
                scenario = run_host_smoke_scenario(
                    project_root=Path(args.project),
                    catalog_path=catalog_path,
                    resume=args.resume,
                )
            except (OSError, ValueError, RuntimeError) as exc:
                raise ContractError(str(exc)) from exc
            print(
                "宿主冒烟完成：关键证据不足时未生成草稿，补件后已恢复并验证站点式 HTML。\n"
                f"初始运行：{scenario.record['initial']['run_id']}\n"
                f"恢复运行：{scenario.run_result.run_id}"
            )
            return 0
        result = run_fixture_case(
            case_id=args.case,
            project_root=Path(args.project),
            reports=reports,
            outputs=outputs,
            catalog_path=catalog_path,
            resume=args.resume,
        )
    except ContractError:
        raise
    except FixtureCaseError as exc:
        raise ContractError(str(exc)) from exc
    except RendererUnavailableError as exc:
        print(f"RENDERER_UNAVAILABLE {exc}", file=sys.stderr)
        return 3
    except EvidenceBlockedError as exc:
        print(f"EVIDENCE_BLOCKED {exc}", file=sys.stderr)
        return 4
    except RunError as exc:
        print(f"RUN_FAILED {exc}", file=sys.stderr)
        return 2

    run_r = result.run_result
    if run_r.outcome == "evidence_blocked":
        print(
            "项目因关键证据不足暂时无法继续。\n"
            f"运行标识：{run_r.run_id}\n"
            f"案例：{result.case_id}\n"
            "请查看项目目录中的「证据不足说明」了解详情。"
        )
        return 4
    elif run_r.outcome == "capability_blocked":
        print(
            "当前执行环境缺少本次研究或 HTML 交付所需能力，项目已安全暂停。\n"
            f"运行标识：{run_r.run_id}\n"
            f"案例：{result.case_id}"
        )
        return 5
    elif run_r.outcome == "failed":
        print(f"本轮运行遇到技术问题，未能完成。\n运行标识：{run_r.run_id}")
        return 2
    elif run_r.outcome == "running":
        print(
            "案例已启动，证据采集工作正在进行中。\n"
            f"运行标识：{run_r.run_id}\n"
            f"案例：{result.case_id}"
        )
        return 0
    else:
        print(f"案例运行完成。运行标识：{run_r.run_id}")
        return 0


def _review_issue_handler(args: argparse.Namespace) -> int:
    from ci_workflow.application.review_issuer import (
        ReviewIssuanceError,
        issue_review_receipt,
        resolve_host_executable,
    )

    review_command = tuple(
        part.strip() for part in str(args.review_command).split(",") if part.strip()
    )
    if not review_command:
        raise ContractError("请提供宿主可执行文件之后的复核命令参数")
    try:
        host_executable = resolve_host_executable(
            cast(Any, args.host),
            explicit_path=args.host_executable,
        )
        outcome = issue_review_receipt(
            project_root=Path(args.root),
            report_kind=args.report,
            reviewer_id=args.reviewer_id,
            review_session_id=args.review_session_id,
            host=cast(Any, args.host),
            host_executable=host_executable,
            review_argv=review_command,
            verdict_relative_path=args.verdict,
        )
    except ReviewIssuanceError as exc:
        raise ContractError(str(exc)) from exc
    print(
        "REVIEW_ISSUED 独立科学复核回执已签发："
        f"报告 {args.report}；回执 {outcome.receipt_path}；"
        f"签发记录 {outcome.record_path}"
    )
    return 0


def _not_implemented(args: argparse.Namespace) -> int:
    print(
        f"CAPABILITY_NOT_IMPLEMENTED 功能尚未实现：{args.command_path}",
        file=sys.stderr,
    )
    return 3


def _build_parser() -> argparse.ArgumentParser:
    parser = ChineseArgumentParser(
        prog="ci-workflow",
        description="竞品调研工作流：根据适应症自主研究并生成独立 A/B/C 站点式 HTML 门户。",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="显示版本并退出",
    )
    groups = parser.add_subparsers(dest="group", required=True)

    package = groups.add_parser("package", help="核验安装包")
    package_commands = package.add_subparsers(dest="package_command", required=True)
    package_verify = package_commands.add_parser("verify", help="核验安装包完整性与版本")
    package_verify.add_argument("--root", required=True, help="安装包根目录")
    package_verify.set_defaults(handler=_package_verify)

    project = groups.add_parser("project", help="创建竞品调研项目并管理运行")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    project_create = project_commands.add_parser("create", help="创建竞品调研项目")
    project_create.add_argument(
        "--root", "--project", dest="root", required=True, help="新项目目录"
    )
    create_input = project_create.add_mutually_exclusive_group(required=True)
    create_input.add_argument("--request", help="一句话竞品调研请求")
    create_input.add_argument("--indication", help="高级模式的显式适应症")
    project_create.add_argument("--reports", help="报告类型，如 A,B,C；缺省时返回原生 Ask")
    project_create.add_argument("--outputs", default="html", help="交付格式固定为 html")
    project_create.add_argument(
        "--timezone", default="Asia/Shanghai", help="项目时区，默认 Asia/Shanghai"
    )
    project_create.add_argument("--cutoff", help="可选的历史数据截止日或日期时间")
    project_create.set_defaults(handler=_create_project)
    project_verify = project_commands.add_parser("verify", help="核验项目合同")
    project_verify.add_argument("--root", "--project", dest="root", required=True, help="项目目录")
    project_verify.set_defaults(handler=_verify_project)
    project_run = project_commands.add_parser("run", help="运行或恢复项目")
    project_run.add_argument("--root", "--project", dest="root", required=True, help="项目目录")
    project_run.add_argument("--resume", action="store_true", help="从同一项目检查点恢复")
    project_run.add_argument(
        "--host",
        choices=("local", "codex", "hermes", "omp"),
        default="local",
        help="当前执行宿主，默认 local",
    )
    project_run.add_argument(
        "--independent-context-probe",
        help="宿主独立上下文能力探针的可执行文件；必须实际运行并返回回执",
    )
    project_run.set_defaults(handler=_project_run_handler)
    project_share = project_commands.add_parser(
        "share", help="从已提交的current生成离线HTML报告分享包"
    )
    project_share.add_argument(
        "--root", "--project", dest="root", required=True, help="项目目录"
    )
    project_share.add_argument("--output", required=True, help="新分享包 ZIP 路径；不得覆盖")
    project_share.add_argument(
        "--reports", default="A,B,C", help="导出报告，如 A 或 A,B,C"
    )
    project_share.add_argument(
        "--view-config", help="可选的版本绑定视图配置 JSON"
    )
    project_share.set_defaults(handler=_project_share_handler)
    project_accept_visual = project_commands.add_parser(
        "accept-visual", help="持久化独立网页视觉验收并推进 HTML 状态"
    )
    project_accept_visual.add_argument(
        "--root", "--project", dest="root", required=True, help="项目目录"
    )
    project_accept_visual.add_argument("--version", required=True, help="报告版本")
    project_accept_visual.add_argument(
        "--report", choices=("A", "B", "C"), default="B", help="独立报告类型；兼容旧命令默认B"
    )
    project_accept_visual.add_argument(
        "--visual-plan", "--plan", dest="visual_plan", required=True, help="视觉策划书 JSON"
    )
    project_accept_visual.add_argument(
        "--render-evidence",
        "--render",
        dest="render_evidence",
        required=True,
        help="真实呈现证据 JSON",
    )
    project_accept_visual.add_argument(
        "--verification-reference",
        "--verification",
        dest="verification_reference",
        required=True,
        help="独立视觉审阅结论 JSON",
    )
    project_accept_visual.add_argument(
        "--beautification-round",
        type=int,
        default=1,
        help="最终美化轮次，默认 1（允许 1 到 3）",
    )
    project_accept_visual.set_defaults(handler=_visual_acceptance_handler)

    capability = groups.add_parser("capability", help="检查所选任务所需能力")
    capability_commands = capability.add_subparsers(dest="capability_command", required=True)
    preflight = capability_commands.add_parser("preflight", help="检查所选任务所需能力")
    preflight.add_argument("--host", required=True, choices=("local", "codex", "hermes", "omp"))
    preflight.add_argument("--project", help="从已保存的项目合同读取报告与格式选择")
    preflight.add_argument("--reports", help="创建项目前内联指定报告类型，如 A,B,C")
    preflight.add_argument("--outputs", help="交付格式固定为 html")
    preflight.add_argument(
        "--source-routes",
        default="public-http,public-browser",
        help="适用的来源访问方式",
    )
    preflight.add_argument("--require-ocr", action="store_true", help="本次已知需要读取扫描件")
    preflight.add_argument(
        "--independent-context-probe",
        help="宿主独立上下文能力探针的可执行文件；必须实际运行并返回回执",
    )
    preflight.add_argument(
        "--json",
        help="保存机器可读能力矩阵的位置；项目模式默认保存到项目内 capabilities/preflight.json",
    )
    preflight.set_defaults(handler=_capability_preflight)

    research = groups.add_parser("research", help="提交宿主完成的自主研究资料")
    research_commands = research.add_subparsers(dest="research_command", required=True)
    research_capture = research_commands.add_parser(
        "capture", help="保留原始来源并生成可验证文本回执"
    )
    research_capture.add_argument(
        "--root", "--project", dest="root", required=True, help="项目目录"
    )
    research_capture.add_argument("--input", required=True, help="公开来源原始文件")
    research_capture.add_argument("--media-type", required=True, help="原始文件媒体类型")
    research_capture.set_defaults(handler=_research_capture_handler)
    research_fetch = research_commands.add_parser(
        "fetch-ctgov", help="逐页获取当前CT.gov记录并保留原始证据，不代替闭包或历史重建"
    )
    research_fetch.add_argument("--root", "--project", dest="root", required=True)
    research_fetch.add_argument("--condition", required=True, help="英文适应症或别名检索式")
    research_fetch.add_argument("--page-size", type=int, default=100)
    research_fetch.add_argument(
        "--max-pages", type=int, default=1000, help="资源上限，耗尽不算完成"
    )
    research_fetch.set_defaults(handler=_research_fetch_ctgov_handler)
    research_fetch_pubmed = research_commands.add_parser(
        "fetch-pubmed", help="逐页检索并获取当前PubMed记录原文，不代替闭包或论文判定"
    )
    research_fetch_pubmed.add_argument("--root", "--project", dest="root", required=True)
    research_fetch_pubmed.add_argument("--term", required=True, help="PubMed 检索式或字段限定式")
    research_fetch_pubmed.add_argument("--page-size", type=int, default=200)
    research_fetch_pubmed.add_argument(
        "--max-pages", type=int, default=1000, help="资源上限，耗尽不算完成"
    )
    research_fetch_pubmed.set_defaults(handler=_research_fetch_pubmed_handler)
    research_semantic = research_commands.add_parser(
        "semantic-review",
        help="发射或提交 B 报告语义归并复核工作项（宿主模型提案+独立上下文复核）",
    )
    research_semantic.add_argument("--root", "--project", dest="root", required=True)
    research_semantic.add_argument("--report-data", required=True, help="B 门户载荷 JSON")
    mode = research_semantic.add_mutually_exclusive_group(required=True)
    mode.add_argument("--emit", action="store_true", help="发射复核工作项")
    mode.add_argument("--submit", action="store_true", help="验证并保存宿主提交")
    research_semantic.add_argument("--submission", help="已批准归并 JSON 数组（--submit 必填）")
    research_semantic.set_defaults(handler=_research_semantic_review_handler)
    research_submit = research_commands.add_parser(
        "submit", help="校验并绑定严格研究审计包及 A/B/C 科学载荷"
    )
    research_submit.add_argument("--root", "--project", dest="root", required=True, help="项目目录")
    research_submit.add_argument("--package", required=True, help="v1.3 研究审计包 JSON")
    research_submit.add_argument("--a-package", help="A 类科学载荷 JSON")
    research_submit.add_argument("--b-package", help="B 类科学载荷 JSON")
    research_submit.add_argument("--c-package", help="C 类科学载荷 JSON")
    research_submit.set_defaults(handler=_research_submit_handler)

    publication = groups.add_parser("publication", help="处理关键公开论文补件")
    publication_commands = publication.add_subparsers(dest="publication_command", required=True)
    publication_unavailable = publication_commands.add_parser(
        "unavailable", help="记录本快照无法取得补件的一次性回答"
    )
    publication_unavailable.add_argument(
        "--root", "--project", dest="root", required=True, help="项目目录"
    )
    publication_unavailable.add_argument(
        "--official-evidence",
        required=True,
        choices=("sufficient", "insufficient"),
        help="官方登记或监管来源是否足以回答核心问题",
    )
    publication_unavailable.add_argument(
        "--limitation", help="官方证据足够继续时必须提供的中文限制说明"
    )
    publication_unavailable.set_defaults(handler=_publication_unavailable_handler)

    yaozh = groups.add_parser("yaozh", help="记录本项目一次性的药智网访问条件回答")
    yaozh_commands = yaozh.add_subparsers(dest="yaozh_command", required=True)
    yaozh_answer = yaozh_commands.add_parser(
        "answer", help="持久化一次性的药智网访问条件回答（不接收任何凭据）"
    )
    yaozh_answer.add_argument("--root", "--project", dest="root", required=True, help="项目目录")
    yaozh_answer.add_argument(
        "--answer",
        required=True,
        choices=("available", "unavailable", "skipped"),
        help="访问条件回答：available=具备，unavailable=不具备，skipped=无账号跳过",
    )
    yaozh_answer.set_defaults(handler=_yaozh_answer_handler)
    yaozh_observe = yaozh_commands.add_parser(
        "observe", help="提交宿主产生的无凭据药智会话观察"
    )
    yaozh_observe.add_argument("--root", "--project", dest="root", required=True, help="项目目录")
    yaozh_observe.add_argument(
        "--observation", required=True, help="符合合同的药智会话观察 JSON"
    )
    yaozh_observe.set_defaults(handler=_yaozh_observe_handler)
    yaozh_check = yaozh_commands.add_parser("check", help="检查本运行药智观察是否仍可短期复用")
    yaozh_check.add_argument("--root", "--project", dest="root", required=True, help="项目目录")
    yaozh_check.add_argument(
        "--host", required=True, choices=("local", "codex", "hermes", "omp"), help="当前宿主"
    )
    yaozh_check.set_defaults(handler=_yaozh_check_handler)

    review = groups.add_parser("review", help="独立科学复核签发入口（供独立复核宿主会话使用）")
    review_commands = review.add_subparsers(dest="review_command", required=True)
    review_issue = review_commands.add_parser(
        "issue",
        help="绑定已发布的科学复核请求，运行独立复核进程并签发正式回执",
    )
    review_issue.add_argument("--root", "--project", dest="root", required=True, help="项目目录")
    review_issue.add_argument("--report", required=True, choices=("A", "B", "C"), help="报告类型")
    review_issue.add_argument("--reviewer-id", required=True, help="独立复核者身份")
    review_issue.add_argument("--review-session-id", required=True, help="本次独立复核宿主会话标识")
    review_issue.add_argument(
        "--host", required=True, choices=("codex", "hermes", "omp"), help="复核宿主"
    )
    review_issue.add_argument(
        "--host-executable",
        default=None,
        help="宿主可执行文件路径；缺省从 PATH 解析",
    )
    review_issue.add_argument(
        "--review-command",
        required=True,
        help="宿主可执行文件之后的复核命令参数，逗号分隔",
    )
    review_issue.add_argument(
        "--verdict",
        required=True,
        help="复核结论 JSON 的项目相对路径",
    )
    review_issue.set_defaults(handler=_review_issue_handler)

    fixture = groups.add_parser("fixture", help="运行固定验收案例")
    fixture_commands = fixture.add_subparsers(dest="fixture_command", required=True)
    fixture_run = fixture_commands.add_parser("run", help="运行固定验收案例")
    fixture_run.add_argument("--case", required=True, help="案例标识")
    fixture_run.add_argument("--reports", required=True, help="报告类型，如 A,B,C")
    fixture_run.add_argument("--outputs", default="html", help="输出格式，默认 html")
    fixture_run.add_argument("--project", required=True, help="案例运行输出目录")
    fixture_run.add_argument(
        "--catalog",
        default=None,
        help="唯一 fixture catalog.yaml 路径；缺省用安装包对应根目录（fresh-install 可移植入口）",
    )
    fixture_run.add_argument("--resume", action="store_true", help="从已有 fixture 项目恢复")
    fixture_run.add_argument(
        "--host-smoke-recovery",
        action="store_true",
        help="仅用于候选包验收：完成证据阻断、补件恢复和项目验证",
    )
    fixture_run.set_defaults(handler=_fixture_run_handler)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        handler = cast(Any, args.handler)
        return int(handler(args))
    except ContractError as exc:
        print(f"CONTRACT_ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
