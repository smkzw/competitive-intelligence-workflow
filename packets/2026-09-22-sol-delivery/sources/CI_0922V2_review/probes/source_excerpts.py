"""Behavior-preserving source excerpts captured from commit 700bd4c.
Not an installed repository. Comments/docstrings/import surroundings omitted.
Upstream files and blob IDs are listed in evidence/source_manifest.json.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

# reports/b/safety_concepts.py: classification rules and functions.
_NEGATION_PATTERNS = (
    re.compile(r"\bnon[\s-]*serious\b", re.I),
    re.compile(r"\b(?:not|no|without)[\s-]+serious\b", re.I),
    re.compile(r"\bnon[\s-]*treatment[\s-]*emergent\b", re.I),
    re.compile(r"\bnon[\s-]*teaes?\b", re.I),
    re.compile(r"\b(?:not|no|without)\s+teaes?\b", re.I),
)
_SPECIFIC_RULES = (
    ("discontinuation_ae", re.compile(
        r"discontinu\w*(?:\s+\w+){0,4}\s(?:due\s+to|because\s+of|leading)|"
        r"(?:due\s+to|because\s+of)\s+adverse|leading\s+to\s+(?:treatment\s+)?discontinu", re.I)),
    ("treatment_related_ae", re.compile(r"treatment[\s-]*related|related\s+adverse\s+events?", re.I)),
    ("grade_3_plus", re.compile(
        r"grade\s*(?:≥|>=)?\s*[34]\b"
        r"|grade\s+[12]\s+(?:or|and)\s+[34]\b"
        r"|grade\s+[34]\s+(?:or|and)\s+[1-4]\b", re.I)),
    ("aesi", re.compile(r"(?:adverse\s+events?|\(?teaes?\)?)\s+of\s+special\s+interest|(?<![a-z])aesis?(?![a-z])", re.I)),
    ("serious_teae_subset", re.compile(r"serious\s+(?:treatment[\s-]*emergent|teaes?)", re.I)),
)
_GENERAL_RULES = (
    ("any_teae", re.compile(r"(?<![a-z\-])teaes?(?![a-z])", re.I)),
    ("any_teae", re.compile(r"\b(?:any|overall|all)\b[^.;]{0,40}treatment[\s-]*emergent", re.I)),
    ("any_sae", re.compile(r"\bserious\s+adverse\s+events?\b", re.I)),
    ("any_sae", re.compile(r"(?<![a-z\-])saes?(?![a-z])", re.I)),
    ("death", re.compile(r"\bdeaths?\b|\bmortality\b", re.I)),
)
_GENERIC_RULE = re.compile(r"\badverse\s+events?\b|(?<![a-z\-])aes(?![a-z])", re.I)
def _classify_single(text: str) -> str | None:
    for concept, pattern in _SPECIFIC_RULES:
        if pattern.search(text): return concept
    for concept, pattern in _GENERAL_RULES:
        if pattern.search(text): return concept
    if _GENERIC_RULE.search(text): return "generic_ae"
    if re.search(r"adverse|safety|\bae\b", text, re.I): return "specific_ae"
    return None

def classify_safety_concept(title: str) -> str:
    text = " ".join(str(title or "").split())
    if not text: return "unknown"
    stripped = text
    for pattern in _NEGATION_PATTERNS:
        stripped = pattern.sub(" ", stripped)
    fragments = [fragment.strip(" ,;:") for fragment in re.split(r",|;|\band\b", stripped, flags=re.I) if fragment.strip(" ,;:")]
    fragment_concepts = [concept for fragment in fragments if (concept := _classify_single(fragment)) is not None]
    distinct = set(fragment_concepts)
    if len(distinct) == 1: return fragment_concepts[0]
    if len(distinct) > 1: return "composite_ae"
    whole = _classify_single(stripped)
    if whole is not None: return whole
    return "unknown"

# reports/b/safety_denominator_crosswalk.py: complete computational surface.
_VALID_STATS = frozenset({"serious", "other", "deaths", "person_time"})
def normalize_period(value: str | None) -> str | None:
    text = str(value or "").strip().upper().replace(" ", "").replace("-", "")
    if not text: return None
    m = re.fullmatch(r"TP(\d+)", text)
    if m: return f"TP{m.group(1)}"
    if text in {"LTE", "LTEP"}: return "LTE"
    if text == "OLTP": return "OLTP"
    if text == "OLEP": return "OLEP"
    return text

def period_of(title: str) -> str | None:
    text = str(title or "")
    m = re.search(r"\btp\s*[- ]?(\d+)\b", text, re.I)
    if m: return f"TP{m.group(1)}"
    m = re.search(r"\bperiod\s*(\d+)\b", text, re.I)
    if m: return f"TP{m.group(1)}"
    if re.search(r"\boltp\b", text, re.I): return "OLTP"
    if re.search(r"\bolep\b", text, re.I): return "OLEP"
    if re.search(r"\b(?:ltep|lte)\b", text, re.I): return "LTE"
    return None

def _base_title(title: str) -> str:
    text = " ".join(str(title or "").split()).casefold()
    text = re.sub(r"\((?:tp\s*\d+|lte|olep|oltp|randomized[^)]*)\)", " ", text)
    text = re.sub(r"^(?:treatment\s+)?period\s*\d+\s*[:：]\s*", " ", text)
    text = re.sub(r"\b(?:oltp|olep|ltep|lte|tp\s*\d+)\b:?", " ", text)
    text = re.sub(r"\btp\s*(\d+)\b", " ", text)
    return " ".join(text.split())
@dataclass(frozen=True)
class _Entry:
    stat: str
    period: str | None
    base_title: str
    group_id: str
    title: str
    num_at_risk: float
@dataclass
class _Crosswalk:
    entries: tuple[_Entry, ...]
    conflicts: list[dict] = field(default_factory=list)
    def lookup(self, *, stat: str, period: str | None, title: str) -> float | None:
        if stat not in _VALID_STATS: return None
        base = _base_title(title)
        candidates = [e for e in self.entries if e.stat == stat and e.base_title == base]
        if not candidates:
            same_stat = [e for e in self.entries if e.stat == stat]
            if len(same_stat) == 1:
                e0 = same_stat[0]
                base_tokens = base.split()
                entry_tokens = set(e0.base_title.split())
                token_included = bool(base_tokens) and base_tokens[0] == e0.base_title.split()[0] and set(base_tokens) <= entry_tokens
                requested = normalize_period(period)
                period_ok = requested is None or e0.period == requested
                if token_included and period_ok and base and e0.base_title:
                    return e0.num_at_risk
            return None
        values = {e.num_at_risk for e in candidates}
        requested = normalize_period(period)
        if requested is not None:
            scoped = [e for e in candidates if e.period == requested]
            scoped_values = {e.num_at_risk for e in scoped}
            if len(scoped_values) == 1: return scoped.pop().num_at_risk
            if len(scoped_values) > 1:
                self.conflicts.append({"stat":stat,"period":requested,"base_title":base,"values":sorted(scoped_values),"reason":"period_scoped_conflict"})
                return None
            self.conflicts.append({"stat":stat,"period":requested,"base_title":base,"values":sorted({e.num_at_risk for e in candidates}),"reason":"requested_period_absent"})
            return None
        if len(values) == 1 and len({e.period for e in candidates}) == 1:
            return candidates[0].num_at_risk
        self.conflicts.append({"stat":stat,"period":period,"base_title":base,"values":sorted(values),"reason":"ambiguous_candidates"})
        return None

def build_atrisk_crosswalk(rows) -> _Crosswalk:
    entries = []
    for row in rows:
        stat = str(row.get("stat") or "").strip()
        risk = row.get("num_at_risk")
        if stat not in _VALID_STATS or risk is None: continue
        try: value = float(risk)
        except (TypeError, ValueError): continue
        if value < 0 or not math_isfinite(value): continue
        title = str(row.get("title") or "")
        entries.append(_Entry(stat=stat, period=normalize_period(row.get("period") or period_of(title)), base_title=_base_title(title), group_id=str(row.get("group_id") or ""), title=title,num_at_risk=value))
    return _Crosswalk(entries=tuple(entries))
def math_isfinite(value: float) -> bool:
    return value == value and value not in (float("inf"),float("-inf"))

# reports/c/endpoint_instances.py: matching/coverage behavior, unchanged.
class EndpointInstanceError(ValueError): pass
@dataclass(frozen=True)
class EndpointInstance:
    outcome_id: str
    role: str
    trial_id: str
    measure: str
    timepoint: str | None

def _family_of(observation) -> str:
    return str(getattr(observation,"field_family","") or "")
def build_endpoint_instances(observations) -> tuple[EndpointInstance,...]:
    measures, times = {}, {}
    for observation in observations:
        oid = getattr(observation,"outcome_id",None)
        if not oid: continue
        key = (str(observation.trial_id),str(oid))
        family = _family_of(observation)
        if family == "endpoint": measures.setdefault(key,[]).append(observation)
        elif family == "timepoint": times.setdefault(key,[]).append(observation)
    instances = []
    for (trial_id,oid),rows in measures.items():
        role = str(rows[0].endpoint_key or "")
        measure = "；".join(" ".join(str(row.source_text).split()) for row in rows)
        tp_rows = times.pop((trial_id,oid),[])
        timepoint = "；".join(" ".join(str(row.source_text).split()) for row in tp_rows if str(row.source_text or "").strip()) or None
        instances.append(EndpointInstance(outcome_id=oid,role=role,trial_id=trial_id,measure=measure,timepoint=timepoint))
    return tuple(instances)
def validate_endpoint_timepoint_pairs(observations, *, universe_trial_ids=None):
    endpoint_ids, timepoint_ids = {}, {}
    for observation in observations:
        family = _family_of(observation)
        if family not in {"endpoint","timepoint"}: continue
        oid = getattr(observation,"outcome_id",None)
        if not oid: raise EndpointInstanceError("missing outcome_id")
        trial_id = str(observation.trial_id)
        if family == "endpoint":
            text = " ".join(str(observation.source_text or "").split())
            seen = endpoint_ids.setdefault(trial_id,{})
            prior = seen.get(str(oid))
            if prior is not None and prior != text: raise EndpointInstanceError("conflicting definition")
            seen[str(oid)] = text
        elif family == "timepoint":
            if not str(observation.source_text or "").strip(): raise EndpointInstanceError("blank timepoint")
            timepoint_ids.setdefault(trial_id,set()).add(str(oid))
    instances = build_endpoint_instances(observations)
    problems = []
    for trial_id,ids in endpoint_ids.items():
        if universe_trial_ids is not None and trial_id not in universe_trial_ids: continue
        tps = timepoint_ids.get(trial_id,set())
        missing = sorted(set(ids)-tps)
        orphan = sorted(tps-set(ids))
        if missing: problems.append("missing timepoints")
        if orphan: problems.append("orphan timepoints")
    for trial_id,tps in timepoint_ids.items():
        if universe_trial_ids is not None and trial_id not in universe_trial_ids: continue
        if not endpoint_ids.get(trial_id): problems.append("orphan trial")
    if problems: raise EndpointInstanceError(";".join(problems))
    return instances
