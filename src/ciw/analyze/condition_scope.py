"""Source-condition scope: select groups without splitting N or altering original observations."""
from __future__ import annotations

import re

_SCOPE_LABELS = {"target": "本次适应症", "other": "其他登记疾病", "mixed": "多个登记疾病", "unresolved": "原登记队列"}


def study_scope(cfg, trial):
    target, other = [], []
    names = {" ".join(name.casefold().split()) for name in
             [cfg.name_en, cfg.name_zh, cfg.abbr, *cfg.ctgov.conditions] if name}
    for condition in trial.conditions:
        matched = (" ".join(condition.casefold().split()) in names or
                   any(re.fullmatch(p, condition.strip(), re.I) for p in cfg.ctgov.relevance_patterns))
        (target if matched and cfg.is_relevant_text(condition) else other).append(condition)
    return dict(multiple_conditions=bool(other and len(set(trial.conditions)) > 1),
                target_conditions=target, other_conditions=other)


def _text_scope(cfg, scope, text):
    if not cfg.is_relevant_text(text) and any(re.search(pattern, text, re.I)
                                            for pattern in cfg.ctgov.relevance_exclude_patterns):
        return "other"
    targets = [match.span() for pattern in cfg.ctgov.relevance_patterns
               for match in re.finditer(pattern, text, re.I)] if cfg.is_relevant_text(text) else []
    if any(re.search(r"\bwith\s+(?:or|and)\s+without\s*$|伴或不伴(?:有)?\s*$", text[:start], re.I)
           for start, _ in targets):
        return "mixed"
    others = [match.span() for condition in scope["other_conditions"] if condition.strip()
              for match in re.finditer(r"(?<!\w)" + re.escape(condition.strip()) + r"(?!\w)", text, re.I)]
    # An explicit longer name wins over a substring: Primary X vs X, or Secondary X vs X.
    foreign = [span for span in others if not any(a <= span[0] and span[1] <= b for a, b in targets)]
    target = any(not any(a <= start and end <= b for a, b in foreign) for start, end in targets)
    # Mentioning two conditions cannot distinguish separate cohorts from co-morbidity.
    return "unresolved" if target and foreign else "target" if target else "other" if foreign else "unresolved"


def _labeled(scope, status):
    return {**scope, "status": status, "label": _SCOPE_LABELS[status]}


def text_scope(cfg, trial, text):
    scope = study_scope(cfg, trial)
    clear = not trial.conditions or (scope["target_conditions"] and not scope["other_conditions"])
    status = _text_scope(cfg, scope, text)
    return _labeled(scope, "target" if clear and status == "unresolved" else status)


def group_scopes(cfg, trial, result):
    scope = study_scope(cfg, trial)
    statuses = {group.group_id: _text_scope(cfg, scope, group.title) for group in result.groups}
    population = _text_scope(cfg, scope, result.population)
    clear = not trial.conditions or bool(scope["target_conditions"] and not scope["other_conditions"])
    fallback = "target" if clear else population
    if fallback == "target" and "other" not in statuses.values():
        statuses = {key: "target" if value == "unresolved" else value for key, value in statuses.items()}
    elif not statuses or all(status == "unresolved" for status in statuses.values()):
        if fallback == "unresolved":
            fallback = _text_scope(cfg, scope, "\n".join([result.title, result.description,
                result.class_title, result.category_title, result.subgroup]))
        statuses = dict.fromkeys(statuses, fallback)
    elif population == "other":
        statuses = {key: "unresolved" if value == "target" else value for key, value in statuses.items()}
    return {key: _labeled(scope, value) for key, value in statuses.items()}


def result_scope(cfg, trial, result):
    scopes = list(group_scopes(cfg, trial, result).values())
    statuses = {scope["status"] for scope in scopes}
    if not statuses:
        return text_scope(cfg, trial, result.population or result.title)
    status = next(iter(statuses)) if len(statuses) == 1 else "mixed"
    return _labeled(study_scope(cfg, trial), status)


def target_results(cfg, trials, results):
    selected = []
    for result in results:
        trial = trials.get(result.trial_id)
        if trial is None or trial.relevance != "core":
            continue
        scopes = group_scopes(cfg, trial, result)
        if not result.groups and result_scope(cfg, trial, result)["status"] == "target":
            selected.append(result.model_copy())
            continue
        groups = [group for group in result.groups if scopes[group.group_id]["status"] == "target"]
        ids = {group.group_id for group in groups}
        if groups:
            selected.append(result.model_copy(update={"groups": groups, "analyses": [analysis
                for analysis in result.analyses if set(analysis.group_ids) <= ids
                and (analysis.group_ids or len(groups) == len(result.groups))]}))
    return selected
