from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, time
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ci_workflow.domain.enums import OutputFormat, ReportKind
from ci_workflow.domain.ids import stable_id


class ProjectContract(BaseModel):
    """创建时冻结、恢复时不漂移的项目合同版本。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    contract_version: int = Field(ge=1)
    project_id: str
    indication: str
    reports: tuple[ReportKind, ...]
    outputs: tuple[OutputFormat, ...]
    timezone: str
    data_cutoff: datetime
    cutoff_was_user_supplied: bool
    created_at: datetime

    @field_validator("indication")
    @classmethod
    def _indication_is_not_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("适应症不能为空")
        return normalized

    @field_validator("timezone")
    @classmethod
    def _timezone_is_iana(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("时区必须是有效的 IANA 时区") from exc
        return value


    @field_validator("reports")
    @classmethod
    def _reports_are_nonempty_unique(
        cls, value: tuple[ReportKind, ...]
    ) -> tuple[ReportKind, ...]:
        if not value:
            raise ValueError("请至少选择一种报告")
        if len(value) != len(set(value)):
            raise ValueError("报告类型不能重复")
        return value

    @field_validator("outputs")
    @classmethod
    def _outputs_are_html_only(
        cls, value: tuple[OutputFormat, ...]
    ) -> tuple[OutputFormat, ...]:
        if value != (OutputFormat.HTML,):
            raise ValueError("首版交付格式必须严格为 html")
        return value

    @field_validator("data_cutoff", "created_at")
    @classmethod
    def _datetimes_have_offsets(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("日期时间必须包含明确时区偏移")
        return value


def project_contract_format_checker() -> FormatChecker:
    """返回包含项目合同自定义 IANA 时区检查的格式检查器。"""

    checker = FormatChecker()

    def is_iana_timezone(value: object) -> bool:
        if not isinstance(value, str):
            return False
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError:
            return False
        return True

    checker.checkers["iana-timezone"] = (is_iana_timezone, ())
    return checker


def validate_project_contract_document(
    payload: Mapping[str, Any], schema: Mapping[str, Any]
) -> ProjectContract:
    """以同一生产入口执行 JSON Schema 和 Pydantic 双重合同验证。"""

    Draft202012Validator(
        schema,
        format_checker=project_contract_format_checker(),
    ).validate(dict(payload))
    return ProjectContract.model_validate(payload)


def _parse_reports(values: list[str]) -> tuple[ReportKind, ...]:
    try:
        reports = tuple(ReportKind(value) for value in values)
    except ValueError as exc:
        raise ValueError("报告类型只允许 A、B、C") from exc
    if len(reports) != len(set(reports)):
        raise ValueError("报告类型不能重复")
    return reports


def _parse_outputs(values: list[str]) -> tuple[OutputFormat, ...]:
    if values != ["html"]:
        raise ValueError("首版交付格式必须严格为 html")
    return (OutputFormat.HTML,)


def _local_date(value: str | date | datetime, timezone: ZoneInfo) -> date:
    if isinstance(value, datetime):
        localized = (
            value.replace(tzinfo=timezone)
            if value.tzinfo is None
            else value.astimezone(timezone)
        )
        return localized.date()
    if isinstance(value, date):
        return value
    try:
        if "T" in value:
            parsed = datetime.fromisoformat(value)
            localized = (
                parsed.replace(tzinfo=timezone)
                if parsed.tzinfo is None
                else parsed.astimezone(timezone)
            )
            return localized.date()
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("数据截止日必须是 ISO 日期或日期时间") from exc


def create_project_contract(
    *,
    indication: str,
    reports: list[str],
    outputs: list[str],
    timezone: str = "Asia/Shanghai",
    cutoff: str | date | datetime | None = None,
    created_at: datetime | None = None,
    contract_version: int = 1,
) -> ProjectContract:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("时区必须是有效的 IANA 时区") from exc
    created = datetime.now(zone) if created_at is None else created_at
    if created.tzinfo is None or created.utcoffset() is None:
        raise ValueError("项目创建时间必须包含明确时区偏移")
    created = created.astimezone(zone)
    cutoff_date = created.date() if cutoff is None else _local_date(cutoff, zone)
    if cutoff_date > created.date():
        raise ValueError("数据截止日不能晚于项目合同创建日")
    cutoff_at = datetime.combine(cutoff_date, time.max, tzinfo=zone)
    parsed_reports = _parse_reports(reports)
    parsed_outputs = _parse_outputs(outputs)
    normalized_indication = " ".join(indication.split())
    project_id = stable_id(
        "project",
        normalized_indication,
        created.isoformat(),
        ",".join(item.value for item in parsed_reports),
    )
    return ProjectContract(
        contract_version=contract_version,
        project_id=project_id,
        indication=normalized_indication,
        reports=parsed_reports,
        outputs=parsed_outputs,
        timezone=timezone,
        data_cutoff=cutoff_at,
        cutoff_was_user_supplied=cutoff is not None,
        created_at=created,
    )


def resume_project_contract(
    contract: ProjectContract, *, resumed_at: datetime | None = None
) -> ProjectContract:
    """恢复同一合同版本；时间参数只用于调用方审计，不改变科学边界。"""

    if resumed_at is not None and (resumed_at.tzinfo is None or resumed_at.utcoffset() is None):
        raise ValueError("恢复时间必须包含明确时区偏移")
    return contract


def refresh_project_contract(
    contract: ProjectContract,
    *,
    cutoff: str | date | datetime,
    created_at: datetime,
) -> ProjectContract:
    """扩大数据截止日并创建新合同版本，不改写原版本。"""

    zone = ZoneInfo(contract.timezone)
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("刷新合同创建时间必须包含明确时区偏移")
    created = created_at.astimezone(zone)
    cutoff_date = _local_date(cutoff, zone)
    if cutoff_date <= contract.data_cutoff.astimezone(zone).date():
        raise ValueError("刷新后的数据截止日必须晚于当前合同")
    if cutoff_date > created.date():
        raise ValueError("数据截止日不能晚于刷新合同创建日")
    return ProjectContract(
        schema_version=contract.schema_version,
        contract_version=contract.contract_version + 1,
        project_id=contract.project_id,
        indication=contract.indication,
        reports=contract.reports,
        outputs=contract.outputs,
        timezone=contract.timezone,
        data_cutoff=datetime.combine(cutoff_date, time.max, tzinfo=zone),
        cutoff_was_user_supplied=True,
        created_at=created,
    )
