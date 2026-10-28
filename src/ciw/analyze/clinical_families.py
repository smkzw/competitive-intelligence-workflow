"""Project related studies together while preserving each existing numeric frame contract."""
from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from copy import deepcopy


def _frame_key(question, frame):
    return (frame["frame_id"], question["time_key"], question["measure_kind"],
            question.get("change_from_baseline"), question.get("percent_change"),
            question["subgroup"], question["category"], tuple(question["units"]), question["direction"])


def _frames(questions):
    frames = {}
    for q in questions:
        for original in q["frames"]:
            key = _frame_key(q, original)
            context = {k: original.get(k) for k in ("title", "description", "population", "trial_ids", "result_ids")}
            if key not in frames:
                frames[key] = {**deepcopy(original), "frame_id": "family-frame_" + hashlib.sha256(
                    repr(key).encode()).hexdigest()[:16], "source_contexts": [context],
                    **{k: q[k] for k in ("time_key", "time_label", "weeks", "measure_kind",
                                         "measure_label", "units", "direction", "category", "subgroup")}}
            else:
                target = frames[key]
                target["trial_ids"] = sorted(set(target["trial_ids"]) | set(original["trial_ids"]))
                for field in ("result_ids", "rows", "comparisons", "source_statistics"):
                    target[field].extend(deepcopy(original.get(field, [])))
                target["source_contexts"].append(context)
    return sorted(frames.values(), key=lambda f: (-len(f["trial_ids"]),
                  f["weeks"] if f["weeks"] is not None else float("inf"), f["time_key"], f["frame_id"]))


def project_clinical_families(body, groups):
    """Do not change facts or silently merge unknown contexts. Unassigned questions stay available."""
    counts = Counter(cid for group in groups for cid in group["member_ids"])
    groups = [g for g in groups if all(counts[cid] == 1 for cid in g["member_ids"])]
    if not groups:
        return body
    mapping = {cid: group for group in groups for cid in group["member_ids"]}
    buckets, untouched = defaultdict(list), []
    for question in body["questions"]:
        group = mapping.get(question["concept_id"])
        if group:
            buckets[group["family_id"]].append(question)
        else:
            untouched.append(question)
    families = []
    by_id = {g["family_id"]: g for g in groups}
    for family_id, questions in buckets.items():
        first, group = questions[0], by_id[family_id]
        frames = _frames(questions)
        families.append({**first, "question_id": family_id, "family_id": family_id, "is_family": True,
            "label": group["family_label"], "member_concept_ids": sorted({q["concept_id"] for q in questions}),
            "source_question_ids": [q["question_id"] for q in questions],
            "time_label": "", "time_key": "", "weeks": None,
            "trial_ids": sorted({tid for q in questions for tid in q["trial_ids"]}),
            "has_primary": any(q["has_primary"] for q in questions), "frames": frames,
            "rows": [r for f in frames for r in f["rows"]],
            "comparisons": [r for f in frames for r in f["comparisons"]]})
    return {**body, "questions": sorted(families + untouched,
        key=lambda q: (not q["has_primary"], -len(q["trial_ids"]), q["label"], q["question_id"]))}
