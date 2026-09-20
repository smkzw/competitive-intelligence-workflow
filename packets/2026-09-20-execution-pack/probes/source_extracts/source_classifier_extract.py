"""Transcribed source function, not a full repository checkout.
Source: src/ci_workflow/application/source_research_service.py @ d6cb6d51e1b5a5e2abdacea485ea84b5268dc7ca.
Git blob (full original file): 32e5883ce3d4e78b383117c77d4531e0290e761d.
"""
from __future__ import annotations


def _outcome_category(
    title: str, class_title: str = ""
) -> _ParsedOutcomeCategory | None:
    normalized = title.casefold()
    class_name = class_title.casefold()
    combined = f"{normalized} {class_name}"
    if class_name:
        if "aesi" in class_name or "adverse event of special interest" in class_name:
            return "aesi"
        if "serious" in class_name or class_name.strip() in {"sae", "saes", "serious aes"}:
            return "sae"
        if "teae" in class_name or "treatment emergent adverse event" in class_name:
            return "teae"
        if class_name.strip() in {"ae", "aes", "any ae", "any aes", "adverse events"}:
            return "teae"
    has_teae = "teae" in combined or "treatment-emergent adverse event" in combined
    has_sae = (
        "sae" in combined
        or "serious adverse event" in combined
        or "treatment-emergent serious" in combined
    )
    if "aesi" in combined or "adverse event of special interest" in combined:
        return "aesi"
    if has_teae and has_sae:
        class_is_sae = "sae" in class_name or "serious" in class_name
        class_is_teae = "teae" in class_name or (
            "adverse event" in class_name and not class_is_sae
        )
        if class_is_sae:
            return "sae"
        if class_is_teae or class_name.strip() in {"aes", "any aes"}:
            return "teae"
        return None
    if has_sae:
        return "sae"
    if has_teae:
        return "teae"
    return "outcome"
