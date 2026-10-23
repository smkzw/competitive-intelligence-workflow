"""Study/source-scoped result-arm projection; no substring identity inference."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from ciw2.domain.identity import CONTROL_LABELS, name_key, name_owners
from ciw2.render.drug_identity import drug_identities
from ciw2.store.db import DB


def _arm_index(db: DB, pid: str) -> dict[tuple, dict[tuple[str, ...], set[str]]]:
    index: dict[tuple, dict[tuple[str, ...], set[str]]] = defaultdict(lambda: defaultdict(set))
    for fact in db.current_facts(pid):
        if fact['field'] != 'design.arms' or fact['status'] != 'verified' or not fact['source_id']:
            continue
        if not isinstance(fact['value'], list):
            continue
        for arm in fact['value']:
            if not isinstance(arm, dict) or not isinstance(arm.get('label'), str):
                continue
            declared = arm.get('interventions')
            if not isinstance(declared, list) or not all(isinstance(item, str) for item in declared):
                continue
            key = (fact['entity_id'], fact['source_id'], fact['context'].get('source_snapshot'), name_key(arm['label']))
            index[key][tuple(sorted({name_key(item) for item in declared}))].add(fact['id'])
    return index


def _declared_drugs(declared: tuple[str, ...], owners: dict[str, set[str]]) -> tuple[set[str], str]:
    resolved: set[str] = set()
    controls = 0
    for intervention in declared:
        kind, separator, label = intervention.partition(':')
        name = name_key(label) if separator and kind in {'drug', 'biological'} else intervention
        if name in CONTROL_LABELS:
            controls += 1
            continue
        ids = owners.get(name, set())
        if len(ids) != 1:
            return set(), 'ambiguous_drug_identity' if ids else 'unresolved_drug_identity'
        resolved.update(ids)
    return resolved, 'resolved' if resolved else ('control' if controls else 'source_arm_relation_missing')


def bind_result_drugs(db: DB, pid: str, rows: list[dict[str, Any]]) -> None:
    """Keep trial candidates as context; each result uses only its explicit arm relation."""
    drugs = drug_identities(db,pid)
    per_trial: dict[str, set[str]] = defaultdict(set)
    for link in db.query("SELECT src,dst FROM links WHERE project_id=? AND rel='drug-trial'", (pid,)):
        if link['src'] in drugs:
            per_trial[link['dst']].add(link['src'])
    owners = {tid: name_owners([drugs[eid] for eid in ids]) for tid, ids in per_trial.items()}
    index = _arm_index(db, pid)
    for row in rows:
        row['trial_drugs'] = row['drugs']
        refs: list[str] = []
        ids: set[str] = set()
        reason = 'source_arm_relation_missing'
        if row['entity_type'] == 'drug' and row['entity_id'] in drugs:
            ids, reason = {row['entity_id']}, 'resolved'
        elif row['arm'] and row['source_id']:
            key = (row['entity_id'], row['source_id'], row.get('source_snapshot'), name_key(row['arm']))
            declarations = index.get(key, {})
            refs = sorted({ref for references in declarations.values() for ref in references})
            if len(declarations) > 1:
                reason = 'conflicting_arm_relations'
            elif declarations:
                ids, reason = _declared_drugs(next(iter(declarations)), owners.get(row['entity_id'], {}))
        names = sorted({drugs[eid]['name'] for eid in ids}, key=name_key)
        row.update(arm_drugs=names, drugs=names, arm_drug=' / '.join(names) or None,
                   arm_binding_status=reason if reason in {'resolved', 'control'} else 'unresolved',
                   arm_binding_reason=reason, arm_binding_refs=refs)
