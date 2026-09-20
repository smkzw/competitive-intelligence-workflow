import json
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_a import build_report_a_artifact
from tests.integration.test_fresh_a_research_package import _package_payload


@pytest.mark.parametrize("change", [
    "none", "data", "site", "limitation", "no-resume", "snapshot-link",
])
def test_committed_recovery_requires_same_inputs_and_immutable_bytes(
    tmp_path: Path, change: str,
) -> None:
    payload = _package_payload()["report_data"]
    path = tmp_path / "data.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    site, manifest = build_report_a_artifact(
        project_root=tmp_path, data_path=path, project_id="project", contract_version=1,
        run_id="initial",
    )
    if change == "data":
        payload["efficacy"][0]["value"] += 1
        path.write_text(json.dumps(payload), encoding="utf-8")
    if change == "site":
        (site / "overview.html").write_bytes(b"changed")
    if change == "snapshot-link":
        value = json.loads(manifest.read_bytes())
        snapshot = tmp_path / "snapshots/reports/A" / f'{value["report_snapshot_id"]}.json'
        original = tmp_path / "outside-snapshot.json"
        snapshot.rename(original)
        snapshot.symlink_to(original)
    before = {file: (file.read_bytes(), file.stat().st_mtime_ns)
              for file in site.parent.rglob("*") if file.is_file()}

    def recover() -> tuple[Path, Path]:
        return build_report_a_artifact(
            project_root=tmp_path, data_path=path, project_id="project", contract_version=1,
            run_id="recovery", recover_committed=change != "no-resume",
            publication_limitation_zh="changed limitation" if change == "limitation" else None,
        )

    if change == "none":
        assert recover() == (site, manifest)
    else:
        with pytest.raises((ValueError, RuntimeError)):
            recover()
    assert before == {file: (file.read_bytes(), file.stat().st_mtime_ns)
                      for file in site.parent.rglob("*") if file.is_file()}
