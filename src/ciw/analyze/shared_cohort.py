"""Shared-cohort display deduplication requires an explicit pooled statement and study IDs."""
from __future__ import annotations

import json
import re

_PROVENANCE = {"result_id", "trial_id", "acronym", "source_id", "path", "url", "phase"}


def collapse_shared(rows, results, trials):
    by_result = {r.result_id: r for r in results}
    out, seen = [], {}
    for row in rows:
        result = by_result[row["result_id"]]
        text = result.title + " " + result.population
        cohort = []
        if re.search(r"\bpooled\b|合并(?:人群|队列|分析)", text, re.I):
            for tid, trial in trials.items():
                ids = {tid, *trial.ids.values()}
                if any(len(value) >= 4 and re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", text, re.I)
                       for value in ids):
                    cohort.append(tid)
        if len(cohort) < 2 or row["trial_id"] not in cohort:
            out.append(row)
            continue
        key = tuple(sorted(cohort)), json.dumps({k: v for k, v in row.items() if k not in _PROVENANCE},
                                                 ensure_ascii=False, sort_keys=True)
        source = {k: row.get(k) for k in _PROVENANCE}
        if key not in seen:
            item = dict(row, source_records=[source])
            seen[key] = item
            out.append(item)
        else:
            item = seen[key]
            item["source_records"].append(source)
            ids = sorted({s["trial_id"] for s in item["source_records"]})
            item["acronym"] = "合并分析 · " + " / ".join(
                trials[tid].acronym or trials[tid].ids.get("org") or tid for tid in ids)
    return out
