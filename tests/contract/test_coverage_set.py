"""Task 4.1 规范覆盖集合与格式覆盖投影合同测试。

合同边界（诚实声明）：
- Draft 2020-12 Schema 只表达可表示结构（必填、枚举、最小长度、摘要格式、
  引用非空等）；跨数组的逐项身份唯一、集合闭合、覆盖/例外重叠、等价行集
  绑定、格式例外规则、页面责任目录权威与确定性摘要重算由生产验证器语义
  层强制执行，本文件对每一条都提供正例与负例。
- 页面责任权威：公开 ``validate_coverage_set_payload`` 始终加载冻结
  PageRegistry（源码树或包内数据布局），不接受调用方注入注册表；自定义
  注册表只允许经内部/测试专用路径 ``_validate_coverage_set_payload_with_registry``。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from jsonschema import Draft202012Validator

from ci_workflow.domain.enums import OutputFormat, ReportKind
from ci_workflow.reports.common.coverage import (
    CoverageBoundaryError,
    CoverageExceptionKind,
    CoverageItemKind,
    CoverageProjection,
    CoverageSet,
    compute_coverage_projection_content_digest,
    compute_coverage_set_content_digest,
    derive_coverage_exception_id,
    derive_coverage_item_id,
    derive_coverage_projection_id,
    derive_coverage_set_id,
    validate_coverage_projection_payload,
    validate_coverage_set_payload,
)
from ci_workflow.reports.common.page_registry import PageRegistry

ROOT = Path(__file__).resolve().parents[2]

# 共享行集摘要：与 ChartTableModule 计算口径一致的真实 SHA-256 形式值。
ROW_SET_DIGEST = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

PROJECT_ID = "project-atopic-dermatitis-01"
CONTRACT_VERSION = 1
REPORT = "A"
REPORT_VERSION = "1.0"
DATA_CUTOFF = "2026-08-13T00:00:00+08:00"
EVIDENCE_SNAPSHOT_ID = "evidence-snapshot-01"
CLAIM_SNAPSHOT_ID = "claim-snapshot-01"
CREATED_AT = "2026-08-13T01:00:00+08:00"


def item(
    kind: CoverageItemKind | str,
    page: str,
    refs: tuple[str, ...],
    label: str,
    *,
    report: str = REPORT,
) -> dict[str, Any]:
    kind_value = kind.value if isinstance(kind, CoverageItemKind) else kind
    return {
        "item_id": derive_coverage_item_id(
            ReportKind(report), CoverageItemKind(kind_value), page, refs
        ),
        "kind": kind_value,
        "page_responsibility_id": page,
        "referenced_ids": list(refs),
        "label_zh": label,
    }


def set_items() -> list[dict[str, Any]]:
    """A 报告 9 项覆盖：章节/页面/产品/试验/声明/图表/表格/证据/附录。"""
    return [
        item("chapter", "overview", ("overview",), "总览章节"),
        item("page", "overview", ("product-01", "product-02"), "首页全景"),
        item("product", "product-overview", ("product-01",), "产品一档案"),
        item("trial", "clinical-portfolio", ("trial-01",), "试验一核心试验"),
        item("claim", "efficacy", ("claim-01",), "疗效声明"),
        item(
            "chart",
            "efficacy",
            (ROW_SET_DIGEST, "claim-01"),
            "疗效分组柱状图",
        ),
        item(
            "table",
            "efficacy",
            (ROW_SET_DIGEST, "fact-01"),
            "疗效完整数值表",
        ),
        item("evidence", "evidence-limitations", ("fragment-01",), "证据引用"),
        item("appendix", "evidence-limitations", ("appendix-a",), "附录甲"),
    ]


def set_payload(
    items: list[dict[str, Any]] | None = None,
    *,
    report: str = REPORT,
    **overrides: Any,
) -> dict[str, Any]:
    selected = items if items is not None else set_items()
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "coverage_set_id": derive_coverage_set_id(
            PROJECT_ID,
            CONTRACT_VERSION,
            ReportKind(report),
            REPORT_VERSION,
            DATA_CUTOFF,
            EVIDENCE_SNAPSHOT_ID,
            CLAIM_SNAPSHOT_ID,
            tuple(str(i["item_id"]) for i in selected),
        ),
        "project_id": PROJECT_ID,
        "contract_version": CONTRACT_VERSION,
        "report": report,
        "report_version": REPORT_VERSION,
        "data_cutoff": DATA_CUTOFF,
        "evidence_snapshot_id": EVIDENCE_SNAPSHOT_ID,
        "claim_snapshot_id": CLAIM_SNAPSHOT_ID,
        "items": items if items is not None else set_items(),
        "created_at": CREATED_AT,
    }
    payload["content_digest"] = compute_coverage_set_content_digest(payload)
    payload.update(overrides)
    return payload


def exception_payload(
    *,
    omitted_item_id: str,
    exception_kind: str = "chart_equivalence",
    replacement_expression: str = "由疗效分组柱状图完整呈现同一行集数值",
    rationale_zh: str = "图已完整表达同一数值集合，省略冗余表",
    row_set_digest: str = ROW_SET_DIGEST,
    equivalent_item_id: str | None = None,
    version: int = 1,
) -> dict[str, Any]:
    if equivalent_item_id is None:
        equivalent_item_id = cast(str, set_items()[5]["item_id"])  # 图表项
    return {
        "exception_id": derive_coverage_exception_id(
            version, omitted_item_id, CoverageExceptionKind(exception_kind),
            replacement_expression, row_set_digest,
        ),
        "version": version,
        "omitted_item_id": omitted_item_id,
        "exception_kind": exception_kind,
        "replacement_expression": replacement_expression,
        "rationale_zh": rationale_zh,
        "equivalence_evidence": {
            "equivalent_item_id": equivalent_item_id,
            "row_set_digest": row_set_digest,
            "basis_zh": "图表与完整表共享同一行集摘要，数值完全一致",
        },
    }


def projection_payload(
    *,
    format_id: str,
    covered: list[str],
    exceptions: list[dict[str, Any]] | None = None,
    set_payload_: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    base = set_payload_ if set_payload_ is not None else set_payload()
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "coverage_projection_id": derive_coverage_projection_id(
            str(base["coverage_set_id"]),
            OutputFormat(format_id),
            tuple(covered),
            tuple(exceptions or ()),
        ),
        "coverage_set_id": base["coverage_set_id"],
        "coverage_set_digest": base["content_digest"],
        "report": REPORT,
        "report_version": REPORT_VERSION,
        "evidence_snapshot_id": EVIDENCE_SNAPSHOT_ID,
        "claim_snapshot_id": CLAIM_SNAPSHOT_ID,
        "format": format_id,
        "covered_item_ids": covered,
        "exceptions": exceptions or [],
        "created_at": "2026-08-13T02:00:00+08:00",
    }
    payload["content_digest"] = compute_coverage_projection_content_digest(payload)
    payload.update(overrides)
    return payload


@pytest.fixture(scope="module")
def coverage_set() -> CoverageSet:
    return validate_coverage_set_payload(set_payload())


# ─── CoverageSet：正例与绑定 ────────────────────────────────────────────────


def test_coverage_set_binds_project_contract_report_version_cutoff_and_snapshots() -> None:
    coverage = validate_coverage_set_payload(set_payload())
    assert coverage.project_id == PROJECT_ID
    assert coverage.contract_version == CONTRACT_VERSION
    assert coverage.report is ReportKind.A
    assert coverage.report_version == REPORT_VERSION
    assert coverage.data_cutoff.isoformat() == DATA_CUTOFF
    assert coverage.evidence_snapshot_id == EVIDENCE_SNAPSHOT_ID
    assert coverage.claim_snapshot_id == CLAIM_SNAPSHOT_ID
    assert len(coverage.items) == 9
    assert coverage.coverage_set_id == set_payload()["coverage_set_id"]


def test_coverage_set_identity_and_digest_are_deterministic() -> None:
    first = validate_coverage_set_payload(set_payload())
    second = validate_coverage_set_payload(set_payload())
    assert first.coverage_set_id == second.coverage_set_id
    assert first.content_digest == second.content_digest
    # 项目内换序不改变规范身份与摘要（集合身份与摘要按 item_id 规范化）。
    reordered = set_payload(items=list(reversed(set_items())))
    again = validate_coverage_set_payload(reordered)
    assert again.coverage_set_id == first.coverage_set_id
    assert again.content_digest == first.content_digest


def test_coverage_set_rejects_duplicate_semantic_items() -> None:
    """负例：Draft 2020-12 无法表达逐项身份唯一（仅深度相等），语义层拒绝。"""
    items = set_items()
    dup = dict(items[5])
    dup["label_zh"] = "同一科学身份的重复图表项"
    payload = set_payload(items=[*items, dup])
    with pytest.raises(CoverageBoundaryError, match="重复"):
        validate_coverage_set_payload(payload)


def test_coverage_set_rejects_empty_referenced_ids() -> None:
    payload = set_payload(items=[item("page", "overview", (), "空引用页面项")])
    with pytest.raises(CoverageBoundaryError, match="打包 Schema"):
        validate_coverage_set_payload(payload)


def test_coverage_set_rejects_unknown_responsibility() -> None:
    """负例：不传注册表参数，页面责任也必须属于同一报告类型的冻结目录。"""
    payload = set_payload(items=[item("page", "b-overview", ("product-01",), "混入 B 首页")])
    with pytest.raises(CoverageBoundaryError, match="责任"):
        validate_coverage_set_payload(payload)


def test_coverage_set_rejects_mixed_report_identity() -> None:
    """负例：按 B 报告推导的条目身份放入 A 集合，身份重算不一致即拒绝。"""
    foreign = {
        "item_id": derive_coverage_item_id(
            ReportKind.B, CoverageItemKind.PAGE, "overview", ("product-01",)
        ),
        "kind": "page",
        "page_responsibility_id": "overview",
        "referenced_ids": ["product-01"],
        "label_zh": "B 报告首页项",
    }
    payload = set_payload(items=[foreign])
    with pytest.raises(CoverageBoundaryError, match="身份"):
        validate_coverage_set_payload(payload)


def test_coverage_set_rejects_free_form_item_or_set_identity() -> None:
    """负例：条目 ID 与集合 ID 必须是确定性推导身份，自由文本替换失败关闭。"""
    free_form = dict(item("page", "overview", ("product-01",), "首页"))
    free_form["item_id"] = "自由文本ID"
    payload = set_payload(items=[free_form])
    with pytest.raises(CoverageBoundaryError, match="身份"):
        validate_coverage_set_payload(payload)
    payload = set_payload(coverage_set_id="自由文本集合ID")
    with pytest.raises(CoverageBoundaryError, match="身份"):
        validate_coverage_set_payload(payload)


def test_coverage_set_rejects_content_digest_mismatch() -> None:
    payload = set_payload(content_digest="0" * 64)
    with pytest.raises(CoverageBoundaryError, match="摘要"):
        validate_coverage_set_payload(payload)


def test_coverage_set_validation_runs_schema_before_model_and_semantics() -> None:
    """Schema 先于模型/语义执行：布尔值不能冒充整数最小版本（Schema 拒绝，
    而 Pydantic 单独可把 True 强转为 1）。"""
    payload = set_payload(contract_version=True)
    with pytest.raises(CoverageBoundaryError, match="打包 Schema"):
        validate_coverage_set_payload(payload)


def test_coverage_set_schema_is_valid_draft_2020_12() -> None:
    schema = cast(
        dict[str, Any],
        __import__("json").loads(
            (ROOT / "schemas/coverage-set.schema.json").read_text(encoding="utf-8")
        ),
    )
    Draft202012Validator.check_schema(schema)


def test_packaged_schema_copy_matches_directory_contract() -> None:
    for name in ("coverage-set", "coverage-projection"):
        directory = (ROOT / "schemas" / f"{name}.schema.json").read_bytes()
        packaged = (
            ROOT / "src" / "ci_workflow" / "schemas" / f"{name}.schema.json"
        ).read_bytes()
        assert packaged == directory, f"{name} 打包副本与目录合同不一致"


def test_coverage_set_requires_frozen_page_responsibility_without_registry() -> None:
    """负例：不传注册表参数时，页面责任也必须属于同一报告类型的冻结目录。

    这是对"省略 registry 即跳过目录校验"false-green 的直接攻击。
    """
    for page_id in (
        "b-overview",
        "baseline-demographics",
        "participant-flow",
        "design-map",
        "trial-profile",
        "自由文本页面",
    ):
        payload = set_payload(
            items=[item("page", page_id, ("product-01",), "目录外页面项")]
        )
        with pytest.raises(CoverageBoundaryError, match="责任"):
            validate_coverage_set_payload(payload)


def test_coverage_set_rejects_cross_report_page_labels() -> None:
    """负例：A 集合混入 B/C 专属页面、B 集合混入 A 专属页面均失败关闭。"""
    for page_id in ("baseline-demographics", "participant-flow", "design-map"):
        payload = set_payload(
            items=[item("page", page_id, ("product-01",), "跨报告页面项")]
        )
        with pytest.raises(CoverageBoundaryError, match="责任"):
            validate_coverage_set_payload(payload)
    b_items = [
        item("page", "patents-protection", ("product-01",), "A 专属页面混入 B", report="B")
    ]
    b_payload = set_payload(items=b_items, report="B")
    with pytest.raises(CoverageBoundaryError, match="责任"):
        validate_coverage_set_payload(b_payload)


def _minimal_catalog(report: str, page_ids: tuple[str, ...]) -> str:
    pages = [
        {
            "id": page_id,
            "route": f"/{report.casefold()}/{page_id}",
            "title": "中文页面标题",
            "navigation_group": "总览",
            "responsibility": "呈现核心内容",
            "visuals": ["结构分布图"],
            "complete_table": True,
            "filter_profiles": ["a-overview"],
            "evidence_drawer_profile": "common-clinical",
        }
        for page_id in page_ids
    ]
    return yaml.safe_dump(
        {"contract_version": "1.0", "report": report, "pages": pages},
        allow_unicode=True,
        sort_keys=False,
    )


def test_internal_registry_path_accepts_custom_catalog(tmp_path: Path) -> None:
    """自定义注册表只能经内部/测试专用验证器路径注入；公开边界始终用冻结目录。"""
    from ci_workflow.reports.common.coverage import (
        _validate_coverage_set_payload_with_registry,
    )

    target = tmp_path / "docs" / "architecture" / "page-catalogs"
    target.mkdir(parents=True, exist_ok=True)
    (target / "A.yaml").write_text(
        _minimal_catalog("A", ("overview", "product-overview", "clinical-portfolio")),
        encoding="utf-8",
    )
    (target / "B.yaml").write_text(
        _minimal_catalog("B", ("overview", "b-overview", "product-trial-profiles")),
        encoding="utf-8",
    )
    (target / "C.yaml").write_text(
        _minimal_catalog("C", ("overview", "trial-profile")),
        encoding="utf-8",
    )
    custom = PageRegistry._load_from_dir(target)
    b_items = [
        item("page", "b-overview", ("product-01",), "自定义目录首页", report="B")
    ]
    b_payload = set_payload(items=b_items, report="B")
    validated = _validate_coverage_set_payload_with_registry(b_payload, custom)
    assert validated.report is ReportKind.B
    # 同一载荷在公开生产边界被拒绝（冻结 B 目录没有 b-overview）。
    with pytest.raises(CoverageBoundaryError, match="责任"):
        validate_coverage_set_payload(b_payload)


def test_packaged_page_catalog_copies_match_frozen_originals() -> None:
    """随轮分发的包内页面目录必须与仓库根冻结目录逐字一致，避免安装后口径漂移。"""
    for letter in ("A", "B", "C"):
        directory = (
            ROOT / "docs" / "architecture" / "page-catalogs" / f"{letter}.yaml"
        ).read_bytes()
        packaged = (
            ROOT
            / "src" / "ci_workflow" / "reports" / "common" / "page-catalogs"
            / f"{letter}.yaml"
        ).read_bytes()
        assert packaged == directory, f"{letter}.yaml 打包副本与冻结目录不一致"


def test_page_registry_loads_packaged_catalog_layout() -> None:
    """包内数据布局（安装布局的唯一来源）可直接加载 A/B/C 并展开站点地图。"""
    packaged_dir = (
        ROOT / "src" / "ci_workflow" / "reports" / "common" / "page-catalogs"
    )
    registry = PageRegistry._load_from_dir(packaged_dir)
    assert [c.report.value for c in registry.catalogs] == ["A", "B", "C"]
    sitemap = registry.sitemap(
        ReportKind.A, product_ids=("product-01",), trial_ids=("trial-01",)
    )
    assert "/a/products/product-01" in sitemap


# ─── CoverageProjection：正例与绑定 ─────────────────────────────────────────


def test_coverage_projection_binds_one_set_snapshot_and_format(
    coverage_set: CoverageSet,
) -> None:
    items = set_items()
    covered = [str(i["item_id"]) for i in items if i["kind"] != "table"]
    exceptions = [exception_payload(omitted_item_id=str(items[6]["item_id"]))]
    projection = validate_coverage_projection_payload(
        projection_payload(format_id="pptx", covered=covered, exceptions=exceptions),
        coverage_set,
    )
    assert projection.coverage_set_id == coverage_set.coverage_set_id
    assert projection.coverage_set_digest == coverage_set.content_digest
    assert projection.format is OutputFormat.PPTX
    assert projection.evidence_snapshot_id == coverage_set.evidence_snapshot_id
    assert projection.claim_snapshot_id == coverage_set.claim_snapshot_id
    assert set(projection.covered_item_ids) | {
        e.omitted_item_id for e in projection.exceptions
    } == {i.item_id for i in coverage_set.items}


def test_coverage_projection_identity_and_digest_are_deterministic(
    coverage_set: CoverageSet,
) -> None:
    items = set_items()
    covered = [str(i["item_id"]) for i in items if i["kind"] != "table"]
    exceptions = [exception_payload(omitted_item_id=str(items[6]["item_id"]))]
    base = projection_payload(format_id="pptx", covered=covered, exceptions=exceptions)
    first = validate_coverage_projection_payload(base, coverage_set)
    shuffled = projection_payload(
        format_id="pptx", covered=list(reversed(covered)), exceptions=exceptions
    )
    second = validate_coverage_projection_payload(shuffled, coverage_set)
    assert first.coverage_projection_id == second.coverage_projection_id
    assert first.content_digest == second.content_digest


def test_coverage_projection_rejects_new_or_unknown_items(
    coverage_set: CoverageSet,
) -> None:
    items = set_items()
    covered = [str(i["item_id"]) for i in items if i["kind"] != "table"]
    payload = projection_payload(
        format_id="html", covered=[*covered, "coverage-item_不存在"], exceptions=[]
    )
    with pytest.raises(CoverageBoundaryError, match="集合外"):
        validate_coverage_projection_payload(payload, coverage_set)
    payload = projection_payload(
        format_id="pptx",
        covered=covered,
        exceptions=[exception_payload(omitted_item_id="coverage-item_不存在")],
    )
    with pytest.raises(CoverageBoundaryError, match="集合外"):
        validate_coverage_projection_payload(payload, coverage_set)


def test_coverage_projection_rejects_duplicate_coverage_and_exception(
    coverage_set: CoverageSet,
) -> None:
    items = set_items()
    covered = [str(i["item_id"]) for i in items if i["kind"] != "table"]
    payload = projection_payload(
        format_id="html", covered=[*covered, covered[0]], exceptions=[]
    )
    # 覆盖项重复同时被 Schema uniqueItems 与语义层拒绝，此处只断言失败关闭。
    with pytest.raises(CoverageBoundaryError):
        validate_coverage_projection_payload(payload, coverage_set)
    # Schema 无法表达"同一省略项的不同例外对象"；语义层拒绝重复例外。
    table_id = str(items[6]["item_id"])
    dup = exception_payload(omitted_item_id=table_id)
    dup2 = dict(exception_payload(omitted_item_id=table_id))
    dup2["rationale_zh"] = "另一条同样省略该表的重复例外"
    dup2["exception_id"] = derive_coverage_exception_id(
        2, table_id, CoverageExceptionKind.CHART_EQUIVALENCE,
        dup2["replacement_expression"], ROW_SET_DIGEST,
    )
    payload = projection_payload(
        format_id="pptx", covered=covered, exceptions=[dup, dup2]
    )
    with pytest.raises(CoverageBoundaryError, match="重复"):
        validate_coverage_projection_payload(payload, coverage_set)


def test_coverage_projection_rejects_covered_excepted_overlap(
    coverage_set: CoverageSet,
) -> None:
    items = set_items()
    table_id = str(items[6]["item_id"])
    payload = projection_payload(
        format_id="pptx",
        covered=[str(i["item_id"]) for i in items],
        exceptions=[exception_payload(omitted_item_id=table_id)],
    )
    with pytest.raises(CoverageBoundaryError, match="重叠"):
        validate_coverage_projection_payload(payload, coverage_set)


def test_coverage_projection_rejects_unexplained_difference(
    coverage_set: CoverageSet,
) -> None:
    """负例：规范集合项必须被覆盖或被例外解释，未解释差异失败关闭。"""
    items = set_items()
    # 完全覆盖集合，无任何例外 → 合法；改为遗漏一项且无例外 → 未解释差异。
    covered_all = [str(i["item_id"]) for i in items]
    payload = projection_payload(format_id="html", covered=covered_all, exceptions=[])
    assert validate_coverage_projection_payload(payload, coverage_set) is not None
    missing_one = covered_all[:-1]
    payload = projection_payload(format_id="html", covered=missing_one, exceptions=[])
    with pytest.raises(CoverageBoundaryError, match="未解释"):
        validate_coverage_projection_payload(payload, coverage_set)


def test_coverage_projection_rejects_exception_without_replacement_or_evidence(
    coverage_set: CoverageSet,
) -> None:
    items = set_items()
    covered = [str(i["item_id"]) for i in items if i["kind"] != "table"]
    table_id = str(items[6]["item_id"])
    exception = exception_payload(omitted_item_id=table_id)
    exception.pop("replacement_expression")
    payload = projection_payload(format_id="pptx", covered=covered, exceptions=[exception])
    with pytest.raises(CoverageBoundaryError, match="打包 Schema"):
        validate_coverage_projection_payload(payload, coverage_set)
    exception = exception_payload(omitted_item_id=table_id)
    exception.pop("equivalence_evidence")
    payload = projection_payload(format_id="pptx", covered=covered, exceptions=[exception])
    with pytest.raises(CoverageBoundaryError, match="打包 Schema"):
        validate_coverage_projection_payload(payload, coverage_set)


def test_coverage_projection_rejects_tampered_exception_id(
    coverage_set: CoverageSet,
) -> None:
    """负例：例外身份必须是确定性推导值；任意重算或自由文本替换都失败关闭。

    投影身份绑定已校验的例外身份：例外身份由版本/省略项/类型/替代表达/
    行集摘要推导，篡改身份即违反绑定。
    """
    items = set_items()
    covered = [str(i["item_id"]) for i in items if i["kind"] != "table"]
    table_id = str(items[6]["item_id"])
    base = exception_payload(omitted_item_id=table_id)
    recomputed = derive_coverage_exception_id(
        2, table_id, CoverageExceptionKind.CHART_EQUIVALENCE,
        base["replacement_expression"], ROW_SET_DIGEST,
    )
    for tampered in (recomputed, "自由文本例外ID"):
        exception = dict(base)
        exception["exception_id"] = tampered
        payload = projection_payload(
            format_id="pptx", covered=covered, exceptions=[exception]
        )
        with pytest.raises(CoverageBoundaryError, match="例外身份"):
            validate_coverage_projection_payload(payload, coverage_set)


def test_html_and_pdf_cannot_omit_required_complete_tables(
    coverage_set: CoverageSet,
) -> None:
    """负例：HTML/PDF 冻结合同禁止省略完整表；任何例外都失败关闭。"""
    items = set_items()
    covered = [str(i["item_id"]) for i in items if i["kind"] != "table"]
    exceptions = [exception_payload(omitted_item_id=str(items[6]["item_id"]))]
    for format_id in ("html", "pdf"):
        payload = projection_payload(
            format_id=format_id, covered=covered, exceptions=exceptions
        )
        with pytest.raises(CoverageBoundaryError, match="完整表"):
            validate_coverage_projection_payload(payload, coverage_set)


def test_presentations_allow_only_approved_chart_equivalence(
    coverage_set: CoverageSet,
) -> None:
    items = set_items()
    covered = [str(i["item_id"]) for i in items if i["kind"] != "table"]
    table_id = str(items[6]["item_id"])
    chart_id = str(items[5]["item_id"])
    # 只允许 chart_equivalence：未知例外类型在 Schema 层拒绝。
    other_kind = exception_payload(omitted_item_id=table_id)
    other_kind["exception_kind"] = "other"
    payload = projection_payload(
        format_id="pptx", covered=covered, exceptions=[other_kind]
    )
    with pytest.raises(CoverageBoundaryError, match="打包 Schema"):
        validate_coverage_projection_payload(payload, coverage_set)
    # 例外只能省略完整表项；省略图表项拒绝。
    payload = projection_payload(
        format_id="pptx",
        covered=[i for i in covered if i != chart_id],
        exceptions=[exception_payload(omitted_item_id=chart_id)],
    )
    with pytest.raises(CoverageBoundaryError, match="表格"):
        validate_coverage_projection_payload(payload, coverage_set)
    # 等价证据的图表必须仍在覆盖集合内。
    payload = projection_payload(
        format_id="pptx",
        covered=[i for i in covered if i != chart_id],
        exceptions=[
            exception_payload(
                omitted_item_id=table_id, equivalent_item_id="coverage-item_其他图表"
            )
        ],
    )
    with pytest.raises(CoverageBoundaryError, match="等价"):
        validate_coverage_projection_payload(payload, coverage_set)
    # 等价行集摘要必须同时出现在被省略表格项与等价图表项引用中。
    payload = projection_payload(
        format_id="pptx",
        covered=covered,
        exceptions=[
            exception_payload(
                omitted_item_id=table_id,
                row_set_digest="0" * 64,
            )
        ],
    )
    with pytest.raises(CoverageBoundaryError, match="行集"):
        validate_coverage_projection_payload(payload, coverage_set)


def test_coverage_projection_rejects_mixed_snapshot_binding(
    coverage_set: CoverageSet,
) -> None:
    items = set_items()
    covered = [str(i["item_id"]) for i in items]
    payload = projection_payload(
        format_id="html",
        covered=covered,
        exceptions=[],
        evidence_snapshot_id="evidence-snapshot-其他快照",
    )
    with pytest.raises(CoverageBoundaryError, match="快照"):
        validate_coverage_projection_payload(payload, coverage_set)


def test_projection_equivalence_is_anchored_in_chart_table_row_set(
    coverage_set: CoverageSet,
) -> None:
    """等价证据锚定同一行集：与 ChartTableModule 的行集摘要构成完整链。"""
    from ci_workflow.reports.common.chart_specs import (
        ChartTableModule,
        validate_chart_table_module_payload,
        validate_filtered_row_set_payload,
    )
    from ci_workflow.reports.common.view_state import (
        derive_row_id,
        validate_report_view_model_payload,
    )

    rows = (
        {
            "row_id": derive_row_id(
                product_id="product-01", trial_id="trial-01",
                group_id="group-01", endpoint_id="endpoint-01",
                timepoint_id="timepoint-01",
            ),
            "display_label_zh": "第3组治疗组主要终点",
            "page_responsibility_id": "efficacy",
            "report_snapshot_id": "report-snapshot-01",
            "disclosure_state": "reported_value",
            "product_id": "product-01", "trial_id": "trial-01",
            "group_id": "group-01", "endpoint_id": "endpoint-01",
            "timepoint_id": "timepoint-01",
        },
        {
            "row_id": derive_row_id(
                product_id="product-01", trial_id="trial-01",
                group_id="group-01", event_id="event-01",
            ),
            "display_label_zh": "第3组严重不良事件",
            "page_responsibility_id": "efficacy",
            "report_snapshot_id": "report-snapshot-01",
            "disclosure_state": "not_reported",
            "product_id": "product-01", "trial_id": "trial-01",
            "group_id": "group-01", "event_id": "event-01",
        },
    )
    view = validate_report_view_model_payload(
        {
            "report_kind": "A",
            "page_responsibility_id": "efficacy",
            "report_snapshot_id": "report-snapshot-01",
            "report_version": "1.0",
            "rows": list(rows),
        }
    )
    row_set = validate_filtered_row_set_payload(
        {"view": view.model_dump(mode="json"), "rows": list(rows)}
    )
    module = validate_chart_table_module_payload(
        {"row_set": row_set.model_dump(mode="json")}
    )
    assert isinstance(module, ChartTableModule)
    assert module.chart_row_ids == module.table_row_ids

    items = set_items()
    chart_item = dict(items[5])
    table_item = dict(items[6])
    chart_item["referenced_ids"] = [row_set.row_set_digest, "claim-01"]
    table_item["referenced_ids"] = [row_set.row_set_digest, "fact-01"]
    chart_item["item_id"] = derive_coverage_item_id(
        ReportKind.A,
        CoverageItemKind.CHART,
        chart_item["page_responsibility_id"],
        chart_item["referenced_ids"],
    )
    table_item["item_id"] = derive_coverage_item_id(
        ReportKind.A,
        CoverageItemKind.TABLE,
        table_item["page_responsibility_id"],
        table_item["referenced_ids"],
    )
    payload = set_payload(items=[chart_item, table_item])
    set_ = validate_coverage_set_payload(payload)
    covered = [chart_item["item_id"]]
    exceptions = [
        exception_payload(
            omitted_item_id=table_item["item_id"],
            row_set_digest=row_set.row_set_digest,
            equivalent_item_id=chart_item["item_id"],
        )
    ]
    projection = validate_coverage_projection_payload(
        projection_payload(
            format_id="pptx", covered=covered, exceptions=exceptions,
            set_payload_=payload,
        ),
        set_,
    )
    assert isinstance(projection, CoverageProjection)
