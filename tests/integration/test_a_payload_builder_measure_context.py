"""Measure-level arm and denominator identity in the generic A builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_builder_uses_measure_group_and_rejects_conflicting_denominators(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    cas = tmp_path / "cas" / "evidence" / "raw" / "sha256" / "aa"
    cas.mkdir(parents=True)
    measures = []
    for title, group_title, denoms, value in (
        ("Response A", "Drug 10 mg (TP1)", [30, 30], "7"),
        ("Response B", "Drug 10 mg (TP2)", [20, 25], "5"),
    ):
        measures.append({
            "title": title, "timeFrame": "Week 4", "unitOfMeasure": "Participants",
            "groups": [{"id": "OG1", "title": group_title}],
            "denoms": [
                {"counts": [{"groupId": "OG1", "value": str(count)}]}
                for count in denoms
            ],
            "classes": [{"categories": [{"measurements": [
                {"groupId": "OG1", "value": value},
            ]}]}],
        })
    for title, unit, value in (
        ("Number of Participants With Treatment-emergent Adverse Events (TEAEs)",
         "Participants", "8"),
        ("Number of Events With Adverse Events", "Events", "41"),
        ("Percentage of Participants With Serious Adverse Events (SAEs)",
         "Percentage of participants", "20"),
        ("Number of Participants With TEAEs and Serious Adverse Events (SAEs)",
         "Participants", "9"),
    ):
        is_first_safety = title.startswith("Number of Participants With Treatment-emergent")
        measures.append({
            "title": title, "timeFrame": "Week 4", "unitOfMeasure": unit,
            "groups": [{"id": "OG1", "title": "Drug 10 mg (TP1)"}],
            "denoms": [{"counts": [{"groupId": "OG1", "value": "30"}]}],
            "classes": [{"title": "Week 4" if is_first_safety else "",
                         "categories": [{"title": "Any" if is_first_safety else "",
                                         "measurements": [
                {"groupId": "OG1", "value": value},
            ]}]}],
        })
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001", "briefTitle": "Test trial"},
            "designModule": {"enrollmentInfo": {"count": 50}},
            "armsInterventionsModule": {
                "interventions": [{"name": "Testdrug", "type": "DRUG"}],
                "armGroups": [{"label": "Testdrug", "type": "EXPERIMENTAL"}],
            },
        },
        "resultsSection": {
            "outcomeMeasuresModule": {
                "groups": [{"id": "OG1", "title": "Trial-level generic group"}],
                "outcomeMeasures": measures,
            },
            "adverseEventsModule": {
                "timeFrame": "Week 1 to Week 4",
                "eventGroups": [
                    {"title": "Drug 10 mg", "deathsNumAffected": 2,
                     "deathsNumAtRisk": 30},
                    {"title": "Comparator", "seriousNumAffected": 0,
                     "seriousNumAtRisk": 20},
                ],
            },
        },
    }
    (cas / "page.bin").write_text(json.dumps({"studies": [record]}), encoding="utf-8")
    alias = tmp_path / "alias.json"
    alias.write_text(json.dumps({
        "map_id": "synthetic-v1", "canonical_by_alias": {"Testdrug": "testdrug"},
    }), encoding="utf-8")
    output = tmp_path / "a-payload.json"
    subprocess.run([
        sys.executable, str(root / "tools/build_a_payload.py"),
        "--cas-dir", str(tmp_path / "cas"), "--alias-map", str(alias),
        "--indication", "合成适应症", "--indication-id", "synthetic",
        "--output", str(output), "--cutoff", "2026-09-06",
    ], cwd=root, check=True, capture_output=True, text=True)
    payload = json.loads(output.read_text(encoding="utf-8"))
    rows = payload["efficacy"]
    assert [(row["endpoint"], row["arm"], row["denominator"]) for row in rows] == [
        ("Response A", "Drug 10 mg (TP1)", 30),
        ("Response B", "Drug 10 mg (TP2)", None),
    ]
    assert all(row["group_id"] == "OG1" for row in rows)
    derivation = json.loads(
        output.with_name("a-payload.derivation.json").read_text(encoding="utf-8")
    )
    assert derivation["denominator_conflicts"] == [{
        "trial_id": "nct00000001", "endpoint": "Response B", "group_id": "OG1",
    }]
    safety = payload["safety"]
    assert len(safety) == 6
    assert [(item["unit"], item["measure_object"], item["value"]) for item in safety[:4]] == [
        ("人", "participant_count", 8.0),
        ("次", "event_count", 41.0),
        ("%", "participant_proportion", 20.0),
        ("人", "participant_count", 9.0),
    ]
    assert (safety[0]["numerator"], safety[0]["denominator"]) == (8, 30)
    assert all(item["numerator"] is None and item["denominator"] is None
               for item in safety[1:4])
    assert safety[3]["count_basis"] == "mixed"
    assert all(item["term_key"] and item["time_window"] == "Week 4"
               for item in safety[:4])
    assert all(item["group_id"] == "OG1" for item in safety[:4])
    assert (safety[0]["source_class_title"], safety[0]["source_category_title"]) == (
        "Week 4", "Any",
    )
    assert all(item["source_class_title"] is None and
               item["source_category_title"] is None for item in safety[1:4])
    assert [(item["term_key"], item["value"], item["numerator"], item["denominator"])
            for item in safety[4:]] == [
        ("death", 2, 2, 30), ("any_sae", 0, 0, 20),
    ]
    assert all(item["time_window"] == "Week 1 to Week 4" for item in safety[4:])
