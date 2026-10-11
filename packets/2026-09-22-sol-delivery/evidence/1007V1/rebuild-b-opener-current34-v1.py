"""Normal B-only presentation save after actual four-width source/opener checks.

A/C remain byte-identical; all active facts and source science remain untouched.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import (
    CurrentPresentationRebuildCommand,
    UserFactEditService,
)
from tools.bundle_contract import validate_portal_asset_mirror

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = ROOT / ".artifacts/1007-b-opener-current34-v1"
PREVIEW = ROOT / ".artifacts/1007-b-opener-preview-v1"
AUTHOR = ROOT / "src/ci_workflow/renderers/portal"


def main() -> None:
    assert not OUT.exists(), "Reopen durable return/current/journal; never replay blindly"
    validate_portal_asset_mirror(ROOT)
    previous = Path(__file__).with_name("rebuild-abc-reading-current33-v1.py")
    expected = "6aeb0df78626a1da95281579e0600a064150c29ea0ae0aa4b88c4371993cbef4"
    assert hashlib.sha256(previous.read_bytes()).hexdigest() == expected
    spec = importlib.util.spec_from_file_location("existing_presentation_checks", previous)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = OUT
    qa = json.loads((PREVIEW / "qa/actual.json").read_bytes())
    proof = json.loads((PREVIEW / "actual.json").read_bytes())
    assert qa["state"] == "FOUR_WIDTH_GLYPH_CLEAR_EDIT_ACTUAL_OPENER_PASS"
    assert len(qa["states"]) == 12 and not qa["failures"]
    assert proof["current_writes"] == 0 and proof["facts"] == 1505
    for name, digest in proof["author_sha256"].items():
        assert module.sha(AUTHOR / name) == digest
    before = read_current_delivery(PROJECT)
    assert before and before.revision == 33
    assert current_bundle_sha256(before) == proof["source_generation"]
    service = UserFactEditService(PROJECT)
    facts, tables = service.current_facts(), module.frozen_tables()
    pins = {p.relative_to(PROJECT).as_posix(): module.sha(p)
            for directory in ("reports", "snapshots")
            for p in (PROJECT / directory).rglob("*") if p.is_file()}
    command = CurrentPresentationRebuildCommand(
        request_id="owner-1007-b-opener-current34-v1", project_id=before.project_id,
        expected_revision=33, reports=("B",), requested_by="owner-1007-presentation",
        requested_at=datetime.now(UTC),
    )
    OUT.mkdir()
    module.write("command.json", command.model_dump(mode="json"))
    module.write("prewrite.json", {"current": before.model_dump(mode="json"),
        "protected_files": pins, "frozen_tables": tables,
        "recipe_sha256": module.sha(Path(__file__)),
        "qa_sha256": module.sha(PREVIEW / "qa/actual.json"),
        "author_sha256": proof["author_sha256"]})
    after = service.rebuild_current_presentation(command)
    module.write("rebuild-return.json", after.model_dump(mode="json"))
    assert read_current_delivery(PROJECT) == after and after.revision == 34
    assert after.active_fact_version_ids == before.active_fact_version_ids
    assert service.current_facts() == facts and module.frozen_tables() == tables
    assert all(module.sha(PROJECT / path) == digest for path, digest in pins.items())
    for old in before.reports:
        new = next(item for item in after.reports if item.report == old.report)
        if old.report == "B":
            assert new.revision == 34 and new.builder_input_sha256 == old.builder_input_sha256
            assert new.fact_version_ids == old.fact_version_ids
        else:
            assert new == old
    module.write("verified.json", {"state": "CURRENT34_B_OPENER_COMMITTED_NOT_RELEASE_ACCEPTED",
        "revision": 34, "generation": current_bundle_sha256(after),
        "reports": {r.report:r.revision for r in after.reports},
        "active_facts_unchanged": len(facts),
        "old_files_unchanged": len(pins), "clinical_edits": 0, "source_adoptions": 0,
        "AC_descriptors_and_bytes_unchanged": True, "current": after.model_dump(mode="json"),
        "same_current_config_share": "NOT_RUN", "product_state": "REVISE"})
    print(json.dumps({"revision":34,"generation":current_bundle_sha256(after)}), flush=True)


if __name__ == "__main__":
    main()
