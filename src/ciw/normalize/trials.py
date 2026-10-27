"""Unify explicit registry identifiers; never infer identity from names or array order."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from ciw.models import Trial


def registry_ids(text: str, registry: str) -> list[str]:
    prefix = {"ctgov": "NCT", "cde": "CTR"}[registry]
    return sorted(set(re.findall(rf"(?<![A-Z0-9]){prefix}[0-9]{{8}}(?![A-Z0-9])", text.upper())))


def deduplicate_trials(trials: list[Trial]) -> tuple[list[Trial], list[dict[str, Any]]]:
    current = {t.trial_id: t.model_copy(deep=True) for t in trials}
    references: dict[str, set[str]] = defaultdict(set)
    for t in trials:
        if t.registry == "ctgov":
            for ctr in registry_ids(t.ids.get("ctr", ""), "cde"):
                references[ctr].add(t.trial_id)
    issues = []
    for t in sorted(trials, key=lambda item: item.trial_id):
        if t.registry != "cde":
            continue
        targets = references[t.trial_id] | set(registry_ids(t.ids.get("nct", ""), "ctgov"))
        if not targets:
            continue
        primary = current.get(next(iter(targets))) if len(targets) == 1 else None
        mismatch = (
            primary and t.product_ids and primary.product_ids and not set(t.product_ids) & set(primary.product_ids)
        )
        if primary is None or primary.registry != "ctgov" or mismatch:
            issues.append(
                {
                    "kind": "registry_link_conflict",
                    "ref": t.trial_id,
                    "trials": sorted(targets),
                    "note": "登记号关联未唯一匹配当前研究或产品，原记录分别保留",
                }
            )
            continue
        primary.registrations.append(t.model_copy(deep=True))
        ids = registry_ids(primary.ids.get("ctr", ""), "cde") + [t.trial_id]
        primary.ids["ctr"] = ";".join(sorted(set(ids)))
        del current[t.trial_id]
    return [current[key] for key in sorted(current)], issues
