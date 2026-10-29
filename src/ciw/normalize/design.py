"""Shared source design fields, source roles and threshold markup; no rendering or inference."""
import re

_THRESHOLD = re.compile(
    r"(?:>=|<=|≥|≤|>|<|至少|不低于|不超过|大于|小于|不少于|不大于|at least|at most|"
    r"greater than(?: or equal to)?|less than(?: or equal to)?)\s*\d+(?:\.\d+)?"
    r"(?:\s*(?:%|points?\b|分|岁|years?\b|mg(?:/dL)?\b|g/L\b|mL/min\b))?"
    r"|\d+(?:\.\d+)?\s*(?:or (?:more|greater|less)|及以上|及以下)"
    r"|\bbetween\s+\d+(?:\.\d+)?\s+and\s+\d+(?:\.\d+)?"
    r"|(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*(?:–|—|-|to|至)\s*\d+(?:\.\d+)?\s*"
    r"(?:years?|months?|weeks?|days?|points?|岁|分|mL/min|mg/dL|g/24\s*h|g/L|g/g|RU/mL|%)(?![A-Za-z])",
    re.I,
)


def threshold_spans(text: str) -> list[dict]:
    return [{"start": m.start(), "end": m.end()} for m in _THRESHOLD.finditer(text)]


def _criterion_role(text, excerpt):
    roles = set()
    pattern = r"inclusion(?: criteria)?|exclusion(?: criteria)?|入选(?:标准)?|排除(?:标准)?"
    for occurrence in re.finditer(re.escape(excerpt), text):
        headings = list(re.finditer(pattern, text[:occurrence.end()], re.I))
        roles.add(("exclusion" if re.search(r"exclusion|排除", headings[-1][0], re.I) else "inclusion")
                  if headings else "unspecified")
    return next(iter(roles)) if len(roles) == 1 else "unspecified"


def design_passages(trial):
    """One shared inventory of original design fields for indexing and source checking."""
    passages = [("入排标准", trial.design.eligibility_text, "eligibility")]
    passages += [
        ("研究摘要", trial.design.brief_summary, "brief_summary"),
        ("研究描述", trial.design.detailed_description, "detailed_description"),
        ("设计描述", trial.design.model_description, "model_description"),
    ]
    passages += [(a.label, a.description, f"arm:{a.arm_id}") for a in trial.arms]
    passages += [("背景治疗", value, f"background:{i}") for i, value in enumerate(trial.design.background_therapy)]
    passages += [(o.title, o.description, f"outcome:{i}") for i, o in enumerate(trial.outcomes_planned)]
    passages += [("终点名称", o.title, f"outcome:{i}:title") for i, o in enumerate(trial.outcomes_planned)]
    passages += [("终点时点", o.timeframe, f"outcome:{i}:timeframe") for i, o in enumerate(trial.outcomes_planned)]
    return passages


def topic_catalog(topics):
    return [dict(topic_id=f"design-topic-{i}", label=t.label.replace("入组阈值", "入排阈值"),
                 kind=t.kind, aliases=t.aliases)
            for i, t in enumerate(topics)]


def topic_field_matches(kind, field):
    if kind == "eligibility_threshold":
        return field == "eligibility"
    if kind == "endpoint_definition":
        return bool(re.fullmatch(r"outcome:\d+", field))
    if kind in {"treatment_duration", "dosing_regimen", "background_therapy", "follow_up"}:
        return field not in {"eligibility"} and not field.startswith("outcome:")
    return True


LOGICAL_PARENT = re.compile(r"[^.;\n]*(?:\ball\b|\bany\b|\bone\b|\bfollowing\b|全部|任一|以下)[^.;\n]*[:：]", re.I)
_SECTION = re.compile(r"^\s*(?:inclusion(?: criteria)?|exclusion(?: criteria)?|"
                      r"入选(?:标准)?|排除(?:标准)?)\s*[:：]", re.I | re.M)


def logical_contexts(text, excerpt):
    """Keep a literal preceding list introducer, including when the children occupy new lines."""
    contexts = []
    for occurrence in re.finditer(re.escape(excerpt), text):
        before = text[:occurrence.end()]
        parents = list(LOGICAL_PARENT.finditer(before))
        headings = list(_SECTION.finditer(before))
        if not parents or (headings and parents[-1].start() < headings[-1].end()):
            continue
        parent = parents[-1]
        end = text.find("\n", occurrence.end())
        contexts.append(dict(condition=parent[0], context=text[parent.start():end if end >= 0 else len(text)]))
    return contexts
