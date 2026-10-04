"""A fixed real C source candidate is recoverable, not a fabricated reviewed portal."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ci_workflow.domain.evidence import ContentBlob
from ci_workflow.storage.content_store import ContentAddressedStore
from tests.integration.test_r24_ctgov_c_design_projection import (
    _CAS_DIGEST,
    _CAS_ROOT,
    _full_bindings,
)


def _builder():
    try:
        from tools.materialize_ctgov_c_candidate import materialize
    except ImportError:
        pytest.fail("real C projection needs a recoverable materialization entry")
    return materialize


def _raw() -> ContentBlob:
    relative = f"evidence/raw/sha256/{_CAS_DIGEST[:2]}/{_CAS_DIGEST}.bin"
    return ContentBlob(sha256=_CAS_DIGEST, relative_path=relative,
        byte_size=(_CAS_ROOT / relative).stat().st_size, media_type="application/json")


def test_fixed_real_c_materialization_preserves_sources_versions_and_candidates(
    tmp_path: Path,
) -> None:
    output = tmp_path / "fixed-c"
    result = _builder()(source_root=_CAS_ROOT, raw_asset=_raw(), output=output,
        bindings=_full_bindings(), indication_id="pnh", indication="阵发性睡眠性血红蛋白尿症",
        cutoff="2026-09-26", observed_at=datetime(2026, 10, 3, tzinfo=UTC))
    assert result["observations"] == 85
    assert result["unresolved_atoms"] == 1
    assert result["source_versions"] == 2
    assert result["endpoint_instances"] == 17
    assert result["current_generation_switched"] is False
    assert result["scientific_acceptance"] == "not_accepted"
    assert result["acquisition_mode"] == "offline_cas_replay"
    assert ContentAddressedStore(output / "project").read_bytes(_raw()) == (
        ContentAddressedStore(_CAS_ROOT).read_bytes(_raw()))
    assert (output / "candidate-manifest.json").is_file()
    assert (output / "projection.json").is_file()
    assert not list((output / "project/reports/C").rglob("*.html"))


def test_source_byte_drift_and_existing_output_do_not_overwrite(tmp_path: Path) -> None:
    builder = _builder()
    raw = _raw().model_copy(update={"sha256": "0" * 64})
    output = tmp_path / "must-not-exist"
    with pytest.raises(ValueError):
        builder(source_root=_CAS_ROOT, raw_asset=raw, output=output,
            bindings=_full_bindings(), indication_id="pnh", indication="阵发性睡眠性血红蛋白尿症",
            cutoff="2026-09-26", observed_at=datetime(2026, 10, 3, tzinfo=UTC))
    assert not output.exists()
    output.mkdir()
    with pytest.raises(ValueError, match="fresh|新"):
        builder(source_root=_CAS_ROOT, raw_asset=_raw(), output=output,
            bindings=_full_bindings(), indication_id="pnh", indication="阵发性睡眠性血红蛋白尿症",
            cutoff="2026-09-26", observed_at=datetime(2026, 10, 3, tzinfo=UTC))
    assert list(output.iterdir()) == []


def test_real_candidate_preview_preserves_source_status_and_unknown_product_metadata(
    tmp_path: Path,
) -> None:
    from tools import materialize_ctgov_c_candidate as module

    preview = getattr(module, "render_review_preview", None)
    assert preview is not None, "fixed real C source must reach a review-only portal"
    output = tmp_path / "review-c-source"
    _builder()(source_root=_CAS_ROOT, raw_asset=_raw(), output=output,
        bindings=_full_bindings(), indication_id="pnh", indication="阵发性睡眠性血红蛋白尿症",
        cutoff="2026-09-26", observed_at=datetime(2026, 10, 3, tzinfo=UTC))
    result = preview(output, rendered_at=datetime(2026, 10, 3, tzinfo=UTC))
    assert result["observations"] == 85
    assert result["registered_consumers"] == 85
    assert result["scientific_acceptance"] is False
    assert result["current_generation_switched"] is False
    data = json.loads((output / "review-portal-data.json").read_bytes())
    assert {row["review_state"] for row in data["observations"]} == {"candidate"}
    assert {row["developer_basis"] for row in data["products"]} == {"unverified"}
    trial = next(row for row in data["trials"] if row["display_id"] == "NCT03829449")
    assert trial["status"] == "已终止"
    assert trial["region"] == "Poland"
    assert trial["reported_sample_size"] == 15
    assert trial["planned_sample_size"] is None
    assert not (output / "project/reports/current.json").exists()
    site = output / result["site_relative_path"]
    assert "待复核资料" in (site / "sample-analysis-statistics.html").read_text()
    assert "NCT03829449" in (site / "inclusion-criteria.html").read_text()


@pytest.mark.parametrize("timestamp", [
    datetime(2099, 1, 1, tzinfo=UTC), datetime(2026, 10, 3),
])
def test_future_or_naive_observation_fails_before_candidate_creation(
    tmp_path: Path, timestamp: datetime,
) -> None:
    output = tmp_path / "invalid-observation-time"
    with pytest.raises(ValueError, match="时区|未来"):
        _builder()(source_root=_CAS_ROOT, raw_asset=_raw(), output=output,
            bindings=_full_bindings(), indication_id="pnh", indication="阵发性睡眠性血红蛋白尿症",
            cutoff="2026-09-26", observed_at=timestamp)
    assert not output.exists()


@pytest.mark.parametrize("mode", ["future", "naive", "before_observation"])
def test_invalid_preview_time_does_not_register_consumers_or_create_site(
    tmp_path: Path, mode: str,
) -> None:
    from tools.materialize_ctgov_c_candidate import render_review_preview

    output = tmp_path / "invalid-preview-time"
    observed = datetime(2026, 10, 3, tzinfo=UTC)
    _builder()(source_root=_CAS_ROOT, raw_asset=_raw(), output=output,
        bindings=_full_bindings(), indication_id="pnh", indication="阵发性睡眠性血红蛋白尿症",
        cutoff="2026-09-26", observed_at=observed)
    rendered = (datetime(2099, 1, 1, tzinfo=UTC) if mode == "future" else
                observed.replace(tzinfo=None) if mode == "naive" else
                observed - timedelta(seconds=1))
    with pytest.raises(ValueError, match="时区|未来|早于"):
        render_review_preview(output, rendered_at=rendered)
    assert not (output / "review-preview-manifest.json").exists()
    assert not (output / "project/reports/C/review-candidate/html").exists()
