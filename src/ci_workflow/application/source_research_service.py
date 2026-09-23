"""宿主 Agent 与确定性执行器之间的 A 类新鲜来源交接合同。"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.evidence import (
    DateEvidence,
    DatePrecision,
    EvidenceFragmentRecord,
    EvidenceLocator,
    SourceTextDerivation,
    source_version_identity,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.domain.public_provenance import (
    PublicCalculationEvidence,
    PublicProvenance,
    PublicSource,
)
from ci_workflow.renderers.portal.report_a import EfficacyRow, ReportAPortalData, SafetyRow
from ci_workflow.sources.connectors.ctgov_fetch import DerivedCtgovStudy
from ci_workflow.storage.manifest_store import ArtifactManifest
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from ci_workflow.storage.source_derivation import (
    extract_locator_quote,
    source_json_decoder,
    verify_source_text_derivation,
)
from ci_workflow.storage.sqlite import open_database


class ResearchPackageError(ValueError):
    """新鲜来源研究包不能形成可审计科学真源。"""


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


class CaptureDatePrecisions(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    published_at: DatePrecision = "instant"
    effective_at: DatePrecision = "instant"
    first_disclosed_at: DatePrecision = "instant"


class SourceCapture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    route_id: str
    source_type: str
    title: str
    url: str
    query_or_identifier: str
    language: str
    access_method: str
    media_type: str = "application/json"
    content_text: str
    text_derivation: SourceTextDerivation | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    acquired_at: datetime
    published_at: datetime | None
    effective_at: datetime | None
    first_disclosed_at: datetime
    date_precisions: CaptureDatePrecisions | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    locator: EvidenceLocator

    def date_evidence(self, role: str) -> DateEvidence:
        if role not in ("published_at", "effective_at", "first_disclosed_at"):
            raise ValueError("未知来源日期角色")
        value = getattr(self, role)
        return DateEvidence(
            state="reported" if value is not None else "not_publicly_disclosed",
            value=value, locator=self.locator,
            precision=getattr(self.date_precisions, role) if self.date_precisions else "instant",
        )

    @model_validator(mode="after")
    def _date_precision_matches_values(self) -> Self:
        for role in ("published_at", "effective_at", "first_disclosed_at"):
            self.date_evidence(role)
        return self

    @field_validator(
        "source_id", "route_id", "source_type", "title", "url",
        "query_or_identifier", "language", "access_method", "media_type", "content_text",
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("来源采集字段不能为空")
        return value.strip()

    @field_validator("acquired_at", "published_at", "effective_at", "first_disclosed_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("来源日期必须包含明确时区")
        return value

    @model_validator(mode="after")
    def _derived_text_matches_receipt(self) -> Self:
        if self.text_derivation is not None:
            if hashlib.sha256(self.content_text.encode("utf-8")).hexdigest() != (
                self.text_derivation.text_sha256
            ):
                raise ValueError("来源规范文本摘要与原始资产派生回执不一致")
            if self.media_type != self.text_derivation.raw_asset.media_type:
                raise ValueError("来源媒体类型与原始资产不一致")
        elif self.media_type == "application/pdf":
            raise ValueError("PDF提取文本必须绑定原始资产及派生回执")
        return self


def source_capture_from_ctgov_study(
    project_root: Path, study: DerivedCtgovStudy,
) -> SourceCapture:
    """Bridge one replayed CT.gov record into the existing precision-bound source contract.

    This does not create facts or assert that the trial-result universe is closed.
    The posted *calendar day* is the first disclosure of this current record
    version; it is never promoted to an exact publication instant.
    """
    verify_source_text_derivation(project_root, study.text_derivation, study.content_text)
    try:
        record = source_json_decoder().decode(study.content_text)
        if not isinstance(record, dict):
            raise TypeError("登记切片不是对象")
        protocol = record["protocolSection"]
        if not isinstance(protocol, dict):
            raise TypeError("登记方案字段不是对象")
        identification = protocol["identificationModule"]
        status = protocol["statusModule"]
        if not isinstance(identification, dict) or not isinstance(status, dict):
            raise TypeError("登记身份或状态字段不是对象")
        last_update = status["lastUpdatePostDateStruct"]
        if not isinstance(last_update, dict):
            raise TypeError("登记版本日期字段不是对象")
        expected_title = str(
            identification.get("briefTitle") or identification.get("officialTitle")
            or study.nct_id
        ).strip()
        posted = date.fromisoformat(study.registry_posted_version_date)
        if (
            identification.get("nctId") != study.nct_id
            or study.text_derivation.record_selector is None
            or study.text_derivation.record_selector.nct_id != study.nct_id
            or study.title != expected_title
            or last_update.get("date") != study.registry_posted_version_date
            or study.record_url != f"https://clinicaltrials.gov/study/{study.nct_id}"
        ):
            raise ResearchPackageError("登记切片与研究身份或公开版本日期不一致")
    except (KeyError, TypeError, ValueError) as error:
        raise ResearchPackageError("登记切片无法证明研究身份与公开版本日期") from error
    posted_day = datetime.combine(posted, time.min, tzinfo=UTC)
    return SourceCapture(
        source_id=f"ctgov-{study.nct_id.lower()}",
        route_id="ctgov-api-v2",
        source_type="clinical_trial_registry",
        title=study.title,
        url=study.record_url,
        query_or_identifier=study.nct_id,
        language="en",
        access_method="public_api",
        media_type="application/json",
        content_text=study.content_text,
        text_derivation=study.text_derivation,
        acquired_at=study.acquired_at,
        published_at=posted_day,
        effective_at=None,
        first_disclosed_at=posted_day,
        date_precisions=CaptureDatePrecisions(
            published_at="calendar_day", first_disclosed_at="calendar_day"
        ),
        locator=EvidenceLocator(
            document_role="clinical_trial_registry",
            field_path="$.protocolSection.identificationModule.nctId",
            url=study.record_url,
        ),
    )


class ResearchResultContext(BaseModel):
    """Scientific identity of a registry atom, not a display-label shortcut."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result_key: str
    category: Literal["outcome", "teae", "sae", "aesi", "common_ae"]
    trial_id: str
    group_id: str
    group_title: str
    arm: str
    term: str
    endpoint: str
    timepoint: str
    value_role: Literal["reported_measure", "participant_count", "affected_count", "denominator"]
    source_unit: str
    class_title: str | None = Field(default=None, exclude_if=lambda value: value is None)
    category_title: str | None = Field(default=None, exclude_if=lambda value: value is None)
    observation_timepoint: str | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class ResearchFact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str
    row_ref: str
    entity_id: str
    entity_type: str
    canonical_name: str
    field_id: str
    raw_value: str | None
    normalized_value: str | None
    disclosure_state: Literal[
        "reported_value", "reported_zero", "not_reported",
        "below_reporting_threshold", "not_publicly_disclosed",
        "not_applicable", "conflicting", "unresolved_due_to_route",
    ]
    source_id: str
    locator: EvidenceLocator
    original_text: str
    result_context: ResearchResultContext | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @field_validator(
        "fact_id", "row_ref", "entity_id", "entity_type", "canonical_name",
        "field_id", "source_id", "original_text",
    )
    @classmethod
    def _required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("事实字段不能为空")
        return value.strip()


class CtgovAeRateCalculation(BaseModel):
    """One bounded n/N rule; the source quotes remain separate atomic facts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: Literal["ctgov-ae-affected-over-at-risk-percent"] = (
        "ctgov-ae-affected-over-at-risk-percent"
    )
    rule_version: Literal["1"] = "1"
    formula: Literal["round(100 * affected / at_risk, 1)"] = (
        "round(100 * affected / at_risk, 1)"
    )
    decimal_places: Literal[1] = 1
    output_value: float = Field(allow_inf_nan=False)
    unit: Literal["%"] = "%"
    scope_row_ref: str


class ResearchClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    claim_text: str
    claim_kind: Literal["direct_evidence", "deterministic_calculation", "synthesis"]
    fact_ids: tuple[str, ...] = Field(min_length=1)
    calculation: CtgovAeRateCalculation | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def _calculation_has_two_inputs(self) -> Self:
        if self.calculation is not None and (
            self.claim_kind != "deterministic_calculation"
            or len(self.fact_ids) != 2
            or self.fact_ids[0] == self.fact_ids[1]
            or not self.calculation.scope_row_ref.startswith("safety:")
        ):
            raise ValueError("AE 计算必须引用两条不同原子事实和一个安全性结果行")
        return self


class RouteAttempt(BaseModel):
    """没有取得内容的真实技术路线尝试；不得改写为没有证据。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    attempt_id: str
    route_id: str
    strategy_unit_id: str
    gap_id: str
    query_or_identifier: str
    language: str
    access_method: str
    attempt_index: int = Field(ge=1)
    started_at: datetime
    ended_at: datetime
    result_class: Literal[
        "network_error",
        "rate_limited",
        "captcha_required",
        "permission_denied",
        "proxy_error",
        "dns_error",
        "tls_error",
        "http_error",
        "parser_error",
        "tool_unavailable",
        "content_truncated",
    ]
    error_class: str
    alternative_paths: tuple[str, ...] = Field(min_length=2)
    diagnostic_confidence: Literal["low", "medium", "high"]
    parent_attempt_id: str | None = None
    recovery_round: int = Field(ge=0)

    @field_validator("started_at", "ended_at")
    @classmethod
    def _attempt_time_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("技术路线尝试时间必须包含明确时区")
        return value

    @model_validator(mode="after")
    def _attempt_has_forward_time(self) -> Self:
        if self.ended_at < self.started_at:
            raise ValueError("技术路线尝试结束时间不得早于开始时间")
        return self


class ScientificReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reviewer_id: str
    reviewer_role: Literal["independent_scientific_verifier"]
    status: Literal["accepted", "rejected"]
    reviewed_at: datetime
    reviewed_content_digest: str
    observations: tuple[str, ...]

    @field_validator("reviewer_id", "reviewed_content_digest")
    @classmethod
    def _required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("科学复核字段不能为空")
        return value.strip()

    @field_validator("reviewed_at")
    @classmethod
    def _review_time_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("科学复核时间必须包含明确时区")
        return value


ClinicalTrialsResultCategory = Literal[
    "outcome", "teae", "sae", "aesi", "common_ae", "parse_failure"
]
ClinicalTrialsResultIssueStatus = Literal["missing", "misclassified", "parse_failure"]
_ParsedOutcomeCategory = Literal["outcome", "teae", "sae", "aesi"]
ClinicalTrialsTrialCoverageStatus = Literal[
    "registry_results_projected",
    "reported_by_secondary_source",
    "reported_not_projected",
    "registry_results_not_posted",
    "source_parse_failure",
    "source_not_captured",
]


@dataclass(frozen=True)
class ClinicalTrialsTrialCoverage:
    """一个报告试验在来源、解析和报告投影各层的数值覆盖状态。"""

    trial_id: str
    product_id: str
    registry_source_ids: tuple[str, ...]
    registry_sources_with_results: tuple[str, ...]
    result_source_ids: tuple[str, ...]
    projected_efficacy_rows: int
    projected_safety_rows: int
    status: ClinicalTrialsTrialCoverageStatus


@dataclass(frozen=True)
class ClinicalTrialsProductCoverage:
    """产品级结果状态与实际可比较试验的确定性摘要。"""

    product_id: str
    result_status: Literal[
        "有公开关键结果",
        "已有部分公开结果",
        "暂无公开关键结果",
        "临床前",
    ]
    trial_ids: tuple[str, ...]
    numeric_result_trial_ids: tuple[str, ...]
    comparable_result_trial_ids: tuple[str, ...]


@dataclass(frozen=True)
class ClinicalTrialsResultCoverageIssue:
    """一个登记结果未被报告投影或无法安全解析的可审计问题。"""

    category: ClinicalTrialsResultCategory
    status: ClinicalTrialsResultIssueStatus
    trial_id: str
    source_id: str
    source_path: str
    result_key: str
    reason_zh: str
    report_row_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClinicalTrialsResultCoverageAudit:
    """ClinicalTrials.gov 结果模块与 A 类报告行之间的确定性覆盖审计。"""

    audited_trial_ids: tuple[str, ...]
    inventory_counts: Mapping[str, int]
    issues: tuple[ClinicalTrialsResultCoverageIssue, ...]
    trial_coverage: tuple[ClinicalTrialsTrialCoverage, ...] = ()
    product_coverage: tuple[ClinicalTrialsProductCoverage, ...] = ()
    product_status_mismatches: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.issues and not self.product_status_mismatches

    @property
    def error_message_zh(self) -> str:
        if self.passed:
            return "ClinicalTrials.gov 结果覆盖审计通过"
        details_list = [issue.reason_zh for issue in self.issues[:8]]
        if self.product_status_mismatches:
            details_list.append(
                "报告产品结果状态与实际可比较结果不一致："
                + "、".join(self.product_status_mismatches[:8])
            )
        details = "；".join(details_list)
        issue_count = len(self.issues) + len(self.product_status_mismatches)
        suffix = "" if issue_count <= 8 else f"；另有 {issue_count - 8} 项"
        return f"ClinicalTrials.gov 结果覆盖审计失败：{details}{suffix}"


@dataclass(frozen=True)
class _RegistryResult:
    category: Literal["outcome", "teae", "sae", "aesi", "common_ae"]
    trial_id: str
    source_id: str
    source_path: str
    result_key: str
    term: str
    group_id: str
    arm: str
    value: float | None
    numerator: int | None
    denominator: int | None
    endpoint: str = ""
    timepoint: str = ""
    unit: str = ""
    group_title: str = ""
    value_path: str = ""
    denominator_path: str | None = None
    raw_unit: str = ""
    class_title: str = ""
    category_title: str = ""
    observation_timepoint: str = ""


@dataclass(frozen=True)
class CtgovAtomicResult:
    """One registry result with re-extracted numerator/value and denominator atoms."""

    result_key: str
    category: Literal["outcome", "teae", "sae", "aesi", "common_ae"]
    trial_id: str
    source_id: str
    group_id: str
    group_title: str
    arm: str
    term: str
    endpoint: str
    timepoint: str
    display_value: float | None
    display_unit: str
    numerator: int | None
    denominator: int | None
    value_locator: EvidenceLocator
    value_quote: str
    denominator_locator: EvidenceLocator | None
    denominator_quote: str | None
    raw_unit: str = ""
    class_title: str = ""
    category_title: str = ""
    observation_timepoint: str = ""


_RESULT_NCT_ID = re.compile(r"NCT[0-9]{8}", re.IGNORECASE)
_NUMERIC_RESULT = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")
_TIME_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_TEXT_TOKEN = re.compile(r"[a-z]+|\d+(?:\.\d+)?|[\u4e00-\u9fff]+")
_COMMON_AE_AGGREGATE_TERMS = frozenset(
    {"其他AE汇总", "其他不良事件汇总", "常见AE汇总", "常见AE谱"}
)
_TEAE_TERMS = frozenset({"任何TEAE", "TEAE", "anyteae", "treatmentemergentadverseevents"})
_AESI_TERMS = frozenset({"AESI", "预先界定AESI", "特别关注不良事件"})
_RESULT_CATEGORY_ZH = {
    "teae": "治疗期间不良事件",
    "sae": "严重不良事件",
    "aesi": "特别关注不良事件",
    "common_ae": "常见不良事件",
}


def _result_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _result_nct_id(value: object) -> str | None:
    match = _RESULT_NCT_ID.search(_result_text(value))
    return None if match is None else match.group(0).upper()


def _result_number(value: object, *, integer: bool = False) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError("缺少数值")
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = _result_text(value).replace(",", "")
        if _NUMERIC_RESULT.fullmatch(text) is None:
            raise ValueError(f"不支持的数值表达：{text}")
        number = float(text)
    if not math.isfinite(number) or (integer and not number.is_integer()):
        raise ValueError("数值不是有限整数")
    return number


def _result_int(value: object) -> int:
    return int(_result_number(value, integer=True))


def _result_tokens(value: object) -> set[str]:
    text = _result_text(value).casefold()
    for old, new in (
        ("investigator's global assessment", " iga "),
        ("investigator global assessment", " iga "),
        ("eczema area and severity index", " easi "),
        ("numerical rating scale", " nrs "),
        ("pruritus nrs", " nrs "),
        ("body surface area", " bsa "),
        ("dermatology life quality index", " dlqi "),
        ("patient oriented eczema measure", " poem "),
        ("scoring atopic dermatitis", " scorad "),
        ("global individual signs score", " giss "),
        ("percentage of participants", " "),
        ("participants with", " "),
        ("from baseline", " "),
        ("at baseline", " "),
    ):
        text = text.replace(old, new)
    return {
        token
        for token in _TEXT_TOKEN.findall(text)
        if token not in {"the", "of", "and", "with", "to", "in", "at", "from"}
    }


def _result_time_tokens(value: object) -> set[str]:
    text = _result_text(value).casefold().replace("周", " week ").replace("天", " day ")
    return set(_TIME_NUMBER.findall(text)) | {
        token for token in ("baseline", "week", "day", "month") if token in text
    }


def _result_time_matches(source: str, report: str) -> bool:
    source_tokens = _result_time_tokens(source)
    report_tokens = _result_time_tokens(report)
    if not source_tokens or not report_tokens:
        return _result_text(source).casefold() == _result_text(report).casefold()
    source_numbers = {token for token in source_tokens if token[0].isdigit()}
    report_numbers = {token for token in report_tokens if token[0].isdigit()}
    if source_numbers and source_numbers != report_numbers:
        return False
    return (
        source_tokens <= report_tokens
        or report_tokens <= source_tokens
        or bool(source_numbers & report_numbers)
    )


def _result_class_visit_title(class_title: str) -> str:
    """Only a stated visit, not any mention of baseline, can narrow a measure window."""
    title = _result_text(class_title)
    if title.casefold() in {"baseline", "at baseline"}:
        return title
    visits = re.findall(r"\b(?:day|week|month)\s*-?\d+(?:\.\d+)?\b", title.casefold())
    return title if len(visits) == 1 else ""


def _result_population_labels(population: str) -> frozenset[str]:
    text = _result_text(population)
    if "（" not in text or not text.endswith("）"):
        return frozenset()
    labels = text.split("（", 1)[1][:-1]
    return frozenset(_result_text(label).casefold() for label in labels.split("；"))


def _result_arm(group_title: object) -> str:
    text = _result_text(group_title).casefold()
    if "placebo- " in text:
        current = text.rsplit("placebo- ", 1)[-1]
        if not any(token in current for token in ("placebo", "vehicle", "control", "对照")):
            return "治疗组"
    for separator in (" then ", " to ", "/"):
        if separator in text:
            current = text.rsplit(separator, 1)[-1]
            if not any(token in current for token in ("placebo", "vehicle", "control", "对照")):
                return "治疗组"
    if any(token in text for token in ("placebo", "vehicle", "control", "对照")):
        return "对照组"
    return "治疗组"


def _result_arm_matches(source_arm: str, report_arm: str) -> bool:
    normalized = _result_text(report_arm)
    return normalized == source_arm or source_arm in normalized


def _result_category_zh(category: str) -> str:
    return _RESULT_CATEGORY_ZH.get(category, "安全性结果")


def _result_key(*parts: object) -> str:
    return stable_id("clinicaltrials-result", *(str(part) for part in parts))


def _result_issue(
    *,
    issues: list[ClinicalTrialsResultCoverageIssue],
    category: ClinicalTrialsResultCategory,
    status: ClinicalTrialsResultIssueStatus,
    trial_id: str,
    source_id: str,
    source_path: str,
    result_key: str,
    reason_zh: str,
    report_row_ids: tuple[str, ...] = (),
) -> None:
    issues.append(
        ClinicalTrialsResultCoverageIssue(
            category=category,
            status=status,
            trial_id=trial_id,
            source_id=source_id,
            source_path=source_path,
            result_key=result_key,
            reason_zh=reason_zh,
            report_row_ids=report_row_ids,
        )
    )


def _parse_failure(
    *,
    issues: list[ClinicalTrialsResultCoverageIssue],
    trial_id: str,
    source_id: str,
    source_path: str,
    detail: str,
) -> None:
    _result_issue(
        issues=issues,
        category="parse_failure",
        status="parse_failure",
        trial_id=trial_id,
        source_id=source_id,
        source_path=source_path,
        result_key=_result_key(trial_id, source_id, source_path),
        reason_zh=(
            f"{trial_id} 的 ClinicalTrials.gov 来源结构暂未支持（{source_path}）：{detail}；"
            "不得降级为未公开"
        ),
    )


def _mapping_at(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} 必须是对象")
    return value


def _list_at(value: object, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} 必须是列表")
    return value


def _explicit_aesi(value: Mapping[str, Any]) -> bool:
    for key in (
        "isAESI", "isAesi", "aesi", "AESI", "specialInterest", "eventCategory",
        "classification", "eventType", "category",
    ):
        marker = value.get(key)
        if marker is True:
            return True
        if isinstance(marker, str) and _result_text(marker).casefold() in {
            "aesi", "aes", "adverse events of special interest", "特别关注不良事件",
        }:
            return True
    return False


def _outcome_category(
    title: str, class_title: str = ""
) -> _ParsedOutcomeCategory | None:
    normalized = title.casefold()
    class_name = class_title.casefold()
    combined = f"{normalized} {class_name}"
    if class_name:
        if "aesi" in class_name or "adverse event of special interest" in class_name:
            return "aesi"
        if "serious" in class_name or class_name.strip() in {"sae", "saes", "serious aes"}:
            return "sae"
        if "teae" in class_name or "treatment emergent adverse event" in class_name:
            return "teae"
        if class_name.strip() in {"ae", "aes", "any ae", "any aes", "adverse events"}:
            return "teae"
    has_teae = "teae" in combined or "treatment-emergent adverse event" in combined
    has_sae = (
        "sae" in combined
        or "serious adverse event" in combined
        or "treatment-emergent serious" in combined
    )
    if "aesi" in combined or "adverse event of special interest" in combined:
        return "aesi"
    if has_teae and has_sae:
        class_is_sae = "sae" in class_name or "serious" in class_name
        class_is_teae = "teae" in class_name or (
            "adverse event" in class_name and not class_is_sae
        )
        if class_is_sae:
            return "sae"
        if class_is_teae or class_name.strip() in {"aes", "any aes"}:
            return "teae"
        return None
    if has_sae:
        return "sae"
    if has_teae:
        return "teae"
    return "outcome"


def _outcome_report_term(category: str, title: str, class_title: str) -> str:
    if category == "sae":
        return "任何SAE"
    if category == "aesi":
        return "预先界定AESI"
    if category != "teae":
        return title
    class_name = class_title.casefold().strip()
    if "any treatment emergent" in class_name or "any teae" in class_name:
        return "任何TEAE"
    if (
        class_name in {"ae", "aes", "any ae", "any aes", "adverse events"}
        and re.search(
            r"(?:number|percentage) of participants with treatment[- ]emergent adverse events",
            title.casefold(),
        )
    ):
        return "任何TEAE"
    if class_name in {"ae", "aes", "any ae", "any aes", "adverse events"}:
        return "任何AE"
    return title


def _source_bound_row_ids(
    row: object,
    *,
    prefix: str,
    source_id: str,
    fact_sources: Mapping[str, str] | None,
) -> bool:
    if fact_sources is None:
        return True
    row_id = getattr(row, "row_id", "")
    return fact_sources.get(f"{prefix}:{row_id}") == source_id


def _report_outcome_match(
    row: object,
    expected: _RegistryResult,
    *,
    source_title: str,
) -> bool:
    endpoint = str(getattr(row, "endpoint", ""))
    if not _result_time_matches(expected.timepoint, str(getattr(row, "timepoint", ""))):
        return False
    source_tokens = _result_tokens(source_title)
    report_tokens = _result_tokens(endpoint)
    overlap = source_tokens & report_tokens
    if not (
        _result_text(source_title).casefold() == _result_text(endpoint).casefold()
        or source_tokens <= report_tokens
        or report_tokens <= source_tokens
        or len(overlap) >= 2
    ):
        return False
    report_arm = str(getattr(row, "arm", ""))
    if not _result_arm_matches(expected.arm, report_arm):
        return False
    report_value = getattr(row, "value", None)
    if expected.unit and str(getattr(row, "unit", "")) != expected.unit:
        return False
    if expected.value is None:
        return False
    return (
        isinstance(report_value, (int, float))
        and not isinstance(report_value, bool)
        and math.isclose(
            float(report_value), float(expected.value), rel_tol=0.0, abs_tol=0.11
        )
    )


def _report_safety_match(row: object, expected: _RegistryResult) -> bool:
    if getattr(row, "trial_id", None) is None:
        return False
    if not _result_arm_matches(expected.arm, str(getattr(row, "arm", ""))):
        return False
    value = getattr(row, "value", None)
    numerator = getattr(row, "numerator", None)
    denominator = getattr(row, "denominator", None)
    if expected.value is None or not isinstance(value, (int, float)):
        return False
    if expected.unit and str(getattr(row, "unit", "")) != expected.unit:
        return False
    if expected.numerator is not None and numerator != expected.numerator:
        return False
    if expected.denominator is not None and denominator != expected.denominator:
        return False
    return (
        getattr(row, "disclosure_state", "已公开") == "已公开"
        and math.isclose(float(value), expected.value, rel_tol=0.0, abs_tol=0.11)
    )


def _report_safety_term_matches(row: object, expected: _RegistryResult) -> bool:
    category = str(getattr(row, "category", ""))
    term = _result_text(getattr(row, "term", ""))
    if expected.category == "sae":
        if category != "严重不良事件":
            return False
        return term == expected.term or (expected.term == "任何SAE" and term == "任何SAE")
    if expected.category == "teae":
        return category == "治疗期间不良事件" and (
            term == expected.term
            or (expected.term == "任何TEAE" and term in _TEAE_TERMS)
        )
    if expected.category == "aesi":
        return category == "特别关注不良事件" and term in _AESI_TERMS | {expected.term}
    if expected.category == "common_ae":
        return category == "常见不良事件" and (
            term == expected.term or term in _COMMON_AE_AGGREGATE_TERMS
        )
    return False


def _iter_outcome_results(
    *,
    record: Mapping[str, Any],
    trial_id: str,
    source_id: str,
    issues: list[ClinicalTrialsResultCoverageIssue],
) -> list[_RegistryResult]:
    results: list[_RegistryResult] = []
    results_section = _mapping_at(record.get("resultsSection"), "resultsSection")
    module = results_section.get("outcomeMeasuresModule")
    if module is None:
        return results
    module_mapping = _mapping_at(module, "resultsSection.outcomeMeasuresModule")
    measures = module_mapping.get("outcomeMeasures")
    if measures is None:
        return results
    for index, raw_measure in enumerate(
        _list_at(measures, "resultsSection.outcomeMeasuresModule.outcomeMeasures")
    ):
        path = f"resultsSection.outcomeMeasuresModule.outcomeMeasures[{index}]"
        try:
            measure = _mapping_at(raw_measure, path)
            title = _result_text(measure.get("title"))
            timeframe = _result_text(measure.get("timeFrame"))
            if not title or not timeframe:
                raise ValueError("缺少结局标题或时间窗")
            groups = {
                str(_mapping_at(item, f"{path}.groups[{group_index}]")["id"]): _result_text(
                    _mapping_at(item, f"{path}.groups[{group_index}]").get("title")
                )
                for group_index, item in enumerate(
                    _list_at(measure.get("groups", []), f"{path}.groups")
                )
            }
            if any(not title for title in groups.values()):
                raise ValueError("结果组别缺少标题")
            denominator_by_group: dict[str, tuple[int, str]] = {}
            for denom_index, raw_denom in enumerate(measure.get("denoms", [])):
                denom = _mapping_at(raw_denom, f"{path}.denoms[{denom_index}]")
                for count_index, raw_count in enumerate(denom.get("counts", [])):
                    count = _mapping_at(
                        raw_count, f"{path}.denoms[{denom_index}].counts[{count_index}]"
                    )
                    group_id = _result_text(count.get("groupId"))
                    denominator_by_group[group_id] = (
                        _result_int(count.get("value")),
                        f"{path}.denoms[{denom_index}].counts[{count_index}].value",
                    )
            unit_raw = _result_text(measure.get("unitOfMeasure"))
            unit = unit_raw.casefold()
            param_type = _result_text(measure.get("paramType")).casefold()
            is_percentage = any(
                token in unit for token in ("percent", "percentage", "%", "百分比")
            ) or (not unit and any(
                token in _result_text(measure.get("title")).casefold()
                for token in ("percent", "percentage", "%", "百分比")
            ))
            is_participant_count = not is_percentage and (
                any(token in unit for token in ("participant", "subject", "person", "人"))
                or "count_of_participants" in param_type
            )
            classes = _list_at(measure.get("classes", []), f"{path}.classes")
            measurements: list[
                tuple[str, float, str, _ParsedOutcomeCategory, str, str, str]
            ] = []
            saw_not_reported = False
            for class_index, raw_class in enumerate(classes):
                class_mapping = _mapping_at(raw_class, f"{path}.classes[{class_index}]")
                class_title = _result_text(class_mapping.get("title"))
                observation_timepoint = _result_class_visit_title(class_title)
                result_category = _outcome_category(title, class_title)
                if result_category is None:
                    _parse_failure(
                        issues=issues,
                        trial_id=trial_id,
                        source_id=source_id,
                        source_path=f"{path}.classes[{class_index}]",
                        detail="同一结局同时包含 TEAE 与 SAE，且类别标题不足以拆分",
                    )
                    continue
                categories = _list_at(
                    class_mapping.get("categories", []),
                    f"{path}.classes[{class_index}].categories",
                )
                for category_index, raw_category in enumerate(categories):
                    category_mapping = _mapping_at(
                        raw_category,
                        f"{path}.classes[{class_index}].categories[{category_index}]",
                    )
                    category_title = _result_text(category_mapping.get("title"))
                    for measurement_index, raw_measurement in enumerate(
                        _list_at(
                            category_mapping.get("measurements", []),
                            f"{path}.classes[{class_index}].categories[{category_index}].measurements",
                        )
                    ):
                        measurement_path = (
                            f"{path}.classes[{class_index}].categories[{category_index}]"
                            f".measurements[{measurement_index}]"
                        )
                        try:
                            measurement = _mapping_at(raw_measurement, measurement_path)
                            group_id = str(measurement.get("groupId", "")).strip()
                            if not group_id or group_id not in groups:
                                raise ValueError(f"结果组别未定义：{group_id or '空值'}")
                            raw_value = measurement.get("value")
                            if _result_text(raw_value).casefold() in {
                                "na", "n/a", "nr", "not available", "not reported"
                            }:
                                saw_not_reported = True
                                continue
                            measurements.append(
                                (
                                    group_id,
                                    _result_number(raw_value, integer=is_participant_count),
                                    measurement_path,
                                    result_category,
                                    class_title,
                                    category_title,
                                    observation_timepoint,
                                )
                            )
                        except (TypeError, ValueError, KeyError) as exc:
                            _parse_failure(
                                issues=issues,
                                trial_id=trial_id,
                                source_id=source_id,
                                source_path=measurement_path,
                                detail=str(exc),
                            )
            if not measurements:
                if saw_not_reported:
                    continue
                detail = "结局没有可解析的组别数值"
                _parse_failure(
                    issues=issues,
                    trial_id=trial_id,
                    source_id=source_id,
                    source_path=path,
                    detail=detail,
                )
                continue
            for (
                group_id, value, measurement_path, result_category,
                class_title, category_title, observation_timepoint,
            ) in measurements:
                report_term = _outcome_report_term(result_category, title, class_title)
                numerator = None
                denominator = None
                denominator_path = None
                normalized_value = value
                normalized_unit = "%" if is_percentage else (
                    "人" if is_participant_count else unit_raw
                )
                if is_participant_count:
                    denominator_entry = denominator_by_group.get(group_id)
                    if denominator_entry is None:
                        raise ValueError(f"受试者人数缺少分母：{group_id}")
                    denominator, denominator_path = denominator_entry
                    numerator = int(value)
                    if numerator < 0 or numerator > denominator:
                        raise ValueError("受试者人数超出来源分母")
                    if denominator == 0:
                        _result_issue(
                            issues=issues,
                            category=result_category,
                            status="missing",
                            trial_id=trial_id,
                            source_id=source_id,
                            source_path=denominator_path,
                            result_key=_result_key(
                                result_category, trial_id, title, timeframe,
                                group_id, measurement_path,
                            ),
                            reason_zh="来源明确记录 0/0；比例未定义，不得报告零风险率",
                        )
                        continue
                    normalized_value = round(numerator * 100 / denominator, 1)
                    normalized_unit = "%"
                results.append(
                    _RegistryResult(
                        category=result_category,
                        trial_id=trial_id,
                        source_id=source_id,
                        source_path=measurement_path,
                        result_key=_result_key(
                            result_category,
                            trial_id,
                            title,
                            timeframe,
                            group_id,
                            measurement_path,
                        ),
                        term=report_term,
                        group_id=group_id,
                        arm=_result_arm(groups[group_id]),
                        group_title=groups[group_id],
                        value=normalized_value,
                        numerator=numerator,
                        denominator=denominator,
                        endpoint=title,
                        timepoint=timeframe,
                        unit=normalized_unit,
                        value_path=f"{measurement_path}.value",
                        denominator_path=denominator_path,
                        raw_unit=unit_raw,
                        class_title=class_title,
                        category_title=category_title,
                        observation_timepoint=observation_timepoint,
                    )
                )
        except (TypeError, ValueError, KeyError) as exc:
            _parse_failure(
                issues=issues,
                trial_id=trial_id,
                source_id=source_id,
                source_path=path,
                detail=str(exc),
            )
    return results


def _iter_adverse_event_results(
    *,
    record: Mapping[str, Any],
    trial_id: str,
    source_id: str,
    issues: list[ClinicalTrialsResultCoverageIssue],
) -> list[_RegistryResult]:
    results: list[_RegistryResult] = []
    results_section = _mapping_at(record.get("resultsSection"), "resultsSection")
    raw_module = results_section.get("adverseEventsModule")
    if raw_module is None:
        return results
    module = _mapping_at(raw_module, "resultsSection.adverseEventsModule")
    event_timeframe = _result_text(module.get("timeFrame"))
    raw_groups = module.get("eventGroups", [])
    groups = _list_at(raw_groups, "resultsSection.adverseEventsModule.eventGroups")
    group_info: dict[str, tuple[str, str]] = {}
    for index, raw_group in enumerate(groups):
        path = f"resultsSection.adverseEventsModule.eventGroups[{index}]"
        try:
            group = _mapping_at(raw_group, path)
            group_id = str(group.get("id", "")).strip()
            if not group_id:
                raise ValueError("缺少事件组标识")
            group_info[group_id] = (
                _result_text(group.get("title")),
                _result_arm(group.get("title")),
            )
            for category, term, affected_key, at_risk_key in (
                ("sae", "任何SAE", "seriousNumAffected", "seriousNumAtRisk"),
                ("common_ae", "其他AE汇总", "otherNumAffected", "otherNumAtRisk"),
                ("teae", "任何TEAE", "teaeNumAffected", "teaeNumAtRisk"),
                ("teae", "任何TEAE", "anyTeaeNumAffected", "anyTeaeNumAtRisk"),
                ("teae", "任何TEAE", "anyTEAENumAffected", "anyTEAENumAtRisk"),
            ):
                affected = group.get(affected_key)
                at_risk = group.get(at_risk_key)
                if affected is None and at_risk is None:
                    continue
                if affected is None or at_risk is None:
                    missing_key = affected_key if affected is None else at_risk_key
                    _result_issue(
                        issues=issues,
                        category=category,  # type: ignore[arg-type]
                        status="missing",
                        trial_id=trial_id,
                        source_id=source_id,
                        source_path=f"{path}.{missing_key}",
                        result_key=_result_key(category, trial_id, group_id, path),
                        reason_zh=(
                            f"{trial_id} 的 {group_id} 未提供 {missing_key}；"
                            "当前比例未知，待核，不得推断为 0"
                        ),
                    )
                    continue
                numerator = _result_int(affected)
                denominator = _result_int(at_risk)
                if numerator == 0 and denominator == 0:
                    _result_issue(
                        issues=issues,
                        category=category,  # type: ignore[arg-type]
                        status="missing",
                        trial_id=trial_id,
                        source_id=source_id,
                        source_path=f"{path}.{at_risk_key}",
                        result_key=_result_key(category, trial_id, group_id, path),
                        reason_zh="来源明确记录 0/0；比例未定义，不得报告零风险率",
                    )
                    continue
                if denominator <= 0 or numerator < 0 or numerator > denominator:
                    raise ValueError("事件组分子/分母不符合范围")
                results.append(
                    _RegistryResult(
                        category=category,  # type: ignore[arg-type]
                        trial_id=trial_id,
                        source_id=source_id,
                        source_path=f"{path}.{affected_key}",
                        result_key=_result_key(category, trial_id, group_id, path),
                        term=term,
                        group_id=group_id,
                        arm=group_info[group_id][1],
                        group_title=group_info[group_id][0],
                        value=round(numerator * 100 / denominator, 1),
                        numerator=numerator,
                        denominator=denominator,
                        timepoint=event_timeframe,
                        value_path=f"{path}.{affected_key}",
                        denominator_path=f"{path}.{at_risk_key}",
                    )
                )
        except (TypeError, ValueError, KeyError) as exc:
            _parse_failure(
                issues=issues,
                trial_id=trial_id,
                source_id=source_id,
                source_path=path,
                detail=str(exc),
            )

    for event_field, category, _term_label in (
        ("seriousEvents", "sae", "严重不良事件"),
        ("otherEvents", "common_ae", "常见不良事件"),
    ):
        raw_events = module.get(event_field, [])
        try:
            events = _list_at(raw_events, f"resultsSection.adverseEventsModule.{event_field}")
        except ValueError as exc:
            _parse_failure(
                issues=issues,
                trial_id=trial_id,
                source_id=source_id,
                source_path=f"resultsSection.adverseEventsModule.{event_field}",
                detail=str(exc),
            )
            continue
        for event_index, raw_event in enumerate(events):
            path = f"resultsSection.adverseEventsModule.{event_field}[{event_index}]"
            try:
                event = _mapping_at(raw_event, path)
                term = _result_text(event.get("term"))
                if not term:
                    raise ValueError("缺少 AE 术语")
                stats = _list_at(event.get("stats", []), f"{path}.stats")
                if not stats:
                    raise ValueError("缺少 AE 逐组统计")
                explicit_aesi = _explicit_aesi(event)
            except (TypeError, ValueError, KeyError) as exc:
                _parse_failure(
                    issues=issues,
                    trial_id=trial_id,
                    source_id=source_id,
                    source_path=path,
                    detail=str(exc),
                )
                continue
            for stat_index, raw_stat in enumerate(stats):
                stat_path = f"{path}.stats[{stat_index}]"
                try:
                    stat = _mapping_at(raw_stat, stat_path)
                    group_id = _result_text(stat.get("groupId"))
                    if group_id not in group_info:
                        raise ValueError(f"事件组未定义：{group_id or '空值'}")
                    # A missing field is not evidence of zero affected patients.
                    # Keep the exact location for recovery instead of drawing a
                    # zero event/rate from a protobuf/JSON omission hypothesis.
                    if stat.get("numAffected") is None:
                        _result_issue(
                            issues=issues,
                            category=category,  # type: ignore[arg-type]
                            status="missing",
                            trial_id=trial_id,
                            source_id=source_id,
                            source_path=f"{stat_path}.numAffected",
                            result_key=_result_key(
                                category, trial_id, term, group_id, stat_path
                            ),
                            reason_zh=(
                                f"{trial_id} 的 {term} / {group_id} 未提供 numAffected；"
                                "受影响人数未知，待核，不得推断为 0"
                            ),
                        )
                        continue
                    numerator = _result_int(stat["numAffected"])
                    denominator = _result_int(stat.get("numAtRisk"))
                    if denominator == 0 and numerator == 0:
                        _result_issue(
                            issues=issues,
                            category=category,  # type: ignore[arg-type]
                            status="missing",
                            trial_id=trial_id,
                            source_id=source_id,
                            source_path=f"{stat_path}.numAtRisk",
                            result_key=_result_key(
                                category, trial_id, term, group_id, stat_path
                            ),
                            reason_zh="来源明确记录 0/0；比例未定义，不得报告零风险率",
                        )
                        continue
                    if denominator <= 0 or numerator < 0 or numerator > denominator:
                        raise ValueError("AE 分子/分母不符合范围")
                    result = _RegistryResult(
                        category=category,  # type: ignore[arg-type]
                        trial_id=trial_id,
                        source_id=source_id,
                        source_path=stat_path,
                        result_key=_result_key(category, trial_id, term, group_id, stat_path),
                        term=term,
                        group_id=group_id,
                        arm=group_info[group_id][1],
                        group_title=group_info[group_id][0],
                        value=round(numerator * 100 / denominator, 1),
                        numerator=numerator,
                        denominator=denominator,
                        timepoint=event_timeframe,
                        value_path=f"{stat_path}.numAffected",
                        denominator_path=f"{stat_path}.numAtRisk",
                    )
                    results.append(result)
                    if explicit_aesi:
                        results.append(
                            _RegistryResult(
                                category="aesi",
                                trial_id=trial_id,
                                source_id=source_id,
                                source_path=stat_path,
                                result_key=_result_key(
                                    "aesi", trial_id, term, group_id, stat_path
                                ),
                                term=term,
                                group_id=group_id,
                                arm=group_info[group_id][1],
                                group_title=group_info[group_id][0],
                                value=result.value,
                                numerator=numerator,
                                denominator=denominator,
                                timepoint=event_timeframe,
                                value_path=f"{stat_path}.numAffected",
                                denominator_path=f"{stat_path}.numAtRisk",
                            )
                        )
                except (TypeError, ValueError, KeyError) as exc:
                    _parse_failure(
                        issues=issues,
                        trial_id=trial_id,
                        source_id=source_id,
                        source_path=stat_path,
                        detail=str(exc),
                    )
    return results


def extract_ctgov_atomic_results(
    source: SourceCapture,
) -> tuple[tuple[CtgovAtomicResult, ...], tuple[ClinicalTrialsResultCoverageIssue, ...]]:
    """Reopen one captured registry record and retain every scalar source path.

    The display percentage is only a projection. Its affected count and at-risk
    denominator stay independently addressable; parse/missing issues remain in
    the return value and must not be counted as verified zeroes.
    """
    if source.source_type != "clinical_trial_registry" or source.media_type != "application/json":
        raise ResearchPackageError("原子结果提取需要 JSON 登记来源")
    try:
        record = source_json_decoder().decode(source.content_text)
        if not isinstance(record, dict):
            raise TypeError("登记来源不是对象")
        trial_id = str(
            record["protocolSection"]["identificationModule"]["nctId"]
        ).strip()
        if not trial_id or trial_id.casefold() != source.query_or_identifier.casefold():
            raise ValueError("来源试验身份不一致")
    except (KeyError, TypeError, ValueError) as error:
        raise ResearchPackageError("登记来源不能证明试验身份") from error
    if record.get("resultsSection") is None:
        if record.get("hasResults") is False:
            # Source has explicitly not posted results; callers classify this
            # separately from a parse failure, and no atom/rate can be emitted.
            return (), ()
        raise ResearchPackageError("登记未明确声明无结果却缺少 resultsSection，需重取核查")
    issues: list[ClinicalTrialsResultCoverageIssue] = []
    parsed = [
        *_iter_outcome_results(
            record=record, trial_id=trial_id, source_id=source.source_id, issues=issues
        ),
        *_iter_adverse_event_results(
            record=record, trial_id=trial_id, source_id=source.source_id, issues=issues
        ),
    ]
    atoms: list[CtgovAtomicResult] = []
    for result in parsed:
        if not result.value_path:
            raise ResearchPackageError("登记结果没有原子数值路径")
        value_locator = EvidenceLocator(
            document_role="clinical_trial_registry",
            field_path=f"$.{result.value_path}",
            url=source.url,
        )
        value_quote = extract_locator_quote(
            source.content_text, media_type=source.media_type, locator=value_locator
        )
        try:
            expected_raw = result.numerator if result.numerator is not None else result.value
            if expected_raw is None or not math.isclose(
                _result_number(value_quote), float(expected_raw), rel_tol=0.0, abs_tol=1e-9
            ):
                raise ValueError("原子数值与已解析登记结果不一致")
        except (TypeError, ValueError) as error:
            raise ResearchPackageError("登记结果的原子数值不能按精确路径复核") from error
        denominator_locator = None
        denominator_quote = None
        if result.denominator is not None:
            if result.denominator_path is None:
                raise ResearchPackageError("派生比例缺少分母精确路径")
            denominator_locator = EvidenceLocator(
                document_role="clinical_trial_registry",
                field_path=f"$.{result.denominator_path}",
                url=source.url,
            )
            denominator_quote = extract_locator_quote(
                source.content_text, media_type=source.media_type,
                locator=denominator_locator,
            )
            try:
                if _result_int(denominator_quote) != result.denominator:
                    raise ValueError("分母与已解析结果不一致")
            except ValueError as error:
                raise ResearchPackageError("登记结果分母不能按精确路径复核") from error
        atoms.append(CtgovAtomicResult(
            result_key=result.result_key, category=result.category,
            trial_id=result.trial_id, source_id=result.source_id,
            group_id=result.group_id, group_title=result.group_title,
            arm=result.arm, term=result.term,
            endpoint=result.endpoint,
            timepoint=result.timepoint, display_value=result.value,
            display_unit=result.unit, numerator=result.numerator,
            denominator=result.denominator, value_locator=value_locator,
            value_quote=value_quote, denominator_locator=denominator_locator,
            denominator_quote=denominator_quote,
            raw_unit=result.raw_unit,
            class_title=result.class_title,
            category_title=result.category_title,
            observation_timepoint=result.observation_timepoint,
        ))
    return tuple(atoms), tuple(issues)


def research_facts_from_ctgov_atom(
    atom: CtgovAtomicResult,
    *,
    report_row_ref: str | None = None,
) -> tuple[ResearchFact, ...]:
    """Turn one verified registry result into direct source facts for W01 ingestion.

    A derived display percentage is intentionally not written as a source fact;
    its calculation must be recorded separately with both input fact versions.
    """
    expected_prefix = "efficacy:" if atom.category == "outcome" else "safety:"
    if report_row_ref is not None and not report_row_ref.startswith(expected_prefix):
        raise ResearchPackageError("登记原子与报告行领域不一致")
    row_ref = report_row_ref or f"registry:{atom.result_key}:source_value"
    entity_id = stable_id("clinical-trial", atom.trial_id)

    def make_fact(
        *, role: Literal[
            "reported_measure", "participant_count", "affected_count", "denominator"
        ],
        locator: EvidenceLocator, quote: str, reference: str,
    ) -> ResearchFact:
        numeric = _result_number(quote, integer=role != "reported_measure")
        normalized = (
            str(int(numeric)) if role != "reported_measure" else str(numeric)
        )
        context = ResearchResultContext(
            result_key=atom.result_key, category=atom.category,
            trial_id=atom.trial_id, group_id=atom.group_id,
            group_title=atom.group_title,
            arm=atom.arm, term=atom.term, endpoint=atom.endpoint,
            timepoint=atom.timepoint,
            value_role=role,
            source_unit=(
                (atom.raw_unit or atom.display_unit)
                if role == "reported_measure" else "人"
            ),
            class_title=atom.class_title or None,
            category_title=atom.category_title or None,
            observation_timepoint=atom.observation_timepoint or None,
        )
        return ResearchFact(
            fact_id=stable_id(
                "ctgov-atomic-fact", atom.source_id, atom.result_key,
                locator.field_path or "", role,
            ),
            row_ref=reference, entity_id=entity_id, entity_type="clinical_trial",
            canonical_name=atom.trial_id,
            field_id=f"ctgov.{atom.category}.{role}",
            raw_value=quote, normalized_value=normalized,
            disclosure_state="reported_zero" if numeric == 0 else "reported_value",
            source_id=atom.source_id, locator=locator, original_text=quote,
            result_context=context,
        )

    role: Literal["reported_measure", "participant_count", "affected_count"] = (
        "reported_measure" if atom.numerator is None
        else "participant_count" if atom.category == "outcome"
        else "affected_count"
    )
    facts = [make_fact(
        role=role, locator=atom.value_locator, quote=atom.value_quote,
        reference=row_ref,
    )]
    if atom.denominator_locator is not None and atom.denominator_quote is not None:
        facts.append(make_fact(
            role="denominator", locator=atom.denominator_locator,
            quote=atom.denominator_quote, reference=f"{row_ref}:denominator",
        ))
    return tuple(facts)


def _capture_version_id(source: SourceCapture) -> str:
    return source_version_identity(
        source.source_id,
        hashlib.sha256(source.content_text.encode("utf-8")).hexdigest(),
        published_at=source.date_evidence("published_at"),
        effective_at=source.date_evidence("effective_at"),
        first_disclosed_at=source.date_evidence("first_disclosed_at"),
        text_derivation=source.text_derivation,
    )


def _bind_verified_ctgov_outcome_to_a_row(
    source: SourceCapture,
    atom: CtgovAtomicResult,
    row: EfficacyRow,
) -> tuple[EfficacyRow, tuple[ResearchFact, ...]]:
    if atom.category != "outcome":
        raise ResearchPackageError("此绑定仅接受登记疗效结局")
    is_count = atom.numerator is not None
    if is_count and (
        atom.denominator is None or row.unit not in {"Participants", "受试者", "人"}
        or row.numerator not in {None, atom.numerator}
        or row.denominator not in {None, atom.denominator}
    ):
        raise ResearchPackageError("登记应答人数缺少同组分母或与报告人数口径不一致")
    expected_value = (
        float(atom.numerator) if atom.numerator is not None else atom.display_value
    )
    population_labels = _result_population_labels(row.population)
    exact_path = row.source_field_path == atom.value_locator.field_path
    measure_time_matches = (
        _result_text(row.timepoint).casefold() == _result_text(atom.timepoint).casefold()
    )
    observation_time_matches = bool(atom.observation_timepoint) and (
        _result_text(row.timepoint).casefold()
        == _result_text(atom.observation_timepoint).casefold()
    )
    class_matches = (
        not atom.class_title or exact_path
        or _result_text(atom.class_title).casefold() in population_labels
        or observation_time_matches
    )
    category_matches = (
        not atom.category_title or exact_path
        or _result_text(atom.category_title).casefold() in population_labels
    )
    if (
        row.trial_id.casefold() != atom.trial_id.casefold()
        or _result_text(row.endpoint).casefold() != _result_text(atom.endpoint).casefold()
        or not (measure_time_matches or observation_time_matches)
        or not class_matches or not category_matches
        or row.arm not in {atom.arm, atom.group_title}
        or (not is_count and row.unit not in {atom.display_unit, atom.raw_unit})
        or row.value is None
        or expected_value is None
        or not math.isclose(row.value, expected_value, rel_tol=0.0, abs_tol=1e-9)
    ):
        raise ResearchPackageError("登记原子与疗效行的试验、终点、组别、时间或数值不一致")
    if row.arm_detail is None and row.group_id is None and row.arm != atom.group_title:
        raise ResearchPackageError("疗效行缺少可核对的来源组别明细或组号")
    if row.arm_detail is not None and (
        _result_text(row.arm_detail).casefold()
        != _result_text(atom.group_title).casefold()
    ):
        raise ResearchPackageError("疗效行组别明细与来源组别标题不一致")
    if row.group_id is not None and row.group_id != atom.group_id:
        raise ResearchPackageError("疗效行来源组号与登记结果不一致")
    expected_fields = {
        "source_field_path": atom.value_locator.field_path,
        "source_version_id": _capture_version_id(source),
        "source_text": atom.value_quote,
    }
    for field, expected in expected_fields.items():
        previous = getattr(row, field)
        if previous is not None and previous != expected:
            raise ResearchPackageError(f"疗效行已有冲突的{field}，不得静默覆盖")
    bound = EfficacyRow.model_validate({
        **row.model_dump(mode="json"),
        **expected_fields,
        "group_id": atom.group_id,
        **({"numerator": atom.numerator, "denominator": atom.denominator} if is_count else {}),
    })
    facts = research_facts_from_ctgov_atom(
        atom, report_row_ref=f"efficacy:{row.row_id}"
    )
    return bound, facts


def bind_ctgov_outcome_to_a_row(
    source: SourceCapture,
    atom: CtgovAtomicResult,
    row: EfficacyRow,
) -> tuple[EfficacyRow, tuple[ResearchFact, ...]]:
    """Bind a direct measure or reported participant count, never an inferred rate."""
    verified_atoms, _issues = extract_ctgov_atomic_results(source)
    if atom not in verified_atoms or atom.source_id != source.source_id:
        raise ResearchPackageError("登记原子与当前来源版本不一致")
    matches: list[CtgovAtomicResult] = []
    bound_result: tuple[EfficacyRow, tuple[ResearchFact, ...]] | None = None
    for candidate in verified_atoms:
        if candidate.category != "outcome":
            continue
        try:
            result = _bind_verified_ctgov_outcome_to_a_row(source, candidate, row)
        except ResearchPackageError:
            continue
        matches.append(candidate)
        if candidate == atom:
            bound_result = result
    if len(matches) != 1 or matches[0] != atom or bound_result is None:
        raise ResearchPackageError("登记结局与报告行没有唯一的完整医学身份匹配")
    return bound_result


def _bind_verified_ctgov_ae_to_a_row(
    source: SourceCapture,
    atom: CtgovAtomicResult,
    row: SafetyRow,
) -> tuple[SafetyRow, tuple[ResearchFact, ...], ResearchClaim]:
    if (
        atom.category == "outcome" or atom.numerator is None
        or atom.denominator is None or not atom.timepoint
    ):
        raise ResearchPackageError("AE 行缺少来源分子、风险人数或收集时间窗")
    if (
        row.trial_id is None
        or row.trial_id.casefold() != atom.trial_id.casefold()
        or row.arm != atom.arm
        or row.category != _RESULT_CATEGORY_ZH[atom.category]
        or _result_text(row.term).casefold() != _result_text(atom.term).casefold()
        or _result_text(row.time_window).casefold()
        != _result_text(atom.timepoint).casefold()
        or row.unit != "%"
        or row.measure_object != "participant_proportion"
        or row.count_basis != "participants"
        or row.disclosure_state != "已公开"
        or row.numerator != atom.numerator
        or row.denominator != atom.denominator
        or row.value is None or atom.display_value is None
        or not math.isclose(row.value, atom.display_value, rel_tol=0.0, abs_tol=1e-9)
    ):
        raise ResearchPackageError("AE 行与来源类别、事件、组别、时间或 n/N 比例不一致")
    if row.arm_detail is None and row.group_id is None:
        raise ResearchPackageError("AE 行缺少可核对的来源组别明细或组号")
    if row.arm_detail is not None and (
        _result_text(row.arm_detail).casefold()
        != _result_text(atom.group_title).casefold()
    ):
        raise ResearchPackageError("AE 行组别明细与来源组别标题不一致")
    if row.group_id is not None and row.group_id != atom.group_id:
        raise ResearchPackageError("AE 行来源组号与登记结果不一致")
    expected_fields = {
        "source_field_path": atom.value_locator.field_path,
        "source_version_id": _capture_version_id(source),
        "source_text": atom.value_quote,
    }
    for field, expected in expected_fields.items():
        previous = getattr(row, field)
        if previous is not None and previous != expected:
            raise ResearchPackageError(f"AE 行已有冲突的{field}，不得静默覆盖")
    bound = SafetyRow.model_validate({
        **row.model_dump(mode="json"),
        **expected_fields,
        "group_id": atom.group_id,
    })
    facts = research_facts_from_ctgov_atom(
        atom, report_row_ref=f"safety:{row.row_id}"
    )
    if len(facts) != 2:
        raise ResearchPackageError("AE 比例必须同时绑定分子和风险人数来源事实")
    claim = ResearchClaim(
        claim_id=stable_id("ctgov-ae-rate-claim", row.row_id, *[item.fact_id for item in facts]),
        claim_text=(
            f"{atom.numerator}/{atom.denominator}×100，按登记结果解析规则保留一位小数"
            f"={atom.display_value}%（{atom.term}；{atom.group_title}）"
        ),
        claim_kind="deterministic_calculation",
        fact_ids=tuple(item.fact_id for item in facts),
        calculation=CtgovAeRateCalculation(
            output_value=atom.display_value,
            scope_row_ref=f"safety:{row.row_id}",
        ),
    )
    return bound, facts, claim


def bind_ctgov_ae_to_a_row(
    source: SourceCapture,
    atom: CtgovAtomicResult,
    row: SafetyRow,
) -> tuple[SafetyRow, tuple[ResearchFact, ...], ResearchClaim]:
    """Bind verified affected/at-risk atoms and a deterministic rate claim."""
    verified_atoms, _issues = extract_ctgov_atomic_results(source)
    if atom not in verified_atoms or atom.source_id != source.source_id:
        raise ResearchPackageError("登记 AE 原子与当前来源版本不一致")
    return _bind_verified_ctgov_ae_to_a_row(source, atom, row)


def _validate_bound_ctgov_a_results(
    report_data: ReportAPortalData,
    sources: tuple[SourceCapture, ...],
    facts: tuple[ResearchFact, ...],
    claims: tuple[ResearchClaim, ...] = (),
) -> None:
    """Reopen each source once for atomic facts offered as visible A results."""
    efficacy_rows = {f"efficacy:{row.row_id}": row for row in report_data.efficacy}
    safety_rows = {f"safety:{row.row_id}": row for row in report_data.safety}
    source_by_id = {source.source_id: source for source in sources}
    atom_by_source: dict[str, dict[tuple[str, str], CtgovAtomicResult]] = {}
    row_ref_counts: dict[str, int] = {}
    facts_by_ref: dict[str, ResearchFact] = {}
    for fact in facts:
        row_ref_counts[fact.row_ref] = row_ref_counts.get(fact.row_ref, 0) + 1
        facts_by_ref[fact.row_ref] = fact
    matched_denominator_refs: set[str] = set()
    for fact in facts:
        if fact.result_context is None or not fact.row_ref.startswith(("efficacy:", "safety:")):
            continue
        if fact.row_ref.endswith(":denominator"):
            continue
        if row_ref_counts[fact.row_ref] != 1:
            raise ResearchPackageError("登记结果行有多个主事实绑定，不能选择性覆盖")
        context = fact.result_context
        source = source_by_id.get(fact.source_id)
        if source is None or fact.locator.field_path is None:
            raise ResearchPackageError("登记原子绑定的来源或精确路径不存在")
        if fact.source_id not in atom_by_source:
            atoms, _issues = extract_ctgov_atomic_results(source)
            atom_by_source[fact.source_id] = {
                (atom.result_key, atom.value_locator.field_path or ""): atom
                for atom in atoms
            }
        atom = atom_by_source[fact.source_id].get(
            (context.result_key, fact.locator.field_path)
        )
        if atom is None:
            raise ResearchPackageError("登记原子事实不能从当前来源精确重提取")
        if fact.row_ref.startswith("efficacy:"):
            row = efficacy_rows.get(fact.row_ref)
            if row is None or context.value_role not in {"reported_measure", "participant_count"}:
                raise ResearchPackageError("已绑定疗效行缺少直接报告的来源结局或人数")
            expected_row, expected_facts = _bind_verified_ctgov_outcome_to_a_row(
                source, atom, row
            )
            if expected_row != row or fact != expected_facts[0]:
                raise ResearchPackageError("登记原子事实与已提交疗效行不一致")
            if context.value_role == "participant_count":
                denominator_ref = f"{fact.row_ref}:denominator"
                if (
                    len(expected_facts) != 2
                    or row_ref_counts.get(denominator_ref) != 1
                    or facts_by_ref.get(denominator_ref) != expected_facts[1]
                ):
                    raise ResearchPackageError("登记应答人数缺少同组分母原子事实")
                matched_denominator_refs.add(denominator_ref)
            continue
        safety_row = safety_rows.get(fact.row_ref)
        if safety_row is None or context.value_role != "affected_count":
            raise ResearchPackageError("已绑定 AE 行缺少受影响人数原子")
        safety_expected_row, safety_expected_facts, expected_claim = (
            _bind_verified_ctgov_ae_to_a_row(source, atom, safety_row)
        )
        denominator_ref = f"{fact.row_ref}:denominator"
        if (
            safety_expected_row != safety_row or fact != safety_expected_facts[0]
            or row_ref_counts.get(denominator_ref) != 1
            or facts_by_ref.get(denominator_ref) != safety_expected_facts[1]
            or expected_claim not in claims
        ):
            raise ResearchPackageError("AE 派生比例缺少匹配的分母事实或计算声明")
        matched_denominator_refs.add(denominator_ref)
    for fact in facts:
        if (
            fact.row_ref.startswith(("efficacy:", "safety:"))
            and fact.row_ref.endswith(":denominator")
            and fact.result_context is not None
            and fact.row_ref not in matched_denominator_refs
        ):
            raise ResearchPackageError("登记分母原子没有对应的已核证结果行")


def _audit_source_record(
    *,
    source: SourceCapture,
    trial_id: str,
    record: Mapping[str, Any],
    report_data: ReportAPortalData,
    fact_sources: Mapping[str, str] | None,
    fact_paths: Mapping[str, str] | None,
    issues: list[ClinicalTrialsResultCoverageIssue],
    used_efficacy_rows: set[str],
) -> dict[str, int]:
    inventory = {category: 0 for category in ("outcome", "teae", "sae", "aesi", "common_ae")}
    registry_results: list[_RegistryResult] = []
    for parser, path in (
        (_iter_outcome_results, "resultsSection.outcomeMeasuresModule"),
        (_iter_adverse_event_results, "resultsSection.adverseEventsModule"),
    ):
        try:
            registry_results.extend(
                parser(
                    record=record,
                    trial_id=trial_id,
                    source_id=source.source_id,
                    issues=issues,
                )
            )
        except (TypeError, ValueError, KeyError) as exc:
            _parse_failure(
                issues=issues,
                trial_id=trial_id,
                source_id=source.source_id,
                source_path=path,
                detail=str(exc),
            )
    efficacy_rows = [
        row
        for row in report_data.efficacy
        if row.trial_id.casefold() == trial_id.casefold()
        and _source_bound_row_ids(
            row, prefix="efficacy", source_id=source.source_id, fact_sources=fact_sources
        )
    ]
    safety_rows = [
        row
        for row in report_data.safety
        if row.trial_id is not None
        and row.trial_id.casefold() == trial_id.casefold()
        and _source_bound_row_ids(
            row, prefix="safety", source_id=source.source_id, fact_sources=fact_sources
        )
    ]
    efficacy_by_source_path: dict[str, list[Any]] = {}
    safety_by_source_path: dict[str, list[Any]] = {}
    if fact_paths is not None:
        for efficacy_row in efficacy_rows:
            source_path = fact_paths.get(f"efficacy:{efficacy_row.row_id}")
            if source_path:
                efficacy_by_source_path.setdefault(source_path, []).append(efficacy_row)
        for safety_row in safety_rows:
            source_path = fact_paths.get(f"safety:{safety_row.row_id}")
            if source_path:
                safety_by_source_path.setdefault(source_path, []).append(safety_row)
    outcome_titles = {
        result.result_key: result.term
        for result in registry_results
        if result.category == "outcome"
    }
    for result in registry_results:
        inventory[result.category] += 1
        if result.category == "outcome":
            exact = [
                row
                for row in efficacy_by_source_path.get(result.source_path, [])
                if _report_outcome_match(
                    row, result, source_title=outcome_titles[result.result_key]
                )
            ]
            candidates = [] if fact_paths is not None else [
                row
                for row in efficacy_rows
                if row.row_id not in used_efficacy_rows
                and _report_outcome_match(
                    row, result, source_title=outcome_titles[result.result_key]
                )
            ]
            matched = exact or candidates
            if matched:
                used_efficacy_rows.add(matched[0].row_id)
                continue
            _result_issue(
                issues=issues,
                category="outcome",
                status="missing",
                trial_id=trial_id,
                source_id=source.source_id,
                source_path=result.source_path,
                result_key=result.result_key,
                reason_zh=(
                    f"{trial_id} 的登记结局“{result.term}”组别 {result.group_id} 已有数值，"
                    "但报告没有对应疗效行"
                ),
            )
            continue
        exact_safety = [
            row for row in safety_by_source_path.get(result.source_path, [])
            if _report_safety_term_matches(row, result)
            and _report_safety_match(row, result)
        ]
        matches = exact_safety or ([] if fact_paths is not None else [
            row
            for row in safety_rows
            if _report_safety_term_matches(row, result) and _report_safety_match(row, result)
        ])
        if not matches:
            _result_issue(
                issues=issues,
                category=result.category,
                status="missing",
                trial_id=trial_id,
                source_id=source.source_id,
                source_path=result.source_path,
                result_key=result.result_key,
                reason_zh=(
                    f"{trial_id} 的登记{_result_category_zh(result.category)}"
                    f"“{result.term}”组别 {result.group_id} 已有数值，"
                    "但报告没有对应安全性行"
                ),
            )
    registry_has_explicit_teae = any(result.category == "teae" for result in registry_results)
    registry_has_explicit_aesi = any(result.category == "aesi" for result in registry_results)
    other_ae_aggregates = [
        result
        for result in registry_results
        if result.category == "common_ae" and result.term == "其他AE汇总"
    ]
    for safety_row in safety_rows:
        term = _result_text(safety_row.term)
        if safety_row.value is None:
            continue
        other_aggregate = next(
            (
                result
                for result in other_ae_aggregates
                if _report_safety_match(safety_row, result)
            ),
            None,
        )
        if (
            safety_row.category == "治疗期间不良事件"
            and term in _TEAE_TERMS
            and (not registry_has_explicit_teae or other_aggregate is not None)
        ):
            _result_issue(
                issues=issues,
                category="teae",
                status="misclassified",
                trial_id=trial_id,
                source_id=source.source_id,
                source_path=(
                    other_aggregate.source_path
                    if other_aggregate is not None
                    else "resultsSection.adverseEventsModule.eventGroups.otherNumAffected"
                ),
                result_key=_result_key("teae", trial_id, safety_row.arm),
                reason_zh=(
                    f"{trial_id} 的报告行“{term}”不能由 ClinicalTrials.gov "
                    "otherNumAffected 充当 TEAE；登记来源未提供明确 TEAE 聚合值"
                ),
                report_row_ids=(safety_row.row_id,),
            )
        if (
            safety_row.category == "特别关注不良事件"
            and term in _AESI_TERMS
            and not registry_has_explicit_aesi
        ):
            _result_issue(
                issues=issues,
                category="aesi",
                status="misclassified",
                trial_id=trial_id,
                source_id=source.source_id,
                source_path="resultsSection.adverseEventsModule",
                result_key=_result_key("aesi", trial_id, safety_row.arm),
                reason_zh=(
                    f"{trial_id} 的报告行“{term}”没有登记来源明确 AESI 标记；"
                    "不得从普通 AE 术语自行推断 AESI"
                ),
                report_row_ids=(safety_row.row_id,),
            )
    return inventory


def _numeric_rows_for_trial(
    report_data: ReportAPortalData,
    trial_id: str,
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    normalized_trial_id = trial_id.casefold()
    efficacy_rows = tuple(
        efficacy_row
        for row in report_data.efficacy
        for efficacy_row in (row,)
        if efficacy_row.trial_id.casefold() == normalized_trial_id
        and efficacy_row.value is not None
    )
    safety_rows = tuple(
        safety_row
        for row in report_data.safety
        for safety_row in (row,)
        if safety_row.trial_id is not None
        and safety_row.trial_id.casefold() == normalized_trial_id
        and safety_row.value is not None
    )
    return efficacy_rows, safety_rows


def _comparable_result_trial_ids(
    report_data: ReportAPortalData,
    product_id: str,
) -> set[str]:
    """只把同一试验内成对的疗效与关键安全性记录算作产品结果。"""

    efficacy_contexts: dict[tuple[str, tuple[str, ...]], set[str]] = {}
    safety_contexts: dict[tuple[str, tuple[str, ...]], set[str]] = {}
    for efficacy_row in report_data.efficacy:
        if efficacy_row.product_id != product_id or efficacy_row.value is None:
            continue
        context = (
            efficacy_row.trial_id.casefold(),
            (
                efficacy_row.endpoint,
                efficacy_row.timepoint,
                efficacy_row.unit,
                efficacy_row.population,
            ),
        )
        efficacy_contexts.setdefault(context, set()).add(efficacy_row.arm)
    for safety_row in report_data.safety:
        if (
            safety_row.product_id != product_id
            or safety_row.value is None
            or safety_row.term not in {"任何TEAE", "任何SAE"}
        ):
            continue
        context = (
            safety_row.trial_id.casefold() if safety_row.trial_id is not None else "",
            (
                safety_row.category,
                safety_row.term,
                safety_row.time_window,
                safety_row.unit,
            ),
        )
        safety_contexts.setdefault(context, set()).add(safety_row.arm)
    efficacy_trials = {
        trial_id for (trial_id, _context), arms in efficacy_contexts.items()
        if {"治疗组", "对照组"} <= arms
    }
    safety_trials = {
        trial_id for (trial_id, _context), arms in safety_contexts.items()
        if trial_id and {"治疗组", "对照组"} <= arms
    }
    return efficacy_trials & safety_trials


def _row_source_ids(
    rows: tuple[Any, ...],
    *,
    prefix: str,
    fact_sources: Mapping[str, str] | None,
) -> set[str]:
    if fact_sources is None:
        return set()
    return {
        source_id
        for row in rows
        if (source_id := fact_sources.get(f"{prefix}:{row.row_id}")) is not None
    }


def audit_clinicaltrials_result_coverage(
    report_data: ReportAPortalData,
    sources: tuple[SourceCapture, ...],
    *,
    facts: tuple[ResearchFact, ...] | None = None,
) -> ClinicalTrialsResultCoverageAudit:
    """审计登记结果模块是否完整投影到报告行；不联网、不修改来源。

    审计对象覆盖报告中的每一项试验。登记没有 ``resultsSection`` 时只标记为
    ``registry_results_not_posted``，不得据此推断其他公开渠道也没有结果；若报告行
    由论文、会议或其他允许来源承载，则标记为 ``reported_by_secondary_source``。
    """
    report_trial_ids: dict[str, str] = {}
    for trial in report_data.trials:
        for identifier in (trial.id, trial.display_id):
            nct = _result_nct_id(identifier)
            if nct is not None:
                report_trial_ids[nct.casefold()] = trial.id
    fact_sources = None if facts is None else {fact.row_ref: fact.source_id for fact in facts}
    fact_paths = None if facts is None else {
        fact.row_ref: fact.locator.field_path or "" for fact in facts
    }
    issues: list[ClinicalTrialsResultCoverageIssue] = []
    registry_source_ids_by_trial: dict[str, set[str]] = {}
    registry_results_by_trial: dict[str, set[str]] = {}
    registry_parse_failures_by_trial: dict[str, set[str]] = {}
    registry_projection_issues_by_trial: dict[str, set[str]] = {}
    inventory_counts = {
        category: 0 for category in ("outcome", "teae", "sae", "aesi", "common_ae", "parse_failure")
    }
    used_efficacy_rows: set[str] = set()
    for source in sources:
        if source.source_type != "clinical_trial_registry":
            continue
        query_nct = _result_nct_id(source.query_or_identifier)
        try:
            decoded = json.loads(source.content_text)
            record = _mapping_at(decoded, "ClinicalTrials.gov 记录")
            content_nct = _result_nct_id(
                _mapping_at(
                    _mapping_at(record.get("protocolSection"), "protocolSection").get(
                        "identificationModule"
                    ),
                    "protocolSection.identificationModule",
                ).get("nctId")
            )
            nct = content_nct or query_nct
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            nct = query_nct
            if nct is not None and nct.casefold() in report_trial_ids:
                trial_id = report_trial_ids[nct.casefold()]
                registry_source_ids_by_trial.setdefault(trial_id, set()).add(source.source_id)
                registry_parse_failures_by_trial.setdefault(trial_id, set()).add(source.source_id)
                _parse_failure(
                    issues=issues,
                    trial_id=trial_id,
                    source_id=source.source_id,
                    source_path="content_text",
                    detail=str(exc),
                )
            continue
        if nct is None or nct.casefold() not in report_trial_ids:
            continue
        trial_id = report_trial_ids[nct.casefold()]
        registry_source_ids_by_trial.setdefault(trial_id, set()).add(source.source_id)
        if "resultsSection" not in record:
            continue
        registry_results_by_trial.setdefault(trial_id, set()).add(source.source_id)
        issue_count_before = len(issues)
        counts = _audit_source_record(
            source=source,
            trial_id=trial_id,
            record=record,
            report_data=report_data,
            fact_sources=fact_sources,
            fact_paths=fact_paths,
            issues=issues,
            used_efficacy_rows=used_efficacy_rows,
        )
        new_issues = issues[issue_count_before:]
        if new_issues:
            registry_projection_issues_by_trial.setdefault(trial_id, set()).add(source.source_id)
        if any(issue.status == "parse_failure" for issue in new_issues):
            registry_parse_failures_by_trial.setdefault(trial_id, set()).add(source.source_id)
        for category, count in counts.items():
            inventory_counts[category] += count
    inventory_counts["parse_failure"] = sum(
        1 for issue in issues if issue.category == "parse_failure"
    )

    trial_coverage: list[ClinicalTrialsTrialCoverage] = []
    for trial in report_data.trials:
        efficacy_rows, safety_rows = _numeric_rows_for_trial(report_data, trial.id)
        result_source_ids = _row_source_ids(
            efficacy_rows,
            prefix="efficacy",
            fact_sources=fact_sources,
        ) | _row_source_ids(
            safety_rows,
            prefix="safety",
            fact_sources=fact_sources,
        )
        registry_ids = registry_source_ids_by_trial.get(trial.id, set())
        result_module_ids = registry_results_by_trial.get(trial.id, set())
        if registry_parse_failures_by_trial.get(trial.id):
            status: ClinicalTrialsTrialCoverageStatus = "source_parse_failure"
        elif result_module_ids:
            status = (
                "registry_results_projected"
                if not any(
                    source_id in registry_projection_issues_by_trial.get(trial.id, set())
                    for source_id in result_module_ids
                )
                and (efficacy_rows or safety_rows)
                else "reported_not_projected"
            )
        elif efficacy_rows or safety_rows:
            status = "reported_by_secondary_source"
        elif registry_ids:
            status = "registry_results_not_posted"
        else:
            status = "source_not_captured"
        trial_coverage.append(
            ClinicalTrialsTrialCoverage(
                trial_id=trial.id,
                product_id=trial.product_id,
                registry_source_ids=tuple(sorted(registry_ids)),
                registry_sources_with_results=tuple(sorted(result_module_ids)),
                result_source_ids=tuple(sorted(result_source_ids)),
                projected_efficacy_rows=len(efficacy_rows),
                projected_safety_rows=len(safety_rows),
                status=status,
            )
        )

    product_coverage: list[ClinicalTrialsProductCoverage] = []
    product_status_mismatches: list[str] = []
    comparable_by_product = {
        product.id: _comparable_result_trial_ids(report_data, product.id)
        for product in report_data.products
    }
    for product in report_data.products:
        product_trials = tuple(
            trial.id for trial in report_data.trials if trial.product_id == product.id
        )
        numeric_trial_ids = tuple(
            coverage.trial_id
            for coverage in trial_coverage
            if coverage.product_id == product.id
            and (coverage.projected_efficacy_rows or coverage.projected_safety_rows)
        )
        comparable_trial_ids = tuple(
            trial_id for trial_id in product_trials if trial_id.casefold() in {
                item.casefold() for item in comparable_by_product[product.id]
            }
        )
        product_coverage.append(
            ClinicalTrialsProductCoverage(
                product_id=product.id,
                result_status=product.result_status,
                trial_ids=product_trials,
                numeric_result_trial_ids=numeric_trial_ids,
                comparable_result_trial_ids=comparable_trial_ids,
            )
        )
        observed = bool(numeric_trial_ids) or any(
            coverage.product_id == product.id and coverage.registry_sources_with_results
            for coverage in trial_coverage
        )
        status_mismatch = (
            product.result_status == "有公开关键结果" and not comparable_trial_ids
        ) or (
            product.result_status == "已有部分公开结果"
            and (not observed or bool(comparable_trial_ids))
        ) or (
            product.result_status == "暂无公开关键结果" and observed
        ) or (
            product.result_status == "临床前" and observed
        )
        if status_mismatch:
            product_status_mismatches.append(product.id)
    return ClinicalTrialsResultCoverageAudit(
        audited_trial_ids=tuple(sorted(registry_source_ids_by_trial)),
        inventory_counts=inventory_counts,
        issues=tuple(issues),
        trial_coverage=tuple(trial_coverage),
        product_coverage=tuple(product_coverage),
        product_status_mismatches=tuple(sorted(product_status_mismatches)),
    )


def validate_clinicaltrials_result_coverage(
    report_data: ReportAPortalData,
    sources: tuple[SourceCapture, ...],
    *,
    facts: tuple[ResearchFact, ...] | None = None,
) -> ClinicalTrialsResultCoverageAudit:
    """执行结果覆盖审计并在有漏投影时失败关闭。"""
    audit = audit_clinicaltrials_result_coverage(report_data, sources, facts=facts)
    if not audit.passed:
        raise ResearchPackageError(audit.error_message_zh)
    return audit


class FreshAResearchContent(BaseModel):
    """独立复核前可规范化、可摘要的 A 类科学内容。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    indication: str
    data_cutoff: datetime
    report_version: str
    universe_closed: Literal[True]
    universe_product_ids: tuple[str, ...] = Field(min_length=1)
    report_data: ReportAPortalData
    sources: tuple[SourceCapture, ...] = Field(min_length=1)
    route_attempts: tuple[RouteAttempt, ...] = ()
    facts: tuple[ResearchFact, ...] = Field(min_length=1)
    claims: tuple[ResearchClaim, ...] = Field(min_length=1)
    gate_status: Literal["passed"]

    @model_validator(mode="after")
    def _content_is_closed(self) -> Self:
        if self.indication != self.report_data.indication:
            raise ValueError("研究包与报告数据的适应症不一致")
        if self.data_cutoff != self.report_data.data_cutoff:
            raise ValueError("研究包与报告数据的数据截止不一致")
        if self.report_version != self.report_data.report_version:
            raise ValueError("研究包与报告数据的报告版本不一致")
        if tuple(self.universe_product_ids) != tuple(self.report_data.product_ids):
            raise ValueError("锁定竞品宇宙与报告产品顺序不一致")
        source_ids = [item.source_id for item in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("来源标识重复")
        if any(not item.date_evidence("first_disclosed_at").is_known_by(self.data_cutoff)
               for item in self.sources):
            raise ValueError("截止日之后或无法证明截止时点前首次披露的来源不得进入当前快照")
        source_set = set(source_ids)
        if any(fact.source_id not in source_set for fact in self.facts):
            raise ValueError("事实引用了研究包外来源")
        fact_ids = [item.fact_id for item in self.facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("事实标识重复")
        fact_set = set(fact_ids)
        if any(not set(claim.fact_ids) <= fact_set for claim in self.claims):
            raise ValueError("声明引用了研究包外事实")
        required_refs = {
            *(f"product:{item.id}" for item in self.report_data.products),
            *(f"trial:{item.id}" for item in self.report_data.trials),
            *(f"efficacy:{item.row_id}" for item in self.report_data.efficacy),
            *(f"safety:{item.row_id}" for item in self.report_data.safety),
        }
        available_refs = {item.row_ref for item in self.facts}
        missing = sorted(required_refs - available_refs)
        if missing:
            raise ValueError("核心受众事实缺少来源绑定：" + "、".join(missing[:5]))
        _validate_bound_ctgov_a_results(
            self.report_data, self.sources, self.facts, self.claims
        )
        validate_clinicaltrials_result_coverage(
            self.report_data,
            self.sources,
            facts=self.facts,
        )
        incomplete_safety = [
            item.row_id
            for item in self.report_data.safety
            if item.disclosure_state == "已公开"
            and (item.trial_id is None or not item.arm.strip())
        ]
        if incomplete_safety:
            raise ValueError(
                "已公开安全性数值缺少试验或组别语境："
                + "、".join(incomplete_safety[:5])
            )
        mature_product_ids = {
            item.id
            for item in self.report_data.products
            if item.result_status == "有公开关键结果"
        }
        efficacy_arms: dict[str, set[str]] = {}
        for efficacy_row in self.report_data.efficacy:
            if efficacy_row.value is not None:
                efficacy_arms.setdefault(efficacy_row.product_id, set()).add(
                    efficacy_row.arm
                )
        efficacy_incomplete = sorted(
            product_id
            for product_id in mature_product_ids
            if not {"治疗组", "对照组"} <= efficacy_arms.get(product_id, set())
        )
        if efficacy_incomplete:
            raise ValueError(
                "已有关键结果的竞品缺少治疗组与对照组疗效："
                + "、".join(efficacy_incomplete[:5])
            )
        safety_arms: dict[str, set[str]] = {}
        for safety_row in self.report_data.safety:
            if (
                safety_row.value is not None
                and safety_row.term in {"任何TEAE", "任何SAE"}
                and safety_row.disclosure_state == "已公开"
            ):
                safety_arms.setdefault(safety_row.product_id, set()).add(safety_row.arm)
        safety_incomplete = sorted(
            product_id
            for product_id in mature_product_ids
            if not {"治疗组", "对照组"} <= safety_arms.get(product_id, set())
        )
        if safety_incomplete:
            raise ValueError(
                "已有关键结果的竞品缺少治疗组与对照组TEAE或SAE："
                + "、".join(safety_incomplete[:5])
            )
        marketed_product_ids = {
            item.id for item in self.report_data.products if "获批" in item.status
        }
        marketed_teae_arms: dict[str, set[str]] = {}
        for safety_row in self.report_data.safety:
            if (
                safety_row.value is not None
                and safety_row.term.startswith("任何TEAE")
                and safety_row.disclosure_state == "已公开"
            ):
                marketed_teae_arms.setdefault(safety_row.product_id, set()).add(
                    safety_row.arm
                )
        marketed_teae_incomplete = sorted(
            product_id
            for product_id in marketed_product_ids
            if not {"治疗组", "对照组"}
            <= marketed_teae_arms.get(product_id, set())
        )
        if marketed_teae_incomplete:
            raise ValueError(
                "已获批竞品缺少治疗组与对照组总体TEAE："
                + "、".join(marketed_teae_incomplete[:5])
            )
        return self


class FreshAResearchPackage(FreshAResearchContent):
    """可由任意宿主 Agent 生成、由本地执行器验真的完整 A 类交接包。"""

    scientific_review: ScientificReview

    @property
    def research_content(self) -> dict[str, object]:
        return FreshAResearchContent.model_validate(
            self.model_dump(mode="json", exclude={"scientific_review"})
        ).model_dump(mode="json")

    @property
    def research_content_digest(self) -> str:
        return _digest(self.research_content)

    @model_validator(mode="after")
    def _package_is_independently_accepted(self) -> Self:
        if self.scientific_review.status != "accepted":
            raise ValueError("独立科学复核未接受，不得生成报告")
        if self.scientific_review.reviewed_content_digest != self.research_content_digest:
            raise ValueError("独立科学复核与当前研究内容摘要不一致")
        return self


@dataclass(frozen=True)
class ResearchLineage:
    package_digest: str
    evidence_snapshot: LockedSnapshot
    claim_snapshot_id: str
    coverage_set_id: str
    coverage_projection_id: str
    claim_ids: tuple[str, ...]
    source_version_ids: tuple[str, ...]
    source_fragment_ids: tuple[str, ...]
    fact_version_ids: tuple[str, ...]
    fragment_ids: tuple[str, ...]


def compute_research_content_digest(payload: dict[str, object]) -> str:
    """供宿主在提交独立复核前计算与执行器一致的内容摘要。"""
    candidate = dict(payload)
    candidate.pop("scientific_review", None)
    normalized = FreshAResearchContent.model_validate(candidate)
    return _digest(normalized.model_dump(mode="json"))


def load_fresh_a_research_package(path: Path) -> FreshAResearchPackage:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchPackageError("无法读取 A 类新鲜来源研究包") from exc
    try:
        return FreshAResearchPackage.model_validate(value)
    except ValueError as exc:
        raise ResearchPackageError(f"A 类新鲜来源研究包不符合合同：{exc}") from exc


def project_a_public_provenance(
    package: FreshAResearchPackage, lineage: ResearchLineage,
) -> PublicProvenance:
    """Join by computed version identity, never by sorted-list position."""
    package = FreshAResearchPackage.model_validate(package.model_dump(mode="json"))
    if package.research_content_digest != lineage.package_digest:
        raise ResearchPackageError("公共来源与已锁定研究内容不一致")
    sources = []
    for capture in package.sources:
        version_id = source_version_identity(
            capture.source_id, hashlib.sha256(capture.content_text.encode("utf-8")).hexdigest(),
            published_at=capture.date_evidence("published_at"),
            effective_at=capture.date_evidence("effective_at"),
            first_disclosed_at=capture.date_evidence("first_disclosed_at"),
            text_derivation=capture.text_derivation,
        )
        sources.append(PublicSource(
            source_version_id=version_id, label=capture.title,
            url=capture.url, source_type={
                "clinical_trial_registry": "临床试验登记",
                "regulatory_document": "监管文件",
                "primary_trial_report": "主要试验报告",
                "peer_reviewed_primary_report": "同行评议主要研究论文",
                "peer_reviewed_publication": "同行评议文献",
                "company_disclosure": "企业披露",
                "conference_abstract": "会议摘要",
            }.get(capture.source_type, capture.source_type),
            published_at=(
                capture.published_at.date().isoformat()
                if capture.published_at is not None else "未知（来源未明确公开）"
            ),
            data_cutoff=package.data_cutoff.date().isoformat(),
            limitation="报告级来源清单；具体行级支持关系尚未在此展开。",
        ))
    if sorted(item.source_version_id for item in sources) != sorted(lineage.source_version_ids):
        raise ResearchPackageError("公共来源与已锁定来源版本不一致")
    return PublicProvenance(
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        report_data_digest=hashlib.sha256(
            package.report_data.model_dump_json().encode("utf-8")
        ).hexdigest(),
        sources=tuple(sources),
    )


def project_a_calculation_evidence(
    project_root: Path, report_data: ReportAPortalData, lineage: ResearchLineage,
) -> tuple[PublicCalculationEvidence, ...]:
    """Expose only calculations that close against locked facts and visible A rows."""
    snapshot = SnapshotStore(project_root).read(lineage.evidence_snapshot)
    if snapshot["scientific_content_digest"] != lineage.package_digest:
        raise ResearchPackageError("计算依据与证据快照内容不一致")
    closure = snapshot["closure"]
    fragments = {
        item.fragment_id: item
        for raw in closure["fragments"]
        for item in (EvidenceFragmentRecord.model_validate(raw),)
    }
    facts = {
        str(raw["fact_version_id"]): (
            ResearchFact.model_validate(raw["fact"]), str(raw["primary_fragment_id"])
        )
        for raw in closure["facts"]
    }
    claims = {
        str(raw["claim_version_id"]): ResearchClaim.model_validate(raw["claim"])
        for raw in closure["claims"]
    }
    rows = {f"safety:{row.row_id}": row for row in report_data.safety}
    exposed: dict[str, PublicCalculationEvidence] = {}
    for raw in closure["derivations"]:
        if raw["derivation_kind"] != "calculation":
            continue
        output = raw["output"]
        scope = str(output["scope_row_ref"])
        row = rows.get(scope)
        claim = claims.get(str(output["claim_version_id"]))
        version_ids = output["input_fact_version_ids"]
        fragment_ids = raw["input_fragment_ids"]
        if (
            row is None or claim is None or claim.calculation is None
            or scope in exposed or len(version_ids) != 2 or len(fragment_ids) != 2
            or raw["rule_id"] != claim.calculation.rule_id
            or raw["rule_version"] != claim.calculation.rule_version
            or output["formula"] != claim.calculation.formula
            or output["value"] != claim.calculation.output_value
            or output["unit"] != claim.calculation.unit
            or output["parameters"] != {"decimal_places": claim.calculation.decimal_places}
            or scope != claim.calculation.scope_row_ref
        ):
            raise ResearchPackageError("计算派生与报告行或声明不一致")
        try:
            (numerator_fact, numerator_fragment_id), (
                denominator_fact, denominator_fragment_id
            ) = (facts[str(item)] for item in version_ids)
            numerator_fragment = fragments[numerator_fragment_id]
            denominator_fragment = fragments[denominator_fragment_id]
            numerator = int(numerator_fact.raw_value or "")
            denominator = int(denominator_fact.raw_value or "")
        except (KeyError, ValueError) as error:
            raise ResearchPackageError("计算派生输入缺少原子事实或原文片段") from error
        if (
            fragment_ids != [numerator_fragment_id, denominator_fragment_id]
            or numerator_fact.fact_id != claim.fact_ids[0]
            or denominator_fact.fact_id != claim.fact_ids[1]
            or numerator_fact.row_ref != scope
            or denominator_fact.row_ref != f"{scope}:denominator"
            or numerator_fragment.source_version_id != row.source_version_id
            or denominator_fragment.source_version_id != row.source_version_id
            or numerator_fragment.original_text != numerator_fact.original_text
            or denominator_fragment.original_text != denominator_fact.original_text
            or numerator_fragment.locator.field_path != row.source_field_path
            or numerator_fragment.original_text != row.source_text
            or numerator_fragment.locator.field_path is None
            or denominator_fragment.locator.field_path is None
            or row.numerator != numerator or row.denominator != denominator
            or row.value is None
            or not math.isclose(row.value, float(output["value"]), abs_tol=1e-9)
            or not math.isclose(
                row.value, round(100 * numerator / denominator, 1), abs_tol=1e-9
            )
        ):
            raise ResearchPackageError("计算派生原文、来源版本或展示值不一致")
        exposed[scope] = PublicCalculationEvidence(
            row_id=row.row_id,
            derivation_id=str(raw["derivation_id"]),
            claim_version_id=str(output["claim_version_id"]),
            source_version_id=row.source_version_id,
            numerator=numerator,
            denominator=denominator,
            numerator_quote=numerator_fragment.original_text,
            denominator_quote=denominator_fragment.original_text,
            numerator_field_path=numerator_fragment.locator.field_path,
            denominator_field_path=denominator_fragment.locator.field_path,
            value=row.value,
            unit=row.unit,
            rule_id=str(raw["rule_id"]),
            rule_version=str(raw["rule_version"]),
        )
    expected_scopes = {
        claim.calculation.scope_row_ref
        for claim in claims.values() if claim.calculation is not None
    }
    if set(exposed) != expected_scopes:
        raise ResearchPackageError("已声明的报告计算缺少快照派生或公开行")
    return tuple(exposed[key] for key in sorted(exposed))


def ingest_fresh_a_research_package(
    *, project_root: Path, project_id: str, contract_version: int,
    package: FreshAResearchPackage,
) -> ResearchLineage:
    """幂等摄取来源、事实、声明和真实锁定证据快照。"""
    # Compatibility entry only: the embedded legacy ``scientific_review`` is
    # input metadata, never an acceptance authority.  All new persistence uses
    # the shared candidate ingestion path; formal acceptance remains exclusively
    # in review_issuer + scientific_review_transition.
    from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence

    candidate_created_at = max(item.acquired_at for item in package.sources)
    candidate = ingest_research_evidence(
        project_root=project_root,
        project_id=project_id,
        contract_version=contract_version,
        report_kind="A",
        data_cutoff=package.data_cutoff,
        scientific_content_digest=package.research_content_digest,
        created_at=candidate_created_at,
        sources=package.sources,
        route_attempts=package.route_attempts,
        facts=package.facts,
        claims=package.claims,
    )
    claim_snapshot_id = stable_id(
        "claim-snapshot", project_id, package.research_content_digest,
        *candidate.claim_version_ids,
    )
    coverage_set_id = stable_id(
        "coverage-set", project_id, "A", candidate.evidence_snapshot.snapshot_id,
        claim_snapshot_id,
    )
    return ResearchLineage(
        package_digest=package.research_content_digest,
        evidence_snapshot=candidate.evidence_snapshot,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
        coverage_projection_id=stable_id("coverage-projection", coverage_set_id, "html"),
        claim_ids=candidate.claim_ids,
        source_version_ids=candidate.source_version_ids,
        source_fragment_ids=candidate.source_fragment_ids,
        fact_version_ids=candidate.fact_version_ids,
        fragment_ids=candidate.fragment_ids,
    )

def persist_report_a_projection(
    *,
    project_root: Path,
    lineage: ResearchLineage,
    manifest_path: Path,
) -> None:
    """把已生成门户反向绑定到报告快照与格式覆盖记录。"""
    manifest = ArtifactManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    if (
        manifest.evidence_snapshot_id != lineage.evidence_snapshot.snapshot_id
        or manifest.claim_snapshot_id != lineage.claim_snapshot_id
        or manifest.coverage_set_id != lineage.coverage_set_id
        or manifest.coverage_projection_id != lineage.coverage_projection_id
    ):
        raise ResearchPackageError("A 类门户清单未绑定当前新鲜来源谱系")
    report_snapshot_path = (
        project_root
        / "snapshots"
        / "reports"
        / "A"
        / f"{manifest.report_snapshot_id}.json"
    )
    report_snapshot = json.loads(report_snapshot_path.read_text(encoding="utf-8"))
    timestamp = manifest.generated_at.isoformat()
    with open_database(project_root / "state/project.sqlite") as database:
        database.execute(
            """
            INSERT OR IGNORE INTO report_snapshots (
                snapshot_id,project_id,report_kind,report_version,evidence_state,
                manifest_json,created_at
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                manifest.report_snapshot_id,
                manifest.project_id,
                "A",
                manifest.report_version,
                "snapshot_locked",
                json.dumps(report_snapshot, ensure_ascii=False, sort_keys=True),
                timestamp,
            ),
        )
        database.execute(
            """
            INSERT OR IGNORE INTO coverage_sets (
                coverage_set_id,snapshot_id,report_kind,coverage_json,created_at
            ) VALUES (?,?,?,?,?)
            """,
            (
                lineage.coverage_set_id,
                manifest.report_snapshot_id,
                "A",
                json.dumps(
                    {
                        "claim_ids": list(lineage.claim_ids),
                        "source_version_ids": list(lineage.source_version_ids),
                        "status": "complete",
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                timestamp,
            ),
        )
        database.execute(
            """
            INSERT OR IGNORE INTO coverage_projections (
                projection_id,coverage_set_id,output_format,projection_json,
                exception_json,created_at
            ) VALUES (?,?,?,?,?,?)
            """,
            (
                lineage.coverage_projection_id,
                lineage.coverage_set_id,
                "html",
                json.dumps(
                    {
                        "artifact": manifest.artifact.relative_path,
                        "artifact_sha256": manifest.artifact.sha256,
                        "status": "generated",
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "[]",
                timestamp,
            ),
        )
