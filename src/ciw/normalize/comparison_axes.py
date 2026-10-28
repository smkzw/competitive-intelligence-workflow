"""Source-context identities and exact unit aliases; no value conversion."""
from __future__ import annotations

import hashlib
import json

from ciw.normalize.comparison_context import _cfb, _pct, _unit_key

_UNIT_ALIASES = {"grams per deciliter": "g/dL", "gram per deciliter": "g/dL",
                 "grams/deciliter": "g/dL", "units on a scale": "scale points",
                 "score on a scale": "scale points", "points": "scale points",
                 "point": "scale points", "percent": "%"}


def canonical_unit(unit):
    return _UNIT_ALIASES.get(" ".join(unit.casefold().split()), _unit_key(unit))


def context_id(result):
    fields = (result.trial_id, result.locator.source_id, result.outcome_index, result.title,
              result.description, result.population, result.unit, result.measure_kind,
              result.subgroup, result.category_title, _cfb(result), _pct(result))
    return "context_" + hashlib.sha256(repr(fields).encode()).hexdigest()[:20]


def numeric_guard(result):
    return (result.measure_kind, _cfb(result), _pct(result), canonical_unit(result.unit),
            result.subgroup, result.category_title)


def context_catalog(results, trials, families, concepts=()):
    mapping = {cid: g["family_id"] for g in families for cid in g["member_ids"]}
    directions = {c.id: c.direction for c in concepts}
    catalog = {}
    for r in results:
        t = trials.get(r.trial_id)
        if (not t or t.relevance != "core" or r.domain != "efficacy" or not r.concept_id
                or not r.description.strip() or not r.population.strip() or not r.unit.strip()):
            continue
        key = context_id(r)
        fields = [t.title, r.title, r.description, r.population]
        catalog.setdefault(key, dict(trial_id=r.trial_id, source_id=r.locator.source_id,
            path=r.locator.path, outcome_index=r.outcome_index, title=r.title, fields=fields,
            material="\n".join(fields), guard=numeric_guard(r),
            direction=directions.get(r.concept_id, "none"), family_id=mapping.get(r.concept_id, r.concept_id)))
    return catalog


def material_text(catalog):
    return "\n\n".join("Context:" + key + "\n" + json.dumps(value, ensure_ascii=False, sort_keys=True)
                         for key, value in sorted(catalog.items()))

