"""Literal source-condition scope for mixed registrations; never infer cohort membership or split N."""
from __future__ import annotations

import re


def study_scope(cfg, trial):
    target, other = [], []
    for condition in trial.conditions:
        (target if cfg.is_relevant_text(condition) else other).append(condition)
    # Multiple nonmatching registry conditions can denote multiple cohorts or co-morbidities.
    # Their relationship is not inferred. The entire registration remains available.
    multiple = bool(other and len(set(trial.conditions)) > 1)
    return dict(multiple_conditions=multiple, target_conditions=target, other_conditions=other)


def _literal_present(phrase, text):
    pattern = r"(?<!\w)" + re.escape(phrase.strip()) + r"(?!\w)"
    return bool(phrase.strip() and re.search(pattern, text, re.I))


def _text_scope(cfg, scope, text):
    target = cfg.is_relevant_text(text)
    # A broad registry name inside an explicit target name is not a second population.
    remainder = text
    for pattern in cfg.ctgov.relevance_patterns:
        remainder = re.sub(pattern, "", remainder, flags=re.I)
    foreign = any(_literal_present(condition, remainder) for condition in scope["other_conditions"])
    return "mixed" if target and foreign else "target" if target else "other" if foreign else "unresolved"


def text_scope(cfg, trial, text):
    scope = study_scope(cfg, trial)
    return {**scope, "status": _text_scope(cfg, scope, text) if scope["multiple_conditions"] else "target"}


def result_scope(cfg, trial, result):
    scope = study_scope(cfg, trial)
    if not scope["multiple_conditions"]:
        return {**scope, "status": "target"}
    # Explicit analysis population outranks study-wide endpoint background.
    status = _text_scope(cfg, scope, result.population)
    if status == "unresolved":
        status = _text_scope(cfg, scope, "\n".join([result.title, result.description,
            result.class_title, result.category_title, result.subgroup, *(g.title for g in result.groups)]))
    return {**scope, "status": status}


def target_results(cfg, trials, results):
    return [result for result in results if (trial := trials.get(result.trial_id))
            and trial.relevance == "core" and result_scope(cfg, trial, result)["status"] == "target"]
