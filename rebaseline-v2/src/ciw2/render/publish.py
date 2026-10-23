"""Prepare all report bytes first, then atomically replace each public file."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ciw2.render import portal

if TYPE_CHECKING:
    from ciw2.pipeline.context import RunContext


def publish_reports(rc: RunContext) -> dict[str, list[str]]:
    target = rc.settings.portals_dir / rc.project_id
    target.mkdir(parents=True, exist_ok=True)
    reports = rc.project['reports']
    # TemporaryDirectory owns only these new files. Existing reports and other
    # project artifacts are never truncated or included in cleanup.
    with TemporaryDirectory(prefix='.render-', dir=target) as temporary:
        pending = []
        for report in reports:
            findings = rc.db.stage_output(rc.run_id, f'analysis_{report}')
            html = portal.render_report(rc.db, rc.project_id, report, findings=findings, inline=True)
            path = Path(temporary) / f'{report}.html'
            path.write_text(html, encoding='utf-8')
            pending.append(path)
        for path in pending:
            path.replace(target / path.name)
    # Each replacement is atomic; this is not a cross-file transaction or a
    # power-loss durability guarantee. A failed later replace still fails stage.
    return {'files': [f'{report}.html' for report in reports]}
