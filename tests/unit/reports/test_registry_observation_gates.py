"""会商 P0 #1 回归探针集：分类器适应症门闩红绿回归（2026-09-21）。

红组：跨适应症文本在指定适应症下不得命中他适应症族；
绿组：本适应症核心族照常命中；未提供 indication 时保持历史行为。
"""

from __future__ import annotations

import pytest

from ci_workflow.reports.b.registry_observation import classify_registry_endpoint


@pytest.mark.parametrize(
    ("text", "indication"),
    [
        ("Plasma Concentration of Atrasentan", "igan"),
        ("Factor Bb and C5b-9 Levels", "igan"),
        ("Sustained Remissions From Week 40 to Week 46", "igan"),
        ("IgA nephropathy proteinuria reduction", "atopic-dermatitis"),
    ],
)
def test_cross_indication_text_does_not_hit_foreign_families(text: str, indication: str) -> None:
    family = classify_registry_endpoint(text, indication_id=indication)
    assert family is None or family.startswith(("endpoint-igan-", "endpoint-generic-")), (
        f"{text!r} 在 {indication} 下误命中 {family}"
    )


@pytest.mark.parametrize(
    ("text", "indication", "expected_prefix"),
    [
        ("IgA nephropathy proteinuria reduction", "igan", "endpoint-igan-proteinuria-v1"),
        ("Urine Protein-Creatinine Ratio Reduction", "igan", "endpoint-igan-proteinuria-v1"),
        ("Albuminuria Reduction From Baseline", "igan", "endpoint-igan-proteinuria-v1"),
        ("UACR Change From Baseline", "igan", "endpoint-igan-proteinuria-v1"),
        ("Estimated GFR Change", "igan", "endpoint-igan-egfr-v1"),
        ("Hematuria Resolution", "igan", "endpoint-igan-hematuria-v1"),
        (
            "Clinical Remission Per Adapted Mayo Score",
            "ulcerative-colitis",
            "endpoint-uc-remission-v1",
        ),
        ("Percentage of Participants With Reduction in Serum LDH", "pnh", "endpoint-pnh-"),
        ("IGA 0/1 Response", "atopic-dermatitis", "endpoint-ad-iga-v1"),
    ],
)
def test_within_indication_families_still_match(
    text: str, indication: str, expected_prefix: str
) -> None:
    family = classify_registry_endpoint(text, indication_id=indication)
    assert family is not None, f"{text!r} 在 {indication} 下不应落入未分类"
    assert family.startswith(expected_prefix), f"{text!r} → {family}"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Sustained Remissions From Week 40 to Week 46", "endpoint-uc-remission-v1"),
    ],
)
def test_legacy_global_behavior_unchanged_without_indication(text: str, expected: str) -> None:
    assert classify_registry_endpoint(text) == expected
