"""Fail explicitly until historical source-version eligibility is implemented in M5."""
from __future__ import annotations


class HistoricalReportUnavailable(ValueError):
    pass


def require_supported_cutoff(cutoff_date: str | None) -> None:
    if cutoff_date:
        raise HistoricalReportUnavailable('历史截止日报告暂不可用：证据版本筛选尚未接通，请留空日期生成当前报告。')
