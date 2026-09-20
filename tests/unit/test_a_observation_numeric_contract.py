import pytest
from pydantic import ValidationError

from ci_workflow.renderers.portal.report_a import EfficacyRow, SafetyRow


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("kind", ["efficacy", "safety"])
def test_nonfinite_observations_are_rejected_before_render(kind: str, value: float) -> None:
    common = {"row_id": "row", "product_id": "product", "trial_id": "trial", "value": value,
              "unit": "%", "arm": "治疗组"}
    with pytest.raises(ValidationError):
        if kind == "efficacy":
            EfficacyRow.model_validate({**common, "endpoint": "应答率", "timepoint": "第12周",
                                       "population": "分析集"})
        else:
            SafetyRow.model_validate({**common, "category": "总体安全性", "term": "任何TEAE",
                                      "time_window": "第1至12周"})
