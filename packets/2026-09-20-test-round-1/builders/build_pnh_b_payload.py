"""PNH B 载荷构建（LOOP 第十九轮）：从 A 载荷真实事实映射 B 门户输入。

疗效事实带 semantic_* 字段供语义裁决链；timeFrame 解析为数值周；
组别名取自原始 groups。诚实边界同 A（G11-1/G7-2/快照）。
"""
from __future__ import annotations

import os

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def _weeks(time_frame: str) -> tuple[float | None, str]:
    text = (time_frame or "").lower().replace("，", " ")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(day|week|month|year)", text)
    if not m:
        return None, "week"
    value, unit = float(m.group(1)), m.group(2)
    factor = {"day": 1 / 7, "week": 1.0, "month": 4.34524, "year": 52.1429}[unit]
    weeks = value * factor
    return weeks, unit


def main() -> None:
    a = json.loads((HERE / "pnh-a-payload.json").read_text(encoding="utf-8"))
    facts = []
    for row in a["efficacy"]:
        weeks, unit = _weeks(row.get("timepoint") or "")
        facts.append({
            "row_id": f"b-{row['row_id']}",
            "product_id": row["product_id"],
            "trial_id": row["trial_id"],
            "original_endpoint": row["endpoint"],
            "original_definition": row["endpoint"],
            "semantic_definition": row["endpoint"],
            "actual_timepoint": weeks if weeks is not None else row.get("timepoint", ""),
            "actual_timepoint_unit": unit,
            "analysis_form": "登记结果度量",
            "analysis_population": row.get("population", ""),
            "arm_label": row.get("arm", "组别未登记"),
            "unit": row.get("unit", ""),
            "value": row.get("value"),
            "direction": "higher_is_better",
            "estimand": "treatment_policy",
            "denominator_semantics": "登记分析集",
            "instrument_or_scale": "登记终点",
            "source_version_id": "ctgov-pnh-page-1",
        })
    payload = {
        "schema_version": "1.0",
        "report_version": "v1",
        "indication": "阵发性睡眠性血红蛋白尿症",
        "data_cutoff": "2026-09-20T23:59:59.999999+08:00",
        "products": a["products"],
        "trials": a["trials"],
        "efficacy": a["efficacy"],
        "safety": a["safety"],
        "regulatory": a["regulatory"],
        "companies": a["companies"],
        "patents": a["patents"],
        "history": a["history"],
        "sources": a["sources"],
        "efficacy_views": {"facts": facts},
    }
    out = HERE / "pnh-b-payload.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("facts:", len(facts), "| bytes:", out.stat().st_size)


if __name__ == "__main__":
    sys.exit(main())
