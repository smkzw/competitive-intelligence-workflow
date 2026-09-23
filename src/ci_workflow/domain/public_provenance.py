"""Public-only source projection; no acquisition or scientific decisions."""
import re
from ipaddress import ip_address
from urllib.parse import parse_qsl, unquote, urlsplit

from pydantic import BaseModel, ConfigDict, field_validator


def public_source_url(value: str) -> str | None:
    try:
        decoded = unquote(value)
        if any(ord(char) < 33 for char in decoded) or "\\" in decoded:
            return None
        parts = urlsplit(decoded)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return None
        if parts.username is not None or parts.password is not None:
            return None
        host = parts.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return None
        try:
            if not ip_address(host).is_global:
                return None
        except ValueError:
            if "." not in host or re.fullmatch(r"[0-9.]+", host):
                return None
        if parts.fragment or any(
            any(marker in key.lower() for marker in (
                "token", "key", "auth", "signature", "secret", "password", "credential",
            ))
            for key, _ in parse_qsl(parts.query)
        ):
            return None
        _ = parts.port
        return value
    except ValueError:
        return None


class PublicSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_version_id: str
    label: str
    url: str | None
    source_type: str
    published_at: str
    data_cutoff: str
    limitation: str

    @field_validator("label", "source_type", "limitation")
    @classmethod
    def _public_text(cls, value: str) -> str:
        if re.search(
            r"(?:file://|/(?:Users|home|private|tmp|var)/|[A-Za-z]:\\|"
            r"(?:token|password|secret|api_key)\s*[:=]|https?://[^\s]*@)",
            value, re.IGNORECASE,
        ):
            raise ValueError("公共来源文字包含不可公开的定位或凭据")
        return value

    @field_validator("url")
    @classmethod
    def _safe_url(cls, value: str | None) -> str | None:
        return None if value is None else public_source_url(value)


class PublicProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    evidence_snapshot_id: str
    report_data_digest: str
    sources: tuple[PublicSource, ...]


class PublicCalculationEvidence(BaseModel):
    """One snapshot-bound, source-backed calculation visible in a report."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    row_id: str
    derivation_id: str
    claim_version_id: str
    source_version_id: str
    numerator: int
    denominator: int
    numerator_quote: str
    denominator_quote: str
    numerator_field_path: str
    denominator_field_path: str
    value: float
    unit: str
    rule_id: str
    rule_version: str
