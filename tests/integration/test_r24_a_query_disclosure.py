"""Query-scoped disclosure uses the production A renderer, not total-page counts."""

import json
from pathlib import Path

import pytest

from tests.integration.test_r24_a_safety_echarts import _PROBE, _run_probe


@pytest.mark.parametrize(
    ("selection", "total", "drawn", "unassigned", "scope"),
    [({}, 71, 70, 1, None), ({"event": ["any_sae"]}, 3, 2, 1, None),
     ({"event": ["specific_ae"]}, 1, 1, 0, None),
     ({"event": ["not-present"]}, 0, 0, 0, None),
     ({"product": ["泰瑞奇单抗"]}, 69, 69, 0, None), ({}, 69, 69, 0, "p1")],
)
def test_disclosure_counts_follow_the_same_query_as_the_chart(
    tmp_path: Path, selection: dict[str, list[str]], total: int, drawn: int,
    unassigned: int, scope: str | None,
) -> None:
    probe = _PROBE.split("/* ---------- 断言：", 1)[0]
    # Expose only the real closure's query setter and renderer to the probe.
    hook = (
        '  window.probeRender = function(q, scope) { selected = q; '
        'var host = document.querySelector("[data-a-chart]"); '
        'if(scope) host.setAttribute("data-product-scope", scope); renderSafety(host); };\n'
        '  applyFilters();\n})();'
    )
    probe = probe.replace(
        'fs.readFileSync(reportPath, "utf8"), sandbox',
        'fs.readFileSync(reportPath, "utf8").replace('
        + json.dumps("  applyFilters();\n})();") + ', ' + json.dumps(hook) + '), sandbox',
    )
    probe += f"\nwindowStub.probeRender({json.dumps(selection)}, {json.dumps(scope)});\n"
    probe += f"""
const disclosure = host.querySelector('[data-safety-query-disclosure]');
assert.ok(disclosure, 'query disclosure missing');
assert.equal(disclosure.getAttribute('data-query-count'), '{total}');
assert.equal(disclosure.getAttribute('data-drawable-count'), '{drawn}');
assert.equal(disclosure.getAttribute('data-unassigned-count'), '{unassigned}');
assert.equal(host.querySelectorAll('[data-row-id]').length, {drawn});
assert.ok(disclosure.textContent.includes('当前筛选 {total} 条'));
assert.ok(disclosure.textContent.includes('可绘制 {drawn} 条'));
assert.ok(!disclosure.textContent.includes('本页有'));
assert.equal(payload.safety.length, 71, 'filtering cannot delete original facts');
"""
    result = _run_probe(tmp_path, probe)
    assert result.returncode == 0, result.stderr


def test_template_does_not_repeat_a_stale_page_total() -> None:
    root = Path(__file__).resolve().parents[2]
    template = root / "src/ci_workflow/renderers/portal/templates/a/safety.html.j2"
    assert "本页有 {{ unassigned_safety_count }}" not in template.read_text()
