"""Deterministic digests for the Task 10.1 acceptance catalog.

The case digest binds every declared case field except ``case_digest`` itself.
JSON objects are key-sorted and unordered declaration lists (reports, formats,
inputs by path) are normalized before compact, UTF-8 JSON encoding. Input file
digests remain byte-for-byte SHA-256 values.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize(item) for item in value]
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_case_payload(case: Mapping[str, Any]) -> dict[str, Any]:
    """Return the normalized case body used by ``compute_case_digest``."""

    payload = {key: value for key, value in case.items() if key != "case_digest"}
    for key in ("reports", "formats"):
        values = payload.get(key)
        if isinstance(values, Sequence) and not isinstance(values, (str, bytes, bytearray)):
            payload[key] = sorted(values)
    inputs = payload.get("inputs")
    if isinstance(inputs, Sequence) and not isinstance(inputs, (str, bytes, bytearray)):
        payload["inputs"] = sorted(
            inputs,
            key=lambda item: str(item.get("path", "")) if isinstance(item, Mapping) else "",
        )
    return cast(dict[str, Any], _normalize(payload))


def compute_case_digest(case: Mapping[str, Any]) -> str:
    """Compute a stable lower-case SHA-256 for a catalog case declaration."""

    return hashlib.sha256(_canonical_json(canonical_case_payload(case)).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """Compute a byte-level SHA-256 for one fixture file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
