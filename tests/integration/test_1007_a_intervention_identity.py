"""1007 source intervention identities through the ordinary A payload CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_a import ReportAPortalData


@pytest.mark.parametrize(
    ("names", "aliases", "expected"),
    [
        (["甲药", "乙药"], {}, {"甲药", "乙药"}),
        (["甲药", "乙药"], {"甲药": "甲正式名", "乙药": "乙正式名"},
         {"甲正式名", "乙正式名"}),
        (["Noveldrug infusion"], {}, {"noveldrug"}),
        (["Soliris-Ultomiris"], {"Soliris": "eculizumab", "Ultomiris": "ravulizumab"},
         {"eculizumab", "ravulizumab"}),
        (["Soliris–Ultomiris"], {"Soliris": "eculizumab", "Ultomiris": "ravulizumab"},
         {"eculizumab", "ravulizumab"}),
        (["Soliris／Ultomiris"], {"Soliris": "eculizumab", "Ultomiris": "ravulizumab"},
         {"eculizumab", "ravulizumab"}),
        (["甲药、乙药"], {"甲药": "甲正式名", "乙药": "乙正式名"}, {"甲正式名", "乙正式名"}),
        (["ＡＢ１２"], {"AB12": "drug-alpha"}, {"drug-alpha"}),
        (["AB-12"], {"AB12": "drug-alpha"}, {"ab-12"}),
        (["nonsteroidal-noveldrug"], {}, {"nonsteroidal-noveldrug"}),
        (["XYZ123 cell infusion"], {}, {"xyz123"}),
        (["transplantation-sparing ABC9"], {}, {"transplantation-sparing abc9"}),
        (["5 mg Serlopitant Tablets"], {}, {"serlopitant"}),
        (["5mg Serlopitant Tablets"], {}, {"serlopitant"}),
        (["0.5 mg Serlopitant Tablets"], {}, {"serlopitant"}),
        (["30 mg 甲药注射液"], {}, {"甲药注射液"}),
        (["10 mcg Noveldrug infusion"], {}, {"noveldrug"}),
        (["5mg Serlopitant; 30mg Nemolizumab"], {}, {"serlopitant", "nemolizumab"}),
        (["Serlopitant 5mg QD"], {}, {"serlopitant"}),
        (["AB-123 100mg QD"], {}, {"ab-123"}),
    ],
)
def test_source_names_survive_without_collapse_or_false_exclusion(
    tmp_path: Path, names: list[str], aliases: dict[str, str], expected: set[str],
) -> None:
    repo = Path(__file__).resolve().parents[2]
    cas = tmp_path / "cas/evidence/raw"
    cas.mkdir(parents=True)
    # The control record keeps the source input valid even when the defect
    # incorrectly drops every challenged intervention.
    studies = []
    for index, name in enumerate(["ControlDrug", *names], 1):
        studies.append({"protocolSection": {
            "identificationModule": {"nctId": f"NCT{index:08d}", "briefTitle": name},
            "armsInterventionsModule": {
                "interventions": [{"type": "DRUG", "name": name,
                                   "armGroupLabels": ["Treatment"]}],
                "armGroups": [{"label": "Treatment", "type": "EXPERIMENTAL"}],
            },
        }})
    (cas / "page.bin").write_text(json.dumps({"studies": studies}), encoding="utf-8")
    alias_file = tmp_path / "aliases.json"
    alias_file.write_text(json.dumps({"map_id": "1007-fixture", "canonical_by_alias": aliases}),
                          encoding="utf-8")
    output = tmp_path / "a.json"
    completed = subprocess.run([
        sys.executable, str(repo / "tools/build_a_payload.py"),
        "--cas-dir", str(tmp_path / "cas"), "--alias-map", str(alias_file),
        "--indication", "合同反例", "--indication-id", "contract-fixture",
        "--cutoff", "2026-10-07", "--output", str(output),
    ], cwd=repo, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    ReportAPortalData.model_validate(payload)
    products = {product["name"]: product["id"] for product in payload["products"]}
    assert set(products) == {"controldrug", *expected}
    assert len(set(products.values())) == len(products)
    assert len(payload["trials"]) == len(studies)
    assert {link["product_id"] for trial in payload["trials"][1:]
            for link in trial["product_links"]} == {products[name] for name in expected}
