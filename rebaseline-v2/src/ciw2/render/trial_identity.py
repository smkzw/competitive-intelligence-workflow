"""Shared clinical reading identity; display never changes study, arm or fact IDs."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from ciw2.domain.identity import name_key
from ciw2.domain.profile_evidence import holder_role
from ciw2.render.drug_identity import drug_identities, web_url
from ciw2.render.drug_profile import drug_profiles
from ciw2.render.labels import phase_label
from ciw2.store.db import DB


def verified_holders(facts: list[dict[str, Any]], sources: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        if (fact['field'] != 'status.china_mah' or fact['status'] != 'verified'
                or not isinstance(fact['value'], str) or not fact['value'].strip()
                or fact['source_id'] not in sources
                or fact['context'].get('jurisdiction') not in {None, 'CN', 'China', '中国'}):
            continue
        context=fact['context']
        role=holder_role(context)
        display=f"{fact['value']}（证书有效期至 {context['valid_until']}）" if role=='许可记录持有人' else fact['value']
        out[fact['entity_id']].append({'role':role,'name':fact['value'],'display_name':display,'fact_id':fact['id'],
            'source_id': fact['source_id'], 'url': web_url(sources[fact['source_id']]['url']),
            'quote': fact['quote'], 'jurisdiction': 'CN',
            'registration_number':fact['context'].get('registration_number'),
            'strength':fact['context'].get('strength'),
            'observed_at':fact['context'].get('observed_at'),
            'valid_until':context.get('valid_until'),'issue_date':context.get('issue_date'),
            'approval_date':context.get('approval_date')})
    return out


def _indication(conditions: list[str], project: dict[str, Any]) -> str:
    aliases = {name_key(n) for n in [project['indication'], *project['indication_aliases']]}
    labels=[]
    for condition in conditions:
        listing=re.fullmatch(r'本品适用于治疗([^，；;。]+)[。]?',condition)
        items=listing[1].split('、') if listing else []
        exact_list=len(items)>1 and any(name_key(n) in aliases for n in items)
        labels.append(project['indication'] if name_key(condition) in aliases or exact_list else condition)
    return ' / '.join(dict.fromkeys(labels))


def trial_identities(db: DB, pid: str) -> dict[str, dict[str, Any]]:
    project = db.project(pid)
    assert project is not None
    drugs = drug_identities(db,pid)
    profiles=drug_profiles(db,pid)
    sources = {s['id']: s for s in db.query('SELECT id,url,kind,meta FROM sources WHERE project_id=?', (pid,))}
    facts = db.current_facts(pid)
    holders = verified_holders(facts, sources)
    per_trial: dict[str, list[str]] = defaultdict(list)
    for edge in db.query("SELECT src,dst FROM links WHERE project_id=? AND rel='drug-trial'", (pid,)):
        if edge['src'] in drugs:
            per_trial[edge['dst']].append(edge['src'])
    phases: dict[str, set[str]] = defaultdict(set)
    legacy_sources: dict[str, set[str]] = defaultdict(set)
    for fact in facts:
        if fact['field'] == 'design.phase' and fact['status'] == 'verified' and isinstance(fact['value'], str):
            phases[fact['entity_id']].add(fact['value'])
        if fact['extracted_by'] == 'code:ctgov' and fact['source_id'] in sources:
            legacy_sources[fact['entity_id']].add(fact['source_id'])
    current_sources = {r['src']: r['dst'] for r in db.query(
        "SELECT src,dst FROM links WHERE project_id=? AND rel='ctgov-current'", (pid,))}
    china_current = {r['src']: r['dst'] for r in db.query(
        "SELECT src,dst FROM links WHERE project_id=? AND rel='chinadrugtrials-current'", (pid,))}
    out = {}
    for trial in db.entities(pid, 'trial'):
        attrs, tid = trial['attrs'], trial['id']
        names = sorted({drugs[d]['name_zh'] or drugs[d]['name'] for d in per_trial[tid]}, key=name_key)
        if not names:
            names = [i['name'] for i in attrs.get('interventions', [])
                     if i.get('type') in {'DRUG', 'BIOLOGICAL'} and isinstance(i.get('name'), str)]
        if not names and attrs.get('registry')=='chinadrugtrials' and tid in china_current:
            names=[attrs['registry_drug_name']] if attrs.get('registry_drug_name') else []
        drug_label = ' / '.join(dict.fromkeys(names)) or '研究方案'
        original_names = sorted({drugs[d]['name'] for d in per_trial[tid]}, key=name_key)
        conditions = [c for c in attrs.get('conditions', []) if isinstance(c, str) and c.strip()]
        indication = _indication(conditions, project)
        phase_text = ' / '.join(sorted({phase_label(p) for p in phases[tid]}))
        companies=[]
        for did in per_trial[tid]:
            for holder in holders[did]:
                groups=[ref for ref in profiles[did]['group_refs']
                        if name_key(ref['legal_entity'])==name_key(holder['name'])]
                companies.append({**holder,**({'role':holder['role']+'所属集团',
                    'display_name':' / '.join(dict.fromkeys(ref['name'] for ref in groups)),
                    'legal_entity':holder['name'],'group_refs':groups} if groups else {})})
            companies.extend(profiles[did]['companies'])
        for fact in facts:
            source=sources.get(fact['source_id'])
            if (fact['entity_id']==tid and fact['field']=='trial.applicant' and fact['status']=='verified'
                    and isinstance(fact['value'],str) and fact['value'].strip() and source
                    and source['kind']=='chinadrugtrials' and fact['source_id']==china_current.get(tid)
                    and json.loads(source['meta']).get('request_context',{}).get('registry_id')==trial['name']):
                companies.append({'role':'登记申请人','name':fact['value'],'fact_id':fact['id'],
                    'source_id':fact['source_id'],'url':web_url(source['url']),
                    'locator':fact['context'].get('json_path'),'quote':fact['quote']})
        sid = current_sources.get(tid)
        if sid is None and attrs.get('registry') == 'ctgov' and len(legacy_sources[tid]) == 1:
            sid = next(iter(legacy_sources[tid]))  # Read-only legacy provenance, not a snapshot activation.
        if attrs.get('sponsor') and sid in sources and sources[sid]['kind'] == 'ctgov':
            companies.append({'role': '申办方', 'name': attrs['sponsor'], 'source_id': sid,
                'url': sources[sid]['url'], 'locator': attrs.get('replay_container_locator', '$') +
                    '.protocolSection.sponsorCollaboratorsModule.leadSponsor.name'})
        company_label = '；'.join(dict.fromkeys(f"{c['role']} {c['name']}" for c in companies))
        label = ' · '.join(part for part in (drug_label, indication, phase_text, company_label) if part)
        out[tid] = {'entity_id': tid, 'registry_id': trial['name'], 'url': web_url(attrs.get('url')),
            'title': attrs.get('title'), 'drug_label': drug_label, 'drugs': names,
            'drug_names_original': original_names,
            'name_refs':[ref for d in per_trial[tid] for ref in drugs[d]['name_refs']],
            'targets':sorted({target for d in per_trial[tid] for target in profiles[d]['targets']},key=name_key),
            'profile_refs':[ref for d in per_trial[tid] for ref in profiles[d]['profile_refs']],
            'indication': indication, 'conditions_original': conditions,
            'scope_indication': project['indication'], 'phase_label': phase_text,
            'companies': companies, 'label': label, 'axis_label': ' · '.join(filter(None, (drug_label, phase_text)))}
    return out
