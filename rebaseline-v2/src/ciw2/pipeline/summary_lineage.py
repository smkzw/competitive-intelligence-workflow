"""Lossless short fact references and auditable narrative selection, not science edits."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from ciw2.domain.models import AnalysisResult
from ciw2.pipeline.context import RunContext
from ciw2.pipeline.recovery import fingerprint


def summary_chars(findings: list[dict[str, Any]]) -> int:
    return len(json.dumps([{k: v for k, v in f.items() if k != 'fact_refs'} for f in findings], ensure_ascii=False))


def _clinical_studies(rc: RunContext, findings: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    from ciw2.render.trial_identity import trial_identities

    facts = {f['id']: f for f in rc.db.current_facts(rc.project_id)}
    identities = trial_identities(rc.db, rc.project_id)
    rows = []
    for finding in findings:
        studies = []
        tids = dict.fromkeys(facts[fid]['entity_id'] for fid in finding['fact_refs'] if fid in facts)
        for tid in tids:
            identity = identities.get(tid)
            if not identity or not any(identity.get(k) for k in ('drugs', 'indication', 'phase_label')):
                continue
            studies.append({**{k: identity[k] for k in
                               ('registry_id', 'drug_label', 'indication', 'phase_label')},
                            'companies': [{k: company[k] for k in ('role', 'name')}
                                          for company in identity['companies']]})
        rows.append(studies)
    return rows


def summary_basis(rc: RunContext, findings: list[dict[str, Any]], verified: set[str]
                  ) -> tuple[list[dict[str, Any]], dict[str, list[str]], str]:
    if any(not f.get('fact_refs') or not set(f['fact_refs']) <= verified for f in findings):
        raise ValueError('摘要输入含未核实或不存在的引用')
    original_ids = list(dict.fromkeys(r for f in findings for r in f['fact_refs']))
    refs = {f'summary_ref_{i}': [ref] for i, ref in enumerate(original_ids)}
    aliases = {ref: key for key, values in refs.items() for ref in values}
    studies = _clinical_studies(rc, findings)
    digest = fingerprint({'findings': findings, 'reference_map': refs, 'clinical_studies': studies})
    lineage = {'schema_version': 'ciw2-summary-basis-v3', 'digest': digest, 'reference_map': refs,
               'reference_granularity': 'one_fact_per_alias', 'input_sha256': fingerprint(findings),
               'scope': 'REFERENCE_MAPPING_NOT_SCIENTIFIC_ACCEPTANCE', 'clinical_studies': studies}
    key = f'analysis_basis:{digest}'
    existing = rc.db.stage_output(rc.run_id, key)
    if existing is None:
        rc.db.set_stage(rc.run_id, key, 'succeeded', output=lineage)
    elif existing != lineage:
        raise ValueError('摘要引用映射检查点与输入不符，不覆盖历史')
    rc.db.log_step(rc.run_id, rc.stage, 'synthesis', 0, 'synthesis_basis', {
        'digest': digest, 'basis_stage': key, 'input_sha256': lineage['input_sha256']})
    return [{**{k: v for k, v in f.items() if k != 'studies'},
             **({'studies': context} if context else {}),
             'fact_refs': [aliases[r] for r in dict.fromkeys(f['fact_refs'])]}
            for f, context in zip(findings, studies, strict=True)], refs, digest


def normalize_references(rc: RunContext, task: dict[str, Any], result: AnalysisResult) -> AnalysisResult:
    """Accept full IDs returned by the fact tool only through this packet's exact mapping.

    This changes transport notation, never the cited fact or narrative. Unknown
    references stay visible to the caller's rejection guard; no fuzzy join/filter.
    Existing model objects and historical cached output are not rewritten.
    """
    digest = task.get('finding_basis_sha256')
    if not digest:
        return result
    basis = rc.db.stage_output(rc.run_id, 'analysis_basis:' + digest)
    if not basis or basis.get('digest') != digest:
        raise ValueError('摘要引用缺少本次完整映射依据')
    mapping = basis.get('reference_map', {})
    supplied = set(task['verified_fact_ids'])
    if any(alias not in mapping or len(mapping[alias]) != 1 for alias in supplied):
        raise ValueError('摘要引用必须具备本任务一对一映射')
    reverse = {mapping[alias][0]: alias for alias in supplied}
    if len(reverse) != len(supplied):
        raise ValueError('摘要引用映射不是一对一，不猜测归属')
    return result.model_copy(update={'findings': [finding.model_copy(update={
        'fact_refs': list(dict.fromkeys(ref if ref in supplied else reverse.get(ref, ref)
                                       for ref in finding.fact_refs))}) for finding in result.findings]})


def resolve_summary(rc: RunContext, report: str, task: dict[str, Any], refs: dict[str, list[str]],
                    call: Callable[..., Any]) -> dict[str, Any]:
    result = call(rc, report, task).model_dump()
    selected_aliases = {ref for f in result['findings'] for ref in f['fact_refs']}
    supplied_aliases = set(task['verified_fact_ids'])
    for finding in result['findings']:
        finding['fact_refs'] = list(dict.fromkeys(ref for key in finding['fact_refs'] for ref in refs[key]))
    selection = {'schema_version': 'ciw2-summary-selection-v1',
                 'scope': 'NARRATIVE_SELECTION_NOT_FACT_RETRACTION',
                 'basis_sha256': task['finding_basis_sha256'], 'task_sha256': fingerprint(task),
                 'selected_fact_ids': sorted({r for a in selected_aliases for r in refs[a]}),
                 'omitted_fact_ids': sorted({r for a in supplied_aliases - selected_aliases for r in refs[a]}),
                 'output_sha256': fingerprint(result)}
    key = f'analysis_selection:{fingerprint(selection)}'
    if rc.db.stage_output(rc.run_id, key) is None:
        rc.db.set_stage(rc.run_id, key, 'succeeded', output=selection)
    return result
