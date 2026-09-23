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
            }
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
    rows = json.loads(output.read_text(encoding="utf-8"))["efficacy"]
    assert [(row["endpoint"], row["arm"], row["denominator"]) for row in rows] == [
        ("Response A", "Drug 10 mg (TP1)", 30),
        ("Response B", "Drug 10 mg (TP2)", None),
    ]
    derivation = json.loads(
        output.with_name("a-payload.derivation.json").read_text(encoding="utf-8")
    )
    assert derivation["denominator_conflicts"] == [{
        "trial_id": "nct00000001", "endpoint": "Response B", "group_id": "OG1",
    }]
