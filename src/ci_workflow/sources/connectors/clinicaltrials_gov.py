from __future__ import annotations

import copy
import json
import re
from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id

_NCT_ID = re.compile(r"NCT[0-9]{8}")


def _offset_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("采集时间必须包含明确时区")
    return parsed


def _required(mapping: Mapping[str, Any], key: str, *, path: str) -> Any:
    if key not in mapping:
        raise ValueError(f"ClinicalTrials.gov 记录缺少字段：{path}.{key}")
    return mapping[key]


def _mapping(value: Any, *, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"ClinicalTrials.gov 字段必须是对象：{path}")
    return value


def _normalized_nct_id(value: Any) -> str:
    normalized = str(value).strip().upper()
    if _NCT_ID.fullmatch(normalized) is None:
        raise ValueError("ClinicalTrials.gov 记录缺少有效 NCT 号")
    return normalized


def _scientific_record_digest_input(study: Mapping[str, Any]) -> str:
    """Exclude the daily platform holder while retaining the scientific record."""
    scientific = copy.deepcopy(dict(study))
    derived = scientific.get("derivedSection")
    if isinstance(derived, dict):
        misc = derived.get("miscInfoModule")
        if isinstance(misc, dict):
            misc.pop("versionHolder", None)
    return json.dumps(scientific, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class ClinicalTrialsGovStudyVersion(BaseModel):
    """一个 NCT 来源身份下的不可变登记内容版本。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    nct_id: str
    source_study_id: str
    source_version_id: str
    title: str
    registry_posted_version_date: str
    platform_version_holder: str
    acquired_at: datetime
    record_url: str
    history_url: str
    raw_record_json: str

    @field_validator("acquired_at")
    @classmethod
    def _acquired_at_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("采集时间必须包含明确时区")
        return value

    @property
    def raw_record(self) -> dict[str, Any]:
        parsed = json.loads(self.raw_record_json)
        return dict(_mapping(parsed, path="stored ClinicalTrials.gov record"))

    @classmethod
    def from_api_record(
        cls, record: Mapping[str, Any], *, acquired_at: str
    ) -> ClinicalTrialsGovStudyVersion:
        protocol = _mapping(
            _required(record, "protocolSection", path="study"),
            path="study.protocolSection",
        )
        identification = _mapping(
            _required(protocol, "identificationModule", path="study.protocolSection"),
            path="study.protocolSection.identificationModule",
        )
        status = _mapping(
            _required(protocol, "statusModule", path="study.protocolSection"),
            path="study.protocolSection.statusModule",
        )
        last_update = _mapping(
            _required(
                status,
                "lastUpdatePostDateStruct",
                path="study.protocolSection.statusModule",
            ),
            path="study.protocolSection.statusModule.lastUpdatePostDateStruct",
        )
        derived = _mapping(
            _required(record, "derivedSection", path="study"),
            path="study.derivedSection",
        )
        misc = _mapping(
            _required(derived, "miscInfoModule", path="study.derivedSection"),
            path="study.derivedSection.miscInfoModule",
        )
        nct_id = _normalized_nct_id(_required(identification, "nctId", path="identificationModule"))
        title = str(
            identification.get("briefTitle")
            or identification.get("officialTitle")
            or nct_id
        ).strip()
        if not title:
            raise ValueError("ClinicalTrials.gov 记录缺少试验标题")
        registry_version_date = str(
            _required(last_update, "date", path="lastUpdatePostDateStruct")
        ).strip()
        holder = str(_required(misc, "versionHolder", path="miscInfoModule")).strip()
        if not registry_version_date or not holder:
            raise ValueError("ClinicalTrials.gov 记录缺少版本日期")
        digest_input = _scientific_record_digest_input(record)
        record_url = f"https://clinicaltrials.gov/study/{nct_id}"
        return cls(
            nct_id=nct_id,
            source_study_id=stable_id("source-study", "clinicaltrials.gov", nct_id),
            source_version_id=stable_id(
                "source-version", "clinicaltrials.gov", nct_id, digest_input
            ),
            title=title,
            registry_posted_version_date=registry_version_date,
            platform_version_holder=holder,
            acquired_at=_offset_datetime(acquired_at),
            record_url=record_url,
            history_url=f"{record_url}?tab=history",
            raw_record_json=json.dumps(
                record,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )


class ClinicalTrialsGovCapture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    studies: tuple[ClinicalTrialsGovStudyVersion, ...]
    next_page_token: str | None = None

    @classmethod
    def from_api_payload(
        cls, payload: Mapping[str, Any], *, acquired_at: str
    ) -> ClinicalTrialsGovCapture:
        raw_studies = _required(payload, "studies", path="response")
        if not isinstance(raw_studies, list):
            raise ValueError("ClinicalTrials.gov studies 必须是列表")
        token = payload.get("nextPageToken")
        if token is not None and not str(token).strip():
            raise ValueError("ClinicalTrials.gov 下一页令牌不能为空")
        return cls(
            studies=tuple(
                ClinicalTrialsGovStudyVersion.from_api_record(
                    _mapping(item, path=f"studies[{index}]"),
                    acquired_at=acquired_at,
                )
                for index, item in enumerate(raw_studies)
            ),
            next_page_token=None if token is None else str(token),
        )


class RegistryObservation(BaseModel):
    """保留登记原值和 API 字段路径，不在连接器层解释临床含义。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    source_version_id: str
    nct_id: str
    claim_domain: Literal["trial_design", "trial_results"]
    original_value: str | int | float | bool
    locator: EvidenceLocator


class PublicationCrossReference(BaseModel):
    """登记平台提供的 NCT—PMID 边；论文角色留待论文分类器判定。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    edge_id: str
    source_version_id: str
    nct_id: str
    pmid: str
    platform_reference_type: str
    publication_role: Literal["unclassified"] = "unclassified"
    citation: str | None
    citation_state: Literal["reported", "not_publicly_disclosed"]
    locator: EvidenceLocator

    @field_validator("pmid")
    @classmethod
    def _pmid_is_numeric(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.isdigit():
            raise ValueError("PubMed 标识必须为数字")
        return normalized

    @field_validator("citation")
    @classmethod
    def _citation_is_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("已披露引文不能为空")
        return normalized

    @model_validator(mode="after")
    def _citation_state_matches_value(self) -> PublicationCrossReference:
        if self.citation_state == "reported" and self.citation is None:
            raise ValueError("已披露引文必须保留引文内容")
        if self.citation_state == "not_publicly_disclosed" and self.citation is not None:
            raise ValueError("未提供引文时不得伪造引文内容")
        return self


def _walk_leaves(value: Any, path: str) -> Iterator[tuple[str, str | int | float | bool]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from _walk_leaves(child, child_path)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_leaves(child, f"{path}[{index}]")
        return
    if isinstance(value, (str, int, float, bool)):
        yield path, value


def extract_registry_observations(
    study: ClinicalTrialsGovStudyVersion,
) -> tuple[RegistryObservation, ...]:
    selected_modules: tuple[tuple[str, Literal["trial_design", "trial_results"]], ...] = (
        ("protocolSection.designModule", "trial_design"),
        ("protocolSection.eligibilityModule", "trial_design"),
        ("protocolSection.armsInterventionsModule", "trial_design"),
        ("protocolSection.outcomesModule", "trial_design"),
        ("resultsSection", "trial_results"),
    )
    observations: list[RegistryObservation] = []
    for prefix, claim_domain in selected_modules:
        current: Any = study.raw_record
        for part in prefix.split("."):
            if not isinstance(current, Mapping) or part not in current:
                current = None
                break
            current = current[part]
        if current is None:
            continue
        for field_path, original_value in _walk_leaves(current, prefix):
            observations.append(
                RegistryObservation(
                    observation_id=stable_id(
                        "registry-observation",
                        study.source_version_id,
                        field_path,
                    ),
                    source_version_id=study.source_version_id,
                    nct_id=study.nct_id,
                    claim_domain=claim_domain,
                    original_value=original_value,
                    locator=EvidenceLocator(
                        document_role="ClinicalTrials.gov 登记记录",
                        field_path=field_path,
                        url=study.record_url,
                    ),
                )
            )
    return tuple(observations)


def create_publication_cross_references(
    study: ClinicalTrialsGovStudyVersion,
) -> tuple[PublicationCrossReference, ...]:
    protocol = study.raw_record.get("protocolSection", {})
    references_module = (
        protocol.get("referencesModule", {}) if isinstance(protocol, Mapping) else {}
    )
    references = (
        references_module.get("references", [])
        if isinstance(references_module, Mapping)
        else []
    )
    if not isinstance(references, list):
        raise ValueError("ClinicalTrials.gov references 必须是列表")
    edges: list[PublicationCrossReference] = []
    for index, reference in enumerate(references):
        item = _mapping(reference, path=f"references[{index}]")
        pmid = item.get("pmid")
        if pmid is None:
            continue
        reference_type = str(item.get("type", "UNSPECIFIED")).strip()
        raw_citation = item.get("citation")
        citation = None if raw_citation is None else str(raw_citation).strip() or None
        if not reference_type:
            raise ValueError("带 PMID 的登记引用必须保留引用类型")
        normalized_pmid = str(pmid).strip()
        field_path = f"protocolSection.referencesModule.references[{index}]"
        edges.append(
            PublicationCrossReference(
                edge_id=stable_id(
                    "publication-cross-reference",
                    study.source_version_id,
                    normalized_pmid,
                    field_path,
                ),
                source_version_id=study.source_version_id,
                nct_id=study.nct_id,
                pmid=normalized_pmid,
                platform_reference_type=reference_type,
                citation=citation,
                citation_state=(
                    "reported" if citation is not None else "not_publicly_disclosed"
                ),
                locator=EvidenceLocator(
                    document_role="ClinicalTrials.gov 关联论文",
                    field_path=field_path,
                    url=study.record_url,
                ),
            )
        )
    return tuple(edges)


def build_next_page_url(base_url: str, next_page_token: str) -> str:
    if not next_page_token.strip():
        raise ValueError("下一页令牌不能为空")
    parts = urlsplit(base_url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query = [(key, value) for key, value in query if key != "pageToken"]
    query.append(("pageToken", next_page_token))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
