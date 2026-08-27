"""Task 5.4：从已校验的 A 类报告数据包生成完整纯静态多页面门户。"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.qc.browser import site_directory_digest
from ci_workflow.reports.common.page_registry import PageRegistry
from ci_workflow.storage.manifest_store import (
    ArtifactFileBinding,
    ArtifactManifest,
    DesignContractBinding,
    DeterministicCheck,
    RendererBinding,
    RenderVerdict,
)
from ci_workflow.storage.snapshot_store import ReportSnapshotManifest, SnapshotStore

from .builder import resolve_echarts_bundle, resolve_logo_src, resolve_portal_asset


class ReportAPortalError(ValueError):
    """A 类门户输入、模板或清单不闭合。"""


class ProductRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    name: str
    target: str
    modality: str
    phase: str
    status: str
    regions: tuple[str, ...] = Field(min_length=1)
    route: str
    developer: str
    mechanism: str
    result_status: Literal["有公开关键结果", "暂无公开关键结果", "临床前"] = "有公开关键结果"

    @field_validator("id")
    @classmethod
    def _id_is_slug(cls, value: str) -> str:
        if not value or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in value):
            raise ValueError("产品标识必须是安全英文路径片段")
        return value


class TrialRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    display_id: str
    product_id: str
    name: str
    phase: str
    region: str
    status: str
    sample_size: int = Field(gt=0)
    treatment_sample_size: int | None = Field(default=None, gt=0)
    role: str

    @model_validator(mode="after")
    def _treatment_group_cannot_exceed_trial(self) -> TrialRow:
        if (
            self.treatment_sample_size is not None
            and self.treatment_sample_size > self.sample_size
        ):
            raise ValueError("治疗组样本量不得大于试验总样本量")
        return self


class EfficacyRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_id: str
    product_id: str
    trial_id: str
    endpoint: str
    timepoint: str
    arm: str
    value: float
    unit: str
    population: str


class SafetyRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_id: str
    product_id: str
    trial_id: str | None = None
    arm: str = "治疗组"
    category: str
    term: str
    value: float | None
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, gt=0)
    unit: str
    time_window: str
    disclosure_state: Literal["已公开", "未公开"] = "已公开"

    @model_validator(mode="after")
    def _value_matches_disclosure_state(self) -> SafetyRow:
        if self.disclosure_state == "已公开" and self.value is None:
            raise ValueError("已公开安全性记录必须包含数值")
        if self.disclosure_state == "未公开" and self.value is not None:
            raise ValueError("未公开安全性记录不得填入推测数值")
        if (self.numerator is None) != (self.denominator is None):
            raise ValueError("安全性分子与分母必须同时公开或同时缺失")
        if (
            self.numerator is not None
            and self.denominator is not None
            and self.numerator > self.denominator
        ):
            raise ValueError("安全性分子不得大于分母")
        return self


class RegulatoryRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str
    track: str
    event: str
    date: str
    status: str


class CompanyRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str
    relationship: str
    licensor: str
    licensee: str
    territory: str
    transaction: str


class PatentRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str
    family: str
    display_family: str
    jurisdiction: str
    scope: str
    expiry: str
    exclusivity: str


class HistoryRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    product_id: str
    status: str
    date: str
    observation: str


class SourceRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: str
    scope: str
    maturity: str
    limitation: str


class ReportALineageBinding(BaseModel):
    """新鲜来源路径传给渲染器的已锁定科学谱系。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    evidence_snapshot_id: str
    claim_snapshot_id: str
    coverage_set_id: str
    coverage_projection_id: str
    claim_ids: tuple[str, ...] = Field(min_length=1)
    source_version_ids: tuple[str, ...] = Field(min_length=1)


class ReportAPortalData(BaseModel):
    """模板只读输入；产品/试验/结果关系必须在入模时闭合。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: str
    report_version: str
    indication: str
    data_cutoff: datetime
    products: tuple[ProductRow, ...] = Field(min_length=1)
    trials: tuple[TrialRow, ...] = Field(min_length=1)
    efficacy: tuple[EfficacyRow, ...] = Field(min_length=1)
    safety: tuple[SafetyRow, ...] = Field(min_length=1)
    regulatory: tuple[RegulatoryRow, ...] = Field(min_length=1)
    companies: tuple[CompanyRow, ...] = Field(min_length=1)
    patents: tuple[PatentRow, ...] = Field(min_length=1)
    history: tuple[HistoryRow, ...] = Field(min_length=1)
    sources: tuple[SourceRow, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _relations_are_closed(self) -> Self:
        product_ids = [item.id for item in self.products]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("产品标识重复")
        trial_ids = [item.id for item in self.trials]
        if len(trial_ids) != len(set(trial_ids)):
            raise ValueError("试验标识重复")
        products = set(product_ids)
        trials = set(trial_ids)
        if any(item.product_id not in products for item in self.trials):
            raise ValueError("试验引用了未知产品")
        linked_product_rows: tuple[
            EfficacyRow | SafetyRow | RegulatoryRow | CompanyRow | PatentRow | HistoryRow,
            ...,
        ] = (
            *self.efficacy,
            *self.safety,
            *self.regulatory,
            *self.companies,
            *self.patents,
            *self.history,
        )
        if any(item.product_id not in products for item in linked_product_rows):
            raise ValueError("报告事实引用了未知产品")
        if any(item.trial_id not in trials for item in self.efficacy):
            raise ValueError("疗效事实引用了未知试验")
        if any(
            item.trial_id is not None and item.trial_id not in trials
            for item in self.safety
        ):
            raise ValueError("安全性事实引用了未知试验")
        required_safety = {"治疗期间不良事件", "严重不良事件", "特别关注不良事件", "常见不良事件"}
        product_by_id = {item.id: item for item in self.products}
        for product_id in products:
            if product_by_id[product_id].result_status != "有公开关键结果":
                continue
            categories = {row.category for row in self.safety if row.product_id == product_id}
            if not required_safety <= categories:
                raise ValueError(f"产品 {product_id} 的关键安全性维度不完整")
            arms = {row.arm for row in self.efficacy if row.product_id == product_id}
            if not {"治疗组", "对照组"} <= arms:
                raise ValueError(f"产品 {product_id} 的疗效比较缺少治疗组或对照组")
        return self

    @property
    def product_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.products)

    @property
    def trial_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.trials)


_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "a"
_ASSET_DIR = Path(__file__).resolve().parent / "assets"
_STATIC_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("overview", "index.html.j2"),
    ("landscape", "landscape.html.j2"),
    ("product-overview", "products.html.j2"),
    ("clinical-portfolio", "clinical_portfolio.html.j2"),
    ("efficacy", "efficacy.html.j2"),
    ("safety", "safety.html.j2"),
    ("matrix", "matrix.html.j2"),
    ("regulatory", "regulatory.html.j2"),
    ("companies-transactions", "companies_deals.html.j2"),
    ("patents-protection", "patents.html.j2"),
    ("historical-edge", "history_edge.html.j2"),
    ("evidence-limitations", "evidence_limitations.html.j2"),
)

_TRIAL_STATUS_ZH = {
    "COMPLETED": "已完成",
    "RECRUITING": "招募中",
    "ACTIVE_NOT_RECRUITING": "进行中（已停止招募）",
    "NOT_YET_RECRUITING": "尚未开始招募",
    "ENROLLING_BY_INVITATION": "仅限邀请入组",
    "SUSPENDED": "已暂停",
    "TERMINATED": "已提前终止",
    "WITHDRAWN": "启动前撤回",
    "UNKNOWN": "登记状态尚不明确",
}


def _contains_chinese(value: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in value)


def _display_trials(data: ReportAPortalData) -> tuple[dict[str, object], ...]:
    """把登记平台字段投影成面向医学用户的中文展示，不改写证据原文。"""
    product_names = {item.id: item.name for item in data.products}
    rows: list[dict[str, object]] = []
    for trial in data.trials:
        row = trial.model_dump(mode="json")
        row["original_name"] = trial.name
        if not _contains_chinese(trial.name):
            row["name"] = f"{product_names[trial.product_id]}{trial.phase}临床研究"
        row["status"] = _TRIAL_STATUS_ZH.get(trial.status, trial.status)
        rows.append(row)
    return tuple(rows)


def _display_regulatory(data: ReportAPortalData) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for item in data.regulatory:
        row = item.model_dump(mode="json")
        if item.track == "境外":
            parts = [
                part.strip()
                for part in item.status.split("；")
                if part.strip() and "中国" not in part
            ]
            row["status"] = "；".join(parts) or "境外状态未核实"
        rows.append(row)
    return tuple(rows)


def load_report_a_data(path: Path) -> ReportAPortalData:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportAPortalError(f"无法读取 A 类报告数据：{path}") from exc
    try:
        return ReportAPortalData.model_validate(payload)
    except ValueError as exc:
        raise ReportAPortalError(f"A 类报告数据不符合合同：{exc}") from exc


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _git_commit() -> str:
    try:
        value = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[4],
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "0" * 40
    return value if len(value) in (40, 64) else "0" * 40


def _copy_assets(site_root: Path) -> None:
    assets = site_root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolve_logo_src(), assets / "logo.svg")
    for name in ("portal.css", "portal.js", "report-a.js"):
        source = _ASSET_DIR / name if name == "report-a.js" else resolve_portal_asset(name)
        shutil.copy2(source, assets / name)
    shutil.copy2(resolve_echarts_bundle(), assets / "echarts.min.js")


def _navigation() -> tuple[dict[str, str], ...]:
    catalog = PageRegistry.load().catalog(ReportKind.A)
    return tuple(
        {"id": page.id, "title": page.title_zh, "group": page.navigation_group_zh}
        for page in catalog.pages
    )


def _view_context(data: ReportAPortalData, *, current: str, depth: int = 0) -> dict[str, Any]:
    product_names = {item.id: item.name for item in data.products}
    display_trials = _display_trials(data)
    trial_names = {str(item["id"]): str(item["name"]) for item in display_trials}
    trial_original_names = {
        str(item["id"]): str(item["original_name"]) for item in display_trials
    }
    return {
        "report": data,
        "products": data.products,
        "trials": display_trials,
        "efficacy": data.efficacy,
        "safety": data.safety,
        "regulatory": _display_regulatory(data),
        "companies": data.companies,
        "patents": data.patents,
        "history": data.history,
        "sources": data.sources,
        "product_names": product_names,
        "trial_names": trial_names,
        "trial_original_names": trial_original_names,
        "navigation": _navigation(),
        "current": current,
        "root_prefix": "../" * depth,
        "asset_prefix": "../" * depth + "assets",
        "data_prefix": "../" * depth + "data",
    }


def render_report_a_site(data: ReportAPortalData, site_root: Path) -> tuple[Path, ...]:
    """生成 12 个静态责任页及全部产品详情页。"""
    env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(("html", "xml")),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    site_root.mkdir(parents=True, exist_ok=True)
    _copy_assets(site_root)
    data_dir = site_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    display_payload = data.model_dump(mode="json")
    display_payload["trials"] = list(_display_trials(data))
    display_payload["regulatory"] = list(_display_regulatory(data))
    literal = json.dumps(display_payload, ensure_ascii=False, separators=(",", ":"))
    (data_dir / "report.js").write_text(f"window.REPORT_A={literal};\n", encoding="utf-8")

    generated: list[Path] = []
    for page_id, template_name in _STATIC_TEMPLATES:
        output = site_root / f"{page_id}.html"
        output.write_text(
            env.get_template(template_name).render(**_view_context(data, current=page_id)),
            encoding="utf-8",
        )
        generated.append(output)

    product_dir = site_root / "products"
    product_dir.mkdir(parents=True, exist_ok=True)
    product_template = env.get_template("product.html.j2")
    for product in data.products:
        output = product_dir / f"{product.id}.html"
        context = _view_context(data, current="product-overview", depth=1)
        context["product"] = product
        context["product_trials"] = tuple(
            row for row in context["trials"] if row["product_id"] == product.id
        )
        context["product_efficacy"] = tuple(
            row for row in data.efficacy if row.product_id == product.id
        )
        context["product_safety"] = tuple(
            row for row in data.safety if row.product_id == product.id
        )
        context["product_regulatory"] = tuple(
            row for row in context["regulatory"] if row["product_id"] == product.id
        )
        context["product_companies"] = tuple(
            row for row in data.companies if row.product_id == product.id
        )
        context["product_patents"] = tuple(
            row for row in data.patents if row.product_id == product.id
        )
        output.write_text(product_template.render(**context), encoding="utf-8")
        generated.append(output)

    routes = [
        {"route": f"/a/{page_id}", "path": f"{page_id}.html"}
        for page_id, _ in _STATIC_TEMPLATES
    ] + [
        {"route": f"/a/products/{product.id}", "path": f"products/{product.id}.html"}
        for product in data.products
    ]
    (data_dir / "sitemap.json").write_bytes(_canonical_json({"routes": routes}))
    search = [
        {"title": item["title"], "slug": item["id"], "keywords": [item["group"]]}
        for item in _navigation()
    ] + [
        {
            "title": product.name,
            "slug": f"products/{product.id}",
            "keywords": [product.target, product.modality],
        }
        for product in data.products
    ]
    (data_dir / "search-index.js").write_text(
        "window.__SEARCH_INDEX__="
        + json.dumps(search, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    return tuple(generated)


def build_report_a_artifact(
    *,
    project_root: Path,
    data_path: Path,
    project_id: str,
    contract_version: int,
    run_id: str,
    lineage: ReportALineageBinding | None = None,
) -> tuple[Path, Path]:
    """生成站点、锁定报告快照并写入 generated 清单。"""
    data = load_report_a_data(data_path)
    started_at = datetime.now(UTC)
    version_root = project_root / "reports" / "A" / data.report_version
    site_root = version_root / "html"
    if site_root.exists():
        raise ReportAPortalError("目标报告版本已存在，拒绝覆盖")
    render_report_a_site(data, site_root)

    result_rows: tuple[EfficacyRow | SafetyRow, ...] = (*data.efficacy, *data.safety)
    data_digest = hashlib.sha256(_canonical_json(data.model_dump(mode="json"))).hexdigest()
    if lineage is None:
        claim_ids = tuple(stable_id("claim", row.row_id) for row in result_rows)
        evidence_snapshot_id = stable_id("evidence-snapshot", project_id, data_digest)
        claim_snapshot_id = stable_id("claim-snapshot", project_id, data_digest)
        coverage_set_id = stable_id("coverage-set", project_id, "A", data_digest)
        coverage_projection_id = stable_id(
            "coverage-projection", project_id, "A", data.report_version
        )
        evidence_reference_ids = tuple(
            stable_id("source", row.source) for row in data.sources
        )
    else:
        claim_ids = lineage.claim_ids
        evidence_snapshot_id = lineage.evidence_snapshot_id
        claim_snapshot_id = lineage.claim_snapshot_id
        coverage_set_id = lineage.coverage_set_id
        coverage_projection_id = lineage.coverage_projection_id
        evidence_reference_ids = lineage.source_version_ids
    snapshot_payload = ReportSnapshotManifest(
        schema_version="1.0",
        project_id=project_id,
        contract_version=contract_version,
        report="A",
        report_version=data.report_version,
        data_cutoff=data.data_cutoff,
        evidence_snapshot_id=evidence_snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
        claim_ids=claim_ids,
        created_at=started_at,
    )
    locked = SnapshotStore(project_root).lock_report_snapshot(
        report="A", manifest=snapshot_payload.model_dump(mode="json")
    )
    site_digest, site_bytes = site_directory_digest(site_root)
    modified_at = datetime.fromtimestamp(
        max(path.stat().st_mtime for path in site_root.rglob("*") if path.is_file()), tz=UTC
    )
    package_digest = hashlib.sha256(
        (Path(__file__).resolve().parents[4] / "package-manifest.json").read_bytes()
    ).hexdigest()
    catalog = PageRegistry.load().catalog(ReportKind.A)
    manifest = ArtifactManifest(
        schema_version="1.0",
        manifest_id=stable_id("artifact-manifest", project_id, run_id, "A", data.report_version),
        project_id=project_id,
        contract_version=contract_version,
        report="A",
        report_version=data.report_version,
        data_cutoff=data.data_cutoff,
        producer_run_id=run_id,
        source_commit=_git_commit(),
        package_digest=package_digest,
        evidence_snapshot_id=evidence_snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        report_snapshot_id=locked.snapshot_id,
        coverage_set_id=coverage_set_id,
        coverage_projection_id=coverage_projection_id,
        structured_exceptions=(),
        pages_or_sections=tuple(page.id for page in catalog.pages),
        product_ids=data.product_ids,
        trial_ids=data.trial_ids,
        claim_ids=claim_ids,
        chart_ids=("landscape-summary", "efficacy-summary", "safety-summary", "matrix-summary"),
        table_ids=(
            "products",
            "trials",
            "efficacy",
            "safety",
            "regulatory",
            "companies",
            "patents",
            "history",
        ),
        evidence_reference_ids=evidence_reference_ids,
        design_contract=DesignContractBinding(
            roles=("report-portal",),
            digest=package_digest,
            applicable_sections=("项目设计合同", "站点式门户"),
        ),
        renderer=RendererBinding(name="report-a-portal", version="1.0"),
        filter_state={},
        generated_at=started_at,
        deterministic_checks=(
            DeterministicCheck(
                check_id="twelve-static-plus-products",
                status="passed",
                receipt=data_digest,
            ),
        ),
        render_verdict=RenderVerdict(
            verdict_id=stable_id("render-verdict", run_id, "awaiting-independent-review"),
            status="rejected",
            verified_at=modified_at,
            anchor_ids=("尚待独立浏览器验收",),
        ),
        accepted_by=None,
        artifact=ArtifactFileBinding(
            relative_path=f"reports/A/{data.report_version}/html",
            sha256=site_digest,
            byte_size=site_bytes,
            modified_at=modified_at,
            media_type="directory",
        ),
        status="generated",
        supersedes_manifest_id=None,
    )
    manifest_path = version_root / "html.manifest.json"
    manifest_path.write_bytes(_canonical_json(manifest.model_dump(mode="json")))
    return site_root, manifest_path
