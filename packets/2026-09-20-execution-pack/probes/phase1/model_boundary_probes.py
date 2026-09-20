"""Isolated model probes for competitive-intelligence-workflow.

Scope: the model definitions below are transcribed from GitHub source excerpts
read at commit d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca. This is NOT a checkout,
NOT the repository test suite, and NOT an end-to-end run.
Sources:
  src/ci_workflow/renderers/portal/report_a.py
    blob 2009cb552de2bf8cf2785e21145fa6f83d404fed (lines 73-171 area)
  src/ci_workflow/domain/enums.py
    blob bf5d6faa46a62a3f1b753e89a9ea163a214fed21
The relevant field and validator bodies are retained; imports are standalone.
Run: python model_boundary_probes.py
"""
from __future__ import annotations
import json
from enum import Enum
from typing import Literal
import pydantic
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

class FactDisclosureState(Enum):
    REPORTED_VALUE = "reported_value"
    REPORTED_ZERO = "reported_zero"
    NOT_REPORTED = "not_reported"
    BELOW_REPORTING_THRESHOLD = "below_reporting_threshold"
    NOT_PUBLICLY_DISCLOSED = "not_publicly_disclosed"
    NOT_APPLICABLE = "not_applicable"
    CONFLICTING = "conflicting"
    UNRESOLVED_DUE_TO_ROUTE = "unresolved_due_to_route"

class TrialRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    display_id: str
    product_id: str
    name: str
    phase: str
    region: str
    status: str
    sample_size: int = Field(gt=0)
    treatment_sample_size: int | None = Field(default=None, gt=0)
    role: str

    @model_validator(mode="after")
    def _treatment_group_cannot_exceed_trial(self) -> TrialRow:
        if self.treatment_sample_size is not None and self.treatment_sample_size > self.sample_size:
            raise ValueError("治疗组样本量不得大于试验总样本量")
        return self

class EfficacyRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_id: str
    product_id: str
    trial_id: str
    endpoint: str
    timepoint: str
    arm: str
    arm_detail: str | None = None
    value: float | None = Field(default=None, allow_inf_nan=False)
    # G10-2：登记/来源存在该终点但未披露数值时保留状态行；禁止伪装数值。
    disclosure_state: FactDisclosureState = FactDisclosureState.REPORTED_VALUE
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, gt=0)
    unit: str
    population: str

    @model_validator(mode="after")
    def _undisclosed_row_carries_no_value(self) -> EfficacyRow:
        if self.disclosure_state != FactDisclosureState.REPORTED_VALUE and self.value is not None:
            raise ValueError("未披露状态行不得携带数值")
        if self.disclosure_state == FactDisclosureState.REPORTED_VALUE and self.value is None:
            raise ValueError("已报告数值行必须携带数值")
        return self

    @model_validator(mode="after")
    def _counts_are_complete_and_ordered(self) -> EfficacyRow:
        if (self.numerator is None) != (self.denominator is None):
            raise ValueError("疗效分子与分母必须同时公开或同时缺失")
        if (
            self.numerator is not None
            and self.denominator is not None
            and self.numerator > self.denominator
        ):
            raise ValueError("疗效分子不得大于分母")
        return self

class SafetyRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_id: str
    product_id: str
    trial_id: str | None = None
    arm: str = "治疗组"
    arm_detail: str | None = None
    category: str
    term: str
    value: float | None = Field(allow_inf_nan=False)
    numerator: int | None = Field(default=None, ge=0)
    denominator: int | None = Field(default=None, gt=0)
    unit: str
    time_window: str
    disclosure_state: Literal["已公开", "未公开", "不适用"] = "已公开"

    @model_validator(mode="after")
    def _value_matches_disclosure_state(self) -> SafetyRow:
        if self.disclosure_state == "已公开" and self.value is None:
            raise ValueError("已公开安全性记录必须包含数值")
        if self.disclosure_state == "未公开" and self.value is not None:
            raise ValueError("未公开安全性记录不得填入推测数值")
        if (self.numerator is None) != (self.denominator is None):
            raise ValueError("安全性分子与分母必须同时公开或同时缺失")
        if (
            self.numerator is not None
            and self.denominator is not None
            and self.numerator > self.denominator
        ):
            raise ValueError("安全性分子不得大于分母")
        return self


def probe(name: str, model: type[BaseModel], payload: dict, expected: str) -> dict:
    try:
        result = model.model_validate(payload)
    except ValidationError as exc:
        return {"case": name, "observed": "rejected", "expected_semantics": expected,
                "errors": [{"loc": list(e["loc"]), "type": e["type"], "msg": e["msg"]}
                           for e in exc.errors()]}
    return {"case": name, "observed": "accepted", "expected_semantics": expected,
            "parsed": result.model_dump(mode="json")}


def main() -> None:
    efficacy = dict(row_id="r-1", product_id="p-1", trial_id="t-1", endpoint="test endpoint",
                    timepoint="week 24", arm="treatment", unit="%", population="ITT")
    safety = dict(row_id="s-1", product_id="p-1", category="test", term="test",
                  unit="%", time_window="week 0-24")
    trial = dict(id="t-1", display_id="TEST", product_id="p-1", name="test trial",
                 phase="phase 2", region="global", status="withdrawn", role="test")
    cases = [
        probe("reported_zero_with_0", EfficacyRow,
              efficacy | {"disclosure_state": "reported_zero", "value": 0},
              "accepted: an explicitly reported zero must retain numeric zero"),
        probe("reported_zero_with_null", EfficacyRow,
              efficacy | {"disclosure_state": "reported_zero", "value": None},
              "rejected: reported_zero cannot be represented as a missing numeric value"),
        probe("reported_value_with_0_control", EfficacyRow,
              efficacy | {"disclosure_state": "reported_value", "value": 0},
              "accepted: numeric zero is valid as a reported value"),
        probe("not_applicable_with_numeric_safety_value", SafetyRow,
              safety | {"disclosure_state": "不适用", "value": 12.5},
              "requires rejection or an explicitly separate non-applicable-measure contract"),
        probe("trial_actual_enrollment_0", TrialRow, trial | {"sample_size": 0},
              "product decision: preserve a known-zero-enrollment trial in the full universe"),
        probe("trial_unknown_enrollment", TrialRow, trial | {"sample_size": None},
              "product decision: preserve an otherwise in-scope trial with enrollment unknown"),
    ]
    print(json.dumps({"commit": "d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca",
                      "scope": "isolated transcribed source-model probes; not repository tests",
                      "pydantic_version": pydantic.__version__, "cases": cases},
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
