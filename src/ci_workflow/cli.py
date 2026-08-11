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
from typing import Any, Never, cast

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from ci_workflow import __version__

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
    "render-deliver",
    "visual-package-qc",
    "correction-refresh",
    "monitoring",
}
EXPECTED_CLI_CATALOG = [
    "package verify",
    "project create",
    "project verify",
    "project run",
    "capability preflight",
    "fixture run",
]
VALID_REPORTS = {"A", "B", "C"}
VALID_OUTPUTS = {"html", "pdf", "html-ppt", "pptx"}


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

    html_ppt = _load_json(root / "assets/html-ppt/manifest.json")
    _verify_digest(
        root / "assets/html-ppt" / str(html_ppt["license_file"]),
        str(html_ppt["license_sha256"]),
    )
    derived_files = cast(dict[str, str], html_ppt["derived_files"])
    for relative_path, expected in derived_files.items():
        _verify_digest(root / "assets/html-ppt" / relative_path, expected)

    echarts = _load_json(root / "assets/third-party/echarts/manifest.json")
    echarts_root = root / "assets/third-party/echarts"
    _verify_digest(echarts_root / str(echarts["bundle"]), str(echarts["bundle_sha256"]))
    _verify_digest(
        echarts_root / str(echarts["license_file"]), str(echarts["license_sha256"])
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
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
            "project"
        ]
    except (FileNotFoundError, tomllib.TOMLDecodeError, KeyError) as exc:
        raise ContractError("无法读取 pyproject.toml 中的项目版本") from exc
    package = cast(dict[str, Any], manifest["package"])
    if package["name"] != project["name"] or package["version"] != project["version"]:
        raise ContractError("安装包名称或版本与 pyproject.toml 不一致")
    if package["cli_version"] != __version__:
        raise ContractError("安装包声明的 CLI 版本与实际模块不一致")

    public_path = root / str(manifest["public_skill"])
    if _skill_frontmatter(public_path)["name"] != "competitive-intelligence-workflow":
        raise ContractError("公开 Skill 名称不符合安装合同")
    public_agent = _load_json_or_yaml(public_path.parent / "agents/openai.yaml")
    public_interface = cast(dict[str, Any], public_agent.get("interface", {}))
    if "$competitive-intelligence-workflow" not in str(
        public_interface.get("default_prompt", "")
    ):
        raise ContractError("公开 Skill 默认提示未绑定自身 Skill")

    internal_items = cast(list[dict[str, Any]], manifest["internal_skills"])
    declared_ids = {str(item["id"]) for item in internal_items}
    if declared_ids != EXPECTED_INTERNAL_SKILLS:
        raise ContractError("内部 Skill 集合与冻结合同不一致")
    actual_ids = {path.parent.name for path in (root / "skills/_internal").glob("*/SKILL.md")}
    if actual_ids != EXPECTED_INTERNAL_SKILLS:
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
    } | {
        path.relative_to(root).as_posix()
        for path in root.glob("contracts/**/*.schema.json")
    }
    if declared_schema != actual_schema:
        raise ContractError("Schema 清单与安装包实际文件不一致")

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
    root = Path(args.root).resolve()
    if root.exists() and any(root.iterdir()):
        raise ContractError(f"项目目录不是空目录：{root}")
    reports = _split_choices(args.reports, VALID_REPORTS, "报告类型")
    outputs = _split_choices(args.outputs, VALID_OUTPUTS, "交付格式")
    project = {
        "schema_version": "0.1-skeleton",
        "contract_status": "skeleton_pending_phase_1",
        "workflow_version": __version__,
        "indication": args.indication.strip(),
        "reports": reports,
        "outputs": outputs,
    }
    if not project["indication"]:
        raise ContractError("适应症不能为空")
    _atomic_json_write(root / "project.yaml", project)
    print(f"PROJECT_CREATED root={root}")
    return 0


def _verify_project(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    project = _load_json(root / "project.yaml")
    required = {
        "schema_version",
        "contract_status",
        "workflow_version",
        "indication",
        "reports",
        "outputs",
    }
    if set(project) != required:
        raise ContractError("项目骨架字段与当前阶段合同不一致")
    if project["contract_status"] != "skeleton_pending_phase_1":
        raise ContractError("项目骨架状态不符合当前阶段合同")
    if project["workflow_version"] != __version__:
        raise ContractError("项目骨架版本与当前工作流不一致")
    reports = project["reports"]
    outputs = project["outputs"]
    if not isinstance(reports, list) or not reports or not set(reports) <= VALID_REPORTS:
        raise ContractError("项目报告类型无效")
    if not isinstance(outputs, list) or not outputs or not set(outputs) <= VALID_OUTPUTS:
        raise ContractError("项目交付格式无效")
    print(f"PROJECT_OK root={root} status={project['contract_status']}")
    return 0


def _package_verify(args: argparse.Namespace) -> int:
    manifest = verify_package(Path(args.root))
    package = cast(dict[str, Any], manifest["package"])
    print(f"PACKAGE_OK version={package['version']} stage={package['build_stage']}")
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
        description="竞品调研工作流：为临床试验医学人员生成中文站点式报告及所选交付格式。",
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
    project_create.add_argument("--root", required=True, help="新项目目录")
    project_create.add_argument("--indication", required=True, help="适应症")
    project_create.add_argument("--reports", required=True, help="报告类型，如 A,B,C")
    project_create.add_argument(
        "--outputs", default="html", help="交付格式，默认 html；可追加 pdf、html-ppt、pptx"
    )
    project_create.set_defaults(handler=_create_project)
    project_verify = project_commands.add_parser("verify", help="核验项目合同")
    project_verify.add_argument("--root", required=True, help="项目目录")
    project_verify.set_defaults(handler=_verify_project)
    project_run = project_commands.add_parser("run", help="运行或恢复项目")
    project_run.add_argument("--root", required=True, help="项目目录")
    project_run.add_argument("--resume", action="store_true", help="从同一项目检查点恢复")
    project_run.set_defaults(handler=_not_implemented, command_path="project run")

    capability = groups.add_parser("capability", help="检查所选任务所需能力")
    capability_commands = capability.add_subparsers(dest="capability_command", required=True)
    preflight = capability_commands.add_parser("preflight", help="检查所选任务所需能力")
    preflight.add_argument("--host", required=True, choices=("codex", "hermes", "omp"))
    preflight.add_argument("--reports", required=True, help="报告类型，如 A,B,C")
    preflight.add_argument("--outputs", default="html", help="交付格式")
    preflight.set_defaults(handler=_not_implemented, command_path="capability preflight")

    fixture = groups.add_parser("fixture", help="运行固定验收案例")
    fixture_commands = fixture.add_subparsers(dest="fixture_command", required=True)
    fixture_run = fixture_commands.add_parser("run", help="运行固定验收案例")
    fixture_run.add_argument("--case", required=True, help="案例标识")
    fixture_run.add_argument("--root", required=True, help="案例运行目录")
    fixture_run.set_defaults(handler=_not_implemented, command_path="fixture run")
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
