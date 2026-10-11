"""Desktop recovery: consume native labels; do not stretch or expose run notes."""

import json
import re
from pathlib import Path

from ci_workflow.renderers.portal.report_b import _controlled_concept, _native_text
from tests.integration.test_1007_series_legend_identity import _group, _probe

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "src/ci_workflow/renderers/portal/assets"


def test_baseline_label_translation_keeps_the_original_semantic_key() -> None:
    original = "Age, Continuous"
    concept = _controlled_concept(original, domain="baseline")
    assert _native_text(original) == "年龄（连续变量）"
    assert concept == ("baseline:agecontinuous", "年龄（连续变量）")


def test_single_shared_panel_uses_desktop_width_without_stretched_grid_rows() -> None:
    css = (ASSETS / "report-b.css").read_text()
    main = re.search(r'\.kz-b-site\[data-comparison-view="comparison"\] '
                     r"\.kz-b-main\s*\{([^}]+)\}", css)
    assert main and "align-content: start" in main.group(1)
    single = re.search(r"\.kz-b-shared-plot:only-child\s*\{([^}]+)\}", css)
    assert single and "grid-column: 1 / -1" in single.group(1)


def test_public_source_footer_does_not_dump_internal_retrieval_scope() -> None:
    template = (ROOT / "src/ci_workflow/renderers/portal/templates/b/base.html.j2").read_text()
    assert "source.scope" not in template
    assert "source.url" in template and "source.label" in template
    assert "external-sources" in template and "data_cutoff" in template


def test_bar_axis_consumes_supplied_native_unit_without_modifying_source() -> None:
    group = _group()
    for row in group["rows"]:
        row.update(unit="years", unit_label_zh="年")
    before = json.dumps(group)
    _probe([group], extra="assert.equal(option.yAxis.name,'年');")
    assert json.dumps(group) == before


def test_registered_study_legend_qualifiers_use_canonical_display_case() -> None:
    group = _group()
    for row in group["rows"]:
        row["trial_id"] = row["trial_id"].lower()
    _probe([group], extra="assert.ok(names.every(name=>!name.includes('nct')));")
