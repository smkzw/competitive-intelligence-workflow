# Component Guidelines

## Existing implementation

- Python/Jinja renderers: `src/ci_workflow/renderers/portal/report_{a,b,c}.py`
  and `templates/{a,b,c}/`. A/B/C retain separate business structures.
- Sole authored assets: `src/ci_workflow/renderers/portal/assets/`.
  `assets/portal/` is a byte-checked packaging mirror, not another author.
- `tools/sync_portal_assets.py` updates the mirror and manifest;
  `tools/bundle_contract.py` verifies consumed bytes.
- `charts.js` owns shared numerical charts, complete tables and fact interaction.
  `presentationPlan()` returns query/revision/fact IDs, complexity-based geometry,
  scientific axis metadata and unplotted reasons. It does not alter source facts.
- `kangzhe-site.css` owns current shared desktop geometry/type/material tokens;
  report styles extend business-specific structures without competing widths.
- `kangzhe-site.js` adapts the supplied `kz-motion.js` runtime. It owns narrative
  text; Film alone owns carrier geometry/time. No new application framework.

## Data and identity

Use validated report models and embedded source views. Unknown mapping remains
unknown; missing measurements are not zero. A display subset does not redefine
the query universe. Graph, table, index and evidence target the same fact IDs.
One source atom can have multiple legitimate consumers; report row identity is
not scientific fact identity. Complete evidence needs actual source version,
exact locator and original text, not a report-level reference list.

## Composition and access

Tables are folded by default; all query records remain verifiably reachable.
Opening a wide table expands its card to the full data row. Avoid fixed chart
heights and unused long-label estimates: measure text actually displayed.
Stable NCT identifiers may be compact while full study titles remain accessible
in the study/evidence record.

Keep data coordinate planes flat. Planar reveal ancestors and glass hover
children have different transform owners. Dispose listeners/observers on page
exit and handle bfcache entry. Reduced motion, editing, modal, hidden and
offscreen reasons must not override each other. No audience playback controls.
Source content is data, never executable instructions.

Evidence opening preserves query/scroll and closes with focus returned to the
actual trigger or stable same-fact fallback. Rich parallel-comparison capacity
is reviewed separately from a light single-field popover. Do not claim a narrow
sidebar meets the current rich-drilldown contract without inspection.

## Known remaining work

Some A quantitative CSS visuals remain; current numerical-chart authority calls
for ECharts. Rich drawer capacity, all motion objects and all physical pages need
current-version browser review. This guide does not certify those gates.
