"""流水线：获取 → 抽取 → 归一 → 核对 → 分析 → release → 渲染。

每一步都是普通函数；原件在 CAS 里，离线重跑（offline=True）不重新联网取来源；启用模型时仍访问模型端点。
LLM 抽取按“原件哈希 + 抽取 schema + 指令”缓存，改动分析/渲染代码不会让已核对的抽取失效。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from ciw.analyze.design import build_design
from ciw.analyze.landscape import build_landscape
from ciw.analyze.results import build_results, build_safety
from ciw.config import ConceptCfg, IndicationConfig
from ciw.extract.ctgov import extract_results, extract_safety, extract_trial
from ciw.models import OutcomeResult, Product, SafetySummary, Source, Trial
from ciw.normalize.products import ProductResolver, is_unclassified_candidate
from ciw.normalize.trials import deduplicate_trials
from ciw.release import write_release
from ciw.sources import captures, cde_registry, ctgov, europepmc
from ciw.sources.nmpa.registry import ingest as ingest_nmpa
from ciw.store import Workspace, now_iso
from ciw.verify.attributes import enrich_attributes
from ciw.verify.llm import Backend
from ciw.verify.publications import extract_publications


@dataclass
class RunResult:
    release_id: str
    release_path: Path
    site_dir: Path | None
    stats: dict[str, Any]
    coverage: list[dict[str, Any]] = field(default_factory=list)


def build_products(cfg: IndicationConfig) -> dict[str, Product]:
    out = {}
    for p in cfg.products:
        out[p.id] = Product(
            product_id=p.id,
            name_en=p.name_en,
            name_zh=p.name_zh,
            codes=[a for a in p.aliases if any(ch.isdigit() for ch in a)][:4],
            brand=p.brand,
            target=p.target,
            mechanism=p.mechanism,
            modality=p.modality,
            route=p.route,
            company=p.company,
            china_partner=p.china_partner,
            innovative=p.innovative,
            is_own=p.own,
            inclusion_reason=p.note or "适应症配置中的竞品",
            attribute_status="config",
        )
    return out


def run(
    cfg: IndicationConfig,
    ws: Workspace,
    *,
    offline: bool = False,
    roles: dict[str, Backend] | None = None,
    render: bool = True,
    log=print,
    preloaded_studies=None,
    report_scope: str | None = None,
    render_reports: list[str] | None = None,
) -> RunResult:
    if report_scope not in {None, "A", "B", "C"}:
        raise ValueError("未知报告类型")
    cfg = cfg.model_copy(deep=True)
    selected = render_reports if render_reports is not None else list("ABC")
    if any(r not in {"A", "B", "C"} for r in selected):
        raise ValueError("未知报告类型")
    coverage: list[dict[str, Any]] = []
    resolver = ProductResolver(cfg)
    products = build_products(cfg)

    studies = preloaded_studies
    if studies is None:
        studies = _load_studies(cfg, ws, offline, coverage, log)
    else:
        coverage.append(dict(source="ctgov", status="ok", records=len(studies),
                             fetched_at=max((src.fetched_at for src, _ in studies.values()), default=None)))

    trials, results, safety, unclassified, stats = _extract_studies(cfg, resolver, studies)

    _add_cde(cfg, ws, resolver, trials, unclassified, coverage, log)

    # 3. 非结构化来源（公告、公众号、NMPA 页面文本）：异构模型交叉核对
    events, review_queue, ev_cov = captures.extract_events(ws, cfg, resolver, roles)
    coverage.extend(ev_cov)
    approvals, approval_issues, approval_coverage = ingest_nmpa(ws, resolver)
    events.extend(approvals)
    review_queue.extend(approval_issues)
    coverage.append(approval_coverage)

    merged_trials, identity_issues = deduplicate_trials(list(trials.values()))
    trials = {trial.trial_id: trial for trial in merged_trials}
    review_queue.extend(identity_issues)
    previous = _reuse_completed(cfg, ws, products, trials, results, coverage, report_scope) or {}
    if report_scope in {None, "A"}:
        log("[research] attributes")
        review_queue.extend(enrich_attributes(ws, products, list(trials.values()), resolver, roles, log=log))

    if report_scope in {None, "B"}:
        log("[research] publications")
        _add_publications(cfg, ws, resolver, trials, results, roles, offline, review_queue, coverage)

    from ciw.verify.endpoint_index import enrich_endpoint_index

    review_queue.extend(enrich_endpoint_index(ws, cfg, results, roles if report_scope in {None, "B"} else None, log))
    from ciw.analyze.clinical_families import project_clinical_families
    from ciw.verify.endpoint_families import enrich_endpoint_families

    families, family_issues = enrich_endpoint_families(ws, cfg, results,
        roles if report_scope in {None, "B"} else None, previous=previous.get("clinical_families"))
    review_queue.extend(family_issues)
    body = _build_body(cfg, ws, products, trials, results, safety, events, review_queue, unclassified, stats, coverage)
    body["clinical_families"] = families
    body["b"] = project_clinical_families(body["b"], families["groups"])
    body["stats"]["questions"] = len(body["b"]["questions"])
    from ciw.render.site import presentation_digest

    body.update(rendered_reports=sorted(set(selected)) if render else [], presentation_digest=presentation_digest())
    release_id, path = write_release(ws, json.loads(json.dumps(body, default=str)))
    site = None
    if render:
        log("[research] render")
        from ciw.render.site import render_release

        site = render_release(path)
    ws.set_current(release_id)
    log(f"[release] {release_id} stats={stats}")
    return RunResult(release_id=release_id, release_path=path, site_dir=site, stats=stats, coverage=coverage)


def _reuse_completed(cfg, ws, products, trials, results, coverage, scope):
    """Reuse adopted source facts, never HTML or unchecked model memory."""
    from ciw.release import load_release
    previous = ws.current_release_dir()
    if not previous:
        return
    old = load_release(previous)
    if old["indication"]["slug"] != cfg.slug:
        return
    for item in old.get("clinical_concepts", []):
        concept = ConceptCfg.model_validate(item)
        if concept.source_definition is not None and not any(c.id == concept.id for c in cfg.concepts):
            concept.origin, concept.provisional = "source_index", False
            cfg.concepts.append(concept)
    source_ids = {entry.locator.source_id for t in trials.values() for entry in (t, *t.registrations)}
    for item in old["products"]:
        prior = Product.model_validate(item)
        product = products.get(prior.product_id)
        if not product or product.name_en != prior.name_en:
            continue
        for attr in ("target", "modality"):
            locator = prior.attribute_locators.get(attr)
            if not getattr(product, attr) and locator and locator.source_id in source_ids:
                setattr(product, attr, getattr(prior, attr))
                product.attribute_locators[attr] = locator
                product.attribute_status = prior.attribute_status
    if scope is not None and scope != "B" and "B" in old.get("rendered_reports", list("ABC")):
        known = {s.source_id: s.kind for s in ws.sources()}
        for item in old["results"]:
            result = OutcomeResult.model_validate(item)
            if result.trial_id in trials and known.get(result.locator.source_id) == "europepmc":
                results.append(result)
        coverage.extend(c for c in old["coverage"] if c["source"] in {"europepmc", "publications"})
    return old


def _collect_unclassified(
    cfg: IndicationConfig, resolver: ProductResolver, study: dict[str, Any], t: Trial, acc: dict[str, dict[str, Any]]
) -> None:
    if not cfg.is_relevant_text(" ".join([t.title, t.official_title, *t.conditions])):
        return
    for iv in study["protocolSection"].get("armsInterventionsModule", {}).get("interventions", []):
        name = iv.get("name", "")
        if resolver.resolve_intervention(name):
            continue
        if is_unclassified_candidate(cfg, name, iv.get("type", ""), t.sponsor_class):
            key = name.strip().casefold()
            entry = acc.setdefault(key, {"name": name.strip(), "trials": [], "sponsors": [], "phases": []})
            entry["trials"].append(t.trial_id)
            if t.sponsor not in entry["sponsors"]:
                entry["sponsors"].append(t.sponsor)
            entry["phases"].append(t.phase)


def _load_studies(cfg, ws, offline, coverage, log):
    # 1. CT.gov
    if offline:
        studies = ctgov.load_from_sources(ws)
        coverage.append(
            {
                "source": "ctgov",
                "status": "ok" if studies else "not_captured",
                "detail": f"离线读取 CAS：{len(studies)} 项研究",
            }
        )
    else:
        studies = ctgov.search_and_store(
            ws, conditions=cfg.ctgov.conditions, intervention_queries=cfg.ctgov.extra_intervention_queries
        )
        coverage.append(
            {
                "source": "ctgov",
                "status": "ok",
                "detail": f"按条件 {cfg.ctgov.conditions} 检索介入性研究",
                "records": len(studies),
                "fetched_at": now_iso(),
            }
        )
    log(f"[ctgov] {len(studies)} studies")

    return studies


def _extract_studies(cfg, resolver, studies):
    trials: dict[str, Trial] = {}
    results: list[OutcomeResult] = []
    safety: list[SafetySummary] = []
    unclassified: dict[str, dict[str, Any]] = {}
    stats = {"analyses_unassigned": 0, "outcomes": 0}
    for nct, (src, study) in sorted(studies.items()):
        t = extract_trial(study, src, cfg, resolver)
        trials[nct] = t
        _collect_unclassified(cfg, resolver, study, t, unclassified)
        if t.relevance != "core" or not t.has_results:
            continue
        rs, st = extract_results(study, t, src, cfg, resolver)
        results.extend(rs)
        for k, v in st.items():
            stats[k] = stats.get(k, 0) + v
        s = extract_safety(study, t, src, resolver)
        if s:
            safety.append(s)

    return trials, results, safety, unclassified, stats


def _add_cde(cfg, ws, resolver, trials, unclassified, coverage, log):
    # 2. 中国登记（CDE 药物临床试验登记与信息公示平台）：采集收件箱
    cde_trials, cde_cov = cde_registry.ingest(ws, cfg, resolver)
    coverage.append(cde_cov)
    for t in cde_trials:
        trials[t.trial_id] = t
        if t.relevance == "background" and not t.product_ids and cfg.is_relevant_text(" ".join(t.conditions)):
            name = t.title if not t.arms else t.arms[0].interventions[0]
            name = next((a.interventions[0] for a in t.arms if a.role == "experimental" and a.interventions), name)
            if not cfg.is_background(name):
                entry = unclassified.setdefault(
                    name.casefold(), {"name": name, "trials": [], "sponsors": [], "phases": []}
                )
                entry["trials"].append(t.trial_id)
                entry["sponsors"] = sorted({*entry["sponsors"], t.sponsor} - {""})
                entry["phases"].append(t.phase)
    log(f"[cde] {cde_cov['status']}: {len(cde_trials)} trials")


def _add_publications(cfg, ws, resolver, trials, results, roles, offline, review_queue, coverage):
    # Paper discovery does not turn a search hit into trial evidence; binding uses literal IDs in abstracts.
    paper_ids = sorted(
        {
            identifier
            for t in trials.values()
            if t.relevance == "core" and not t.has_results and t.phase_rank in (3, 4)
            for identifier in t.ids.values()
            if europepmc.is_registry_id(identifier)
        }
    )
    papers, paper_coverage = europepmc.discover(ws, paper_ids, offline=offline)
    paper_results, paper_issues = extract_publications(ws, cfg, papers, trials, resolver, roles)
    results.extend(paper_results)
    review_queue.extend(paper_issues)
    paper_coverage.update(extracted_results=len(paper_results), extraction_enabled=roles is not None)
    if paper_issues:
        paper_coverage["status"] = "partial"
    coverage.append(paper_coverage)


def _build_body(cfg, ws, products, trials, results, safety, events, review_queue, unclassified, stats, coverage):
    for t in trials.values():
        for pid in t.product_ids:
            if t.relevance == "core" and t.trial_id not in products[pid].trial_ids:
                products[pid].trial_ids.append(t.trial_id)

    review_queue += [
        {"kind": "arm_role_conflict", "trial_id": t.trial_id, "arm_id": a.arm_id,
         "source_id": t.locator.source_id,
         "path": f"{t.locator.path}.armsInterventionsModule.armGroups[{a.arm_id[1:]}]",
         "source_type": a.type, "interventions": a.interventions}
        for t in trials.values() for a in t.arms if a.role_conflict
    ]
    review_queue += [
        {
            "kind": "unclassified_intervention",
            "ref": v["name"],
            "note": "企业申办的药物干预，未在配置中归类",
            "trials": v["trials"],
        }
        for v in unclassified.values()
    ]
    own = cfg.own_product_id
    trial_list = sorted(trials.values(), key=lambda t: t.trial_id)
    a = build_landscape(list(products.values()), trial_list, events, list(unclassified.values()), own)
    b = build_results(cfg, trials, products, results, own)
    b["safety"] = build_safety(trials, products, safety)
    c = build_design(cfg, trial_list, products)

    used = (
        {record.locator.source_id for t in trial_list for record in [t, *t.registrations]}
        | {e.source_id for e in events}
        | {loc.source_id for p in products.values() for loc in p.attribute_locators.values()}
        | {r.locator.source_id for r in results}
    )
    sources: list[Source] = [s for s in ws.sources() if s.source_id in used]
    core = [t for t in trial_list if t.relevance == "core"]
    stats.update(
        {
            "trials_total": len(trial_list),
            "trials_core": len(core),
            "trials_core_with_results": sum(t.has_results for t in core),
            "products_in_landscape": len(a["products"]),
            "results": len(results),
            "questions": len(b["questions"]),
            "comparisons": sum(len(q["comparisons"]) for q in b["questions"]),
            "events": len(events),
            "review_queue": len(review_queue),
            "unclassified_interventions": len(unclassified),
        }
    )
    body = {
        "indication": {"slug": cfg.slug, "name_zh": cfg.name_zh, "name_en": cfg.name_en, "abbr": cfg.abbr},
        # 数据截止：配置给定，否则取本次所用原件中最晚的获取日期（离线重跑结果稳定）
        "cutoff": (
            cfg.cutoff.isoformat()
            if cfg.cutoff
            else max((s.fetched_at[:10] for s in sources), default=date.today().isoformat())
        ),
        "own_product_id": own,
        "coverage": coverage,
        "sources": [s.model_dump() for s in sources],
        "products": [p.model_dump() for p in products.values()],
        "trials": [t.model_dump() for t in trial_list],
        "results": [r.model_dump() for r in results],
        "safety": [s.model_dump() for s in safety],
        "events": [e.model_dump() for e in events],
        "a": a,
        "b": b,
        "c": c,
        "review_queue": review_queue,
        "clinical_concepts": [c.model_dump() for c in cfg.concepts if c.source_definition is not None],
        "stats": stats,
    }
    return body
