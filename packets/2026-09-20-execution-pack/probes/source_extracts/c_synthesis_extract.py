"""Transcribed source functions, not a full repository checkout.
Source: src/ci_workflow/reports/c/synthesis.py @ d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca.
Git blob (full original file): 6acda72435bac04e10db881111b1878693eb9b73.
"""
from __future__ import annotations
import unicodedata


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    punctuation_folded = "".join(
        " " if unicodedata.category(character).startswith("P") else character
        for character in normalized
    )
    return " ".join(punctuation_folded.casefold().split())


def _compact_clause(text: str, *, limit: int = 48) -> str:
    normalized = _normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"
