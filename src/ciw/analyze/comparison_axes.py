"""Project verified measurement axes into shared charts; all source rows and strata remain distinct."""
from __future__ import annotations

import hashlib
from collections import Counter
from copy import deepcopy

from ciw.normalize.comparison_axes import context_id, numeric_guard


def _mapping(groups):
    counts = Counter(cid for group in groups for cid in group["member_ids"])
    return {cid: group for group in groups for cid in group["member_ids"]
            if all(counts[c] == 1 for c in group["member_ids"])}


def _selection(ids, results, mapping):
    if not ids or any(rid not in results for rid in ids):
        return None
    contexts = {context_id(results[rid]) for rid in ids}
    if any(cid not in mapping for cid in contexts):
        return None
    groups = [mapping[cid] for cid in contexts]
    guards = {numeric_guard(results[rid]) for rid in ids}
    if len({g["axis_id"] for g in groups}) != 1 or len(guards) != 1:
        return None
    return groups[0], next(iter(guards))


def _row(row, results, group):
    result = results[row["result_id"]]
    return {**row, "population": result.population, "analysis_set": group["analysis_set"],
            "stratum_label": group["stratum_labels"][context_id(result)]}


def _join_frames(question, results, mapping):
    combined, untouched = {}, []
    for original in question.get("frames", []):
        selection = _selection(original.get("result_ids"), results, mapping)
        if not selection:
            untouched.append(deepcopy(original))
            continue
        group, guard = selection
        times = {results[rid].time.key if results[rid].time else None for rid in original["result_ids"]}
        if len(times) != 1 or None in times:
            untouched.append(deepcopy(original))
            continue
        key = (group["axis_id"], next(iter(times)), guard)
        if key not in combined:
            combined[key] = {**deepcopy(original),
                "frame_id": "matched_" + hashlib.sha256(repr(key).encode()).hexdigest()[:20],
                "axis_id": group["axis_id"], "context_label": group["axis_label"],
                "analysis_set": group["analysis_set"], "units": [guard[3]],
                "rows": [], "comparisons": [], "source_statistics": [], "result_ids": [],
                "trial_ids": [], "source_contexts": []}
        target = combined[key]
        target["trial_ids"] = sorted(set(target["trial_ids"]) | set(original["trial_ids"]))
        target["result_ids"].extend(original["result_ids"])
        target["source_contexts"].extend(deepcopy(original.get("source_contexts") or [{
            k: original.get(k) for k in ("title", "description", "population", "trial_ids", "result_ids")}]))
        for name in ("rows", "comparisons", "source_statistics"):
            target[name].extend(_row(row, results, group) for row in original.get(name, []))
    return sorted([*combined.values(), *untouched],
                  key=lambda f: (-len(f["trial_ids"]), f.get("weeks") or float("inf"), f["frame_id"]))


def _join_longitudinal(charts, results, mapping):
    merged, untouched = {}, []
    for chart in charts:
        ids = {pt["result_id"] for line in chart["lines"] for pt in line["points"]}
        selection = _selection(ids, results, mapping)
        if not selection:
            untouched.append(deepcopy(chart))
            continue
        group, guard = selection
        key = group["axis_id"], guard
        if key not in merged:
            merged[key] = {**deepcopy(chart), "chart_id": "matched_line_" + hashlib.sha256(
                repr(key).encode()).hexdigest()[:20], "axis_id": group["axis_id"],
                "label": group["axis_label"], "unit": guard[3], "lines": []}
        for line in chart["lines"]:
            own_ids = {pt["result_id"] for pt in line["points"]}
            strata = {group["stratum_labels"][context_id(results[rid])] for rid in own_ids}
            if len(strata) != 1:
                # Do not silently label a mixed-stratum curve as a single population.
                untouched.append({**deepcopy(chart), "lines": [deepcopy(line)]})
            else:
                merged[key]["lines"].append({**deepcopy(line), "analysis_set": group["analysis_set"],
                                            "stratum_label": next(iter(strata))})
    return sorted([*[c for c in merged.values() if c["lines"]], *untouched], key=lambda c: -len(c["lines"]))


def project_comparison_axes(body, groups, results):
    if not groups:
        return body
    mapping, by_id = _mapping(groups), {r.result_id: r for r in results}
    questions = []
    for original in body["questions"]:
        q = {**original, "frames": _join_frames(original, by_id, mapping)}
        q["rows"] = [r for f in q["frames"] for r in f["rows"]]
        q["comparisons"] = [r for f in q["frames"] for r in f["comparisons"]]
        questions.append(q)
    return {**body, "questions": questions,
            "longitudinal": _join_longitudinal(body["longitudinal"], by_id, mapping)}

