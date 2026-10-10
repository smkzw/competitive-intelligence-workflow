"""Measure-level arm and denominator identity in the generic A builder."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


@pytest.mark.parametrize("known_participant_unit", [True, False])
def test_builder_uses_measure_group_and_rejects_conflicting_denominators(
    tmp_path: Path, known_participant_unit: bool,
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
                {"units": "Participants", "counts": [{"groupId": "OG1", "value": str(count)}]}
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
            "denoms": [{
                **({"units": "Participants"} if known_participant_unit else {}),
                "counts": [{"groupId": "OG1", "value": "30"}],
            }],
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
    page = cas / "page.bin"
    page.write_text(json.dumps({"studies": [record]}), encoding="utf-8")
    alias = tmp_path / "alias.json"
    alias.write_text(json.dumps({
        "map_id": "synthetic-v1", "canonical_by_alias": {"Testdrug": "testdrug"},
    }), encoding="utf-8")
    output = tmp_path / "a-payload.json"
    command = [
        sys.executable, str(root / "tools/build_a_payload.py"),
        "--cas-dir", str(tmp_path / "cas"), "--alias-map", str(alias),
        "--indication", "合成适应症", "--indication-id", "synthetic",
        "--output", str(output), "--cutoff", "2026-09-06",
    ]
    subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
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
    # Current common resolver preserves scoped reasons/paths. A denominator
    # with no unit is not automatically a participant population.
    conflict_indices = [1] if known_participant_unit else list(range(1, 6))
    assert derivation["denominator_conflicts"] == [
        {
            "trial_id": "nct00000001", "endpoint": measures[index]["title"],
            "group_id": "OG1",
            "source_path": (
                f"$.resultsSection.outcomeMeasuresModule.outcomeMeasures[{index}]"
                ".classes[0].categories[0]"
            ),
            "reason": "incompatible_denominator_candidates",
        }
        for index in conflict_indices
    ]
    row_sources = {item["row_id"]: item for item in derivation["row_source_map"]}
    assert set(row_sources) == {
        *(item["row_id"] for item in rows),
        *(item["row_id"] for item in payload["safety"]),
    }
    first = row_sources[rows[0]["row_id"]]
    second = row_sources[rows[1]["row_id"]]
    assert first["source_page_sha256"] == hashlib.sha256(
        page.read_bytes()
    ).hexdigest()
    assert first["value_path"] == (
        "$.resultsSection.outcomeMeasuresModule.outcomeMeasures[0]"
        ".classes[0].categories[0].measurements[0].value"
    )
    assert first["raw_value"] == "7"
    assert first["raw_value_type"] == "str"
    assert len(first["denominator_candidates"]) == 2
    assert {item["unit"] for item in
            first["denominator_candidates"]} == {"Participants"}
    assert {item["raw_value"] for item in
            second["denominator_candidates"]} == {"20", "25"}
    death = next(item for item in row_sources.values() if item["value_path"] ==
                 "$.resultsSection.adverseEventsModule.eventGroups[0].deathsNumAffected")
    assert death["value_path"] == (
        "$.resultsSection.adverseEventsModule.eventGroups[0].deathsNumAffected"
    )
    assert death["denominator_candidates"] == [{
        "value_path": (
            "$.resultsSection.adverseEventsModule.eventGroups[0].deathsNumAtRisk"
        ),
        "raw_value": 30,
        "raw_value_type": "int",
    }]
    safety = payload["safety"]
    assert len(safety) == 6
    assert [(item["unit"], item["measure_object"], item["value"]) for item in safety[:4]] == [
        ("人", "participant_count", 8.0),
        ("次", "event_count", 41.0),
        ("%", "participant_proportion", 20.0),
        ("人", "participant_count", 9.0),
    ]
    assert (safety[0]["numerator"], safety[0]["denominator"]) == (
        (8, 30) if known_participant_unit else (None, None)
    )
    assert safety[0]["value"] == 8  # Raw n survives even without a usable N/rate.
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
    original_payload = output.read_bytes()
    original_sidecar = output.with_name("a-payload.derivation.json").read_bytes()
    repeated = subprocess.run(command, cwd=root, capture_output=True, text=True)
    assert repeated.returncode != 0 and "已存在" in repeated.stderr
    assert output.read_bytes() == original_payload
    assert output.with_name("a-payload.derivation.json").read_bytes() == original_sidecar
    output.unlink()
    sidecar_only = subprocess.run(command, cwd=root, capture_output=True, text=True)
    assert sidecar_only.returncode != 0 and "已存在" in sidecar_only.stderr
    assert not output.exists()
    assert output.with_name("a-payload.derivation.json").read_bytes() == original_sidecar


def test_result_group_declared_short_form_links_and_other_variants_stay_unknown(
    tmp_path: Path,
) -> None:
    """A declared arm label states its own short form inside the label.

    "Weekly (QW)" declares "QW" for "Weekly"; a result group written as
    "Testdrug 360 mg SC QW" is the same declared arm with the label's own
    short form. Frequency suffixes (BID), split period markers
    ("(Q4W; DBL)"), reordered spellings and ambiguous contractions are not
    declared short forms and must stay unknown, never dropped or guessed.
    """
    root = Path(__file__).resolve().parents[2]
    cas = tmp_path / "cas" / "evidence" / "raw" / "sha256" / "ab"
    cas.mkdir(parents=True)
    declared = [
        "Testdrug 360 mg SC Weekly (QW)",
        "Testdrug With Auto-Injector (AI)",
        "Testdrug 540 mg SC Every 4 Weeks (Q4W; DBL)",
        "Testdrug 720 mg SC Weekly (QW)",
        "Testdrug 720 mg SC Once Weekly (QW)",
    ]
    measures = []
    for group_id, title, value in (
        ("OG1", "Testdrug 360 mg SC QW", "6"),
        ("OG2", "Testdrug With AI", "5"),
        ("OG3", "Testdrug 540 mg SC Q4W (DBL)", "4"),
        ("OG4", "Testdrug 360 mg SC Weekly (QW) BID", "3"),
        ("OG5", "Testdrug With Auto-Injector (AI)", "2"),
        ("OG6", "Testdrug 720 mg SC QW", "1"),
    ):
        measures.append({
            "title": f"Endpoint {group_id}", "timeFrame": "Week 4",
            "unitOfMeasure": "Participants",
            "groups": [{"id": group_id, "title": title}],
            "classes": [{"categories": [{"measurements": [
                {"groupId": group_id, "value": value},
            ]}]}],
        })
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000041", "briefTitle": "Arm relation test"},
            "designModule": {"enrollmentInfo": {"count": 60}},
            "armsInterventionsModule": {
                "interventions": [{"name": "Testdrug", "type": "DRUG",
                                   "armGroupLabels": declared}],
                "armGroups": [{"label": label, "type": "EXPERIMENTAL"}
                              for label in declared],
            },
        },
        "resultsSection": {
            "outcomeMeasuresModule": {"outcomeMeasures": measures},
            "adverseEventsModule": {
                "timeFrame": "Week 1 to Week 4",
                "eventGroups": [{"id": "EG1", "title": "Testdrug 360 mg SC QW",
                                 "seriousNumAffected": 1, "seriousNumAtRisk": 10}],
            },
        },
    }
    page = cas / "page.bin"
    page.write_text(json.dumps({"studies": [record]}), encoding="utf-8")
    alias = tmp_path / "alias.json"
    alias.write_text(json.dumps({
        "map_id": "synthetic-v1", "canonical_by_alias": {"Testdrug": "testdrug"},
    }), encoding="utf-8")
    output = tmp_path / "a-payload.json"
    command = [
        sys.executable, str(root / "tools/build_a_payload.py"),
        "--cas-dir", str(tmp_path / "cas"), "--alias-map", str(alias),
        "--indication", "合成适应症", "--indication-id", "synthetic",
        "--output", str(output), "--cutoff", "2026-10-10",
    ]
    subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
    payload = json.loads(output.read_text(encoding="utf-8"))
    efficacy = {row["arm"]: row for row in payload["efficacy"]}
    assert set(efficacy) == {
        "Testdrug 360 mg SC QW", "Testdrug With AI", "Testdrug 540 mg SC Q4W (DBL)",
        "Testdrug 360 mg SC Weekly (QW) BID", "Testdrug With Auto-Injector (AI)",
        "Testdrug 720 mg SC QW",
    }
    assert [
        (efficacy["Testdrug 360 mg SC QW"]["product_id"],
         efficacy["Testdrug 360 mg SC QW"]["group_assignment_state"]),
        (efficacy["Testdrug With AI"]["product_id"],
         efficacy["Testdrug With AI"]["group_assignment_state"]),
        (efficacy["Testdrug With Auto-Injector (AI)"]["product_id"],
         efficacy["Testdrug With Auto-Injector (AI)"]["group_assignment_state"]),
    ] == [("testdrug", "declared")] * 3
    # An added frequency token, a split DBL period group and an ambiguous
    # contraction (two declared labels share one short form) are not
    # declared identities: they stay report-visible as unknown.
    assert [
        efficacy["Testdrug 540 mg SC Q4W (DBL)"]["group_assignment_state"],
        efficacy["Testdrug 360 mg SC Weekly (QW) BID"]["group_assignment_state"],
        efficacy["Testdrug 720 mg SC QW"]["group_assignment_state"],
    ] == ["unknown"] * 3
    assert [(row["arm"], row["product_id"], row["group_assignment_state"])
            for row in payload["safety"]] == [
        ("Testdrug 360 mg SC QW", "testdrug", "declared"),
    ]
    links = payload["trials"][0]["product_links"]
    assert [(link["product_id"], link["arm_role"], tuple(link["arm_labels"]))
            for link in links] == [("testdrug", "experimental", (
                "Testdrug 360 mg SC QW",
                "Testdrug 360 mg SC Weekly (QW)",
                "Testdrug 540 mg SC Every 4 Weeks (Q4W; DBL)",
                "Testdrug 720 mg SC Once Weekly (QW)",
                "Testdrug 720 mg SC Weekly (QW)",
                "Testdrug With AI",
                "Testdrug With Auto-Injector (AI)",
            ))]
    derivation = json.loads(
        output.with_name("a-payload.derivation.json").read_text(encoding="utf-8")
    )
    assert derivation["arm_label_derivations"] == [
        {
            "trial_id": "nct00000041", "product_id": "testdrug",
            "declared_label": "Testdrug 360 mg SC Weekly (QW)",
            "result_label": "Testdrug 360 mg SC QW",
            "rule": "declared_parenthetical_abbreviation",
        },
        {
            "trial_id": "nct00000041", "product_id": "testdrug",
            "declared_label": "Testdrug With Auto-Injector (AI)",
            "result_label": "Testdrug With AI",
            "rule": "declared_parenthetical_abbreviation",
        },
    ]


@pytest.mark.parametrize(("declared", "forbidden"), [
    ("Testdrug 360 mg SC Weekly (QW)", {
        "testdrug 360 mg qw", "testdrug 360 qw", "testdrug qw",
    }),
    ("Testdrug Phase 2a Weekly (QW)", {
        "testdrug phase qw", "testdrug qw",
    }),
    ("Testdrug With Dual Chamber Syringe (DCS)", {
        "testdrug with dual chamber dcs", "testdrug with dual dcs", "testdrug dcs",
    }),
    ("Testdrug 120 mg (A)", {"testdrug 120 a", "testdrug a"}),
    ("Testdrug Twice Weekly (QW)", {"testdrug twice qw", "testdrug qw"}),
    ("Testdrug Three Times Weekly (QW)", {
        "testdrug three times qw", "testdrug three qw", "testdrug qw",
    }),
    ("Testdrug Not Once Weekly (QW)", {
        "testdrug not once qw", "testdrug not qw", "testdrug qw",
    }),
    ("Testdrug 2 Weekly (QW)", {"testdrug 2 qw"}),
    ("Testdrug No Weekly (QW)", {"testdrug no qw", "testdrug qw"}),
    ("Testdrug Not-Once Weekly (QW)", {"testdrug not-once qw"}),
])
def test_declared_short_form_never_erases_dose_route_phase_or_partial_phrase(
    declared: str, forbidden: set[str],
) -> None:
    # Execute the real production helper, not a copied implementation. The
    # CLI module parses inputs at import time, so isolate its exact AST nodes.
    path = Path(__file__).resolve().parents[2] / "tools/build_a_payload.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = {"_RESULT_LABEL_SHORT_FORM", "_LABEL_WORD", "_declared_result_label_forms"}
    nodes = [node for node in tree.body if (
        isinstance(node, ast.FunctionDef) and node.name in names
        or isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in names for target in node.targets)
    )]
    namespace: dict[str, Any] = {"re": re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    actual = namespace["_declared_result_label_forms"](declared)
    assert not actual & forbidden, f"Unsupported arm contraction: {actual & forbidden}"
