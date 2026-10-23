"""Literal label identity only; pharmacological equivalence needs separate source evidence."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

CODE_HASH = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
CONTROL_LABELS = frozenset({'placebo', '安慰剂'})


def name_key(name: str | None) -> str:
    return ' '.join((name or '').split()).casefold()


def research_aliases(names: list[str | None]) -> list[str]:
    """Apply the existing exact control-label exclusion to aliases, not source text."""
    return [name for name in names if isinstance(name, str) and name_key(name)
            and name_key(name) not in CONTROL_LABELS]


def literal_names(entity: dict[str, Any]) -> set[str]:
    return {name_key(name) for name in [entity['name'], entity.get('name_zh'), *research_aliases(entity.get('aliases', []))]
            if name_key(name)}


def name_owners(entities: list[dict[str, Any]]) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = {}
    for entity in entities:
        for name in literal_names(entity):
            owners.setdefault(name, set()).add(entity['id'])
    return owners


def possible_trial_relation(drug: dict[str, Any], interventions: list[dict[str, Any]]) -> bool:
    """Retain broad discovery hits as pending edges, never as scientific identity.

    Includes the former substring heuristic for recall/recovery only. Exact short
    names and ambiguous aliases are also retained rather than silently dropped.
    """
    labels = {name_key(n) for iv in interventions for n in [iv.get('name'), *(iv.get('other_names') or [])]
              if name_key(n)}
    names = literal_names(drug)
    if names & labels:
        return True
    def compact(text: str) -> str:
        return re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '', text)

    keys = {compact(name) for name in names if len(compact(name)) >= 4}
    return any(key in compact(label) for key in keys for label in labels)
