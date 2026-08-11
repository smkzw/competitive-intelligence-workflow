from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator, Mapping
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal
from urllib.parse import urlencode, urlsplit

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.sources.connectors.regulators import GuidelineBasis
from ci_workflow.sources.policy import ClaimDomain, SourceAuthority, SourcePolicy

_SHA256 = re.compile(r"[0-9a-f]{64}")
ChinaAuthority = Literal["CDE", "NMPA"]
ChinaRegulatoryEventType = Literal[
    "application_accepted",
    "review_in_progress",
    "priority_review",
    "breakthrough_therapy",
    "clinical_trial_implied_license",
    "review_suspended",
    "application_withdrawn",
    "review_resumed",
    "marketing_approved",
    "approval_withdrawn",
]

_CDE_REGULATORY_EVENTS = {
    "application_accepted",
    "review_in_progress",
    "priority_review",
    "breakthrough_therapy",
    "clinical_trial_implied_license",
    "review_suspended",
    "application_withdrawn",
    "review_resumed",
}
_OFFICIAL_CHINA_DOMAINS = {
    "CDE": frozenset({"cde.org.cn", "www.cde.org.cn"}),
    "NMPA": frozenset({"nmpa.gov.cn", "www.nmpa.gov.cn"}),
}
_CHINA_TRIAL_DOMAINS = frozenset(
    {"chinadrugtrials.org.cn", "www.chinadrugtrials.org.cn"}
)


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("中国监管记录字段不能为空")
    return normalized


def _offset_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("中国监管记录日期时间必须包含明确时区")
    return parsed


class ChinaRegulatoryRecordVersion(BaseModel):
    """CDE/NMPA 的一个不可变公开记录版本和一个明确监管事件。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_record_id: str
    source_version_id: str
    event_id: str
    jurisdiction: Literal["CN"] = "CN"
    authority: ChinaAuthority
    external_record_id: str
    product_name: str
    application_number: str
    indication: str
    event_type: ChinaRegulatoryEventType
    status_label_zh: str
    occurred_on: date
    published_at: datetime
    acquired_at: datetime
    content_snapshot: str
    content_sha256: str
    source_url: str
    locator: EvidenceLocator
    is_marketing_approval: bool

    @field_validator(
        "source_record_id",
        "source_version_id",
        "event_id",
        "external_record_id",
        "product_name",
        "application_number",
        "indication",
        "status_label_zh",
        "source_url",
        "content_snapshot",
    )
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _text(value)

    @field_validator("content_sha256")
    @classmethod
    def _valid_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("中国监管记录摘要必须是小写 SHA-256")
        return value

    @field_validator("published_at", "acquired_at")
    @classmethod
    def _dates_have_offsets(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("中国监管记录日期时间必须包含明确时区")
        return value

    @model_validator(mode="after")
    def _approval_flag_matches_event(self) -> ChinaRegulatoryRecordVersion:
        if self.is_marketing_approval != (self.event_type == "marketing_approved"):
            raise ValueError("只有 NMPA 批准上市事件可标记为已批准")
        if (
            self.event_type in {"marketing_approved", "approval_withdrawn"}
            and self.authority != "NMPA"
        ):
            raise ValueError("批准及批准撤回事项必须归属 NMPA")
        if self.event_type in _CDE_REGULATORY_EVENTS and self.authority != "CDE":
            raise ValueError("CDE 专有事项不能归属 NMPA")
        parts = urlsplit(self.source_url)
        if (
            parts.scheme != "https"
            or parts.hostname not in _OFFICIAL_CHINA_DOMAINS[self.authority]
        ):
            raise ValueError("中国监管记录必须使用对应机构官方网站")
        if self.locator.url != self.source_url:
            raise ValueError("中国监管记录定位链接必须与来源链接一致")
        expected_digest = hashlib.sha256(
            self.content_snapshot.encode("utf-8")
        ).hexdigest()
        if self.content_sha256 != expected_digest:
            raise ValueError("中国监管记录摘要与已保存正文不一致")
        expected_record_id = stable_id(
            "china-regulatory-record", self.authority, self.external_record_id
        )
        expected_version_id = stable_id(
            "china-regulatory-version", expected_record_id, self.content_sha256
        )
        expected_event_id = stable_id(
            "china-regulatory-event",
            expected_record_id,
            self.event_type,
            self.occurred_on.isoformat(),
        )
        if self.source_record_id != expected_record_id:
            raise ValueError("中国监管记录标识与机构及记录编号不一致")
        if self.source_version_id != expected_version_id:
            raise ValueError("中国监管记录版本与已保存正文不一致")
        if self.event_id != expected_event_id:
            raise ValueError("中国监管事件标识与事件内容不一致")
        return self

    @classmethod
    def create(
        cls,
        *,
        source_system: ChinaAuthority,
        external_record_id: str,
        product_name: str,
        application_number: str,
        indication: str,
        event_type: ChinaRegulatoryEventType,
        status_label_zh: str,
        occurred_on: str,
        published_at: str,
        acquired_at: str,
        content_snapshot: str,
        source_url: str,
        locator_label: str,
    ) -> ChinaRegulatoryRecordVersion:
        authority = source_system
        external_record_id = _text(external_record_id)
        content_snapshot = _text(content_snapshot)
        content_sha256 = hashlib.sha256(content_snapshot.encode("utf-8")).hexdigest()
        source_record_id = stable_id(
            "china-regulatory-record", authority, external_record_id
        )
        occurred = date.fromisoformat(occurred_on)
        return cls(
            source_record_id=source_record_id,
            source_version_id=stable_id(
                "china-regulatory-version", source_record_id, content_sha256
            ),
            event_id=stable_id(
                "china-regulatory-event",
                source_record_id,
                event_type,
                occurred.isoformat(),
            ),
            authority=authority,
            external_record_id=external_record_id,
            product_name=product_name,
            application_number=application_number,
            indication=indication,
            event_type=event_type,
            status_label_zh=status_label_zh,
            occurred_on=occurred,
            published_at=_offset_datetime(published_at),
            acquired_at=_offset_datetime(acquired_at),
            content_snapshot=content_snapshot,
            content_sha256=content_sha256,
            source_url=source_url,
            locator=EvidenceLocator(
                document_role=f"{authority} 官方公开信息",
                paragraph=locator_label,
                url=source_url,
            ),
            is_marketing_approval=event_type == "marketing_approved",
        )


def build_china_regulatory_timeline(
    records: tuple[ChinaRegulatoryRecordVersion, ...],
) -> tuple[ChinaRegulatoryRecordVersion, ...]:
    event_ids = tuple(item.event_id for item in records)
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("中国监管时间线事件不得重复")
    return tuple(
        sorted(records, key=lambda item: (item.occurred_on, item.authority, item.event_id))
    )


_CTR_ID = re.compile(r"CTR[0-9]{8}")


class ChinaDrugTrialVersion(BaseModel):
    """中国药物临床试验登记平台的一个不可变公开页面版本。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ctr_number: str
    source_trial_id: str
    source_version_id: str
    title: str
    trial_status: str
    protocol_number: str
    protocol_version: str
    updated_on: date
    first_disclosed_at: datetime
    first_disclosed_precision: Literal["calendar_day"] = "calendar_day"
    acquired_at: datetime
    source_url: str
    result_disclosure_state: Literal["reported", "not_publicly_disclosed"]
    raw_record_json: str
    content_sha256: str

    @field_validator(
        "ctr_number",
        "source_trial_id",
        "source_version_id",
        "title",
        "trial_status",
        "protocol_number",
        "protocol_version",
        "source_url",
    )
    @classmethod
    def _trial_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("ctr_number")
    @classmethod
    def _valid_ctr(cls, value: str) -> str:
        normalized = value.upper()
        if _CTR_ID.fullmatch(normalized) is None:
            raise ValueError("中国登记记录缺少有效 CTR 号")
        return normalized

    @field_validator("acquired_at", "first_disclosed_at")
    @classmethod
    def _trial_acquired_at_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("中国登记采集时间必须包含明确时区")
        return value

    @field_validator("content_sha256")
    @classmethod
    def _trial_digest_is_valid(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("中国登记记录摘要必须是小写 SHA-256")
        return value

    @model_validator(mode="after")
    def _trial_snapshot_is_official_and_immutable(self) -> ChinaDrugTrialVersion:
        parts = urlsplit(self.source_url)
        if parts.scheme != "https" or parts.hostname not in _CHINA_TRIAL_DOMAINS:
            raise ValueError("中国试验登记记录必须使用官方平台链接")
        expected_digest = hashlib.sha256(
            self.raw_record_json.encode("utf-8")
        ).hexdigest()
        if self.content_sha256 != expected_digest:
            raise ValueError("中国登记记录摘要与已保存正文不一致")
        expected_trial_id = stable_id(
            "source-trial", "chinadrugtrials", self.ctr_number
        )
        expected_version_id = stable_id(
            "source-version", "chinadrugtrials", self.ctr_number, expected_digest
        )
        if self.source_trial_id != expected_trial_id:
            raise ValueError("中国登记试验标识与 CTR 号不一致")
        if self.source_version_id != expected_version_id:
            raise ValueError("中国登记版本与已保存正文不一致")
        if any(
            (
                self.first_disclosed_at.hour,
                self.first_disclosed_at.minute,
                self.first_disclosed_at.second,
                self.first_disclosed_at.microsecond,
            )
        ):
            raise ValueError("仅公开自然日的首次披露时间必须按北京时间零点保存")
        if self.first_disclosed_at.utcoffset() != timedelta(hours=8):
            raise ValueError("中国登记首次披露自然日必须按北京时间保存")
        return self

    @property
    def raw_record(self) -> dict[str, Any]:
        parsed = json.loads(self.raw_record_json)
        if not isinstance(parsed, dict):
            raise ValueError("已保存的中国登记记录不是对象")
        return parsed

    @classmethod
    def from_public_record(
        cls,
        record: Mapping[str, Any],
        *,
        acquired_at: str,
        source_url: str,
    ) -> ChinaDrugTrialVersion:
        required = {
            "ctr_number",
            "trial_status",
            "protocol_number",
            "protocol_version",
            "updated_on",
            "first_disclosed_on",
            "sections",
        }
        missing = required - set(record)
        if missing:
            raise ValueError("中国登记记录缺少必需字段")
        ctr_number = str(record["ctr_number"]).strip().upper()
        if _CTR_ID.fullmatch(ctr_number) is None:
            raise ValueError("中国登记记录缺少有效 CTR 号")
        sections = record["sections"]
        if not isinstance(sections, Mapping):
            raise ValueError("中国登记 sections 必须是对象")
        title = _text(str(sections.get("试验题目", "")))
        result_summary = sections.get("试验结果摘要")
        has_results = isinstance(result_summary, Mapping) and bool(result_summary)
        canonical = json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        source_trial_id = stable_id("source-trial", "chinadrugtrials", ctr_number)
        content_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        first_disclosed_on = date.fromisoformat(str(record["first_disclosed_on"]))
        first_disclosed_at = datetime.combine(
            first_disclosed_on,
            datetime.min.time(),
            tzinfo=timezone(timedelta(hours=8)),
        )
        return cls(
            ctr_number=ctr_number,
            source_trial_id=source_trial_id,
            source_version_id=stable_id(
                "source-version", "chinadrugtrials", ctr_number, content_sha256
            ),
            title=title,
            trial_status=str(record["trial_status"]),
            protocol_number=str(record["protocol_number"]),
            protocol_version=str(record["protocol_version"]),
            updated_on=date.fromisoformat(str(record["updated_on"])),
            first_disclosed_at=first_disclosed_at,
            acquired_at=_offset_datetime(acquired_at),
            source_url=source_url,
            result_disclosure_state=(
                "reported" if has_results else "not_publicly_disclosed"
            ),
            raw_record_json=canonical,
            content_sha256=content_sha256,
        )


class ChinaTrialObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    source_version_id: str
    ctr_number: str
    claim_domain: Literal["trial_design", "trial_results"]
    original_value: str | int | float | bool
    locator: EvidenceLocator


def _walk_leaves(value: Any, path: str) -> Iterator[tuple[str, str | int | float | bool]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from _walk_leaves(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_leaves(child, f"{path}[{index}]")
        return
    if isinstance(value, (str, int, float, bool)):
        yield path, value


def extract_china_trial_observations(
    trial: ChinaDrugTrialVersion,
) -> tuple[ChinaTrialObservation, ...]:
    sections = trial.raw_record.get("sections")
    if not isinstance(sections, Mapping):
        raise ValueError("中国登记记录缺少可解析 sections")
    observations: list[ChinaTrialObservation] = []
    for field_path, value in _walk_leaves(sections, "sections"):
        claim_domain: Literal["trial_design", "trial_results"] = (
            "trial_results"
            if field_path.startswith("sections.试验结果摘要")
            else "trial_design"
        )
        observations.append(
            ChinaTrialObservation(
                observation_id=stable_id(
                    "china-trial-observation", trial.source_version_id, field_path
                ),
                source_version_id=trial.source_version_id,
                ctr_number=trial.ctr_number,
                claim_domain=claim_domain,
                original_value=value,
                locator=EvidenceLocator(
                    document_role="中国药物临床试验登记与信息公示平台",
                    field_path=field_path,
                    url=trial.source_url,
                ),
            )
        )
    return tuple(observations)


def build_china_trial_search_url(ctr_number: str) -> str:
    normalized = ctr_number.strip().upper()
    if _CTR_ID.fullmatch(normalized) is None:
        raise ValueError("中国登记检索需要有效 CTR 号")
    query = urlencode({"keywords": normalized})
    return (
        "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml?"
        f"{query}"
    )


ChinaDrugReferenceSystem = Literal[
    "dxy_drug_assistant", "nmpa_official", "cde_official"
]
ChinaDrugReferenceRole = Literal[
    "secondary_drug_reference",
    "official_marketing_authority",
    "official_review_authority",
]

_CHINA_REFERENCE_ROLES: dict[
    ChinaDrugReferenceSystem, tuple[ChinaDrugReferenceRole, str, bool]
] = {
    "dxy_drug_assistant": (
        "secondary_drug_reference",
        "专业药品资料（二次参考）",
        False,
    ),
    "nmpa_official": (
        "official_marketing_authority",
        "国家药品监督管理局官方信息",
        True,
    ),
    "cde_official": (
        "official_review_authority",
        "国家药品监督管理局药品审评中心官方信息",
        True,
    ),
}
_CHINA_REFERENCE_POLICY_SOURCES: dict[ChinaDrugReferenceSystem, str] = {
    "dxy_drug_assistant": "dxy_drug_assistant",
    "nmpa_official": "regulator_official",
    "cde_official": "cde",
}


class ChinaDrugReferenceVersion(BaseModel):
    """国内药品参考页的不可变版本，明确区分官方事实与二次参考。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_system: ChinaDrugReferenceSystem
    source_record_id: str
    source_version_id: str
    external_record_id: str
    product_name: str
    content_label_zh: str
    source_role: ChinaDrugReferenceRole
    source_role_label_zh: str
    may_establish_official_regulatory_status: bool
    policy_id: str
    policy_version: str
    published_at: datetime
    acquired_at: datetime
    content_sha256: str
    source_url: str
    locator: EvidenceLocator

    @field_validator(
        "source_record_id",
        "source_version_id",
        "external_record_id",
        "product_name",
        "content_label_zh",
        "source_role_label_zh",
        "policy_id",
        "policy_version",
        "source_url",
    )
    @classmethod
    def _reference_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("content_sha256")
    @classmethod
    def _reference_sha256_is_valid(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("国内药品参考页摘要必须是小写 SHA-256")
        return value

    @field_validator("published_at", "acquired_at")
    @classmethod
    def _reference_times_have_offsets(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("国内药品参考页日期时间必须包含明确时区")
        return value

    @model_validator(mode="after")
    def _source_role_matches_source_system(self) -> ChinaDrugReferenceVersion:
        expected_role, expected_label, expected_official = _CHINA_REFERENCE_ROLES[
            self.source_system
        ]
        if self.source_system == "dxy_drug_assistant" and (
            self.source_role != expected_role
            or self.may_establish_official_regulatory_status
        ):
            raise ValueError("丁香园用药助手不能标记为官方监管来源")
        if (
            self.source_role != expected_role
            or self.source_role_label_zh != expected_label
            or self.may_establish_official_regulatory_status != expected_official
        ):
            raise ValueError("国内药品参考页的来源角色与来源系统不一致")
        return self

    @classmethod
    def create(
        cls,
        *,
        policy: SourcePolicy,
        source_system: ChinaDrugReferenceSystem,
        external_record_id: str,
        product_name: str,
        content_label_zh: str,
        published_at: str,
        acquired_at: str,
        content_sha256: str,
        source_url: str,
        locator_label: str,
    ) -> ChinaDrugReferenceVersion:
        source_role, role_label, is_official = _CHINA_REFERENCE_ROLES[source_system]
        policy_source = policy.source(_CHINA_REFERENCE_POLICY_SOURCES[source_system])
        china_status_authority = policy_source.authorities[
            ClaimDomain.CHINA_DEVELOPMENT_REGULATORY_STATUS
        ]
        if source_system == "dxy_drug_assistant":
            if (
                not policy_source.required_for_china
                or policy_source.authoritative_secondary
                or china_status_authority != SourceAuthority.CROSS_CHECK
            ):
                raise ValueError("来源策略未把丁香园用药助手限定为二次参考")
        elif (
            china_status_authority != SourceAuthority.DIRECT
            or policy_source.authoritative_secondary
        ):
            raise ValueError("来源策略未把中国官方页面标记为直接监管来源")
        external_record_id = _text(external_record_id)
        source_record_id = stable_id(
            "china-drug-reference", source_system, external_record_id
        )
        return cls(
            source_system=source_system,
            source_record_id=source_record_id,
            source_version_id=stable_id(
                "china-drug-reference-version", source_record_id, content_sha256
            ),
            external_record_id=external_record_id,
            product_name=product_name,
            content_label_zh=content_label_zh,
            source_role=source_role,
            source_role_label_zh=role_label,
            may_establish_official_regulatory_status=is_official,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            published_at=_offset_datetime(published_at),
            acquired_at=_offset_datetime(acquired_at),
            content_sha256=content_sha256,
            source_url=source_url,
            locator=EvidenceLocator(
                document_role=role_label,
                paragraph=locator_label,
                url=source_url,
            ),
        )


def capture_cde_guideline_basis(
    *,
    document_id: str,
    title: str,
    guidance_status: Literal["draft", "final"],
    version_date: str,
    population_context: str,
    development_context: str,
    source_url: str,
    locator_label: str,
    locator_page: int,
    content_sha256: str,
    captured_at: str,
    lifecycle_status: Literal["active", "superseded", "withdrawn"],
    supersedes_version_ids: tuple[str, ...] = (),
    superseded_by_version_id: str | None = None,
    withdrawn_at: str | None = None,
) -> GuidelineBasis:
    """把 CDE 指导原则接入与 FDA 相同、但司法辖区独立的版本谱系。"""

    return GuidelineBasis.create(
        jurisdiction="CN",
        agency="CDE",
        document_id=document_id,
        title=title,
        guidance_status=guidance_status,
        version_date=version_date,
        population_context=population_context,
        development_context=development_context,
        source_url=source_url,
        locator_label=locator_label,
        locator_page=locator_page,
        content_sha256=content_sha256,
        captured_at=captured_at,
        lifecycle_status=lifecycle_status,
        supersedes_version_ids=supersedes_version_ids,
        superseded_by_version_id=superseded_by_version_id,
        withdrawn_at=withdrawn_at,
    )
