"""HTML 门户视觉策划书合同验证。

该模块只验证生成前的 ``visual-finalization-plan``，不生成或修改报告内容。
验证先读取随包的 Draft 2020-12 Schema，再执行跨字段语义检查；任一边界失败
都以确定性异常阻止 HTML 门户节点继续生成。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

JsonObject = dict[str, Any]

PLAN_SCHEMA_FILENAME = "visual-finalization-plan.schema.json"
RENDER_EVIDENCE_SCHEMA_FILENAME = "visual-render-evidence.schema.json"
VERIFICATION_SCHEMA_FILENAME = "visual-verification-reference.schema.json"
ROUTE_BY_FORMAT: dict[str, str] = {"html": "portal"}
REQUIRED_CONTRACT_FILES: dict[str, frozenset[str]] = {
    "portal": frozenset({"ROUTER.md", "core.md", "project_profile.md", "track_site.md"}),
}
ACCEPTANCE_DOMAINS = frozenset(
    {
        "copy_zh",
        "hierarchy_density",
        "typography_spacing",
        "color_legibility",
        "charts_tables",
        "interaction_consistency",
        "format_rendering",
    }
)
REQUIRED_PALETTE_TOKENS = frozenset({"kz-orange"})
APPROVED_CJK_FONT_TOKENS = frozenset(
    {"Microsoft YaHei", "微软雅黑", "PingFang SC", "Noto Sans SC"}
)
APPROVED_LATIN_FONT_TOKENS = frozenset({"Arial", "Helvetica Neue", "sans-serif"})


class VisualFinalizationError(ValueError):
    """视觉策划书不能进入格式生成节点。"""


def visual_contract_digest(value: Mapping[str, Any]) -> str:
    """返回视觉合同载荷的规范摘要，供状态图绑定当前嵌套证据。"""

    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_schema(filename: str, label: str) -> JsonObject:
    """从源码树或安装包定位视觉合同 Schema，缺失或损坏时失败关闭。"""

    module_path = Path(__file__).resolve()
    candidates = (
        module_path.parents[3] / "schemas" / filename,
        module_path.parents[1] / "schemas" / filename,
    )
    for candidate in candidates:
        try:
            value = json.loads(candidate.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except (OSError, json.JSONDecodeError) as error:
            raise VisualFinalizationError(f"{label}Schema损坏：{candidate}") from error
        if not isinstance(value, dict):
            raise VisualFinalizationError(f"{label}Schema顶层必须是对象：{candidate}")
        return cast(JsonObject, value)
    raise VisualFinalizationError(f"无法定位{label}Schema（源码树与安装布局均缺失）")


def _load_plan_schema() -> JsonObject:
    return _load_schema(PLAN_SCHEMA_FILENAME, "视觉策划书")


def _schema_errors(instance: JsonObject, schema: JsonObject) -> list[ValidationError]:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise VisualFinalizationError(f"视觉策划书Schema无效：{error.message}") from error
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return sorted(validator.iter_errors(instance), key=lambda error: list(error.path))


def _validate_schema(instance: JsonObject, schema: JsonObject) -> None:
    errors = _schema_errors(instance, schema)
    if errors:
        details = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise VisualFinalizationError(f"视觉策划书不符合打包Schema：{details}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VisualFinalizationError(message)


def _nonempty_unique(values: Sequence[Any], label: str) -> None:
    _require(
        all(isinstance(value, str) and value.strip() for value in values),
        f"{label}不能含空标识",
    )
    _require(len(values) == len(set(values)), f"{label}存在重复稳定标识")


def _file_names(paths: Sequence[Any]) -> set[str]:
    return {Path(cast(str, path)).name for path in paths}


def _validate_route_and_bindings(plan: JsonObject) -> None:
    output_format = cast(str, plan["format"])
    route_id = cast(str, plan["route_id"])
    expected_route = ROUTE_BY_FORMAT[output_format]
    _require(
        route_id == expected_route,
        f"格式 {output_format} 必须使用路线 {expected_route}，不能使用 {route_id}",
    )

    report_snapshot = cast(JsonObject, plan["report_snapshot"])
    _require(
        report_snapshot["report"] == plan["report_kind"],
        "视觉策划书报告类型与锁定报告快照不一致",
    )
    _require(
        report_snapshot["report_version"] == plan["report_version"],
        "视觉策划书报告版本与锁定报告快照不一致",
    )

    design_contract = cast(JsonObject, plan["design_contract"])
    _require(
        design_contract["route_id"] == route_id,
        "视觉策划书路线与康哲设计合同路线不一致",
    )
    _require(
        design_contract["manifest"] == "contracts/kangzhe/manifest.json",
        "视觉策划书只能绑定项目内康哲设计合同清单",
    )
    _require(
        design_contract["contract_version"] == "1.0",
        "视觉策划书的康哲设计合同版本必须为1.0",
    )
    loaded_files = cast(list[Any], design_contract["loaded_files"])
    loaded_names = _file_names(loaded_files)
    required_names = REQUIRED_CONTRACT_FILES[route_id]
    missing = sorted(required_names - loaded_names)
    _require(not missing, f"康哲设计合同路线 {route_id} 缺少必读文件：{', '.join(missing)}")
    unexpected_tracks = sorted(
        name
        for name in loaded_names
        if (name.startswith("track_") or name == "htmlppt_fx.md") and name not in required_names
    )
    _require(
        not unexpected_tracks,
        f"康哲设计合同路线 {route_id} 混入其他媒介轨：{', '.join(unexpected_tracks)}",
    )


def _validate_visual_variables(plan: JsonObject) -> None:
    variables = cast(JsonObject, plan["visual_variables"])
    palette_tokens = cast(list[Any], variables["palette_tokens"])
    _require(
        REQUIRED_PALETTE_TOKENS.issubset(set(cast(list[str], palette_tokens))),
        "视觉变量必须保留康哲主强调色令牌",
    )
    department_tokens = cast(JsonObject, variables["department_tokens"])
    _require(
        department_tokens
        == {
            "MED": "kz-orange",
            "CO": "kz-med-blue",
            "DMST": "kz-stats-green",
            "PV": "kz-pv",
        },
        "康哲四部门色系映射不可调换",
    )
    font_stack = cast(list[Any], variables["font_stack"])
    font_names = set(cast(list[str], font_stack))
    _require(
        bool(font_names & APPROVED_CJK_FONT_TOKENS)
        and bool(font_names & APPROVED_LATIN_FONT_TOKENS),
        "视觉变量字体栈必须包含项目批准的中英文兼容字体",
    )
    font_sizes = cast(list[Any], variables["font_sizes_px"])
    _require(16 in font_sizes, "视觉变量必须声明不低于16px的受众正文地板")
    motion_tokens = cast(list[Any], variables["motion_tokens"])
    _require("none" in motion_tokens, "视觉变量必须声明无动效冻结令牌")
    _require(
        plan["scientific_snapshot_immutable"] is True,
        "科学报告快照必须显式保持不可改写",
    )


def _validate_pages(plan: JsonObject) -> None:
    pages = cast(list[JsonObject], plan["page_responsibilities"])
    page_ids = [page["page_id"] for page in pages]
    _nonempty_unique(page_ids, "页面责任")
    for page in pages:
        _require(
            page["source_facts_preserved"] is True,
            f"页面 {page['page_id']} 未声明保留锁定事实",
        )
        _require(
            len(cast(list[Any], page["information_hierarchy"])) >= 1,
            f"页面 {page['page_id']} 缺少信息层级",
        )


def _validate_charts_and_tables(plan: JsonObject) -> None:
    charts = cast(list[JsonObject], plan["chart_syntax"])
    chart_ids = [chart["chart_id"] for chart in charts]
    _nonempty_unique(chart_ids, "图表")
    for chart in charts:
        mark = cast(str, chart["mark"])
        dimensions = cast(JsonObject, chart["dimensions"])
        if mark in {"line", "forest", "heatmap", "scatter"}:
            _require(
                "x" in dimensions and "y" in dimensions,
                f"图表 {chart['chart_id']} 必须声明x/y维度",
            )
        if mark == "bubble":
            _require(
                "x" in dimensions and "y" in dimensions,
                f"气泡图 {chart['chart_id']} 必须声明x/y维度",
            )
            _require(
                "size" in dimensions,
                f"气泡图 {chart['chart_id']} 必须声明size维度",
            )
        if mark in {"heatmap", "bubble"}:
            redundant = chart.get("redundant_encoding")
            _require(
                redundant in {"direct_label", "shape", "texture", "line_style", "position"}
                and any(key in dimensions for key in ("label", "shape", "texture")),
                f"{mark} {chart['chart_id']} 不能只依赖颜色，必须声明文字、形状或纹理辅助编码",
            )

    tables = cast(list[JsonObject], plan["table_syntax"])
    table_ids = [table["table_id"] for table in tables]
    _nonempty_unique(table_ids, "表格")
    for table in tables:
        if table["completeness"] == "complete":
            _require(
                table["after_chart"] is True,
                f"完整表格 {table['table_id']} 必须声明位于对应图表之后",
            )
    _require(
        all(table["completeness"] != "equivalent_chart" for table in tables),
        "HTML 不得用等价图表表格替代完整表格",
    )


def _validate_interactions(plan: JsonObject) -> None:
    states = cast(list[JsonObject], plan["interaction_states"])
    state_ids = [state["state_id"] for state in states]
    _nonempty_unique(state_ids, "交互状态")
    triggers = {cast(str, state["trigger"]) for state in states}
    required = {
        "page_load",
        "filter_change",
        "drill_down",
        "search",
        "keyboard",
        "reduced_motion",
    }
    missing = sorted(required - triggers)
    _require(not missing, f"视觉策划书缺少必须验证的交互状态：{', '.join(missing)}")


def _validate_acceptance_matrix(plan: JsonObject) -> None:
    domains = cast(list[JsonObject], plan["acceptance_matrix"])
    domain_ids = [cast(str, item["domain"]) for item in domains]
    _nonempty_unique(domain_ids, "验收矩阵域")
    _require(
        set(domain_ids) == ACCEPTANCE_DOMAINS,
        "验收矩阵必须逐域覆盖文字、层级、排版、颜色、图表表格、交互和格式渲染",
    )
    _require(
        all(item["required"] is True for item in domains),
        "验收矩阵每个域都必须是必检项",
    )
    generic = {"通过当前格式专属检查", "符合设计规范", "视觉效果良好", "检查通过"}
    for item in domains:
        criteria = cast(list[str], item["criteria"])
        _require(
            all(criterion.strip() not in generic for criterion in criteria),
            f"验收域 {item['domain']} 不能使用笼统通过语句，必须写明可观察标准",
        )


def validate_visual_finalization_plan(
    raw: Mapping[str, Any],
    *,
    expected_report_snapshot_sha256: str | None = None,
    expected_design_contract_sha256: str | None = None,
) -> JsonObject:
    """验证视觉策划书并返回已校验载荷。

    ``expected_*`` 由锁定快照/项目合同的权威调用方提供；提供时会再次比较
    摘要，防止只改写策划书中的摘要字段就伪造新一轮事实或设计合同。
    """

    if not isinstance(raw, Mapping):
        raise VisualFinalizationError("视觉策划书顶层必须是对象")
    plan = dict(raw)
    schema = _load_plan_schema()
    _validate_schema(plan, schema)
    _validate_route_and_bindings(plan)
    if expected_report_snapshot_sha256 is not None:
        _require(
            plan["report_snapshot_sha256"] == expected_report_snapshot_sha256,
            "视觉策划书报告快照摘要与权威锁定快照不一致",
        )
    if expected_design_contract_sha256 is not None:
        _require(
            plan["design_contract_sha256"] == expected_design_contract_sha256,
            "视觉策划书设计合同摘要与权威项目合同不一致",
        )
    _validate_visual_variables(plan)
    _validate_pages(plan)
    _validate_charts_and_tables(plan)
    _validate_interactions(plan)
    _validate_acceptance_matrix(plan)
    return plan


def validate_visual_render_evidence(
    raw: Mapping[str, Any],
    *,
    expected_artifact_digest: str | None = None,
    expected_plan_digest: str | None = None,
) -> JsonObject:
    """验证当前候选的真实呈现证据及 HTML 响应式/交互完整性。"""

    if not isinstance(raw, Mapping):
        raise VisualFinalizationError("视觉呈现证据顶层必须是对象")
    evidence = dict(raw)
    _validate_schema(
        evidence,
        _load_schema(RENDER_EVIDENCE_SCHEMA_FILENAME, "视觉呈现证据"),
    )
    if expected_artifact_digest is not None:
        _require(
            evidence["candidate_artifact_digest"] == expected_artifact_digest,
            "视觉呈现证据未绑定当前候选产物",
        )
    if expected_plan_digest is not None:
        _require(
            evidence["visual_plan_digest"] == expected_plan_digest,
            "视觉呈现证据未绑定当前视觉策划书",
        )

    targets = cast(list[JsonObject], evidence["render_targets"])
    _nonempty_unique([target["target_id"] for target in targets], "真实呈现目标")
    for target in targets:
        metrics = cast(JsonObject, target["metrics"])
        _require(
            all(metrics[key] == 0 for key in metrics),
            f"呈现目标 {target['target_id']} 仍有横向溢出、裁切、标签碰撞或不可读内容",
        )
        alternatives = {
            item["field"]: item
            for item in cast(list[JsonObject], target["responsive_alternatives"])
        }
        for field in cast(list[str], target["unavailable_required_fields"]):
            alternative = alternatives.get(field)
            _require(
                alternative is not None and alternative["verified"] is True,
                f"呈现目标 {target['target_id']} 的字段“{field}”缺少已验证的用户可见替代入口",
            )
        text_scan = cast(JsonObject, target["visible_text_scan"])
        _require(
            text_scan["passed"] is True
            and not text_scan["engineering_tokens_found"]
            and not text_scan["untranslated_tokens_found"],
            f"呈现目标 {target['target_id']} 的用户可见文字仍含工程化或未中文化内容",
        )

    open_blocking = [
        defect
        for defect in cast(list[JsonObject], evidence["defects"])
        if defect["blocking"] is True and defect["status"] == "open"
    ]
    _require(not open_blocking, "视觉呈现证据仍有未关闭的阻断缺陷")

    if evidence["format"] == "html":
        required_widths = {768, 1024, 1440}
        required_engines = {"chromium", "webkit"}
        target_matrix = {
            (
                cast(str, target["engine"]),
                cast(int, cast(JsonObject, target["viewport"])["width"]),
            )
            for target in targets
        }
        required_matrix = {
            (engine, width) for engine in required_engines for width in required_widths
        }
        _require(
            required_matrix.issubset(target_matrix),
            "HTML真实呈现证据必须完整覆盖 Chromium/WebKit 与768、1024、1440的组合",
        )
        required_triggers = {
            "page_load", "filter_change", "drill_down", "search", "keyboard", "reduced_motion"
        }
        for target in targets:
            checks = {
                cast(str, check["trigger"]): check["passed"]
                for check in cast(list[JsonObject], target["interaction_checks"])
            }
            _require(
                all(checks.get(trigger) is True for trigger in required_triggers),
                f"HTML呈现目标 {target['target_id']} 未逐项通过六类关键交互检查",
            )
    return evidence


def validate_visual_verification_reference(
    raw: Mapping[str, Any],
    *,
    expected_artifact_digest: str | None = None,
    expected_render_digest: str | None = None,
    expected_plan_digest: str | None = None,
) -> JsonObject:
    """验证独立审阅者逐域、逐证据签署的当前候选结论。"""

    if not isinstance(raw, Mapping):
        raise VisualFinalizationError("独立视觉审阅结论顶层必须是对象")
    verdict = dict(raw)
    _validate_schema(
        verdict,
        _load_schema(VERIFICATION_SCHEMA_FILENAME, "独立视觉审阅结论"),
    )
    _require(verdict["producer_identity"] != verdict["verifier_identity"], "视觉审阅不得自签")
    bindings = (
        ("candidate_artifact_digest", expected_artifact_digest, "候选产物"),
        ("render_evidence_digest", expected_render_digest, "真实呈现证据"),
        ("visual_plan_digest", expected_plan_digest, "视觉策划书"),
    )
    for field, expected, label in bindings:
        if expected is not None:
            _require(verdict[field] == expected, f"独立视觉审阅结论未绑定当前{label}")
    domains = cast(list[JsonObject], verdict["domains"])
    _nonempty_unique([domain["domain"] for domain in domains], "独立视觉审阅域")
    _require(
        {domain["domain"] for domain in domains} == ACCEPTANCE_DOMAINS,
        "独立视觉审阅必须完整覆盖七个视觉域",
    )
    if verdict["verdict"] == "accepted":
        _require(
            all(domain["status"] == "accepted" for domain in domains),
            "总体接受与逐域结论不一致",
        )
    return verdict


# 便于调用方按任务语义引用；两者指向同一失败关闭验证器。
validate_visual_plan = validate_visual_finalization_plan

__all__ = [
    "PLAN_SCHEMA_FILENAME",
    "RENDER_EVIDENCE_SCHEMA_FILENAME",
    "ROUTE_BY_FORMAT",
    "VERIFICATION_SCHEMA_FILENAME",
    "VisualFinalizationError",
    "validate_visual_finalization_plan",
    "validate_visual_plan",
    "validate_visual_render_evidence",
    "validate_visual_verification_reference",
    "visual_contract_digest",
]
