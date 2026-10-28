"""Conservative source contexts inside a clinical question, without inferring medical equivalence."""
from __future__ import annotations

import re

from ciw.config import ConceptCfg
from ciw.models import OutcomeResult

_TIME = re.compile(r"\b(?:weeks?|days?|months?)\s*\d+(?:\.\d+)?|\b\d+(?:\.\d+)?\s*(?:weeks?|days?|months?)\b", re.I)
_WORDING = re.compile(
    r"\b(?:number|percentage|percent|proportion|of|participants?|patients?|subjects?|with|who|were|are|"
    r"achiev(?:e|ed|ing)|at|the|as|per)\b", re.I)


def _text(value):
    return " ".join(value.casefold().split())


def endpoint_context(result: OutcomeResult, concept: ConceptCfg) -> tuple[str, str, str]:
    title = result.title
    # Only literal terms can be elided as lexical aliases. Wildcards must not erase clinical qualifiers.
    for pattern in concept.patterns:
        if re.search(r"[.*+?{}|()\\]", pattern):
            continue
        title = re.sub(pattern, " ", title, flags=re.I)
    title = _WORDING.sub(" ", _TIME.sub(" ", title))
    title = re.sub(r"[^\w<>%=.+/-]+", " ", title, flags=re.UNICODE).strip()
    # Silence is not a shared analysis context. Keep missing context local to the
    # original source measure; repeated time classes in that measure can still form a line.
    measure = f"{result.trial_id}:{result.outcome_index}:{result.locator.source_id}"
    population = _text(result.population) or "unknown-population:" + measure
    definition = _text(result.description) or "unknown-definition:" + measure
    return _text(title), population, definition


def context_display_label(result: OutcomeResult) -> str:
    """Compact lexical labels only; raw definitions remain available and matching does not use these labels."""
    labels = []
    for pattern, label in (
        (r"\bglobal definition\b", "Global定义"), (r"\bUS definition\b", "US定义"),
        (r"\bdurable\b|\bsustained\b", "持续结局"),
        (r"\bsteroid[- ]free\b|without (?:the use of )?corticosteroids", "无激素结局"),
    ):
        if re.search(pattern, result.title, re.I):
            labels.append(label)
    if result.subgroup:
        labels.append("条件人群")
    return " · ".join(labels) or "原文定义"
