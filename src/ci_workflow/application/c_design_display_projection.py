"""Bind whole-clause translations to existing source observations, display only.

This validates provenance, not clinical fidelity or acceptance. Translators and
reviewers remain outside this pure projection; no model route or new approval is
created. Original facts, source quotes, identities and snapshots stay unchanged.
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from ci_workflow.domain.enums import FactReviewState
from ci_workflow.renderers.portal.report_c import ReportCPortalData

_FIELDS = frozenset({
    "row_id", "source_version_id", "source_locator", "source_text_sha256", "display_text",
})


def apply_c_display_translations(
    report: ReportCPortalData, entries: Sequence[Mapping[str, object]],
) -> ReportCPortalData:
    """Return a new display candidate only after the whole packet binds exactly.

    Scope is one row's exact source version, locator and full original quote. A
    partial substring, matching drug name, current value or another row's quote
    does not bind. Text remains data and must be escaped by normal renderers.
    """
    by_id = {row.row_id: row for row in report.observations}
    if len(by_id) != len(report.observations):
        raise ValueError("中文呈现输入包含重复观察身份")
    translated: dict[str, str] = {}
    for entry in entries:
        if set(entry) != _FIELDS:
            raise ValueError("中文呈现包字段不符合来源绑定合同")
        row_id = entry["row_id"]
        if not isinstance(row_id, str) or row_id not in by_id or row_id in translated:
            raise ValueError("中文呈现包行身份未知或重复")
        row = by_id[row_id]
        if row.review_state is FactReviewState.USER_MODIFIED or row_id in report.user_edits:
            raise ValueError("来源译文不得覆盖用户当前修订")
        text = entry["display_text"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("中文呈现包缺少完整非空文本")
        if (
            entry["source_version_id"] != row.source_version_id
            or entry["source_locator"] != row.source_locator.model_dump(mode="json")
            or entry["source_text_sha256"] != hashlib.sha256(row.source_text.encode()).hexdigest()
        ):
            raise ValueError("中文呈现包与观察完整原文、定位或版本不一致")
        translated[row_id] = text
    observations = tuple(
        row.model_copy(update={"display_text": translated[row.row_id]})
        if row.row_id in translated else row
        for row in report.observations
    )
    return report.model_copy(update={"observations": observations})
