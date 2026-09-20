"""Public v1.3 intake and optional Yaozh boundary.

The public entry accepts a one-sentence request.  This module turns it into a
small typed intake object and a host-native report-type Ask when the request
omits A/B/C.  Yaozh is represented only by a project-level answer record; no
credential, cookie, token, or session material is accepted by these contracts.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.research_package import ReportName


class IntakeContractError(ValueError):
    """入口请求或项目级可选来源回答不符合合同。"""


class YaozhAskAlreadyAnswered(IntakeContractError):
    """同一新项目已经完成过药智访问条件询问。"""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _text(value: str, *, label: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{label}不能为空")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("时间必须包含明确时区")
    return value


class ReportTypeOption(_StrictModel):
    code: ReportName
    label_zh: str
    explanation_zh: str

    @field_validator("label_zh", "explanation_zh")
    @classmethod
    def _text_fields(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "字段")
        return _text(value, label=str(field_name))


REPORT_TYPE_OPTIONS: tuple[ReportTypeOption, ...] = (
    ReportTypeOption(
        code="A",
        label_zh="A：创新竞品与管线",
        explanation_zh="研究创新竞品、管线、作用机制，以及开发和监管状态。",
    ),
    ReportTypeOption(
        code="B",
        label_zh="B：临床结果比较",
        explanation_zh="研究临床疗效、安全性、基线、人群和结果差异。",
    ),
    ReportTypeOption(
        code="C",
        label_zh="C：试验设计图谱",
        explanation_zh="研究人群、终点、访视、入排标准和试验设计模式。",
    ),
)


class ReportTypeAsk(_StrictModel):
    question_zh: str
    options: tuple[ReportTypeOption, ...] = Field(min_length=3, max_length=3)
    response_required: Literal[True] = True

    @field_validator("question_zh")
    @classmethod
    def _question(cls, value: str) -> str:
        return _text(value, label="询问")

    @model_validator(mode="after")
    def _options_are_fixed(self) -> Self:
        if tuple(option.code for option in self.options) != ("A", "B", "C"):
            raise IntakeContractError("报告类型 Ask 必须按 A、B、C 顺序提供")
        return self


class PublicIntakeRequest(_StrictModel):
    """自然语言入口转换后的最小项目请求。"""

    schema_version: Literal["1.3"]
    user_request: str
    indication: str
    reports: tuple[ReportName, ...] = ()
    historical_cutoff: date | None = None
    default_cutoff: date
    autonomous_research: Literal[True] = True
    ask: ReportTypeAsk | None = None

    @field_validator("user_request", "indication")
    @classmethod
    def _text_fields(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "字段")
        return _text(value, label=str(field_name))

    @field_validator("reports")
    @classmethod
    def _reports_are_unique(cls, values: tuple[ReportName, ...]) -> tuple[ReportName, ...]:
        if len(values) != len(set(values)):
            raise IntakeContractError("报告类型不能重复")
        if not set(values) <= {"A", "B", "C"}:
            raise IntakeContractError("报告类型只能是 A、B、C")
        return values

    @model_validator(mode="after")
    def _ask_matches_missing_types(self) -> Self:
        if self.reports and self.ask is not None:
            raise IntakeContractError("已指定报告类型时不应重复发起 Ask")
        if not self.reports and self.ask is None:
            raise IntakeContractError("未指定报告类型时必须发起原生 Ask")
        return self


def build_public_intake(
    user_request: str,
    *,
    reports: tuple[ReportName, ...] | list[ReportName] | None = None,
    historical_cutoff: date | str | None = None,
    declared_on: date | None = None,
) -> PublicIntakeRequest:
    """Build an intake object without requiring technical configuration.

    ``reports=None`` deliberately remains a valid pending intake and carries
    the exact three explanatory options for the host's native Ask surface.
    """

    normalized_request = _text(user_request, label="用户请求")
    normalized_reports = tuple(reports or ())
    indication = _extract_indication(normalized_request)
    default_cutoff = declared_on or date.today()
    parsed_cutoff = (
        date.fromisoformat(historical_cutoff)
        if isinstance(historical_cutoff, str)
        else historical_cutoff
    )
    ask = None
    if not normalized_reports:
        ask = ReportTypeAsk(
            question_zh="您希望查看哪类竞品调研？可选择一个或多个。",
            options=REPORT_TYPE_OPTIONS,
        )
    return PublicIntakeRequest(
        schema_version="1.3",
        user_request=normalized_request,
        indication=indication,
        reports=normalized_reports,
        historical_cutoff=parsed_cutoff,
        default_cutoff=default_cutoff,
        ask=ask,
    )


def _extract_indication(user_request: str) -> str:
    """Keep natural-language parsing conservative; callers may pass a plain name."""

    normalized = user_request
    for marker in (
        "请做",
        "请进行",
        "的竞品调研",
        "竞品调研",
        "的 A、B、C",
        "的 A、B",
        "的 A",
        "的 B",
        "的 C",
    ):
        normalized = normalized.replace(marker, " ")
    normalized = " ".join(normalized.replace("A、B、C", "").split())
    return normalized.strip(" 的。,，") or user_request


YaozhAnswer = Literal["available", "unavailable", "skipped"]


class YaozhAccessRecord(_StrictModel):
    """一次且仅一次的项目级药智访问条件回答。"""

    schema_version: Literal["1.0"]
    project_id: str
    answer: YaozhAnswer
    asked_at: datetime
    ask_count: Literal[1] = 1
    route_enabled: bool
    source_role_zh: Literal["可选线索与交叉核验来源"] = "可选线索与交叉核验来源"

    @field_validator("project_id")
    @classmethod
    def _project_id(cls, value: str) -> str:
        return _text(value, label="project_id")

    @field_validator("asked_at")
    @classmethod
    def _asked_at(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @model_validator(mode="after")
    def _route_is_optional(self) -> Self:
        if self.answer == "available" and not self.route_enabled:
            raise IntakeContractError("具备药智访问条件时可选路线必须启用")
        if self.answer != "available" and self.route_enabled:
            raise IntakeContractError("未具备药智访问条件时不得启用路线")
        return self


class YaozhRouteDecision(_StrictModel):
    enabled: bool
    route_id: Literal["yaozh-optional-browser"]
    rationale_zh: str
    blocks_core_research: Literal[False] = False

    @field_validator("rationale_zh")
    @classmethod
    def _rationale(cls, value: str) -> str:
        return _text(value, label="药智路线说明")


def record_yaozh_answer(
    project_id: str,
    answer: YaozhAnswer,
    *,
    existing: YaozhAccessRecord | None = None,
    asked_at: datetime | None = None,
) -> YaozhAccessRecord:
    """Record one project answer; same-answer replay is idempotent."""

    if existing is not None:
        if existing.project_id != project_id:
            raise IntakeContractError("药智回答与当前项目身份不一致")
        if existing.answer == answer:
            return existing
        raise YaozhAskAlreadyAnswered("同一项目的药智访问条件只能询问一次")
    return YaozhAccessRecord(
        schema_version="1.0",
        project_id=project_id,
        answer=answer,
        asked_at=asked_at or datetime.now(UTC),
        route_enabled=answer == "available",
    )


def yaozh_route_decision(record: YaozhAccessRecord) -> YaozhRouteDecision:
    if record.route_enabled:
        return YaozhRouteDecision(
            enabled=True,
            route_id="yaozh-optional-browser",
            rationale_zh="药智网仅用于身份、别名、中国状态和线索交叉核验；核心数值仍需适格官方来源。",
        )
    return YaozhRouteDecision(
        enabled=False,
        route_id="yaozh-optional-browser",
        rationale_zh="本项目未启用药智网可选路线；其他适格来源继续完成核心研究。",
    )


__all__ = [
    "IntakeContractError",
    "PublicIntakeRequest",
    "REPORT_TYPE_OPTIONS",
    "ReportTypeAsk",
    "ReportTypeOption",
    "YaozhAccessRecord",
    "YaozhAskAlreadyAnswered",
    "YaozhRouteDecision",
    "build_public_intake",
    "record_yaozh_answer",
    "yaozh_route_decision",
]
