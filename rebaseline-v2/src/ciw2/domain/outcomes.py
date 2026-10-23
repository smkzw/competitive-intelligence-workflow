"""Reversible reading domains, not scientific identity or numeric eligibility.

Only measured wording and explicitly supplied source drug names participate.
Mixed/ambiguous measures stay reachable as unresolved; source facts are never
rewritten. An outcome definition can expand an acronym, not supply a treatment
identity merely mentioned in background prose.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

DOMAIN_LABELS = {
    'clinical': '临床结果', 'safety': '安全性', 'pk': '药代动力学',
    'pd': '药效动力学', 'immunogenicity': '免疫原性',
    'biomarker': '生物标志物', 'unresolved': '其他研究指标',
}


def _pattern(value: str) -> re.Pattern[str]:
    return re.compile(value, re.IGNORECASE)


_SAFETY = _pattern(
    r'\badverse (?:drug )?(?:events?|reactions?)\b|\b(?:TEAEs?|SAEs?|AESIs?|AEs?)\b'
    r'|\bside[- ]effects?\b|\bsafety\b|\btolerability\b|\btoxicit(?:y|ies)\b'
    r'|\binjection[- ]site reactions?\b|\binfusion[- ]related reactions?\b')
_IMMUNE = _pattern(r'\banti[- ]?(?:drug|therapeutic) antibod(?:y|ies)\b|\bimmunogenicity\b')
_PK = _pattern(
    r'\bpharmacokinetic(?:s)?\b|\bPK\b|\bconcentration[- ]time curve\b'
    r'|\b(?:Cmax|Cmin|Ctrough|Cavg|Tmax|Cl/F|Vd/F|Vz/F)\b|\bt1/2\b')
_PD = _pattern(r'\bpharmacodynamic(?:s)?\b|\b(?:receptor|target) occupancy\b|\btarget engagement\b')
_BIOMARKER = _pattern(r'\bbiomarkers?\b|\b(?:serum|plasma|blood) eosinophil counts?\b')
_CLINICAL = _pattern(
    r'\bEASI(?:-\d+)?\b|(?-i:\bIGA\b)|\bSCORAD\b|(?-i:\bPOEM\b)|\b(?:c|i)?DLQI\b'
    r'|\bNRS\b|\bpruritus\b|\bitch(?:ing)?\b|\bsleep disturbance\b|\b(?:quality of life|life quality)\b'
    r'|\bglobal assessment\b|\bpatient[- ]reported\b|\bsymptom (?:score|severity|scale)\b'
    r'|\b(?:lesions?|erythema|excoriations?|lichenification|flares?|remission)\b'
    r'|\b(?:rescue therapy|treatment success|disease control|exacerbations?|clinical response)\b'
    r'|\bbody surface area\b|\b(?:overall|progression[- ]free|disease[- ]free) survival\b')
_MIXED_PKPD = _pattern(r'\bPK\s*/\s*PD\b|\bpharmacokinetic(?:s)?\s*(?:\(PK\))?\s*/\s*pharmacodynamic')
_BACKGROUND = _pattern(r'\b(?:also|receiv(?:e|es|ing|ed)|participants|patients|were|was)\b')
_CONCENTRATION = r'(?:concentrations?|levels?)'


def _analyte_pattern(name: str) -> re.Pattern[str]:
    # Literal full names, including codes and compound names. Never INN suffixes.
    literal = rf'(?<!\w){re.escape(name)}(?!\w)'
    return _pattern(
        rf'\b(?:serum|plasma|blood)\s+{_CONCENTRATION}\s+of\s+(?:the\s+)?{literal}'
        rf'|\b(?:serum|plasma|blood)\s+{literal}\s+{_CONCENTRATION}\b'
        rf'|{literal}\s+(?:serum|plasma|blood)\s+{_CONCENTRATION}\b')


def _assess(text: str, drug_names: Sequence[str]) -> set[str]:
    domains = set()
    for label, pattern in (('clinical', _CLINICAL), ('safety', _SAFETY),
                           ('immunogenicity', _IMMUNE), ('pk', _PK),
                           ('pd', _PD), ('biomarker', _BIOMARKER)):
        if pattern.search(text):
            domains.add(label)
    if any(name and _analyte_pattern(name).search(text) for name in drug_names):
        domains.add('pk')
    if any(_analyte_pattern(name).search(text) for name in ('IgE', 'IgA', 'IgG')):
        domains.add('biomarker')
    if re.search(rf'\b{_CONCENTRATION}\b', text, re.IGNORECASE) and not domains & {'pk', 'biomarker', 'immunogenicity'}:
        domains.add('unresolved')
    # These named parameters require a source-bound drug, not a guessed suffix.
    if any(re.search(rf'\b(?:clearance|volume of distribution|absorption rate constant|half[- ]life)'
                     rf'[^.;]{{0,40}}\bof\s+(?<!\w){re.escape(name)}(?!\w)', text, re.IGNORECASE)
           for name in drug_names if name):
        domains.add('pk')
    return domains


def classify_outcome_domain(title: str, description: str | None = None, *,
                            drug_names: Sequence[str] = ()) -> str:
    """Project a reading label; unknown abbreviations do not become guesses.

    ``description`` must be the same outcome's definition, not a study summary.
    A generic title may use its definition only when it names a measured target
    rather than treatment/population/background prose.
    """
    title = ' '.join(title.split())
    definition = ' '.join((description or '').split())
    # Explicit expansions defeat unrelated interpretations of the same acronym.
    if re.search(r'\b(?:receiver operating characteristic|adenosine deaminase|bovine serum albumin)\b',
                 title + ' ' + definition, re.IGNORECASE):
        return 'unresolved'
    if _MIXED_PKPD.search(title):
        return 'unresolved'
    domains = _assess(title, drug_names)
    if (not domains or domains == {'unresolved'}) and definition and not _BACKGROUND.search(definition):
        domains = _assess(definition, drug_names)
    if re.search(r'\befficacy\b', title, re.IGNORECASE) and 'clinical' not in domains:
        return 'unresolved'
    return next(iter(domains)) if len(domains) == 1 else 'unresolved'
