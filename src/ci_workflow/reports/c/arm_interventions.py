"""Project CT.gov interventions onto arms only through explicit labels."""
from __future__ import annotations

from collections.abc import Mapping, Sequence


def project_arm_interventions(
    *, trial_id: str, arms: Sequence[Mapping[str, object]],
    interventions: Sequence[Mapping[str, object]],
) -> tuple[dict[str, object], ...]:
    arm_ids = {
        str(arm.get("label") or ""): f"arm{index}"
        for index, arm in enumerate(arms, start=1)
        if str(arm.get("label") or "").strip()
    }
    rows: list[dict[str, object]] = []
    for intervention_index, intervention in enumerate(interventions):
        labels = intervention.get("armGroupLabels") or ()
        base = {
            "trial_id": trial_id,
            "intervention_name": str(intervention.get("name") or ""),
            "description": str(intervention.get("description") or ""),
            "relationship_basis": "armGroupLabels",
            "intervention_index": intervention_index,
        }
        if not isinstance(labels, (list, tuple)) or not labels:
            rows.append({**base, "group_id": None, "arm_label": "",
                         "relationship_status": "missing_arm_labels", "blocking": True})
            continue
        for label in labels:
            group_id = arm_ids.get(str(label))
            if group_id is None:
                rows.append({**base, "group_id": None, "arm_label": str(label),
                             "relationship_status": "unknown_arm_label", "blocking": True})
                continue
            rows.append({**base,
                "group_id": group_id,
                "arm_label": str(label),
                "relationship_status": "bound",
                "blocking": False,
            })
    return tuple(rows)
