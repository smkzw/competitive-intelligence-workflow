"""Current-code transaction/config/share chain on a labelled development fixture.

This is not browser or clinical-source acceptance. One shared project exercises
failure/retry, legal A+B clear/undo and all four current-generation share variants.
"""

import json
from zipfile import ZipFile

import pytest

from ci_workflow.application.share_export import (
    ShareViewSelection,
    _FilterInventory,
    _validate_static_resources,
    export_current_html_share,
)
from ci_workflow.application.user_fact_edit import FactEdit, UserFactEditService
from tests.integration.test_w04_user_fact_edit import _command, _project, _projection


def test_current_comparison_clear_retry_undo_and_four_share_variants(tmp_path):
    root, _fragments = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    clear = _command(request_id="1007-clear", edits=FactEdit(normalized_value=None))

    def interrupt(report):
        if report == "A":
            raise OSError("1007 transaction interruption")

    service._after_report_built = interrupt
    with pytest.raises(OSError, match="1007 transaction"):
        service.save(clear)
    assert service.read_current_delivery() == before
    service._after_report_built = lambda _report: None
    result = service.save(clear)
    assert result.rebuilt_reports == ("A", "B")
    assert service.save(clear).revision == result.revision  # same request, no new version
    for kind in ("A", "B"):
        row = next(r for r in _projection(root, kind)["safety"] if r["row_id"] == "safe-apply-t-1")
        assert row["value"] is None and row["disclosure_state"] in {
            "user_cleared", "用户清除，待重新核实",
        }
    fact = service.current_facts()["fact-crude-rate"]
    assert fact["disclosure_state"] == "user_cleared"
    service.save(_command(request_id="1007-undo", expected_revision=1,
                         fact_version_id=fact["fact_version_id"], operation="undo"))
    current = service.read_current_delivery()
    assert current.revision == 2
    assert next(r for r in current.reports if r.report == "C") == next(
        r for r in before.reports if r.report == "C"
    )
    selections = {}
    for report in current.reports:
        entry = "clinical-portfolio.html" if report.report == "A" else "overview.html"
        page = (root / report.site_relative_path / entry).read_bytes()
        query = {"view": ("comparison",)}
        if report.report in {"A", "B"}:
            inventory = _FilterInventory()
            inventory.feed(page.decode())
            question = sorted(inventory.comparison_questions(report.report))[0]
            query.update(cmp=(question,), cmp_page=("1",))
        selections[report.report] = ShareViewSelection(report=report.report,
            revision=report.revision, entry_page=entry, query=query)
    for kinds in (("A",), ("B",), ("C",), ("A", "B", "C")):
        destination = tmp_path / ("-".join(kinds) + ".zip")
        receipt = export_current_html_share(root, destination,
            selections=tuple(selections[kind] for kind in kinds))
        assert receipt.current_revision == 2
        with ZipFile(destination) as archive:
            manifest = json.loads(archive.read("share-manifest.json"))
            assert manifest["current_revision"] == 2
            assert set(manifest["reports"]) == set(kinds)
            files = {name: archive.read(name) for name in archive.namelist()}
            for kind in kinds:
                assert manifest["reports"][kind]["view_config"]["query"]["view"] == ["comparison"]
                _validate_static_resources({name.removeprefix(kind + "/"): payload
                    for name, payload in files.items() if name.startswith(kind + "/")})
        moved = tmp_path / ("moved-" + "-".join(kinds))
        with ZipFile(destination) as archive:
            archive.extractall(moved)
        for kind in kinds:
            assert (moved / kind / selections[kind].entry_page).is_file()
    assert service.read_current_delivery() == current
