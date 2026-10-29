"""Topic-indexed verbatim design clauses; thresholds are highlighted, never inferred."""

import re

from ciw.normalize.design import (
    _criterion_role,
    logical_contexts,
    topic_field_matches,
)
from ciw.normalize.design import (
    design_passages as design_passages,
)
from ciw.normalize.design import (
    threshold_spans as threshold_spans,
)
from ciw.normalize.design import (
    topic_catalog as topic_catalog,
)

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


def _clauses(text, preserve_lists=False):
    for line in text.splitlines():
        # Keep an introduced logical list intact; its AND/OR must stay in the primary excerpt.
        if preserve_lists and re.search(r"[:：][^\n]*[;；]", line):
            yield line, line
            continue
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z一-鿿])|(?<=[。！？])|(?<=[;；])\s*", line):
            if sentence.strip():
                yield sentence, line


def _metric_match(patterns, text):
    return any((not (match.start() and text[match.start()].isalnum() and text[match.start()-1].isalnum())
                and not (match.end() < len(text) and text[match.end()-1].isalnum() and text[match.end()].isalnum()))
               for pattern in patterns for match in pattern.finditer(text) if match.start() < match.end())


def _matching_lines(topic, patterns, text, field, section=""):
    if not topic_field_matches(topic.kind, field):
        return []
    if topic.kind == "treatment_duration":
        return [(clause, context) for clause, context in _clauses(text)
                if _DURATION.search(clause) and not (_POSTDOSE.search(clause) or _FOLLOWUP.search(clause))]
    excludes = [re.compile(p, re.I) for p in topic.exclude]
    if topic.kind == "endpoint_definition" and text and any(p.search(section) for p in patterns):
        patterns = [*patterns, re.compile(re.escape(text), re.I)]
    # Preserve historical combined lookup topics; typed topics select precise clauses instead of paragraphs.
    clauses = (((line, line) for line in text.splitlines()) if topic.kind == "lookup" else
               _clauses(text, preserve_lists=topic.kind in {"eligibility_threshold", "endpoint_definition"}))
    selected = []
    for clause, context in clauses:
        if not clause.strip() or not any(p.search(clause) for p in patterns) or any(p.search(clause) for p in excludes):
            continue
        if (topic.kind == "eligibility_threshold" and
                (not threshold_spans(clause) or not _metric_match(patterns, clause))):
            continue
        if topic.kind == "background_therapy" and re.search(r"rescue|non[- ]?respon|救援|无应答", clause, re.I):
            prefix = re.split(r",\s+and\s+", clause, maxsplit=1, flags=re.I)[0]
            if (prefix == clause or not any(p.search(prefix) for p in patterns)
                    or re.search(r"rescue|non[- ]?respon|救援|无应答", prefix, re.I)):
                continue
            clause = prefix
        selected.append((clause, context))
    return selected


def design_search_text(trial, topics):
    """Search aliases index source mentions, including mentions without a numeric cutoff."""
    terms = []
    for topic in topics:
        patterns = [re.compile(p, re.I) for p in [*topic.patterns, *topic.metric_patterns]]
        if any(topic_field_matches(topic.kind, field) and any(p.search(text) for p in patterns)
               for _, text, field in design_passages(trial)):
            terms.extend([topic.label, *topic.aliases])
    return " ".join(dict.fromkeys(terms))


def design_excerpts(trial, topics) -> list[dict]:
    """Keep the complete matching line, source identity, and its original section."""
    passages = design_passages(trial)
    found = []
    for i, topic in enumerate(topics):
        patterns = [re.compile(p, re.I) for p in [*topic.patterns, *topic.metric_patterns]]
        snippets, seen = [], set()
        for section, text, field in passages:
            for line, context in _matching_lines(topic, patterns, text, field, section):
                identity = (field, line)
                if identity in seen:
                    continue
                seen.add(identity)
                parents = logical_contexts(text, line) if field == "eligibility" else []
                if parents:
                    context = parents[0]["context"]
                timing = {}
                if re.fullmatch(r"outcome:\d+", field):
                    timing = dict(timeframe=trial.outcomes_planned[int(field.split(":")[1])].timeframe,
                                  timeframe_field=field + ":timeframe")
                snippets.append(
                    {
                        "section": section,
                        "text": line,
                        "marks": threshold_spans(line),
                        "source_id": trial.locator.source_id,
                        "field": field,
                        **timing,
                        **({"condition": parents[0]["condition"],
                            "condition_marks": threshold_spans(parents[0]["condition"])} if parents else {}),
                        **({"criterion_role": _criterion_role(text, line)} if field == "eligibility" else {}),
                        **({"context": context, "context_marks": threshold_spans(context)} if context != line else {}),
                    }
                )
        if snippets:
            found.append({"topic_id": f"design-topic-{i}", "label": topic.label,
                          "aliases": topic.aliases, "snippets": snippets})
    return found
