"""Source refresh must not bless an identity-correct but numerically wrong builder.

Synthetic accepted source atoms exercise persisted production transactions; they
are not actual source acceptance or a clinical correction.
"""

import json
from pathlib import Path

import pytest

from ci_workflow.application.source_current_refresh import (
    SourceCurrentRefreshService,
    SourceFactRefusalError,
)
from tests.integration.test_r24_source_current_refresh import (
    SOURCE_FACT_1,
    SOURCE_FACT_2,
    SOURCE_VERSION_2,
    _new_bindings,
    _read_current,
    _refresh_command,
    _seed_source_atom,
    _world,
    _write_new_inputs,
)


@pytest.mark.parametrize("drift", ["value", "counts", "a_quote", "b_quote"])
def test_registered_builder_cannot_disagree_with_accepted_source_value(
    tmp_path: Path, drift: str,
) -> None:
    world = _world(tmp_path, user_edit=True)
    assert world.user_version is not None
    # Binding digest is legitimately for the supplied row, so identity-only
    # validation cannot detect disagreement with the source atom itself.
    paths = _write_new_inputs(
        world.root, source_version=SOURCE_VERSION_2,
        value=99.0 if drift == "value" else 54.8,
        raw=("99% (34/62)" if drift == "value" else
             "54.8% (31/62)" if drift == "counts" else "54.8% (34/62)"),
        numerator=31 if drift == "counts" else 34, denominator=62,
    )
    if drift in {"a_quote", "b_quote"}:
        report = "A" if drift == "a_quote" else "B"
        path = world.root / paths[report]
        payload = json.loads(path.read_bytes())
        rows = payload["safety"] if report == "A" else payload["safety_views"]["facts"]
        row = next(row for row in rows if row["row_id"] == "safe-apply-t-1")
        row["source_text"] = "99/100例受试者发生任何TEAE（99%）。"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _seed_source_atom(
        world.root, version_id=SOURCE_FACT_2, source_version=SOURCE_VERSION_2,
        raw="54.8% (34/62)", normalized="54.8", numerator=34, denominator=62,
        bindings=_new_bindings(world.root, paths),
    )
    before = _read_current(world.root)
    with pytest.raises(SourceFactRefusalError, match="来源.*一致"):
        SourceCurrentRefreshService(world.root).refresh(_refresh_command(
            world, paths=paths, request_id="source-builder-" + drift,
            current_version=world.user_version, user_version=world.user_version,
            base_version=SOURCE_FACT_1,
        ))
    assert _read_current(world.root) == before
    assert not tuple(world.root.glob("reports/*/v1-source-r*"))
