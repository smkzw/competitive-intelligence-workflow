"""Ordinary readonly A/B current32: unit, source-target and visit consumer repair."""

import hashlib
from pathlib import Path

base = Path(__file__).with_name("render-ab-shared-question-preview-v1.py")
raw = base.read_bytes()
assert hashlib.sha256(raw).hexdigest() == (
    "202bcbb56625d775c6c70ef37cbd757a1c33dc88c5f883df72f4f6e54ded7bf6"
)
source = raw.decode().replace(".artifacts/1007-ab-shared-question-preview-v1",
                             ".artifacts/1007-ab-shared-chart-reading-v5")
source = source.replace('"assets/portal.js", "assets/charts.js",',
                        '"assets/portal.js", "assets/charts.js", "assets/portal.css",')
source = source.replace("UserFactEditService, _bound_identity_context",
                        "UserFactEditService, _bound_identity_context, _bound_a_public_context")
source = source.replace(
    "pages = render_report_a_site(data, destination, active_revision=active,",
    "public, _legacy_limitation = _bound_a_public_context(PROJECT, report, data)\n"
    "                assert public is not None, 'Use the existing bound public source closure'\n"
    "                pages = render_report_a_site(data, destination, public_provenance=public,\n"
    "                                            active_revision=active,",
)
exec(compile(source, str(Path(__file__)), "exec"))
