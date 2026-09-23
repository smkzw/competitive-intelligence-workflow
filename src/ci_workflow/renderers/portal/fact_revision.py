"""Quarantined pre-rereview overlay implementation; not part of any runtime path.

Kept only to preserve the dirty-tree forensic record.  W04 production code imports
``active_fact_projection`` and invokes the A/B/C builders directly.  This module is
intentionally absent from ``__all__`` and must not be imported by application code.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

ReportCode = Literal["A", "B", "C"]
ArtifactKind = Literal["chart", "table", "narrative", "index", "source_pointer"]

_REPORT_GLOBAL = {"A": "REPORT_A", "B": "REPORT_B", "C": "REPORT_C"}
_PAGE_RULES: dict[ReportCode, tuple[tuple[str, str], ...]] = {
    "A": (
        ("safety", "safety"),
        ("eligibility", "clinical-portfolio"),
        ("efficacy", "efficacy"),
        ("baseline", "overview"),
    ),
    "B": (
        ("safety", "safety"),
        ("eligibility", "baseline-disease-context"),
        ("efficacy", "efficacy"),
        ("baseline", "baseline-overview"),
    ),
    "C": (
        ("safety", "sample-analysis-statistics"),
        ("eligibility", "inclusion-criteria"),
        ("efficacy", "endpoint-timepoint-matrix"),
        ("baseline", "sample-analysis-statistics"),
    ),
}
_ARTIFACTS: tuple[ArtifactKind, ...] = (
    "chart",
    "table",
    "narrative",
    "index",
    "source_pointer",
)
_REVISION_SECTION = re.compile(
    r'<section class="user-fact-revision"[^>]*></section>', re.DOTALL
)
_REVISION_STYLESHEET = '<link rel="stylesheet" href="assets/user-fact-revision.css">'
_REVISION_PAYLOAD_SCRIPT = '<script src="data/report.js"></script>'
_REVISION_SCRIPT = '<script src="assets/user-fact-revision.js"></script>'


class PortalFactConsumer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportCode
    page_slug: str
    fact_id: str
    fact_version_id: str
    artifacts: tuple[ArtifactKind, ...] = _ARTIFACTS


class PortalFactRevisionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportCode
    revision: int
    request_id: str
    fact_revision_digest: str
    payload_relative_path: str
    payload_sha256: str
    search_index_relative_path: str
    search_index_sha256: str
    javascript_relative_path: str
    javascript_sha256: str
    html_sha256: dict[str, str]
    consumers: tuple[PortalFactConsumer, ...]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_assignment(path: Path, global_name: str) -> Any:
    text = path.read_text(encoding="utf-8").strip()
    prefix = f"window.{global_name}="
    if not text.startswith(prefix) or not text.endswith(";"):
        raise ValueError(f"门户载荷不是受支持的{global_name}赋值")
    return json.loads(text[len(prefix) : -1])


def _write_assignment(path: Path, global_name: str, payload: Any) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text(f"window.{global_name}={encoded};\n", encoding="utf-8")


def _page_for_fact(report: ReportCode, fact: dict[str, Any]) -> str:
    field_id = str(fact.get("field_id", ""))
    for prefix, page in _PAGE_RULES[report]:
        if field_id.startswith(f"{prefix}."):
            return page
    statistical_form = str(fact.get("statistical_form", ""))
    if statistical_form in {"crude_rate", "adjusted_rate"}:
        return _PAGE_RULES[report][0][1]
    if statistical_form == "threshold":
        return _PAGE_RULES[report][1][1]
    if statistical_form == "ls_mean":
        return _PAGE_RULES[report][2][1]
    return _PAGE_RULES[report][3][1]


def _javascript() -> str:
    return """(() => {
  'use strict';
  const report = window.REPORT_A || window.REPORT_B || window.REPORT_C;
  if (!report || !report.user_fact_revision) return;
  const revision = report.user_fact_revision;
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
  document.querySelectorAll('[data-user-fact-consumer]').forEach((root) => {
    const ids = JSON.parse(root.dataset.factIds || '[]');
    const facts = ids.map((id) => revision.facts[id]).filter(Boolean);
    root.dataset.renderedRevision = String(revision.revision);
    const rows = facts.map((fact) =>
      `<tr data-fact-id="${esc(fact.fact_id)}">` +
      `<th>${esc(fact.field_id)}</th>` +
      `<td>${esc(fact.raw_value ?? fact.normalized_value ?? '')}</td>` +
      `<td>${esc(fact.fact_version_id)}</td></tr>`
    ).join('');
    const bars = facts.map((fact) => {
      const value = Math.min(100, Math.max(0, Number(fact.normalized_value) || 0));
      return `<div class="user-fact-bar" data-fact-id="${esc(fact.fact_id)}" ` +
        `style="--value:${value}%"><span>` +
        `${esc(fact.raw_value ?? fact.normalized_value ?? '')}</span></div>`;
    }).join('');
    const narrative = facts.map((fact) =>
      `<li data-fact-id="${esc(fact.fact_id)}">` +
      `${esc(fact.endpoint_definition || fact.field_id)}：` +
      `${esc(fact.raw_value ?? fact.normalized_value ?? '')}</li>`
    ).join('');
    const sources = facts.map((fact) =>
      `<li data-source-pointer="${esc(fact.primary_fragment_id)}">` +
      `<code>${esc(fact.primary_fragment_id)}</code> · ` +
      `${esc(fact.fact_version_id)}</li>`
    ).join('');
    root.innerHTML = [
      `<header><p class="eyebrow">用户事实修订 · revision ${revision.revision}</p>`,
      '<h2>当前事实同步</h2><p>未继承独立科学接受</p></header>',
      `<div class="user-fact-chart" role="img" ` +
        `aria-label="revision ${revision.revision}事实图">${bars}</div>`,
      `<table><caption>revision ${revision.revision}事实表</caption>`,
      '<thead><tr><th>字段</th><th>当前值</th><th>事实版本</th></tr></thead>',
      `<tbody>${rows}</tbody></table>`,
      `<section><h3>文字摘要</h3><ul>${narrative}</ul></section>`,
      `<section><h3>来源指针</h3><ul>${sources}</ul></section>`
    ].join('');
  });
})();
"""


def _stylesheet() -> str:
    return """.user-fact-revision{
margin:1.25rem 0;padding:1rem;border:1px solid #cbd5df;border-left:5px solid #8b1e2d;
border-radius:10px;background:#fff}.user-fact-revision .eyebrow{color:#8b1e2d;font-weight:700}
.user-fact-revision table{width:100%;border-collapse:collapse}
.user-fact-revision th,.user-fact-revision td{
padding:.5rem;border-bottom:1px solid #dde4ea;text-align:left}
.user-fact-chart{display:grid;gap:.4rem;margin:1rem 0}
.user-fact-bar{position:relative;padding:.45rem;
background:linear-gradient(90deg,#9b2536 var(--value),#edf1f4 var(--value));color:#111}
.user-fact-bar span{background:#ffffffd9;padding:.1rem .3rem}
"""


def integrate_fact_revision(
    site_root: Path,
    *,
    report: ReportCode,
    revision: int,
    request_id: str,
    fact_revision_digest: str,
    facts: dict[str, dict[str, Any]],
) -> PortalFactRevisionReceipt:
    """Mutate an unpublished real portal staging tree and return its real dependencies."""
    data_dir = site_root / "data"
    assets_dir = site_root / "assets"
    payload_path = data_dir / "report.js"
    search_path = data_dir / "search-index.js"
    sitemap_path = data_dir / "sitemap.json"
    if not all(path.is_file() for path in (payload_path, search_path, sitemap_path)):
        raise ValueError("W04只能接入由现有portal builder生成的真实站点")
    sitemap = json.loads(sitemap_path.read_bytes())
    routes = {str(item["path"]) for item in sitemap.get("routes", [])}
    consumers: list[PortalFactConsumer] = []
    pages: dict[str, list[str]] = {}
    for fact_id, fact in sorted(facts.items()):
        page_slug = _page_for_fact(report, fact)
        page_relative = f"{page_slug}.html"
        if page_relative not in routes or not (site_root / page_relative).is_file():
            raise ValueError(f"事实依赖页面不在真实站点目录中：{report}/{page_relative}")
        pages.setdefault(page_slug, []).append(fact_id)
        consumers.append(
            PortalFactConsumer(
                report=report,
                page_slug=page_slug,
                fact_id=fact_id,
                fact_version_id=str(fact["fact_version_id"]),
            )
        )

    global_name = _REPORT_GLOBAL[report]
    payload = _read_assignment(payload_path, global_name)
    if not isinstance(payload, dict):
        raise ValueError("真实门户payload必须是对象")
    payload["user_fact_revision"] = {
        "revision": revision,
        "request_id": request_id,
        "fact_revision_digest": fact_revision_digest,
        "facts": facts,
        "consumers": [item.model_dump(mode="json") for item in consumers],
        "independent_scientific_acceptance": "not_inherited",
    }
    _write_assignment(payload_path, global_name, payload)

    search = _read_assignment(search_path, "__SEARCH_INDEX__")
    if not isinstance(search, list):
        raise ValueError("真实门户搜索索引必须是数组")
    search = [
        entry
        for entry in search
        if not (
            isinstance(entry, dict)
            and str(entry.get("anchor", "")).startswith("user-fact-")
        )
    ]
    for consumer in consumers:
        fact = facts[consumer.fact_id]
        search.append(
            {
                "title": f"用户事实：{fact.get('field_id', consumer.fact_id)}",
                "slug": consumer.page_slug,
                "keywords": [
                    consumer.fact_id,
                    consumer.fact_version_id,
                    str(fact.get("raw_value", "")),
                    f"revision {revision}",
                ],
                "anchor": f"user-fact-{consumer.fact_id}",
            }
        )
    _write_assignment(search_path, "__SEARCH_INDEX__", search)

    js_path = assets_dir / "user-fact-revision.js"
    css_path = assets_dir / "user-fact-revision.css"
    js_path.write_text(_javascript(), encoding="utf-8")
    css_path.write_text(_stylesheet(), encoding="utf-8")
    html_hashes: dict[str, str] = {}
    for page_slug, fact_ids in sorted(pages.items()):
        page_path = site_root / f"{page_slug}.html"
        html = page_path.read_text(encoding="utf-8")
        if "</head>" not in html or "</body>" not in html:
            raise ValueError("真实门户页面缺少标准head/body边界")
        html = _REVISION_SECTION.sub("", html)
        html = html.replace(_REVISION_STYLESHEET, "")
        html = html.replace(_REVISION_SCRIPT, "")
        fact_ids_json = json.dumps(fact_ids, ensure_ascii=False).replace('"', "&quot;")
        section = (
            f'<section class="user-fact-revision" id="user-fact-revision" '
            f'data-user-fact-revision="{revision}" data-user-fact-consumer="{report}:{page_slug}" '
            f'data-fact-ids="{fact_ids_json}"></section>'
        )
        html = html.replace(
            "</head>", _REVISION_STYLESHEET + "</head>", 1
        )
        html = re.sub(r"</main>", section + "</main>", html, count=1)
        if section not in html:
            html = html.replace("</body>", section + "</body>", 1)
        if _REVISION_PAYLOAD_SCRIPT not in html:
            html = html.replace("</body>", _REVISION_PAYLOAD_SCRIPT + "</body>", 1)
        html = html.replace(
            "</body>", _REVISION_SCRIPT + "</body>", 1
        )
        page_path.write_text(html, encoding="utf-8")
        html_hashes[f"{page_slug}.html"] = _sha256(page_path)

    return PortalFactRevisionReceipt(
        report=report,
        revision=revision,
        request_id=request_id,
        fact_revision_digest=fact_revision_digest,
        payload_relative_path="data/report.js",
        payload_sha256=_sha256(payload_path),
        search_index_relative_path="data/search-index.js",
        search_index_sha256=_sha256(search_path),
        javascript_relative_path="assets/user-fact-revision.js",
        javascript_sha256=_sha256(js_path),
        html_sha256=html_hashes,
        consumers=tuple(consumers),
    )


__all__: list[str] = []
