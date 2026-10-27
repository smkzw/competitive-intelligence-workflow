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
    # Preserve unknown population and endpoint definitions instead of treating silence as equality.
    return _text(title), _text(result.population), _text(result.description)
