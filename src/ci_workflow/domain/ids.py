from __future__ import annotations

import hashlib
import re
import unicodedata

_KIND_PATTERN = re.compile(r"[a-z][a-z0-9-]*")


def _normalize_identity_part(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("稳定标识的身份材料必须是非空文本")
    normalized = unicodedata.normalize("NFKC", value).strip()
    return " ".join(normalized.split())


def stable_id(kind: str, *identity_parts: str) -> str:
    """由命名空间和规范化身份材料生成稳定、可读前缀的标识。"""

    normalized_kind = _normalize_identity_part(kind).casefold()
    if not _KIND_PATTERN.fullmatch(normalized_kind):
        raise ValueError("标识类型不能为空，且只能包含小写字母、数字和连字符")
    if not identity_parts:
        raise ValueError("稳定标识的身份材料不能为空")
    normalized_parts = tuple(_normalize_identity_part(part) for part in identity_parts)
    if any(not part for part in normalized_parts):
        raise ValueError("稳定标识的身份材料不能为空")
    payload = "\x1f".join((normalized_kind, *normalized_parts)).encode("utf-8")
    return f"{normalized_kind}_{hashlib.sha256(payload).hexdigest()[:24]}"
