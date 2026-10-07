"""Share navigation belongs to the current page, not arbitrary query strings."""

import json
from pathlib import Path

import pytest

from ci_workflow.application.share_export import ShareViewSelection, _validate_view_selection


def _page(kind):
    if kind == "C":
        return b'<a data-c-enter-comparison href="overview.html?view=comparison">Compare</a>'
    columns = [{"question_id": "efficacy::easi75"} for _ in range(9)]
    return ('<section id="full-study-comparison"></section><script>window.__'
            + kind + '_COMPARISON_WORKSPACE__ = '
            + json.dumps({"columns": columns}) + ';</script>').encode()


@pytest.mark.parametrize("kind", ["A", "B", "C"])
def test_current_comparison_navigation_is_shareable(kind):
    query = {"view": ("comparison",)}
    if kind != "C":
        query.update(cmp=("efficacy::easi75",), cmp_page=("3",))
    _validate_view_selection(ShareViewSelection(report=kind, revision=1, query=query), _page(kind))


@pytest.mark.parametrize("kind", ["A", "B"])
@pytest.mark.parametrize("query", [
    {"view": ("unknown",)}, {"cmp": ("fake-question",)}, {"cmp_page": ("4",)},
    {"cmp_page": ("0",)}, {"cmp_page": ("1.5",)}, {"view": ("comparison", "comparison")},
    {"cmp": ("efficacy::easi75", "efficacy::easi75")},
])
def test_comparison_query_rejects_unknown_or_out_of_range(kind, query):
    with pytest.raises(ValueError):
        _validate_view_selection(ShareViewSelection(report=kind, revision=1, query=query),
                                 _page(kind))


@pytest.mark.parametrize("kind", ["A", "B", "C"])
def test_old_or_unrelated_page_cannot_claim_comparison_navigation(kind):
    with pytest.raises(ValueError):
        _validate_view_selection(ShareViewSelection(report=kind, revision=1,
            query={"view": ("comparison",)}), b"<html>legacy page</html>")


@pytest.mark.parametrize("kind", ["A", "B", "C"])
def test_ordinary_portal_navigation_passes_current_share_validator(tmp_path, kind):
    from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
    from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
    from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site

    root = Path(__file__).resolve().parents[2]
    fixture = ("positive/c-atopic-dermatitis" if kind == "C" else "synthetic/a-complete")
    raw = json.loads((root / "fixtures" / fixture / "inputs/report-data.json").read_text())
    model, render = {"A": (ReportAPortalData, render_report_a_site),
                     "B": (ReportBPortalData, render_report_b_site),
                     "C": (ReportCPortalData, render_report_c_site)}[kind]
    render(model.model_validate(raw), tmp_path / kind)
    entry = "clinical-portfolio.html" if kind == "A" else "overview.html"
    page = (tmp_path / kind / entry).read_bytes()
    query = {"view": ("comparison",)}
    if kind != "C":
        from ci_workflow.application.share_export import _FilterInventory

        inventory = _FilterInventory()
        inventory.feed(page.decode())
        question = sorted(inventory.comparison_questions(kind))[0]
        query.update(cmp=(question,), cmp_page=("1",))
    _validate_view_selection(ShareViewSelection(report=kind, revision=0,
        entry_page=entry, query=query), page)
