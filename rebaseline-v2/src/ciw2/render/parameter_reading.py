"""Complete source parameter wording, compactly rendered without drug dictionaries."""
from __future__ import annotations

import re

_PARAMETERS = {
    'Serum Concentration Observed Immediately Before Next Dosing (Ctrough)': '下次给药前即刻血清浓度（Ctrough）',
    'Absorption Rate Constant (Ka)': '吸收速率常数（Ka）',
    'Apparent Terminal Half-life (t1/2)': '表观终末半衰期（t1/2）',
    'Apparent Total Body Clearance (Cl/F)': '表观全身清除率（Cl/F）',
    'Apparent Volume of Distribution (Vd/F)': '表观分布容积（Vd/F）',
    'Area Under the Serum Concentration-Time Curve From Time Zero to Infinity (AUCinf)': '血清AUC（0至无穷，AUCinf）',
}
_SAFETY = ('Number of Participants With Treatment Emergent Adverse Events (TEAEs), '
           'Adverse Events of Special Interest (AESIs), Adverse Events Leading to Discontinuation '
           'and Serious Adverse Events (SAEs)')
_SAFETY_FACETS = {'TEAEs': 'TEAE', 'AESIs': 'AESI', 'SAEs': 'SAE',
                  'AE leading to discontinuation': '因AE停药'}
_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9 -]{0,119}')
_QUALIFIER = re.compile(r'\b(?:with|without|excluding|except|at|during|after|before|in|and|or|versus|vs)\b', re.IGNORECASE)


def _analyte(text: str) -> bool:
    return bool(_NAME.fullmatch(text)) and not _QUALIFIER.search(text)


def safety_facet_label(raw: str, facets: list[str]) -> str | None:
    if ' '.join(raw.split()) != _SAFETY or len(facets) != 1:
        return None
    label = _SAFETY_FACETS.get(facets[0])
    return f'{label} · 受试者人数' if label else None


def parameter_label(text: str) -> str | None:
    if text == _SAFETY:
        return 'TEAE、AESI、因AE停药、SAE · 受试者人数'
    if text == 'Percentage of Participants Receiving Any Rescue Therapy by Rescue Treatment':
        return '接受补救治疗的受试者比例 · 按补救治疗分层'
    for raw, label in _PARAMETERS.items():
        prefix = raw + ' of '
        if text.startswith(prefix) and _analyte(name := text[len(prefix):]):
            return f'{name} · {label}'
    concentration = re.fullmatch(r'(.+) Serum Concentrations', text)
    if concentration and _analyte(concentration[1]):
        return f'{concentration[1]} · 血清浓度'
    antibody = re.fullmatch(r'Number of Participants With Positive Anti-Drug Antibody \(ADA\) for (.+)', text)
    if antibody and _analyte(antibody[1]):
        return f'{antibody[1]} · ADA阳性受试者人数'
    return None


def relationship_parts(text: str) -> tuple[str, str] | None:
    prefix = r'(?:PK/PD|Pharmacokinetic \(PK\)/Pharmacodynamic \(PD\))'
    match = re.fullmatch(prefix+r' Relationship Between (.+) Serum Concentration and Changes in (.+)', text)
    return (match[1],match[2]) if match and _analyte(match[1]) else None
