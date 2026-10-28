"""Topic-indexed verbatim design clauses; thresholds are highlighted, never inferred."""

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


_DURATION = re.compile(
    r"\b(?:treatment duration|duration of (?:study )?treatment|treatment period)\b.{0,80}?"
    r"(?:\b\d+\s*(?:days?|weeks?|months?|years?)\b|\b(?:day|week|month)\s*\d+)"
    r"|\b(?:will (?:be (?:administered|treated)|receive)|administered|treated)\b.{0,140}?"
    r"\b(?:for|through|until|over|up to)\s+(?:a total of )?"
    r"(?:\d+\s*(?:days?|weeks?|months?|years?)\b|(?:day|week|month)\s*\d+)"
    r"|\b\d+[- ]+(?:days?|weeks?|months?|years?)\s+(?:treatment period|treatment|of drug exposure)\b"
    r"|(?:治疗|给药).{0,20}(?:持续|共|至)\s*\d+\s*(?:天|周|月|年)", re.I)
_POSTDOSE = re.compile(
    r"contracept|pregnan|after.{0,30}(?:last|final) dose|previously treated|prior treatment|"
    r"末次.{0,15}(?:避孕|妊娠)|既往治疗", re.I)


_FOLLOWUP = re.compile(r"follow[- ]?up|\bfollowed\b|monitoring|assessment visits?|随访|观察期", re.I)


def _matching_lines(topic, patterns, text, field):
    if topic.kind == "treatment_duration":
        if field == "eligibility" or field.startswith("outcome:"):
            return []
        selected = []
        for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
            for clause in re.split(r"(?<=;)\s+", sentence):
                if _DURATION.search(clause) and not (_POSTDOSE.search(clause) or _FOLLOWUP.search(clause)):
                    selected.append((clause, sentence))
        return selected
    if topic.kind == "eligibility_threshold" and field != "eligibility":
        return []
    if topic.kind == "endpoint_definition" and not field.startswith("outcome:"):
        return []
    excludes = [re.compile(p, re.I) for p in topic.exclude]
    return [(line, line) for line in text.splitlines()
            if line.strip() and any(p.search(line) for p in patterns) and not any(p.search(line) for p in excludes)
            and (topic.kind != "eligibility_threshold" or threshold_spans(line))]


def design_excerpts(trial, topics) -> list[dict]:
    """Keep the complete matching line, source identity, and its original section."""
    passages = [("入排标准", trial.design.eligibility_text, "eligibility")]
    passages += [
        ("研究摘要", trial.design.brief_summary, "brief_summary"),
        ("研究描述", trial.design.detailed_description, "detailed_description"),
        ("设计描述", trial.design.model_description, "model_description"),
    ]
    passages += [(a.label, a.description, f"arm:{a.arm_id}") for a in trial.arms]
    passages += [(o.title, o.description, f"outcome:{i}") for i, o in enumerate(trial.outcomes_planned)]
    found = []
    for topic in topics:
        patterns = [re.compile(p, re.I) for p in topic.patterns]
        snippets, seen = [], set()
        for section, text, field in passages:
            for line, context in _matching_lines(topic, patterns, text, field):
                identity = (field, line)
                if identity in seen:
                    continue
                seen.add(identity)
                snippets.append(
                    {
                        "section": section,
                        "text": line,
                        "marks": threshold_spans(line),
                        "source_id": trial.locator.source_id,
                        "field": field,
                        **({"context": context, "context_marks": threshold_spans(context)} if context != line else {}),
                    }
                )
        if snippets:
            found.append({"label": topic.label, "snippets": snippets})
    return found
