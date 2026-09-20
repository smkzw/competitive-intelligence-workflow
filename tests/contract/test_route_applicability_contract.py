"""F4 合同：路线 ``not_applicable`` 必须携带适用性依据。

"明确不适用"与"未知/失败"是不同状态；不适用是被证据支持的裁决，
一个裸字符串不能让必查路线的闭包门变绿（v1.4 §6.1/§9）。
"""
from __future__ import annotations

import pytest

from ci_workflow.domain.research_package import RouteReceipt

_BASE = {
    "route_id": "china-registry",
    "region": "china",
    "strategy_id": "china-baseline",
    "attempt_ids": ["china-attempt-1"],
}


def test_not_applicable_without_basis_is_rejected() -> None:
    with pytest.raises(ValueError, match="适用性依据"):
        RouteReceipt.model_validate({**_BASE, "result_class": "not_applicable"})


def test_not_applicable_with_basis_is_accepted() -> None:
    receipt = RouteReceipt.model_validate({
        **_BASE,
        "result_class": "not_applicable",
        "diagnostic": "该适应症在中国无已上市创新竞品；经声明域政策逐条判定不适用",
    })
    assert receipt.result_class == "not_applicable"


def test_failed_route_still_requires_diagnostic() -> None:
    with pytest.raises(ValueError, match="诊断"):
        RouteReceipt.model_validate({**_BASE, "result_class": "network_error"})
