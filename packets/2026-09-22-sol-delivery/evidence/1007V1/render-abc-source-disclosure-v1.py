"""Normal readonly A/B/C source-disclosure candidate, not a current/save mutation."""

import hashlib
from pathlib import Path

base = Path(__file__).with_name("render-ab-shared-question-preview-v1.py")
raw = base.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "202bcbb56625d775c6c70ef37cbd757a1c33dc88c5f883df72f4f6e54ded7bf6"
)
source = raw.decode().replace(".artifacts/1007-ab-shared-question-preview-v1",
                             ".artifacts/1007-abc-source-disclosure-v1")
source = source.replace(
    "from tools.bundle_contract import validate_portal_asset_mirror",
    "from tools.bundle_contract import validate_portal_asset_mirror\n"
    "from ci_workflow.renderers.portal.report_c import load_report_c_data, render_report_c_site",
)
source = source.replace('"assets/portal.js", "assets/charts.js",',
                        '"assets/portal.js", "assets/charts.js", "assets/portal.css",')
source = source.replace('"templates/a/base.html.j2", "templates/b/page.html.j2")',
    '"templates/a/base.html.j2", "templates/b/page.html.j2", "templates/b/base.html.j2", '
    '"templates/c/base.html.j2", "report_c.py", "assets/report-c.js", "assets/report-c.css")')
source = source.replace('{"A", "B"}', '{"A", "B", "C"}')
source = source.replace("UserFactEditService, _bound_identity_context",
                        "UserFactEditService, _bound_identity_context, _bound_a_public_context")
source = source.replace(
    "pages = render_report_a_site(data, destination, active_revision=active,",
    "public, _legacy_limitation = _bound_a_public_context(PROJECT, report, data)\n"
    "                assert public is not None, 'Use the existing bound public source closure'\n"
    "                pages = render_report_a_site(data, destination, public_provenance=public,\n"
    "                                            active_revision=active,",
)
source = source.replace(
    "            else:\n                pages = render_report_b_site",
    '            elif report.report == "B":\n                pages = render_report_b_site',
)
source = source.replace(
    '            reports[report.report] = {"pages": len(pages)',
    '            else:\n'
    '                pages = render_report_c_site(load_report_c_data(source), destination,\n'
    '                                            active_revision=active, '
    'identity_context=identity)\n'
    '            reports[report.report] = {"pages": len(pages)',
)
source = source.replace("NORMAL_AB_CURRENT32_PREVIEW_NOT_COMMITTED_OR_ACCEPTED",
                        "NORMAL_ABC_CURRENT32_PREVIEW_NOT_COMMITTED_OR_ACCEPTED")
exec(compile(source, str(Path(__file__)), "exec"))
