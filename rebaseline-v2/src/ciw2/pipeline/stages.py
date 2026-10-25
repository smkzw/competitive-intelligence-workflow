"""阶段定义。确定性工作（抓取、解析、核验、渲染）用代码；判断类工作交给 Skill。

DAG（按报告类型裁剪）：
 intake → universe_china → universe_global → candidate_triage → universe_expand → coverage_review → trial_evidence(code)
       → trial_scope_review → extract_results(B) → extract_design(C) → verify(code) → analysis_A/B/C → render(code)
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ciw2.domain.identity import literal_names, name_key, name_owners, possible_trial_relation, research_aliases
from ciw2.domain.models import AnalysisResult, IntakeResult, UniverseResult
from ciw2.domain.tiers import tier_of
from ciw2.harness.agent import HARNESS_RULES
from ciw2.pipeline import summary_budget, summary_lineage
from ciw2.pipeline.context import IncompleteWork, RunContext, work_limit
from ciw2.pipeline.profile import enrich
from ciw2.pipeline.queries import drug_trials, scoped_drugs
from ciw2.pipeline.queries import intake_data as _intake
from ciw2.pipeline.recovery import fingerprint, get_unit, put_unit
from ciw2.pipeline.summary_lineage import summary_basis as _summary_basis
from ciw2.pipeline.summary_lineage import summary_chars as _summary_chars
from ciw2.sources import ctgov

ANALYSIS_CODE_HASH = hashlib.sha256(Path(__file__).read_bytes() + Path(summary_lineage.__file__).read_bytes() + Path(summary_budget.__file__).read_bytes()).hexdigest()
ANALYSIS_TASK_CHARS = 24000
SYNTHESIS_TASK_CHARS = 8000  # Dense narrative reduction is not a raw-record extraction task.
CTGOV_CODE_HASH = hashlib.sha256(Path(ctgov.__file__).read_bytes()).hexdigest()


@dataclass(frozen=True)
class Stage:
    name: str
    fn: Callable[[RunContext], dict[str, Any]]
    reports: frozenset[str] = frozenset({"A", "B", "C"})  # 哪些报告需要本阶段
    blocking: bool = True    # 失败是否终止运行（非阻断阶段失败会记录并继续）


# ------------------------------------------------------------------ intake
def intake(rc: RunContext) -> dict[str, Any]:
    p = rc.project
    res: IntakeResult = rc.skill("intake", {
        "request_text": p["request_text"], "indication": p["indication"], "reports": p["reports"],
        "focus": p["focus"], "cutoff_date": p["cutoff_date"]})
    aliases = sorted(set(p["indication_aliases"]) | set(res.aliases) | {res.indication_en})
    rc.db.execute("UPDATE projects SET indication_aliases=?, focus=? WHERE id=?",
                  (json.dumps(aliases, ensure_ascii=False), p["focus"] or res.focus, rc.project_id))
    return res.model_dump()


# ------------------------------------------------------------------ universe
def _persist_universe(rc: RunContext, res: UniverseResult) -> int:
    new = 0
    for c in res.candidates:
        attrs = {k: v for k, v in c.model_dump().items()
                 if k not in {"name", "name_zh", "aliases", "route_id"} and v not in (None, [], "unknown")}
        attrs[f"found_in_{res.region}"] = True
        eid, is_new = rc.db.upsert_entity(rc.project_id, "drug", c.name, name_zh=c.name_zh,
                                          aliases=research_aliases(c.aliases), attrs=attrs, route_id=c.route_id)
        new += int(is_new)
        for comp in c.companies:
            cid, _ = rc.db.upsert_entity(rc.project_id, "company", comp, route_id=c.route_id)
            rc.db.link(rc.project_id, eid, "drug-company", cid)
        for t in c.targets:
            tid, _ = rc.db.upsert_entity(rc.project_id, "target", t, route_id=c.route_id)
            rc.db.link(rc.project_id, eid, "drug-target", tid)
        # 中国状态/MAH 属于 critical：只有给出证据 URL 时才写入事实（核验阶段再查原文）
        if c.highest_phase_china != "unknown":
            rc.db.add_fact({"project_id": rc.project_id, "entity_id": eid, "field": "status.china.highest_phase",
                            "value": c.highest_phase_china, "tier": tier_of("status.china"),
                            "status": "unverified", "context": {"evidence_urls": c.evidence_urls},
                            "extracted_by": f"llm:{getattr(rc.llm, 'model', 'llm')}"})
    return new


def _universe(region: str) -> Callable[[RunContext], dict[str, Any]]:
    def run(rc: RunContext) -> dict[str, Any]:
        it = _intake(rc)
        known = [e["name"] for e in rc.db.entities(rc.project_id, "drug")]
        res: UniverseResult = rc.skill(f"universe-{region}", {
            "indication": it["indication"], "indication_en": it.get("indication_en"),
            "aliases": it.get("aliases", []), "focus": rc.project["focus"], "already_known": known})
        if res.region != region:
            res = res.model_copy(update={"region": region})
        new = _persist_universe(rc, res)
        return {"candidates": len(res.candidates), "new": new, "routes_run": res.routes_run,
                "routes_failed": res.routes_failed, "notes": res.notes}
    return run


# ------------------------------------------------------------------ scope / coverage review
def universe_expand(rc: RunContext) -> dict[str, Any]:
    from ciw2.pipeline.expansion import expand_universe
    return expand_universe(rc, lambda result: _persist_universe(rc, result))


def coverage_review(rc: RunContext) -> dict[str, Any]:
    from ciw2.pipeline.scope import review_scope
    return review_scope(rc, _intake(rc)["indication"])


def trial_scope_review(rc: RunContext) -> dict[str, Any]:
    """Review source-collected orphan studies before their facts reach report analysis."""
    from ciw2.pipeline.scope import review_orphan_trials
    return review_orphan_trials(rc, _intake(rc)["indication"])


# ------------------------------------------------------------------ trial evidence (code)
def _matches(drug: dict[str, Any], interventions: list[dict[str, Any]],
             ambiguous_names: set[str] | frozenset[str] = frozenset()) -> bool:
    keys = literal_names(drug) - ambiguous_names
    for iv in interventions:
        names = [iv.get("name"), *(iv.get("other_names") or [])]
        if keys & {name_key(name) for name in names if name_key(name)}:
            return True
    return False


def trial_evidence(rc: RunContext) -> dict[str, Any]:
    from ciw2.pipeline.china_evidence import collect
    from ciw2.pipeline.nmpa_evidence import collect as collect_nmpa
    china=collect(rc)
    nmpa=collect_nmpa(rc)
    it = _intake(rc)
    ctx = rc.tool_ctx()
    cond = it.get("indication_en") or rc.project["indication"]
    max_trials = work_limit(rc.cache.get('max_trials_per_drug'))
    linked, ingested, pending_links, errors = 0, china['ingested'], 0, china['errors']+nmpa['errors']
    pending = china['pending_trials']
    owners = name_owners(rc.db.entities(rc.project_id, 'drug'))
    ambiguous = {name for name, ids in owners.items() if len(ids) > 1}
    for d in scoped_drugs(rc):
        rc.check_cancelled()
        try:
            rows = ctgov.search(ctx, condition=cond, intervention=d["name"], max_results=None)
            rc.db.log_coverage(rc.run_id, "trial:ctgov:intervention", "global", f"{cond} × {d['name']}",
                               "ok", hits=len(rows))
        except Exception as exc:  # noqa: BLE001 - 独立来源边界记录失败并继续其他路线
            rc.db.log_coverage(rc.run_id, "trial:ctgov:intervention", "global", f"{cond} × {d['name']}",
                               "failed", note=str(exc)[:300])
            errors.append(f"{d['name']}: {exc}")
            pending.append({'drug_id': d['id'], 'nct': None, 'reason': 'source_search_failed'})
            rows = []
        known = {t["name"]: t for t in rc.db.entities(rc.project_id, "trial")}
        excluded = {t['name'] for t in known.values() if t['in_scope']==0}
        candidates = {r["nct"]: r for r in rows if r['nct'] not in excluded}
        for t in known.values():
            if t['name'] not in excluded:
                candidates.setdefault(t["name"], {"nct": t["name"], **t["attrs"]})
        hits = [r for r in candidates.values() if _matches(d, r.get("interventions") or [], ambiguous)]
        confirmed = {r['nct'] for r in hits}
        for row in candidates.values():
            if row['nct'] in confirmed or not possible_trial_relation(d, row.get('interventions') or []):
                continue
            trial_id, _ = rc.db.upsert_entity(rc.project_id, 'trial', row['nct'],
                attrs={k: value for k, value in row.items() if k != 'nct'}, route_id='trial:identity-candidate')
            rc.db.link(rc.project_id, d['id'], 'drug-trial-candidate', trial_id,
                attrs={'identity_status': 'pending', 'reason': 'label_variant_or_shared_alias',
                       'intervention_names': [iv.get('name') for iv in row.get('interventions') or []]})
            pending_links += 1
        hits.sort(key=lambda r: (r.get("phase") or "", r.get("start_date") or "", r['nct']), reverse=True)
        started = 0
        for r in hits:
            rc.check_cancelled()
            key = f'trial_ingestion:{CTGOV_CODE_HASH}:{r["nct"]}:{fingerprint(r)}'
            info = get_unit(rc, key)
            if info is None and max_trials is not None and started >= max_trials:
                pending.append({'drug_id': d['id'], 'nct': r['nct'], 'reason': 'execution_budget'})
                continue
            try:
                if info is None:
                    started += 1
                    info = ctgov.ingest_trial(ctx, r['nct'], route_id='trial:ctgov:intervention')
                    put_unit(rc, key, info, urls=[f'{ctgov.API}/{r["nct"]}'])
                    ingested += int(info['facts_added'] > 0)
            except Exception as exc:  # noqa: BLE001 - 单个试验失败不丢其他试验
                errors.append(f"{r['nct']}: {exc}")
                pending.append({'drug_id': d['id'], 'nct': r['nct'], 'reason': 'source_ingestion_failed'})
                continue
            rc.db.link(rc.project_id, d["id"], "drug-trial", info["entity_id"],
                       attrs={'identity_status': 'literal_match'})
            if rc.db.one("SELECT 1 FROM links WHERE project_id=? AND src=? AND rel='drug-trial-candidate' AND dst=?",
                         (rc.project_id, d['id'], info['entity_id'])):
                rc.db.link(rc.project_id, d['id'], 'drug-trial-candidate', info['entity_id'],
                           attrs={'identity_status': 'resolved_literal_match'})
            linked += 1
    output = {"linked": linked, "ingested": ingested, "errors": errors, 'pending_trials': pending,'nmpa':nmpa,
            'pending_identity_links': pending_links,
            'identity_ambiguities': [{'name': name, 'entity_ids': sorted(owners[name])} for name in sorted(ambiguous)]}
    if pending or nmpa['pending_records']:
        raise IncompleteWork(f"研究资料未完成：{len(pending)+len(nmpa['pending_records'])}个待处理单元", output)
    return output


# ------------------------------------------------------------------ LLM extraction
def _extract(skill: str, extra: Callable[[RunContext, dict[str, Any]], dict[str, Any]]) -> Callable[
        [RunContext], dict[str, Any]]:
    def run(rc: RunContext) -> dict[str, Any]:
        from ciw2.pipeline.extraction import extract_drugs
        return extract_drugs(rc, skill, extra)
    return run


def _results_extra(rc: RunContext, d: dict[str, Any]) -> dict[str, Any]:
    have = {(f["entity_id"]) for f in rc.db.current_facts(rc.project_id) if f["field"].startswith("result.")}
    return {"trials_with_registry_results": [t["name"] for t in drug_trials(rc, d["id"]) if t["id"] in have]}


def _design_extra(rc: RunContext, d: dict[str, Any]) -> dict[str, Any]:
    with_design = {f["entity_id"] for f in rc.db.current_facts(rc.project_id)
                   if f["field"] == "design.sample_size" and f["extracted_by"] in {"code:ctgov","code:chinadrugtrials"}}
    return {"trials_with_registry_design": [t["name"] for t in drug_trials(rc, d["id"]) if t["id"] in with_design]}


# ------------------------------------------------------------------ verify (code)
def _entity_for(rc: RunContext, name: str, drug: str) -> str:
    n = name.strip()
    if re.fullmatch(r"NCT\d{8}", n.upper()):
        return rc.db.upsert_entity(rc.project_id, "trial", n.upper(), route_id="extract")[0]
    if re.fullmatch(r"CTR\d{8}", n.upper()):
        return rc.db.upsert_entity(rc.project_id, "trial", n.upper(), attrs={"registry": "chinadrugtrials"},
                                   route_id="extract")[0]
    matches = [d['id'] for d in rc.db.entities(rc.project_id) if name_key(n) in literal_names(d)]
    if len(matches) == 1:
        return matches[0]
    raise ValueError('抽取实体无法唯一关联已发现实体；不按父药物或相似拼写猜测归属')


def cross_check(llm: Any, fact: dict[str, Any]) -> bool | None:
    """可选：第二个模型只回答「原文片段是否支持该值及其语义（组/时间点/人群/统计对象）」。"""
    from ciw2.harness.llm import LLMError
    prompt = ("只回答 YES 或 NO：下面的原文片段是否明确支持该事实（数值、组别、时间点、人群、统计对象全部一致）？\n"
              + json.dumps({k: fact.get(k) for k in ("field", "value", "unit", "stat_type", "arm", "timepoint",
                                                      "population", "denominator", "enrollment_type", "source_context", "quote")}, ensure_ascii=False))
    try:
        reply = llm.chat([{"role": "user", "content": prompt}])
    except LLMError:
        return None
    text = (reply.content or "").strip().upper()
    return True if text.startswith("YES") else False if text.startswith("NO") else None


def verify(rc: RunContext) -> dict[str, Any]:
    from ciw2.pipeline.verification import adopt
    return adopt(rc, _entity_for, cross_check)


# ------------------------------------------------------------------ analysis + render
def _analysis(report: str) -> Callable[[RunContext], dict[str, Any]]:
    def run(rc: RunContext) -> dict[str, Any]:
        from ciw2.render.portal import report_data
        data = report_data(rc.db, rc.project_id, report)
        if not any(data.get(key) for key in ('rows', 'results', 'safety', 'analyses')):
            return {'report': report, 'findings': []}
        verified = {f['id'] for f in rc.db.current_facts(rc.project_id) if f['status'] == 'verified'}
        core = _compact(data)
        base = {'indication': _intake(rc)['indication'], 'focus': rc.project['focus'],
                'cutoff_date': rc.project['cutoff_date'],
                'overview': {key: len(value) for key, value in core.items() if isinstance(value, list)}}
        tasks = _analysis_tasks(core, base, verified)
        findings = []
        for task in tasks:
            rc.check_cancelled()
            res = _analysis_call(rc, report, task)
            findings.extend(f.model_dump() for f in res.findings)
        if not findings and any(task['verified_fact_ids'] for task in tasks):
            raise ValueError('有已核实资料但摘要要点为空，保留原资料供恢复')
        if len(tasks) <= 1 or not findings:
            return {'report': report, 'findings': findings}
        return _analysis_merge(rc, report, findings, base, verified)
    return run


def _clinical_context(context: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in context.items() if k not in {
        'json_path', 'source_url', 'source_snapshot', 'verify_note', 'proposed_supersedes'}}


def _compact_observations(row: dict[str, Any], observations: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for field, refs in observations.items():
        slim = []
        for ref in refs:
            item = {key: ref[key] for key in ('fact_id', 'status') if key in ref}
            if field != 'eligibility_criteria':
                item['context'] = _clinical_context(ref.get('context', {}))
                if len(refs) != 1 or field not in row:
                    item['value'] = ref.get('value')
            slim.append(item)
        out[field] = slim
    return out


def _compact(data: Any) -> Any:
    """Remove duplicate display evidence, never shorten a clinical definition.

    Full source text stays in the report/store. Endpoint definitions, complete
    threshold rules, population, units, time and statistical context stay here.
    """
    if isinstance(data, list):
        return [_compact(item) for item in data]
    if not isinstance(data, dict):
        return data
    out = {}
    for key, value in data.items():
        if key in {'charts', 'endpoint_groups', 'eligibility_criteria', 'eligibility_reading', 'eligibility_clauses', 'quote', 'legacy_geography_ids'}:
            continue
        if 'fact_id' in data and key in {'source_id', 'url', 'locator'}:
            continue  # Stable fact_id resolves original provenance; not clinical definition.
        if key == 'identity' and value:
            out[key] = {k: value[k] for k in ('drug_label', 'indication', 'phase_label', 'conditions_original') if k in value}
            out[key]['companies'] = [{k: c[k] for k in ('role', 'name', 'fact_id') if k in c}
                                     for c in value.get('companies', [])]
        elif key == 'context' and 'fact_id' in data:
            out[key] = _clinical_context(value)
        elif key == 'observations':
            out[key] = _compact_observations(data, value)
        elif key == 'sources':
            out[key] = {field: [{k: ref[k] for k in ('fact_id', 'status') if k in ref} for ref in refs]
                        for field, refs in value.items() if field!='legacy_geography'}
        elif key == 'value' and 'fact_id' in data and isinstance(value, dict) and all(
                name in data and data[name] == item for name, item in value.items()):
            continue  # The same primary endpoint is already present as named fields.
        else:
            out[key] = _compact(value)
    return out


def _analysis_refs(data: Any) -> set[str]:
    if isinstance(data, list):
        return set().union(*(_analysis_refs(item) for item in data)) if data else set()
    if isinstance(data, dict):
        refs = {value for key, value in data.items() if key in {'id', 'fact_id'} and isinstance(value, str)}
        refs.update(ref for ref in data.get('fact_refs', []) if isinstance(ref, str))
        for value in data.values():
            refs.update(_analysis_refs(value))
        return refs
    return set()


def _analysis_budget(task: dict[str, Any], max_chars: int = ANALYSIS_TASK_CHARS) -> None:
    if len(json.dumps(task, ensure_ascii=False, default=str)) > max_chars:
        raise ValueError('摘要输入超过整包预算；保留完整记录，不截断临床定义或伪装全量总结')


def _design_parts(row: dict[str, Any], fits: Callable[[dict[str, Any]], bool]) -> list[dict[str, Any]]:
    """Partition oversized studies by whole endpoints, repeating study context."""
    if fits(row):
        return [row]
    fields = ('primary_endpoints', 'secondary_endpoints')
    endpoints = [(key, item) for key in fields for item in row.get(key, [])]
    if not endpoints:
        return [row]  # The ordinary task guard reports oversized non-endpoint context.
    common = {key: value for key, value in row.items() if key not in fields}
    ids = {e.get('fact_id') for _, e in endpoints if e.get('fact_id')}
    common['sources'] = {key: [ref for ref in refs if key not in {'primary_endpoint', 'secondary_endpoint'}
                              or ref.get('fact_id') not in ids]
                         for key, refs in row.get('sources', {}).items()}

    def empty() -> dict[str, Any]:
        return {**common, **{key: [] for key in fields}, 'study_part': {
            'index': len(endpoints), 'count': len(endpoints),
            'primary_total': len(row.get(fields[0], [])), 'secondary_total': len(row.get(fields[1], []))}}

    pending, parts = empty(), []
    for key, endpoint in endpoints:
        pending[key].append(endpoint)
        if fits(pending):
            continue
        pending[key].pop()
        if any(pending[name] for name in fields):
            parts.append(pending)
        pending = empty()
        pending[key].append(endpoint)
        if not fits(pending):
            raise ValueError('摘要输入中单条完整终点或共同研究上下文超预算，不截断定义')
    if any(pending[name] for name in fields):
        parts.append(pending)
    for index, part in enumerate(parts, 1):
        part['study_part'] = {**part['study_part'], 'index': index, 'count': len(parts)}
    return parts


def _analysis_tasks(data: dict[str, Any], base: dict[str, Any], verified: set[str], *,
                    max_chars: int = ANALYSIS_TASK_CHARS, mode: str = 'batch') -> list[dict[str, Any]]:
    """Plan complete records; large studies use whole endpoints with study context."""
    arrays = {key: value for key, value in data.items() if isinstance(value, list)}
    fixed = {key: value for key, value in data.items() if key not in arrays}

    def task(payload: dict[str, Any]) -> dict[str, Any]:
        return {**base, 'mode': mode, 'data': payload,
                'verified_fact_ids': sorted(_analysis_refs(payload) & verified)}

    def row_fits(row: dict[str, Any]) -> bool:
        payload = {**fixed, **{key: [] for key in arrays}, 'rows': [row]}
        return len(json.dumps(task(payload), ensure_ascii=False, default=str)) <= max_chars

    if 'rows' in arrays:
        arrays['rows'] = [part for row in arrays['rows'] for part in (
            _design_parts(row, row_fits) if isinstance(row, dict) and 'primary_endpoints' in row else [row])]
    pending = {**fixed, **{key: [] for key in arrays}}
    _analysis_budget(task(pending), max_chars)
    tasks = []
    for key, records in arrays.items():
        for record in records:
            pending[key].append(record)
            candidate = task(pending)
            if len(json.dumps(candidate, ensure_ascii=False, default=str)) <= max_chars:
                continue
            pending[key].pop()
            if any(pending[key] for key in arrays):
                tasks.append(task(pending))
            pending = {**fixed, **{name: [] for name in arrays}}
            pending[key].append(record)
            _analysis_budget(task(pending), max_chars)
    if any(pending[key] for key in arrays) or not tasks:
        tasks.append(task(pending))
    return tasks


def _analysis_cache_key(rc: RunContext, report: str, task: dict[str, Any]) -> str:
    skill = rc.skills[f'analysis-{report.lower()}']
    signature = {'task': task, 'code': ANALYSIS_CODE_HASH, 'rules': HARNESS_RULES,
                 'skill': skill.body, 'schema': AnalysisResult.model_json_schema(),
                 'model': rc.settings.llm_model}
    digest = hashlib.sha256(json.dumps(signature, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return f'analysis_{report}:{task["mode"]}:{digest}'


def _analysis_call(rc: RunContext, report: str, task: dict[str, Any]) -> AnalysisResult:
    _analysis_budget(task, SYNTHESIS_TASK_CHARS if task['mode'] == 'synthesis' else ANALYSIS_TASK_CHARS)
    skill = rc.skills[f'analysis-{report.lower()}']
    key = _analysis_cache_key(rc,report,task)
    cached = rc.db.stage_output(rc.run_id, key)
    if cached is not None:
        result = AnalysisResult.model_validate(cached)
        rc.db.log_step(rc.run_id, rc.stage, skill.name, 0, 'cache', {'reused_stage': key})
    else:
        result = rc.skill(skill.name, task)
    result = summary_lineage.normalize_references(rc, task, result)
    result = AnalysisResult.model_validate(result.model_dump())
    if result.report != report:
        raise ValueError('摘要返回的报告类型与任务不一致')
    if len(result.findings) > task.get('finding_limit', 6):
        raise ValueError('摘要条数超过本次归并上限，不缓存超量结果')
    if any(not f.title.strip() or not f.bullets or any(not text.strip() for text in f.bullets)
           for f in result.findings):
        raise ValueError('摘要正文内容为空，不缓存无内容的结构化成功')
    if any(not f.fact_refs or not set(f.fact_refs) <= set(task['verified_fact_ids']) for f in result.findings):
        raise ValueError('摘要引用不属于本次完整输入，不缓存或静默删除')
    if not result.findings and task['verified_fact_ids'] and (task['mode'] == 'batch' or task.get('final_summary')):
        raise ValueError('有已核实资料但摘要要点为空，不缓存空成功')
    if _summary_chars(result.model_dump()['findings']) > SYNTHESIS_TASK_CHARS:
        raise ValueError('归并输出正文超过摘要预算，不缓存膨胀的结果')
    if cached is None:
        rc.db.set_stage(rc.run_id, key, 'succeeded', output=result.model_dump())
    return result


def _summary_resolve(rc: RunContext, report: str, task: dict[str, Any], refs: dict[str, list[str]]) -> dict[str, Any]:
    return summary_lineage.resolve_summary(rc, report, task, refs, _analysis_call)


def _analysis_merge(rc: RunContext, report: str, findings: list[dict[str, Any]],
                    base: dict[str, Any], verified: set[str]) -> dict[str, Any]:
    if not findings:
        return {'report': report, 'findings': []}
    for level in range(12):
        rc.check_cancelled()
        projected, refs, basis = _summary_basis(rc, findings, verified)
        scoped = {**base, 'finding_basis_sha256': basis}
        synthesis = {**scoped, 'mode': 'synthesis', 'finding_limit': 6, 'final_summary': True,
                     'data': {'candidate_findings': projected}, 'verified_fact_ids': sorted(refs)}
        costs=summary_budget.read_costs(rc,refs)
        cached=lambda task: rc.db.stage_output(rc.run_id,_analysis_cache_key(rc,report,task)) is not None
        if (len(json.dumps(synthesis, ensure_ascii=False)) <= SYNTHESIS_TASK_CHARS and
                (cached(synthesis) or summary_budget.context_chars(synthesis,costs)<=summary_budget.MAX_CONTEXT_CHARS)):
            result = _summary_resolve(rc, report, synthesis, refs)
            if not result['findings']:
                raise ValueError('非空摘要输入返回空结果，保留原输入供恢复')
            return result
        packets = _analysis_tasks({'candidate_findings': projected}, {**scoped, 'finding_limit': 1}, set(refs),
                                  max_chars=SYNTHESIS_TASK_CHARS, mode='synthesis')
        packets=summary_budget.packets(packets,costs,cached)
        merged = []
        for packet in packets:
            rc.check_cancelled()
            packet['finding_limit'] = min(6, (len(packet['data']['candidate_findings']) + 1) // 2)
            merged.extend(_summary_resolve(rc, report, packet, refs)['findings'])
        if not merged:
            raise ValueError('非空中间归并返回空结果，保留上一完整层')
        before, after = _summary_chars(findings), _summary_chars(merged)
        accepted = (len(merged) <= len(findings) and after < before
                    and (len(merged) * 4 <= len(findings) * 3 or after * 20 <= before * 17))
        signature = fingerprint([basis, ANALYSIS_CODE_HASH, HARNESS_RULES, rc.skills[f'analysis-{report.lower()}'].body,
                                 AnalysisResult.model_json_schema(), rc.settings.llm_model])
        rc.db.set_stage(rc.run_id, f'analysis_{report}:merge_layer:{signature}',
            'succeeded' if accepted else 'failed', output={
            'schema_version': 'ciw2-summary-layer-v2', 'accepted': accepted,
            'code_sha256': ANALYSIS_CODE_HASH, 'rules_sha256': fingerprint(HARNESS_RULES),
            'skill_sha256': fingerprint(rc.skills[f'analysis-{report.lower()}'].body),
            'schema_sha256': fingerprint(AnalysisResult.model_json_schema()), 'requested_model': rc.settings.llm_model,
            'scope': 'INTERMEDIATE_NOT_FINAL_REPORT', 'report': report, 'level': level, 'findings': merged,
            'input_sha256': fingerprint(findings), 'basis_sha256': basis,
            'input_count': len(findings), 'output_count': len(merged), 'chars_in': before, 'chars_out': after})
        if not accepted:
            raise ValueError('摘要输入归并未收敛；同一策略继续只复用相同结果。'
                             '保留原研究资料，在新归并运行中调整策略；无需重跑研究批次')
        findings = merged
    raise ValueError('摘要归并超过12层，保留完整检查点，不继续模型调用')


def render(rc: RunContext) -> dict[str, Any]:
    from ciw2.render.publish import publish_reports
    return publish_reports(rc)


STAGES: list[Stage] = [
    Stage("intake", intake),
    Stage("universe_china", _universe("china"), blocking=False),
    Stage("universe_global", _universe("global"), blocking=False),
    Stage('candidate_triage', coverage_review),
    Stage('universe_expand', universe_expand, blocking=False),
    Stage("coverage_review", coverage_review),
    Stage("trial_evidence", trial_evidence, blocking=False),
    Stage("trial_scope_review", trial_scope_review),
    Stage('enrich_drugs',enrich,blocking=False),
    Stage("extract_results", _extract("extract-results", _results_extra), frozenset({"B"}), blocking=False),
    Stage("extract_design", _extract("extract-design", _design_extra), frozenset({"C"}), blocking=False),
    Stage("verify", verify),
    Stage("analysis_A", _analysis("A"), frozenset({"A"}), blocking=False),
    Stage("analysis_B", _analysis("B"), frozenset({"B"}), blocking=False),
    Stage("analysis_C", _analysis("C"), frozenset({"C"}), blocking=False),
    Stage("render", render),
]
