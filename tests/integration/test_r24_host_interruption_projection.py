"""Internal recovery state is not identical to the public interruption receipt."""
import json
import shlex
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application import host_smoke_scenario as scenario
from ci_workflow.domain.contracts import ProjectContract

CONTRACT = ProjectContract(
    contract_version=1, project_id="project_example", indication="示例适应症",
    reports=["A"], outputs=["html"], timezone="Asia/Shanghai",
    cutoff_was_user_supplied=True,
    data_cutoff=datetime(2026, 10, 4, tzinfo=UTC), created_at=datetime(2026, 10, 4, tzinfo=UTC),
)


def _initial() -> dict[str, Any]:
    return {"run_id": "run_example", "project_id": CONTRACT.project_id,
            "outcome": "evidence_blocked", "exit_code": 4, "no_draft": True,
            "report_file_count": 0, "manifest_relative_path": "state/initial.json",
            "manifest_sha256": "a" * 64, "manifest_digest": "b" * 64,
            "event_count": 1, "event_stream_digest": "c" * 64,
            "contract": CONTRACT.model_dump(mode="json")}


def test_internal_contract_is_checked_but_not_leaked_to_strict_receipt() -> None:
    initial = _initial()
    before = deepcopy(initial)
    binding = scenario.interruption_receipt_binding(initial, CONTRACT)
    assert "contract" not in binding.model_dump(mode="json")
    assert binding.project_id == CONTRACT.project_id and initial == before


@pytest.mark.parametrize("field,value", [
    ("indication", "伪造适应症"), ("data_cutoff", "2025-01-01T00:00:00+00:00"),
    ("project_id", "project_foreign"), ("contract_version", 2),
])
def test_embedded_contract_drift_is_not_silently_ignored(field: str, value: Any) -> None:
    initial = _initial()
    initial["contract"][field] = value
    with pytest.raises(scenario.HostSmokeScenarioError, match="合同"):
        scenario.interruption_receipt_binding(initial, CONTRACT)


@pytest.mark.parametrize("change", ["unknown", "null_contract", "foreign_project"])
def test_only_named_internal_extension_is_allowed(change: str) -> None:
    initial = _initial()
    if change == "unknown":
        initial["fake_approval"] = True
    elif change == "null_contract":
        initial["contract"] = None
    else:
        initial["project_id"] = "project_foreign"
    with pytest.raises(scenario.HostSmokeScenarioError):
        scenario.interruption_receipt_binding(initial, CONTRACT)


def test_legacy_initial_without_embedded_contract_preserves_receipt_shape() -> None:
    initial = _initial()
    del initial["contract"]
    binding = scenario.interruption_receipt_binding(initial, CONTRACT)
    assert binding.model_dump(mode="json") == initial


def test_production_scenario_receipt_roundtrip_and_contract_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real fixture subprocess, synthetic host executable: NOT a real model/host pass."""
    from ci_workflow.application import host_smoke as smoke

    project = tmp_path / "project"
    catalog = Path(__file__).resolve().parents[2] / "fixtures/catalog.yaml"
    command = [sys.executable, "-m", "ci_workflow", "fixture", "run", "--case",
               "host-smoke-v1", "--reports", "A", "--outputs", "html", "--project",
               str(project), "--catalog", str(catalog), "--host-smoke-recovery"]
    executable = tmp_path / "omp"
    executable.write_text(
        "#!/bin/sh\n" + shlex.join(command) + " || exit $?\n"
        + "echo " + shlex.quote(smoke._HOST_COMPLETION_MARKER) + "\n",
    )
    executable.chmod(0o700)
    # Adapter boundary seam only. The subprocess and recovery files are real;
    # the fabricated host provenance must never be reused as release evidence.
    monkeypatch.setattr(smoke, "resolve_host_executable", lambda *a, **k: (
        {"provenance": "path_resolved", "path": str(executable),
         "version": "synthetic-local-host-test"}, None,
    ))
    receipt = smoke.run_host_smoke(
        "omp", project_root=project, catalog_path=catalog,
        require_external_host_process=True, omp_model="openai-codex/gpt-6.1-sol",
        omp_thinking="high",
    )
    smoke.verify_host_smoke_receipt(receipt, project_root=project, catalog_path=catalog)
    path = project / "state/host-smoke-v1.json"
    original = json.loads(path.read_text())
    assert "contract" in original["initial"]
    assert receipt.interruption is not None
    assert "contract" not in receipt.interruption.model_dump(mode="json")
    for change in ("contract", "unknown"):
        modified = deepcopy(original)
        if change == "contract":
            modified["initial"]["contract"]["indication"] = "伪造适应症"
        else:
            modified["initial"]["invented_approval"] = True
        path.write_text(json.dumps(modified))
        with pytest.raises(smoke.HostSmokeReceiptError, match="初始内部合同"):
            smoke.verify_host_smoke_receipt(receipt, project_root=project, catalog_path=catalog)
    path.write_text(json.dumps(original))
