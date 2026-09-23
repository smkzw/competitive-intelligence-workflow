"""Typed numeric projection shared by report A/B/C portal consumers.

Raw values remain untouched.  This module only decides whether a value is
eligible for a particular visual facet and, when justified, computes the
display value.  It deliberately does not infer participant rates from event
counts or from a participant count without an explicit denominator.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import StrEnum


class NumericMeasureKind(StrEnum):
    PARTICIPANT_PROPORTION = "participant_proportion"
    CONTINUOUS_MEASURE = "continuous_measure"
    PARTICIPANT_COUNT = "participant_count"
    EVENT_COUNT = "event_count"
    PERSON_TIME_RATE = "person_time_rate"
    ADJUSTED_ESTIMATE = "adjusted_estimate"
    SAMPLE_SIZE = "sample_size"


@dataclass(frozen=True)
class NumericProjection:
    kind: NumericMeasureKind
    raw_value: int | float | None
    raw_unit: str
    plot_value: float | None
    plot_unit: str
    numerator: int | float | None
    denominator: int | float | None
    direction: str
    window: str
    estimand: str
    renderable: bool
    unrenderable_reason: str | None
    size_value: float | None = None
    size_basis: str | None = None

    @property
    def facet_key(self) -> str:
        return "|".join(
            (self.kind.value, self.plot_unit, self.direction, self.window, self.estimand)
        )

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        payload["facet_key"] = self.facet_key
        return payload


def project_numeric(
    *,
    value: int | float | None,
    unit: str,
    kind: NumericMeasureKind | str,
    numerator: int | float | None = None,
    denominator: int | float | None = None,
    direction: str = "",
    window: str = "",
    estimand: str = "",
    size_value: int | float | None = None,
    size_basis: str | None = None,
) -> NumericProjection:
    kind = NumericMeasureKind(kind)
    if value is not None and (isinstance(value, bool) or not math.isfinite(float(value))):
        raise ValueError("数值投影只接受有限数值")
    if numerator is not None and (isinstance(numerator, bool) or numerator < 0):
        raise ValueError("分子必须是非负数")
    if denominator is not None and (isinstance(denominator, bool) or denominator <= 0):
        raise ValueError("分母必须是正数")
    reason: str | None = None
    plot_value = None if value is None else float(value)
    plot_unit = str(unit or "")
    if kind is NumericMeasureKind.PARTICIPANT_PROPORTION:
        if numerator is not None and denominator is not None:
            if numerator > denominator:
                raise ValueError("人数比例的分子不得大于分母")
            plot_value = float(numerator) / float(denominator) * 100.0
            plot_unit = "%"
        elif plot_unit in {"%", "百分比"} and value is not None:
            plot_unit = "%"
        else:
            plot_value = None
            reason = "participant_proportion_requires_percent_or_n_over_N"
    elif kind is NumericMeasureKind.EVENT_COUNT:
        plot_unit = plot_unit or "次"
    elif kind in {NumericMeasureKind.PARTICIPANT_COUNT, NumericMeasureKind.SAMPLE_SIZE}:
        plot_unit = plot_unit or "人"
    elif kind is NumericMeasureKind.PERSON_TIME_RATE:
        if not plot_unit or not any(
            token in plot_unit.casefold() for token in ("人年", "person", "/")
        ):
            plot_value = None
            reason = "person_time_rate_requires_reported_rate_unit"
    elif kind is NumericMeasureKind.ADJUSTED_ESTIMATE and not estimand:
        plot_value = None
        reason = "adjusted_estimate_requires_estimand"
    if value is None and reason is None:
        reason = "missing_numeric_value"
    renderable = plot_value is not None and reason is None
    return NumericProjection(
        kind=kind,
        raw_value=value,
        raw_unit=str(unit or ""),
        plot_value=plot_value,
        plot_unit=plot_unit,
        numerator=numerator,
        denominator=denominator,
        direction=str(direction or ""),
        window=str(window or ""),
        estimand=str(estimand or ""),
        renderable=renderable,
        unrenderable_reason=reason,
        size_value=None if size_value is None else float(size_value),
        size_basis=size_basis,
    )


def compatible(left: NumericProjection, right: NumericProjection) -> bool:
    return left.renderable and right.renderable and left.facet_key == right.facet_key


def infer_numeric_kind(
    *, measure_object: str = "", statistic_form: str = "", unit: str = "", domain: str = ""
) -> NumericMeasureKind:
    text = " ".join((measure_object, statistic_form, unit)).casefold()
    if any(token in text for token in ("person_time", "人年", "patient-year", "person-year")):
        return NumericMeasureKind.PERSON_TIME_RATE
    if any(
        token in text for token in ("adjusted", "ls mean", "hazard ratio", "odds ratio", "调整")
    ):
        return NumericMeasureKind.ADJUSTED_ESTIMATE
    if (
        any(token in text for token in ("event_count", "num_events", "事件次数", "次数"))
        or unit == "次"
    ):
        return NumericMeasureKind.EVENT_COUNT
    if any(token in text for token in ("sample_size", "样本量")):
        return NumericMeasureKind.SAMPLE_SIZE
    if (
        any(token in text for token in ("participant_count", "num_affected", "人数"))
        and "%" not in unit
    ):
        return NumericMeasureKind.PARTICIPANT_COUNT
    if domain == "efficacy" and unit.strip() and unit.strip() not in {"%", "百分比"}:
        # A reported score, laboratory value or other continuous endpoint is
        # not a participant proportion. Its raw unit and estimand stay in the
        # facet identity; no conversion or cross-trial normalization occurs.
        return NumericMeasureKind.CONTINUOUS_MEASURE
    if domain in {"efficacy", "safety"}:
        return NumericMeasureKind.PARTICIPANT_PROPORTION
    return NumericMeasureKind.PARTICIPANT_COUNT


def projected_difference(
    left: NumericProjection, right: NumericProjection | None
) -> NumericProjection:
    if (
        right is None
        or not compatible(left, right)
        or left.plot_value is None
        or right.plot_value is None
    ):
        return NumericProjection(
            kind=left.kind,
            raw_value=None,
            raw_unit=left.raw_unit,
            plot_value=None,
            plot_unit=left.plot_unit,
            numerator=None,
            denominator=None,
            direction=left.direction,
            window=left.window,
            estimand=left.estimand,
            renderable=False,
            unrenderable_reason="missing_or_incompatible_control",
            size_value=left.size_value,
            size_basis=left.size_basis,
        )
    return NumericProjection(
        kind=left.kind,
        raw_value=None,
        raw_unit=left.raw_unit,
        plot_value=float(left.plot_value) - float(right.plot_value),
        plot_unit=left.plot_unit,
        numerator=None,
        denominator=None,
        direction=left.direction,
        window=left.window,
        estimand=left.estimand,
        renderable=True,
        unrenderable_reason=None,
        size_value=left.size_value,
        size_basis=left.size_basis,
    )
