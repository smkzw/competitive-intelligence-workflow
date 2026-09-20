"""P3.5-1 合同：疗效页初始分区由科学层（版本化政策）供给，渲染器只服从。

科学分区的来源是 reports/b/portal_science.efficacy_science_partition：
命中政策的观察按 build_efficacy_views 的兼容桶进入初始分组；渲染器
不得用本地文本键替代该裁决（v1.4 §9）。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ci_workflow.renderers.portal import report_b as rb
from ci_workflow.reports.b.portal_science import efficacy_science_partition
from tests.reports.b.test_r13_semantic_grouping import _project_efficacy


def _full_row(
    row_id: str,
    *,
    trial_id: str,
    timepoint: int,
    endpoint: str = "easi75",
    definition: str = "EASI-75 应答者比例",
) -> dict[str, object]:
    row = _project_efficacy(row_id, endpoint, timepoint=timepoint)
    row.update(
        {
            "trial_id": trial_id,
            "original_endpoint": endpoint,
            "semantic_definition": definition,
            "original_definition": definition,
            "semantic_direction": "higher_is_better",
            "direction": "higher_is_better",
            "arm_role": "treatment",
            "unit": "%",
            "analysis_form": "response_rate",
            "actual_timepoint_unit": "week",
            "source_version_id": f"source-{row_id}",
            "source_locator": {
                "document_role": "trial-results",
                "table": "Table 1",
                "row": row_id,
            },
        }
    )
    return row


def test_policy_decides_near_window_compatibility_key() -> None:
    """48/50 周由版本化时间窗政策裁为同一兼容窗（week-52），而非本地文本判断。"""
    rows = [
        _full_row("r48", trial_id="trial-a", timepoint=48),
        _full_row("r50", trial_id="trial-b", timepoint=50),
    ]
    partition = efficacy_science_partition([(dict(row), None) for row in rows])
    assert not partition.unmatched
    assert len(partition.buckets) == 2  # 实际时间点不同，科学分组保留原值
    keys = {key[1] for key in partition.bucket_keys}
    assert keys == {"endpoint-easi75-response-v1/timepoint-week-52-v1"}


def test_unmatched_rows_are_retained_not_dropped() -> None:
    """缺方向/终点的观察进入 unmatched 描述性路径，记录数守恒。"""
    good = _full_row("ok", trial_id="trial-a", timepoint=48)
    no_direction = dict(good, row_id="nodir", semantic_direction="", direction="")
    no_endpoint = dict(
        good, row_id="noend", original_endpoint="", clinical_concept="", endpoint_id="",
    )
    records = [(dict(row), None) for row in (good, no_direction, no_endpoint)]
    partition = efficacy_science_partition(records)
    total = (
        sum(len(bucket) for bucket in partition.buckets)
        + len(partition.unmatched)
    )
    assert total == 3
    assert {row[0]["row_id"] for row in partition.unmatched} == {"nodir", "noend"}


def test_renderer_defers_to_science_membership(monkeypatch: pytest.MonkeyPatch) -> None:
    """疗效页分组服从科学层成员裁决：合并与否由成员输出决定（P3.5-3 接缝）。"""
    rows = [
        _full_row("w12", trial_id="trial-a", timepoint=12),
        _full_row("w24", trial_id="trial-a", timepoint=24),
    ]
    records = [(dict(row, _domain="efficacy"), None) for row in rows]

    def fake_membership(domain, recs, **_kwargs):
        assert domain == "efficacy"
        return (tuple(records),)

    monkeypatch.setattr(rb, "adjudicate_comparable_membership", fake_membership)
    merged = rb._groups_for_page("efficacy", list(records))
    assert len(merged) == 1, "科学层合并的成员渲染器不得拆开"

    def fake_split(domain, recs, **_kwargs):
        return ((records[0],), (records[1],))

    monkeypatch.setattr(rb, "adjudicate_comparable_membership", fake_split)
    split = rb._groups_for_page("efficacy", list(records))
    assert len(split) == 2, "科学层拆开的成员渲染器不得合并"


def test_render_report_consumes_science_membership(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """真实渲染路径必须调用科学层成员裁决（不是仅单元函数可用）。"""
    from tests.browser.test_b_semantic_proposals import proposal_data

    calls: list[str] = []
    real = rb.adjudicate_comparable_membership

    def counting(domain, recs, **kwargs):
        calls.append(domain)
        return real(domain, recs, **kwargs)

    monkeypatch.setattr(rb, "adjudicate_comparable_membership", counting)
    rb.render_report_b_site(proposal_data(), tmp_path / "site")
    assert "efficacy" in calls, "render_report_b_site 未消费科学层成员裁决"
    assert "safety" in calls
