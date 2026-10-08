"""Production regression family for bounded source-to-current refresh (ci-r24-100).

Uses the existing typed W04 project world (real A/B/C portal payloads, accepted
source atoms, user save lineage) and the existing compare/renderer services.
No fabricated pass strings: every assertion reads the actual persisted bytes,
SQLite rows, or rendered site files.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from ci_workflow.application.latest_delivery import (
    CurrentDeliveryBundle,
    CurrentReportDelivery,
)
from ci_workflow.application.source_current_refresh import (
    ReportCode,
    SourceCurrentRefreshCommand,
    SourceCurrentRefreshConflictError,
    SourceCurrentRefreshService,
    SourceFactRefusalError,
    SourceFactReplacement,
    SourceReportBuilderInput,
)
from ci_workflow.application.user_fact_edit import (
    FactEdit,
    UserFactEditService,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.active_fact_projection import ActiveFactBinding
from ci_workflow.renderers.portal.report_a import (
    ReportAPortalData,
    active_fact_binding_for_a,
)
from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    active_fact_binding_for_b,
)
from ci_workflow.reports.common.evidence_view import EvidenceField
from ci_workflow.storage.sqlite import open_database
from tests.integration.reports.test_b_report_portal import _page_json_assignment
from tests.integration.test_w04_user_fact_edit import (
    NOW,
    PROJECT_ID,
    _command,
    _project,
    _projection,
    _seed_fact,
)

SOURCE_FACT_ID = "fact-crude-rate"
SOURCE_VERSION_1 = "nct04558918-safety-report-v1"
SOURCE_VERSION_2 = "nct04558918-safety-report-v2"
SOURCE_VERSION_3 = "nct04558918-safety-report-v3"
SOURCE_FACT_1 = "fact-crude-rate-v1"
SOURCE_FACT_2 = "fact-crude-rate-v2"
SOURCE_FACT_3 = "fact-crude-rate-v3"
ROW_ID = "safe-apply-t-1"
AT = NOW + timedelta(minutes=5)
REFRESH_REQUEST = "source-refresh-1"


@dataclass(frozen=True)
class _World:
    root: Path
    user_version: str | None
    current: CurrentDeliveryBundle


def _projection_any(root: Path, report: str) -> Any:
    return cast(Any, _projection(root, report))


def _read_current(root: Path) -> CurrentDeliveryBundle:
    return UserFactEditService(root).read_current_delivery()


def _delivery(root: Path, report: str) -> CurrentReportDelivery:
    current = _read_current(root)
    return next(item for item in current.reports if item.report == report)


def _site_hashes(root: Path, delivery: CurrentReportDelivery) -> dict[str, str]:
    site = root / delivery.site_relative_path
    return {
        relative: hashlib.sha256((site / relative).read_bytes()).hexdigest()
        for relative in delivery.file_hashes
    }


def _builder_payload(root: Path, report: str) -> dict[str, Any]:
    delivery = _delivery(root, report)
    assert delivery.builder_input_relative_path is not None
    path = root / delivery.builder_input_relative_path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == delivery.builder_input_sha256
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _world(
    tmp_path: Path,
    *,
    user_edit: bool = False,
    edits: FactEdit | None = None,
    complete_workspace: bool = False,
) -> _World:
    root, _fragments = _project(
        tmp_path, cross_report_binding="legal_AB", complete_workspace=complete_workspace,
    )
    user_version: str | None = None
    if user_edit:
        saved = UserFactEditService(root).save(
            _command(
                request_id="source-refresh-user-seed",
                edits=edits or FactEdit(numerator=24, denominator=80),
            )
        )
        user_version = saved.fact_version_id
    return _World(root=root, user_version=user_version, current=_read_current(root))


def _write_new_inputs(
    root: Path,
    *,
    source_version: str,
    value: float,
    raw: str,
    numerator: int,
    denominator: int,
    tag: str = "source-v2",
    keep_old_binding: bool = False,
    keep_old_binding_reports: tuple[str, ...] = (),
) -> dict[str, str]:
    """Ordinary new builder inputs for A and B reflecting the new source atom."""
    a_payload = _builder_payload(root, "A")
    b_payload = _builder_payload(root, "B")
    a_row = next(row for row in a_payload["safety"] if row["row_id"] == ROW_ID)
    if not keep_old_binding and "A" not in keep_old_binding_reports:
        a_row["source_version_id"] = source_version
    a_row.update(value=value, numerator=numerator, denominator=denominator)
    # A now consumes the explicit source view too. A valid refreshed fixture
    # must update both representations; leaving its v1 view attached to the
    # v2 domain row is a source conflict, not a positive refresh example.
    a_view = a_payload.get("safety_views")
    if a_view is not None:
        a_view_row = next(row for row in a_view["facts"] if row["row_id"] == ROW_ID)
        if not keep_old_binding and "A" not in keep_old_binding_reports:
            a_view_row["source_version_id"] = source_version
        a_view_row.update(value=value, raw_value=raw,
                          numerator=numerator, denominator=denominator)
    b_row = next(row for row in b_payload["safety"] if row["row_id"] == ROW_ID)
    if not keep_old_binding and "B" not in keep_old_binding_reports:
        b_row["source_version_id"] = source_version
    b_row.update(value=value, numerator=numerator, denominator=denominator)
    view_rows = b_payload["safety_views"]["facts"]
    view_row = next(row for row in view_rows if row["row_id"] == ROW_ID)
    if not keep_old_binding and "B" not in keep_old_binding_reports:
        view_row["source_version_id"] = source_version
    view_row.update(
        value=value,
        raw_value=raw,
        numerator=numerator,
        denominator=denominator,
    )
    out_dir = root / "inputs" / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for report, payload in (("A", a_payload), ("B", b_payload)):
        path = out_dir / f"report-{report.lower()}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        paths[report] = path.relative_to(root).as_posix()
    return paths


def _new_bindings(root: Path, paths: dict[str, str]) -> tuple[ActiveFactBinding, ActiveFactBinding]:
    a_data = ReportAPortalData.model_validate_json((root / paths["A"]).read_bytes())
    b_data = ReportBPortalData.model_validate_json((root / paths["B"]).read_bytes())
    return (
        active_fact_binding_for_a(a_data, "safety", ROW_ID),
        active_fact_binding_for_b(b_data, "safety", ROW_ID),
    )


@pytest.mark.parametrize("field,bad", (
    ("source_version_id", SOURCE_VERSION_1),
    ("value", 99.0),
    ("source_text", "synthetic mismatched source quotation"),
))
def test_source_refresh_refuses_conflicting_a_view_before_render(
    tmp_path: Path, field: str, bad: object,
) -> None:
    world = _world(tmp_path)
    paths = _write_new_inputs(world.root, source_version=SOURCE_VERSION_2,
                             value=50.0, raw="50.0% (31/62)", numerator=31, denominator=62)
    _seed_source_atom(world.root, version_id=SOURCE_FACT_2, source_version=SOURCE_VERSION_2,
                      raw="50.0% (31/62)", normalized="50.0", numerator=31, denominator=62,
                      bindings=_new_bindings(world.root, paths))
    path = world.root / paths["A"]
    payload = json.loads(path.read_bytes())
    next(row for row in payload["safety_views"]["facts"] if row["row_id"] == ROW_ID)[field] = bad
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SourceFactRefusalError, match="A来源.*明细view"):
        SourceCurrentRefreshService(world.root).refresh(_refresh_command(world, paths=paths))
    assert _read_current(world.root) == world.current
    assert not (world.root / "reports/A/v1-source-r1").exists()
    assert not (world.root / "reports/B/v1-source-r1").exists()


def _seed_source_atom(
    root: Path,
    *,
    version_id: str,
    source_version: str,
    raw: str,
    normalized: str,
    numerator: int,
    denominator: int,
    bindings: tuple[ActiveFactBinding, ...],
    review_state: str = "accepted",
    context_override: dict[str, Any] | None = None,
    quote: str = "31/62例受试者发生任何TEAE（50.0%）。",
) -> None:
    locator = bindings[0].source_pointer
    assert all(item.source_pointer == locator for item in bindings)
    fragment_id = f"fragment-{version_id}"
    context: dict[str, Any] = {
        "numerator": numerator,
        "denominator": denominator,
        "raw_value": raw,
        "normalized_value": normalized,
    }
    if context_override is not None:
        context.update(context_override)
    identity_fields = (
        "product_id",
        "drug_name",
        "trial_id",
        "registry_id",
        "group_id",
        "arm",
        "cohort_id",
        "period",
        "endpoint_definition",
        "event_definition",
        "statistical_form",
        "measure_object",
        "unit",
        "normalized_unit",
    )
    for field in identity_fields:
        values = {json.dumps(getattr(item, field)) for item in bindings}
        assert len(values) == 1, f"shared source atom identity drift: {field}"
    with open_database(root / "state/project.sqlite") as database:
        database.execute(
            "INSERT INTO source_versions (source_version_id,source_id,content_sha256,"
            "acquired_at,created_at) VALUES (?,?,?,?,?)",
            (
                source_version,
                f"source-{hashlib.sha256(source_version.encode()).hexdigest()[:12]}",
                hashlib.sha256(source_version.encode()).hexdigest(),
                NOW.isoformat(),
                NOW.isoformat(),
            ),
        )
        database.execute(
            "INSERT INTO evidence_fragments (fragment_id,source_version_id,locator,"
            "content_text,content_sha256,created_at) VALUES (?,?,?,?,?,?)",
            (
                fragment_id,
                source_version,
                locator,
                quote,
                hashlib.sha256(quote.encode()).hexdigest(),
                NOW.isoformat(),
            ),
        )
        _seed_fact(
            database,
            fact_id=SOURCE_FACT_ID,
            version_id=version_id,
            entity_id="entity-arm",
            field_id="safety.crude_rate",
            raw_value=raw,
            normalized_value=normalized,
            fragment_id=fragment_id,
            context=context,
            review_state=review_state,
        )
        for binding in bindings:
            binding_json = json.dumps(
                binding.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            database.execute(
                "INSERT INTO source_portal_consumer_bindings (binding_id,"
                "source_fact_version_id,evidence_snapshot_id,report,collection,row_id,"
                "binding_json,binding_sha256,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    stable_id(
                        "source-portal-binding",
                        version_id,
                        binding.report,
                        binding.collection,
                        binding.row_id,
                    ),
                    version_id,
                    "evidence-snapshot-development",
                    binding.report,
                    binding.collection,
                    binding.row_id,
                    binding_json,
                    hashlib.sha256(binding_json.encode()).hexdigest(),
                    NOW.isoformat(),
                ),
            )


def _refresh_command(
    world: _World,
    *,
    paths: dict[str, str],
    request_id: str = REFRESH_REQUEST,
    expected_revision: int | None = None,
    current_version: str | None = None,
    user_version: str | None = None,
    base_version: str | None = None,
    source_version: str = SOURCE_VERSION_2,
    replacement_version: str = SOURCE_FACT_2,
    rationale: str = "来源CT.gov再获取，已接受原子替换。",
    inputs: dict[str, SourceReportBuilderInput] | None = None,
) -> SourceCurrentRefreshCommand:
    if current_version is None:
        current_version = user_version if user_version is not None else SOURCE_FACT_1
    if inputs is None:
        inputs = {
            report: SourceReportBuilderInput(
                report=cast(ReportCode, report),
                input_relative_path=paths[report],
                input_sha256=hashlib.sha256((world.root / paths[report]).read_bytes()).hexdigest(),
            )
            for report in paths
        }
    return SourceCurrentRefreshCommand(
        request_id=request_id,
        project_id=PROJECT_ID,
        expected_revision=(
            world.current.revision if expected_revision is None else expected_revision
        ),
        requested_by="source-refresh-worker",
        requested_at=AT,
        replacements=(
            SourceFactReplacement(
                fact_id=SOURCE_FACT_ID,
                current_fact_version_id=current_version,
                replacement_fact_version_id=replacement_version,
                replacement_source_version_id=source_version,
                base_fact_version_id=base_version,
                user_fact_version_id=user_version,
                rationale_zh=rationale,
            ),
        ),
        builder_inputs=tuple(inputs[report] for report in sorted(inputs)),
    )


def _source_atom_count(root: Path) -> int:
    with open_database(root / "state/project.sqlite") as database:
        row = database.execute("SELECT COUNT(*) FROM fact_versions").fetchone()
    assert row is not None
    return int(row[0])


# ── 1. 真实无用户层 A+B 来源更新 ────────────────────────────────────────────
# Replaces the historical implementation-blocker/xfail with actual native
# consumers, values, source identity and immutable previous-current assertions.


def test_no_user_source_update_rebuilds_a_and_b_and_preserves_c(tmp_path: Path) -> None:
    world = _world(tmp_path)
    root = world.root
    assert world.current.revision == 0
    paths = _write_new_inputs(
        root,
        source_version=SOURCE_VERSION_2,
        value=50.0,
        raw="50.0% (31/62)",
        numerator=31,
        denominator=62,
    )
    bindings = _new_bindings(root, paths)
    _seed_source_atom(
        root,
        version_id=SOURCE_FACT_2,
        source_version=SOURCE_VERSION_2,
        raw="50.0% (31/62)",
        normalized="50.0",
        numerator=31,
        denominator=62,
        bindings=bindings,
    )
    c_before = _delivery(root, "C")
    c_hashes = _site_hashes(root, c_before)
    current_pointer = (root / "reports/current.json").read_bytes()
    old_builder_hashes: dict[Path, str] = {}
    for report in ("A", "B", "C"):
        old_delivery = _delivery(root, report)
        assert old_delivery.builder_input_relative_path is not None
        old_path = root / old_delivery.builder_input_relative_path
        old_builder_hashes[old_path] = hashlib.sha256(old_path.read_bytes()).hexdigest()
    with open_database(root / "state/project.sqlite") as database:
        source_fact_before = database.execute(
            "SELECT raw_value,normalized_value,scientific_context_json FROM fact_versions "
            "WHERE fact_version_id=?",
            (SOURCE_FACT_1,),
        ).fetchone()

    result = SourceCurrentRefreshService(root).refresh(_refresh_command(world, paths=paths))

    assert result.revision == 1
    assert result.rebuilt_reports == ("A", "B")
    assert result.appended_fact_version_ids == ()
    assert result.effective_fact_version_ids == {SOURCE_FACT_ID: SOURCE_FACT_2}
    assert result.replacement_source_version_ids == (SOURCE_VERSION_2,)
    current = _read_current(root)
    assert current.revision == 1 and current.request_id == REFRESH_REQUEST
    for report in ("A", "B"):
        delivery = _delivery(root, report)
        assert delivery.revision == 1
        projection = _projection_any(root, report)
        row = next(item for item in projection["safety"] if item["row_id"] == ROW_ID)
        assert row["value"] == 50.0
        assert not projection.get("user_edits")
        receipt = json.loads(
            (root / delivery.site_relative_path / "data/consumer-receipt.json").read_text()
        )
        assert any(
            item["fact_version_id"] == SOURCE_FACT_2
            and item["row_id"] == ROW_ID
            and item["binding_identity"]["source_version_id"] == SOURCE_VERSION_2
            for item in receipt["consumers"]
        )
        search = (root / delivery.site_relative_path / "data/search-index.js").read_text()
        assert "50" in search
    b_site = root / _delivery(root, "B").site_relative_path
    chart_groups = _page_json_assignment(b_site, "safety.html", "__CHART_GROUPS__")
    chart_row = next(
        row
        for group in chart_groups
        for row in group["rows"]
        if row["row_id"] == ROW_ID
    )
    assert chart_row["value"] == 50.0
    evidence_views = _page_json_assignment(b_site, "safety.html", "__EVIDENCE_VIEWS__")
    evidence_row = next(
        view for view in evidence_views
        if view.get("row", {}).get("row_id") == ROW_ID
    )
    # ReportRow carries identity; observed values are separate EvidenceFields.
    # Native legacy IDs/names are retained by the documented serialization
    # boundary, not silently converted to canonical ReportRow IDs/Chinese names.
    assert float(EvidenceField.model_validate(evidence_row["value"]).value) == 50.0
    assert EvidenceField.model_validate(evidence_row["numerator"]).value == "31"
    assert EvidenceField.model_validate(evidence_row["denominator"]).value == "62"
    assert evidence_row["source_version_id"] == SOURCE_VERSION_2
    assert evidence_row["source_trace_state"] == "located"
    assert evidence_row["user_edit"] is None
    # 未受影响报告、旧来源原子、旧builder输入与current协议字节保持不变
    assert _delivery(root, "C") == c_before
    for relative, digest in c_hashes.items():
        assert (
            hashlib.sha256(
                (root / c_before.site_relative_path / relative).read_bytes()
            ).hexdigest()
            == digest
        )
    assert (root / "reports/current.json").read_bytes() == current_pointer
    for old_path, digest in old_builder_hashes.items():
        assert hashlib.sha256(old_path.read_bytes()).hexdigest() == digest
    with open_database(root / "state/project.sqlite") as database:
        source_fact_after = database.execute(
            "SELECT raw_value,normalized_value,scientific_context_json FROM fact_versions "
            "WHERE fact_version_id=?",
            (SOURCE_FACT_1,),
        ).fetchone()
        user_modified = database.execute(
            "SELECT COUNT(*) FROM fact_versions WHERE review_state='user_modified'"
        ).fetchone()
        replacement_state = database.execute(
            "SELECT review_state FROM fact_versions WHERE fact_version_id=?",
            (SOURCE_FACT_2,),
        ).fetchone()
    assert source_fact_after == source_fact_before
    assert user_modified == (0,)
    assert replacement_state == ("accepted",)


# ── 2/3. 用户修订与显式清除在来源未变时保留 ────────────────────────────────


def _user_rebase_world(
    tmp_path: Path,
    *,
    edits: FactEdit | None,
    keep_old_binding_reports: tuple[str, ...] = (),
) -> tuple[_World, dict[str, str]]:
    world = _world(tmp_path, user_edit=True, edits=edits)
    root = world.root
    assert world.user_version is not None
    paths = _write_new_inputs(
        root,
        source_version=SOURCE_VERSION_2,
        value=54.8,
        raw="54.8% (34/62)",
        numerator=34,
        denominator=62,
        keep_old_binding_reports=keep_old_binding_reports,
    )
    bindings = _new_bindings(root, paths)
    _seed_source_atom(
        root,
        version_id=SOURCE_FACT_2,
        source_version=SOURCE_VERSION_2,
        raw="54.8% (34/62)",
        normalized="54.8",
        numerator=34,
        denominator=62,
        bindings=bindings,
    )
    return world, paths


def test_user_edit_rebase_preserves_user_layer_on_unchanged_source(tmp_path: Path) -> None:
    world, paths = _user_rebase_world(tmp_path, edits=None)
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    with open_database(root / "state/project.sqlite") as database:
        user_before = database.execute(
            "SELECT raw_value,normalized_value,scientific_context_json FROM fact_versions "
            "WHERE fact_version_id=?",
            (user_version,),
        ).fetchone()

    result = SourceCurrentRefreshService(root).refresh(
        _refresh_command(
            world,
            paths=paths,
            request_id="source-refresh-user-rebase",
            current_version=user_version,
            user_version=user_version,
            base_version=SOURCE_FACT_1,
        )
    )

    assert result.rebuilt_reports == ("A", "B")
    rebased_id = result.effective_fact_version_ids[SOURCE_FACT_ID]
    assert result.appended_fact_version_ids == (rebased_id,)
    with open_database(root / "state/project.sqlite") as database:
        row = database.execute(
            "SELECT review_state,supersedes_fact_version_id,raw_value,normalized_value,"
            "primary_fragment_id,scientific_context_json FROM fact_versions "
            "WHERE fact_version_id=?",
            (rebased_id,),
        ).fetchone()
        user_after = database.execute(
            "SELECT raw_value,normalized_value,scientific_context_json FROM fact_versions "
            "WHERE fact_version_id=?",
            (user_version,),
        ).fetchone()
    assert row is not None
    assert row[0] == "user_modified"
    assert row[1] == SOURCE_FACT_2
    assert row[2] == "30% (24/80)"
    assert row[3] == "30.0"
    assert row[4] == f"fragment-{SOURCE_FACT_2}"
    context = json.loads(str(row[5]))
    assert context["user_edit"]["request_id"] == "source-refresh-user-seed"
    assert context["user_edit"]["cleared"] is False
    rebase = context["user_edit"]["rebase"]
    assert rebase["original_user_fact_version_id"] == user_version
    assert rebase["original_base_fact_version_id"] == SOURCE_FACT_1
    assert rebase["rebased_on_source_fact_version_id"] == SOURCE_FACT_2
    assert rebase["rebased_on_source_version_id"] == SOURCE_VERSION_2
    assert rebase["refresh_request_id"] == "source-refresh-user-rebase"
    assert all(
        binding["source_version_id"] == SOURCE_VERSION_2
        for binding in context["consumer_bindings"]
    )
    assert user_after == user_before
    for report in ("A", "B"):
        delivery = _delivery(root, report)
        declared = hashlib.sha256((root / paths[report]).read_bytes()).hexdigest()
        assert delivery.builder_input_sha256 == declared
        assert delivery.builder_input_relative_path == (
            f"state/source-refresh-builder-inputs/{declared}.json"
        )
    projection = _projection_any(root, "A")
    row_projection = next(
        item for item in projection["safety"] if item["row_id"] == ROW_ID
    )
    assert row_projection["value"] == 30.0
    edit = projection["user_edits"][ROW_ID]
    assert edit["original_value"].startswith("54.8")
    assert edit["current_value"] == "30% (24/80)"
    assert edit["status_label_zh"] == "用户修订，未独立复核"


def test_user_explicit_clear_rebase_keeps_clear_and_original_source(tmp_path: Path) -> None:
    world, paths = _user_rebase_world(tmp_path, edits=FactEdit(raw_value=None))
    root = world.root
    user_version = world.user_version
    assert user_version is not None

    result = SourceCurrentRefreshService(root).refresh(
        _refresh_command(
            world,
            paths=paths,
            request_id="source-refresh-user-clear",
            current_version=user_version,
            user_version=user_version,
            base_version=SOURCE_FACT_1,
        )
    )

    rebased_id = result.effective_fact_version_ids[SOURCE_FACT_ID]
    with open_database(root / "state/project.sqlite") as database:
        row = database.execute(
            "SELECT review_state,raw_value,normalized_value,supersedes_fact_version_id,"
            "scientific_context_json FROM fact_versions WHERE fact_version_id=?",
            (rebased_id,),
        ).fetchone()
    assert row is not None
    assert row[0] == "user_modified"
    assert row[1] is None and row[2] is None
    assert row[3] == SOURCE_FACT_2
    context = json.loads(str(row[4]))
    assert context["user_edit"]["cleared"] is True
    assert context["numerator"] is None and context["denominator"] is None
    projection = _projection_any(root, "A")
    cleared = next(item for item in projection["safety"] if item["row_id"] == ROW_ID)
    assert cleared["value"] is None
    assert "用户清除" in str(cleared["disclosure_state"])
    edit = projection["user_edits"][ROW_ID]
    assert edit["original_value"].startswith("54.8")
    assert "用户清除" in edit["status_label_zh"]


def test_user_source_convergence_stays_explicit(tmp_path: Path) -> None:
    """用户值与新来源收敛：显式CONVERGED并保留用户层provenance，不按冲突处理。"""
    world = _world(tmp_path, user_edit=True)
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    paths = _write_new_inputs(
        root,
        source_version=SOURCE_VERSION_2,
        value=30.0,
        raw="30% (24/80)",
        numerator=24,
        denominator=80,
    )
    bindings = _new_bindings(root, paths)
    _seed_source_atom(
        root,
        version_id=SOURCE_FACT_2,
        source_version=SOURCE_VERSION_2,
        raw="30% (24/80)",
        normalized="30.0",
        numerator=24,
        denominator=80,
        bindings=bindings,
    )

    result = SourceCurrentRefreshService(root).refresh(
        _refresh_command(
            world,
            paths=paths,
            request_id="source-refresh-converged",
            current_version=user_version,
            user_version=user_version,
            base_version=SOURCE_FACT_1,
        )
    )

    rebased_id = result.effective_fact_version_ids[SOURCE_FACT_ID]
    with open_database(root / "state/project.sqlite") as database:
        states_row = database.execute(
            "SELECT field_states_json FROM user_refresh_conflicts WHERE request_id=?",
            ("source-refresh-converged:fact-crude-rate",),
        ).fetchone()
        row = database.execute(
            "SELECT raw_value,scientific_context_json FROM fact_versions WHERE fact_version_id=?",
            (rebased_id,),
        ).fetchone()
    assert states_row is not None and row is not None
    states = json.loads(str(states_row[0]))
    assert states["raw_value"] == "converged"
    assert states["normalized_value"] == "converged"
    assert states["numerator"] == "converged"
    context = json.loads(str(row[1]))
    assert context["user_edit"]["request_id"] == "source-refresh-user-seed"
    assert context["user_edit"]["rebase"]["rebased_on_source_fact_version_id"] == SOURCE_FACT_2
    assert row[0] == "30% (24/80)"
    projection = _projection_any(root, "A")
    row_projection = next(item for item in projection["safety"] if item["row_id"] == ROW_ID)
    assert row_projection["value"] == 30.0


def test_second_source_refresh_rebases_again_from_original_user_lineage(
    tmp_path: Path,
) -> None:
    """已rebase的current再次遇到新来源：仍以原用户/来源谱系三方比较并追加rebase。"""
    world, paths = _user_rebase_world(tmp_path, edits=None)
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    first = SourceCurrentRefreshService(root).refresh(
        _refresh_command(
            world,
            paths=paths,
            request_id="source-refresh-first",
            current_version=user_version,
            user_version=user_version,
            base_version=SOURCE_FACT_1,
        )
    )
    rebased_1 = first.effective_fact_version_ids[SOURCE_FACT_ID]

    paths_3 = _write_new_inputs(
        root,
        source_version=SOURCE_VERSION_3,
        value=54.8,
        raw="54.8% (34/62)",
        numerator=34,
        denominator=62,
        tag="source-v3",
    )
    bindings_3 = _new_bindings(root, paths_3)
    _seed_source_atom(
        root,
        version_id=SOURCE_FACT_3,
        source_version=SOURCE_VERSION_3,
        raw="54.8% (34/62)",
        normalized="54.8",
        numerator=34,
        denominator=62,
        bindings=bindings_3,
    )
    with open_database(root / "state/project.sqlite") as database:
        rebased_1_before = database.execute(
            "SELECT raw_value,scientific_context_json FROM fact_versions WHERE fact_version_id=?",
            (rebased_1,),
        ).fetchone()
        user_before = database.execute(
            "SELECT content_sha256 FROM fact_versions WHERE fact_version_id=?",
            (user_version,),
        ).fetchone()

    second = SourceCurrentRefreshService(root).refresh(
        SourceCurrentRefreshCommand(
            request_id="source-refresh-second",
            project_id=PROJECT_ID,
            expected_revision=first.revision,
            requested_by="source-refresh-worker",
            requested_at=AT + timedelta(minutes=5),
            replacements=(
                SourceFactReplacement(
                    fact_id=SOURCE_FACT_ID,
                    current_fact_version_id=rebased_1,
                    replacement_fact_version_id=SOURCE_FACT_3,
                    replacement_source_version_id=SOURCE_VERSION_3,
                    base_fact_version_id=SOURCE_FACT_1,
                    user_fact_version_id=user_version,
                    rationale_zh="第二次来源再获取，已接受原子替换。",
                ),
            ),
            builder_inputs=tuple(
                SourceReportBuilderInput(
                    report=cast(ReportCode, report),
                    input_relative_path=paths_3[report],
                    input_sha256=hashlib.sha256(
                        (root / paths_3[report]).read_bytes()
                    ).hexdigest(),
                )
                for report in sorted(paths_3)
            ),
        )
    )

    assert second.revision == first.revision + 1
    rebased_2 = second.effective_fact_version_ids[SOURCE_FACT_ID]
    assert second.appended_fact_version_ids == (rebased_2,)
    with open_database(root / "state/project.sqlite") as database:
        row = database.execute(
            "SELECT review_state,supersedes_fact_version_id,raw_value,"
            "scientific_context_json FROM fact_versions WHERE fact_version_id=?",
            (rebased_2,),
        ).fetchone()
        rebased_1_after = database.execute(
            "SELECT raw_value,scientific_context_json FROM fact_versions WHERE fact_version_id=?",
            (rebased_1,),
        ).fetchone()
        user_after = database.execute(
            "SELECT content_sha256 FROM fact_versions WHERE fact_version_id=?",
            (user_version,),
        ).fetchone()
    assert row is not None
    assert row[0] == "user_modified"
    assert row[1] == SOURCE_FACT_3
    assert row[2] == "30% (24/80)"
    context = json.loads(str(row[3]))
    assert context["user_edit"]["rebase"]["original_user_fact_version_id"] == user_version
    assert context["user_edit"]["rebase"]["rebased_on_source_fact_version_id"] == SOURCE_FACT_3
    assert context["user_edit"]["rebase"]["rebased_on_source_version_id"] == SOURCE_VERSION_3
    assert rebased_1_after == rebased_1_before
    assert user_after == user_before
    projection = _projection_any(root, "A")
    row_projection = next(
        item for item in projection["safety"] if item["row_id"] == ROW_ID
    )
    assert row_projection["value"] == 30.0


# ── 4. 用户层与来源层分歧：失败关闭且不切换 current ─────────────────────────


def test_user_source_divergence_refuses_without_switching_current(tmp_path: Path) -> None:
    world = _world(tmp_path, user_edit=True)
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    paths = _write_new_inputs(
        root,
        source_version=SOURCE_VERSION_2,
        value=50.0,
        raw="50.0% (31/62)",
        numerator=31,
        denominator=62,
    )
    bindings = _new_bindings(root, paths)
    _seed_source_atom(
        root,
        version_id=SOURCE_FACT_2,
        source_version=SOURCE_VERSION_2,
        raw="50.0% (31/62)",
        normalized="50.0",
        numerator=31,
        denominator=62,
        bindings=bindings,
    )
    before = _read_current(root)

    with pytest.raises(SourceFactRefusalError, match="显式解决"):
        SourceCurrentRefreshService(root).refresh(
            _refresh_command(
                world,
                paths=paths,
                request_id="source-refresh-conflict",
                current_version=user_version,
                user_version=user_version,
                base_version=SOURCE_FACT_1,
            )
        )

    assert _read_current(root) == before
    assert not tuple(root.glob("reports/*/v1-source-r*"))
    assert not (root / "state/source-refresh-builder-inputs").exists()
    with open_database(root / "state/project.sqlite") as database:
        comparison = database.execute(
            "SELECT requires_explicit_resolution FROM user_refresh_conflicts "
            "WHERE request_id=?",
            ("source-refresh-conflict:fact-crude-rate",),
        ).fetchone()
    assert comparison == (1,)


# ── 5. 候选来源原子拒绝 ─────────────────────────────────────────────────────


def test_candidate_source_atom_refuses_before_any_write(tmp_path: Path) -> None:
    world = _world(tmp_path)
    root = world.root
    paths = _write_new_inputs(
        root,
        source_version=SOURCE_VERSION_2,
        value=50.0,
        raw="50.0% (31/62)",
        numerator=31,
        denominator=62,
    )
    bindings = _new_bindings(root, paths)
    _seed_source_atom(
        root,
        version_id=SOURCE_FACT_2,
        source_version=SOURCE_VERSION_2,
        raw="50.0% (31/62)",
        normalized="50.0",
        numerator=31,
        denominator=62,
        bindings=bindings,
        review_state="candidate",
    )
    facts_before = _source_atom_count(root)

    with pytest.raises(SourceFactRefusalError, match="已接受事实"):
        SourceCurrentRefreshService(root).refresh(
            _refresh_command(world, paths=paths, request_id="source-refresh-candidate")
        )

    assert _read_current(root).revision == 0
    assert _source_atom_count(root) == facts_before
    assert not tuple(root.glob("reports/*/v1-source-r*"))
    assert not (root / "state/source-refresh-builder-inputs").exists()


# ── 6. 身份/绑定/取值漂移拒绝 ───────────────────────────────────────────────


@pytest.mark.parametrize(
    ("declared_source", "context_override", "match"),
    (
        ("nct04558918-safety-report-vX", None, "声明来源版本"),
        (SOURCE_VERSION_2, {"raw_value": "999% (1/1)"}, "上下文不一致"),
    ),
)
def test_source_atom_binding_or_context_value_drift_refuses(
    tmp_path: Path,
    declared_source: str,
    context_override: dict[str, Any] | None,
    match: str,
) -> None:
    world = _world(tmp_path)
    root = world.root
    paths = _write_new_inputs(
        root,
        source_version=SOURCE_VERSION_2,
        value=50.0,
        raw="50.0% (31/62)",
        numerator=31,
        denominator=62,
    )
    bindings = _new_bindings(root, paths)
    _seed_source_atom(
        root,
        version_id=SOURCE_FACT_2,
        source_version=SOURCE_VERSION_2,
        raw="50.0% (31/62)",
        normalized="50.0",
        numerator=31,
        denominator=62,
        bindings=bindings,
        context_override=context_override,
    )

    with pytest.raises(SourceFactRefusalError, match=match):
        SourceCurrentRefreshService(root).refresh(
            _refresh_command(
                world,
                paths=paths,
                request_id="source-refresh-drift",
                source_version=declared_source,
            )
        )

    assert _read_current(root).revision == 0
    assert not tuple(root.glob("reports/*/v1-source-r*"))


def test_target_identity_drift_refuses(tmp_path: Path) -> None:
    world = _world(tmp_path)
    root = world.root
    paths = _write_new_inputs(
        root,
        source_version=SOURCE_VERSION_2,
        value=50.0,
        raw="50.0% (31/62)",
        numerator=31,
        denominator=62,
    )
    bindings = _new_bindings(root, paths)
    _seed_source_atom(
        root,
        version_id=SOURCE_FACT_2,
        source_version=SOURCE_VERSION_2,
        raw="50.0% (31/62)",
        normalized="50.0",
        numerator=31,
        denominator=62,
        bindings=bindings,
    )
    command = _refresh_command(world, paths=paths, request_id="source-refresh-identity")
    tampered = command.model_copy(
        update={
            "replacements": (
                command.replacements[0].model_copy(
                    update={"current_fact_version_id": "fact-adjusted-rate-v1"}
                ),
            )
        }
    )

    with pytest.raises(SourceCurrentRefreshConflictError, match="替换目标"):
        SourceCurrentRefreshService(root).refresh(tampered)

    assert _read_current(root).revision == 0


# ── 7/8/9/10. builder输入边界 ───────────────────────────────────────────────


def _prepared_user_world(
    tmp_path: Path,
) -> tuple[_World, dict[str, str], tuple[ActiveFactBinding, ...]]:
    world, paths = _user_rebase_world(tmp_path, edits=None)
    root = world.root
    bindings = _new_bindings(root, paths)
    return world, paths, bindings


def test_builder_input_hash_drift_refuses(tmp_path: Path) -> None:
    world, paths, _bindings = _prepared_user_world(tmp_path)
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    wrong = SourceReportBuilderInput(
        report="B",
        input_relative_path=paths["B"],
        input_sha256=hashlib.sha256((root / paths["A"]).read_bytes()).hexdigest(),
    )
    command = _refresh_command(
        world,
        paths=paths,
        request_id="source-refresh-hash",
        current_version=user_version,
        user_version=user_version,
        base_version=SOURCE_FACT_1,
        inputs={
            "A": SourceReportBuilderInput(
                report="A",
                input_relative_path=paths["A"],
                input_sha256=hashlib.sha256((root / paths["A"]).read_bytes()).hexdigest(),
            ),
            "B": wrong,
        },
    )

    with pytest.raises(SourceFactRefusalError, match="哈希不一致"):
        SourceCurrentRefreshService(root).refresh(command)

    assert _read_current(root).revision == 1
    assert not tuple(root.glob("reports/*/v1-source-r*"))


def test_builder_input_row_binding_drift_refuses(tmp_path: Path) -> None:
    world, paths = _user_rebase_world(
        tmp_path, edits=None, keep_old_binding_reports=("A", "B")
    )
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    bindings = _new_bindings(root, paths)
    assert all(item.source_version_id == SOURCE_VERSION_1 for item in bindings)

    # The view identity is now rejected in the all-consumer preflight, before rendering.
    with pytest.raises(SourceFactRefusalError, match="A来源版本与明细view不一致"):
        SourceCurrentRefreshService(root).refresh(
            _refresh_command(
                world,
                paths=paths,
                request_id="source-refresh-row-drift",
                current_version=user_version,
                user_version=user_version,
                base_version=SOURCE_FACT_1,
            )
        )

    assert _read_current(root).revision == 1
    assert not tuple(root.glob("reports/*/v1-source-r*"))


def test_bad_later_consumer_leaves_no_partial_staging(tmp_path: Path) -> None:
    """A 可核验、B 行绑定漂移：整体预检失败且不留任何暂存产物。"""
    world, paths = _user_rebase_world(
        tmp_path, edits=None, keep_old_binding_reports=("B",)
    )
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    command = _refresh_command(
        world,
        paths=paths,
        request_id="source-refresh-bad-later",
        current_version=user_version,
        user_version=user_version,
        base_version=SOURCE_FACT_1,
    )
    before = _read_current(root)

    with pytest.raises(SourceFactRefusalError, match="B来源版本与明细view不一致"):
        SourceCurrentRefreshService(root).refresh(command)

    assert _read_current(root) == before
    assert not tuple(root.glob("reports/*/v1-source-r*"))
    journal_name = hashlib.sha256(b"source-refresh-bad-later").hexdigest()
    assert not (root / f"state/user-fact-transactions/{journal_name}.json").exists()


def test_forced_unaffected_report_input_refuses(tmp_path: Path) -> None:
    world, paths, _bindings = _prepared_user_world(tmp_path)
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    c_delivery = _delivery(root, "C")
    assert c_delivery.builder_input_relative_path is not None
    c_input = root / c_delivery.builder_input_relative_path
    command = _refresh_command(
        world,
        paths=paths,
        request_id="source-refresh-forced-c",
        current_version=user_version,
        user_version=user_version,
        base_version=SOURCE_FACT_1,
        inputs={
            "A": SourceReportBuilderInput(
                report="A",
                input_relative_path=paths["A"],
                input_sha256=hashlib.sha256((root / paths["A"]).read_bytes()).hexdigest(),
            ),
            "B": SourceReportBuilderInput(
                report="B",
                input_relative_path=paths["B"],
                input_sha256=hashlib.sha256((root / paths["B"]).read_bytes()).hexdigest(),
            ),
            "C": SourceReportBuilderInput(
                report="C",
                input_relative_path=c_delivery.builder_input_relative_path,
                input_sha256=hashlib.sha256(c_input.read_bytes()).hexdigest(),
            ),
        },
    )

    with pytest.raises(SourceFactRefusalError, match="禁止强制重建"):
        SourceCurrentRefreshService(root).refresh(command)

    assert _read_current(root).revision == 1


# ── 11. 首个报告后失败：旧current保持，重试不重复版本 ─────────────────────


def test_fail_after_first_report_keeps_old_current_and_retry_reuses_versions(
    tmp_path: Path,
) -> None:
    world, paths = _user_rebase_world(tmp_path, edits=None)
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    command = _refresh_command(
        world,
        paths=paths,
        request_id="source-refresh-fault-retry",
        current_version=user_version,
        user_version=user_version,
        base_version=SOURCE_FACT_1,
    )
    before = _read_current(root)
    service = SourceCurrentRefreshService(root)

    def interrupt(report: str) -> None:
        if report == "A":
            raise OSError("injected failure after first affected report")

    service._after_report_built = interrupt
    with pytest.raises(OSError, match="first affected report"):
        service.refresh(command)
    assert _read_current(root) == before
    journal_name = hashlib.sha256(command.request_id.encode()).hexdigest()
    assert not (root / f"state/user-fact-transactions/{journal_name}.json").exists()
    facts_after_fault = _source_atom_count(root)
    a_staging = root / "reports/A" / f"v1-source-r{before.revision + 1}" / "html.manifest.json"
    assert a_staging.is_file()  # 首个报告已提交渲染事务，但未切换current
    a_manifest_sha = hashlib.sha256(a_staging.read_bytes()).hexdigest()

    # 重试必须复用已暂存的A产物：若重新渲染A则失败。
    import ci_workflow.application.user_fact_edit as user_fact_edit_module

    def fail_render(data: Any, site_root: Path, **kwargs: Any) -> None:
        raise AssertionError("retry must reuse the staged A report, not re-render")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(user_fact_edit_module, "render_report_a_site", fail_render)
    try:
        retry = SourceCurrentRefreshService(root).refresh(command)
    finally:
        monkeypatch.undo()

    assert retry.rebuilt_reports == ("A", "B")
    assert len(retry.appended_fact_version_ids) == 1
    assert _read_current(root).revision == before.revision + 1
    assert _source_atom_count(root) == facts_after_fault
    assert hashlib.sha256(a_staging.read_bytes()).hexdigest() == a_manifest_sha
    with open_database(root / "state/project.sqlite") as database:
        rebase_count = database.execute(
            "SELECT COUNT(*) FROM fact_versions WHERE review_state='user_modified'"
        ).fetchone()
    assert rebase_count == (2,)  # 用户种子版本 + 一次重基线，不重复
    events = [
        event
        for event in SourceCurrentRefreshService(root).event_store.read_all()
        if event.idempotency_key == f"source.current.refresh:{command.request_id}"
    ]
    assert len(events) == 1


def test_fault_after_prepared_journal_resumes_identical_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """journal已prepare但未提交：精确重试续跑，不重复事实/产物/事件。"""
    import ci_workflow.application.source_current_refresh as module

    world, paths, _bindings = _prepared_user_world(tmp_path)
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    command = _refresh_command(
        world,
        paths=paths,
        request_id="source-refresh-journal-resume",
        current_version=user_version,
        user_version=user_version,
        base_version=SOURCE_FACT_1,
    )
    original_commit = module.commit_current_transaction
    failed = False

    def fail_once(
        project_root: Path,
        *,
        request_id: str,
        candidate: CurrentDeliveryBundle,
    ) -> Any:
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("injected journal commit failure")
        return original_commit(project_root, request_id=request_id, candidate=candidate)

    monkeypatch.setattr(module, "commit_current_transaction", fail_once)
    with pytest.raises(OSError, match="journal commit"):
        SourceCurrentRefreshService(root).refresh(command)
    assert _read_current(root).revision == 1
    journal = root / (
        "state/user-fact-transactions/"
        + hashlib.sha256(command.request_id.encode()).hexdigest()
        + ".json"
    )
    assert journal.is_file()
    assert json.loads(journal.read_text(encoding="utf-8"))["phase"] == "prepared"
    facts_after_fault = _source_atom_count(root)

    monkeypatch.undo()
    result = SourceCurrentRefreshService(root).refresh(command)

    assert result.revision == 2
    assert _source_atom_count(root) == facts_after_fault
    assert json.loads(journal.read_text(encoding="utf-8"))["phase"] == "ready"
    events = [
        event
        for event in SourceCurrentRefreshService(root).event_store.read_all()
        if event.idempotency_key == f"source.current.refresh:{command.request_id}"
    ]
    assert len(events) == 1
    assert _read_current(root).request_id == command.request_id


# ── 12/13. 幂等重放、同请求不同载荷、过期revision ──────────────────────────


def test_identical_retry_returns_same_result_and_payload_mismatch_fails(
    tmp_path: Path,
) -> None:
    world, paths, _bindings = _prepared_user_world(tmp_path)
    root = world.root
    user_version = world.user_version
    assert user_version is not None
    command = _refresh_command(
        world,
        paths=paths,
        request_id="source-refresh-replay",
        current_version=user_version,
        user_version=user_version,
        base_version=SOURCE_FACT_1,
    )
    service = SourceCurrentRefreshService(root)

    result = service.refresh(command)
    replay = SourceCurrentRefreshService(root).refresh(command)

    assert replay == result
    tampered = command.model_copy(
        update={
            "replacements": (
                command.replacements[0].model_copy(update={"rationale_zh": "另一份来源载荷。"}),
            )
        }
    )
    with pytest.raises(SourceCurrentRefreshConflictError, match="不同载荷"):
        service.refresh(tampered)


def test_stale_expected_revision_refuses(tmp_path: Path) -> None:
    world = _world(tmp_path, user_edit=True)
    root = world.root
    assert _read_current(root).revision == 1
    paths = _write_new_inputs(
        root,
        source_version=SOURCE_VERSION_2,
        value=50.0,
        raw="50.0% (31/62)",
        numerator=31,
        denominator=62,
    )

    with pytest.raises(SourceCurrentRefreshConflictError, match="版本冲突"):
        SourceCurrentRefreshService(root).refresh(
            _refresh_command(
                world,
                paths=paths,
                request_id="source-refresh-stale",
                expected_revision=0,
            )
        )

    assert _read_current(root).revision == 1
