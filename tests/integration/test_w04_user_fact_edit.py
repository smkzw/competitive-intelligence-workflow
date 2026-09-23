from __future__ import annotations

import hashlib
import http.client
import json
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import ci_workflow.application.latest_delivery as latest_delivery_module
import ci_workflow.application.user_fact_edit as user_fact_edit_module
import ci_workflow.storage.event_store as event_store_module
from ci_workflow.application.latest_delivery import (
    CurrentDeliveryBundle,
    CurrentDeliveryJournal,
    CurrentReportDelivery,
    publish_current_delivery,
    read_effective_delivery,
    read_latest_delivery,
)
from ci_workflow.application.refresh_service import RefreshService
from ci_workflow.application.user_fact_edit import (
    CurrentDeliveryConflictError,
    FactEdit,
    FactTargetIdentity,
    RefreshFieldState,
    UserFactEditService,
    UserFactSaveCommand,
    UserFactSaveConflictError,
    UserFactSaveError,
    UserFactSaveResult,
)
from ci_workflow.application.user_fact_edit_server import LoopbackEditServer
from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.domain.enums import OutputFormat, ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.graph.impact import (
    ImpactEdge,
    ImpactGraph,
    ImpactGraphError,
    ImpactLayer,
    ImpactNode,
)
from ci_workflow.renderers.portal.active_fact_projection import canonical_source_pointer
from ci_workflow.renderers.portal.report_a import (
    ReportAPortalData,
    SafetyRow,
    active_fact_binding_for_a,
    render_report_a_site,
)
from ci_workflow.renderers.portal.report_b import (
    ReportBPortalData,
    active_fact_binding_for_b,
    render_report_b_site,
)
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    active_fact_binding_for_c,
    render_report_c_site,
)
from ci_workflow.storage.event_store import EventStore, EventStoreError, WorkflowEvent
from ci_workflow.storage.migrations import persist_project_contract
from ci_workflow.storage.sqlite import open_database

NOW = datetime(2026, 9, 22, 18, 0, tzinfo=UTC)
PROJECT_ID = "project-w04"


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _seed_fact(
    database: sqlite3.Connection,
    *,
    fact_id: str,
    version_id: str,
    entity_id: str,
    field_id: str,
    raw_value: str,
    normalized_value: str,
    fragment_id: str,
    context: dict[str, object],
    review_state: str = "accepted",
) -> None:
    context_json = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    database.execute(
        "INSERT INTO fact_versions (fact_version_id,fact_id,entity_id,field_id,raw_value,"
        "normalized_value,disclosure_state,review_state,primary_fragment_id,created_at,"
        "content_sha256,scientific_context_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            version_id,
            fact_id,
            entity_id,
            field_id,
            raw_value,
            normalized_value,
            "reported_value",
            review_state,
            fragment_id,
            NOW.isoformat(),
            _digest(context_json.encode()),
            context_json,
        ),
    )
    database.execute(
        "INSERT INTO fact_evidence (fact_version_id,fragment_id,evidence_role,created_at) "
        "VALUES (?,?,?,?)",
        (version_id, fragment_id, "primary", NOW.isoformat()),
    )


def _project(
    tmp_path: Path,
    *,
    b_binding_override: tuple[str, object] | None = None,
    cross_report_binding: str | None = None,
) -> tuple[Path, dict[str, str]]:
    root = tmp_path / "w04-project"
    root.mkdir(parents=True)
    fixture_root = Path("fixtures")
    payloads = {
        "A": (
            ReportAPortalData,
            render_report_a_site,
            fixture_root / "acceptance/full-matrix-v1/inputs/report-a-data.json",
        ),
        "B": (
            ReportBPortalData,
            render_report_b_site,
            fixture_root / "positive/b-pnh/inputs/report-data.json",
        ),
        "C": (
            ReportCPortalData,
            render_report_c_site,
            fixture_root / "acceptance/full-matrix-v1/inputs/report-c-data.json",
        ),
    }
    report_data = {
        report: model.model_validate_json(path.read_bytes())
        for report, (model, _renderer, path) in payloads.items()
    }
    if cross_report_binding == "legal_AB":
        b_data = report_data["B"]
        b_row = next(row for row in b_data.safety if row.row_id == "safe-apply-t-1")
        b_view = next(
            row for row in b_data.safety_views["facts"]
            if row["row_id"] == b_row.row_id
        )
        a_payload = b_data.model_dump(
            mode="python", include=set(ReportAPortalData.model_fields)
        )
        a_payload["safety"] = [
            {key: value for key, value in row.items() if key in SafetyRow.model_fields}
            for row in a_payload["safety"]
        ]
        a_row = next(row for row in a_payload["safety"] if row["row_id"] == b_row.row_id)
        a_row.update(
            source_version_id=b_view["source_version_id"],
            source_field_path=canonical_source_pointer(b_view["source_locator"]),
            group_id=b_view["arm_id"],
            cohort_id=b_view["analysis_population_zh"],
        )
        report_data["A"] = ReportAPortalData.model_validate(a_payload)
        a_path = root / "report-a-shared-source.json"
        a_path.write_text(report_data["A"].model_dump_json(), encoding="utf-8")
        payloads["A"] = (ReportAPortalData, render_report_a_site, a_path)
    a_row_id = "safe-apply-t-1" if cross_report_binding == "legal_AB" else "safe-fixture-teae"
    a_binding = active_fact_binding_for_a(report_data["A"], "safety", a_row_id)
    b_binding = active_fact_binding_for_b(report_data["B"], "safety", "safe-apply-t-1")
    c_binding = active_fact_binding_for_c(report_data["C"], "c-nct04178967-inclusion")
    if b_binding_override is not None:
        field, replacement = b_binding_override
        b_binding = b_binding.model_copy(update={field: replacement})
    consumer_bindings = [b_binding.model_dump(mode="json")]
    a_consumer_bindings = [a_binding.model_dump(mode="json")]
    if cross_report_binding == "legal_AB":
        consumer_bindings.append(a_binding.model_dump(mode="json"))
        a_consumer_bindings = []
    if cross_report_binding == "B":
        a_consumer_bindings.append(
            a_binding.model_copy(
                update={"report": "B", "row_id": b_binding.row_id}
            ).model_dump(mode="json")
        )
    elif cross_report_binding == "C":
        a_consumer_bindings.append(
            a_binding.model_copy(
                update={
                    "report": "C",
                    "collection": "observations",
                    "row_id": c_binding.row_id,
                    "endpoint_definition": "inclusion_criterion",
                    "event_definition": None,
                }
            ).model_dump(mode="json")
        )
    persist_project_contract(
        root / "state/project.sqlite",
        ProjectContract(
            contract_version=1,
            project_id=PROJECT_ID,
            indication="阵发性睡眠性血红蛋白尿症",
            reports=(ReportKind.A, ReportKind.B, ReportKind.C),
            outputs=(OutputFormat.HTML,),
            timezone="Asia/Shanghai",
            data_cutoff=datetime(2026, 9, 20, tzinfo=UTC),
            cutoff_was_user_supplied=True,
            created_at=NOW,
        ),
    )
    with open_database(root / "state/project.sqlite") as database:
        database.execute(
            "INSERT INTO entities (entity_id,entity_type,canonical_name,created_at) "
            "VALUES ('entity-arm','trial_arm','治疗组',?)",
            (NOW.isoformat(),),
        )
        for source_version_id in {
            "source-v1",
            a_binding.source_version_id,
            b_binding.source_version_id,
            c_binding.source_version_id,
        }:
            database.execute(
                "INSERT INTO source_versions (source_version_id,source_id,content_sha256,"
                "acquired_at,created_at) VALUES (?,?,?,?,?)",
                (
                    source_version_id,
                    f"source-{_digest(source_version_id.encode())[:12]}",
                    _digest(source_version_id.encode()),
                    NOW.isoformat(),
                    NOW.isoformat(),
                ),
            )
        fragments = {
            "count": "fragment-count",
            "a": "fragment-a-safety",
            "adjusted": "fragment-adjusted",
            "lsmean": "fragment-lsmean",
            "threshold": "fragment-threshold",
            "unrelated": "fragment-unrelated",
        }
        quotes = {
            "count": "34/62例受试者发生任何TEAE（54.8%）。",
            "a": "任何TEAE在治疗组中的原始门户值为66.2%。",
            "adjusted": "调整后发生率为23.7%。",
            "lsmean": "最小二乘均值变化为20.0。",
            "threshold": "入选标准阈值为至少16分。",
            "unrelated": "另一研究共有20例受试者。",
        }
        source_by_key = {
            "count": (b_binding.source_version_id, b_binding.source_pointer),
            "a": (a_binding.source_version_id, a_binding.source_pointer),
            "threshold": (c_binding.source_version_id, c_binding.source_pointer),
        }
        for key, fragment_id in fragments.items():
            source_version_id, locator = source_by_key.get(key, ("source-v1", f"$.{key}"))
            database.execute(
                "INSERT INTO evidence_fragments (fragment_id,source_version_id,locator,"
                "content_text,content_sha256,created_at) VALUES (?,?,?,?,?,?)",
                (
                    fragment_id,
                    source_version_id,
                    locator,
                    quotes[key],
                    _digest(quotes[key].encode()),
                    NOW.isoformat(),
                ),
            )
        base = {
            "entity_id": "entity-arm",
            "arm_id": "arm-treatment",
            "cohort_id": "cohort-main",
            "population": "ITT人群",
            "timepoint": "第24周",
            "time_window": None,
            "unit": "%",
            "normalized_unit": "%",
            "endpoint_definition": "发生至少一次目标事件的受试者比例",
            "scale": "percentage",
            "direction": "lower_is_better",
            "estimand": "treatment-policy",
            "analysis_set": "ITT",
            "group": "治疗组",
            "period": "双盲期",
            "measure_object": "participants",
        }
        _seed_fact(
            database,
            fact_id="fact-crude-rate",
            version_id="fact-crude-rate-v1",
            entity_id="entity-arm",
            field_id="safety.crude_rate",
            raw_value="54.8% (34/62)",
            normalized_value="54.8",
            fragment_id=fragments["count"],
            context={
                **b_binding.model_dump(
                    mode="json",
                    exclude={"report", "collection", "row_id", "original_row_sha256"},
                ),
                "numerator": 34,
                "denominator": 62,
                "consumer_bindings": consumer_bindings,
            },
        )
        if cross_report_binding != "legal_AB":
            _seed_fact(
                database,
                fact_id="fact-a-safety",
                version_id="fact-a-safety-v1",
                entity_id="entity-arm",
                field_id="safety.any_teae",
                raw_value="66.2%",
                normalized_value="66.2",
                fragment_id=fragments["a"],
                context={
                    **a_binding.model_dump(
                        mode="json",
                        exclude={"report", "collection", "row_id", "original_row_sha256"},
                    ),
                    "consumer_bindings": a_consumer_bindings,
                },
            )
        _seed_fact(
            database,
            fact_id="fact-adjusted-rate",
            version_id="fact-adjusted-rate-v1",
            entity_id="entity-arm",
            field_id="safety.adjusted_rate",
            raw_value="23.7%",
            normalized_value="23.7",
            fragment_id=fragments["adjusted"],
            context={**base, "statistical_form": "adjusted_rate"},
        )
        _seed_fact(
            database,
            fact_id="fact-lsmean",
            version_id="fact-lsmean-v1",
            entity_id="entity-arm",
            field_id="efficacy.ls_mean",
            raw_value="20.0",
            normalized_value="20.0",
            fragment_id=fragments["lsmean"],
            context={**base, "statistical_form": "ls_mean"},
        )
        _seed_fact(
            database,
            fact_id="fact-c-threshold",
            version_id="fact-c-threshold-v1",
            entity_id="entity-arm",
            field_id="eligibility.score_threshold",
            raw_value=">=16 分",
            normalized_value="16",
            fragment_id=fragments["threshold"],
            context={
                **c_binding.model_dump(
                    mode="json",
                    exclude={"report", "collection", "row_id", "original_row_sha256"},
                ),
                "threshold_operator": ">=",
                "threshold_value": 16.0,
                "threshold_unit": "分",
                "consumer_bindings": [c_binding.model_dump(mode="json")],
            },
        )
        _seed_fact(
            database,
            fact_id="fact-unrelated-20",
            version_id="fact-unrelated-20-v1",
            entity_id="entity-arm",
            field_id="baseline.sample_size",
            raw_value="20",
            normalized_value="20",
            fragment_id=fragments["unrelated"],
            context={**base, "unit": "人", "normalized_unit": "人", "statistical_form": "count"},
        )
    report_sites: dict[str, Path] = {}
    for report, (_model, renderer, _payload_path) in payloads.items():
        site = root / "reports" / report / "v1" / "html"
        data = report_data[report]
        renderer(data, site)
        report_sites[report] = site
    service = UserFactEditService(root)
    service.initialize_current_delivery(
        project_id=PROJECT_ID,
        report_sites=report_sites,
        report_data_paths={
            report: payload[2]
            for report, payload in payloads.items()
        },
        fact_version_ids=(
            "fact-crude-rate-v1",
            *(("fact-a-safety-v1",) if cross_report_binding != "legal_AB" else ()),
            "fact-adjusted-rate-v1",
            "fact-lsmean-v1",
            "fact-c-threshold-v1",
            "fact-unrelated-20-v1",
        ),
        created_at=NOW,
    )
    return root, fragments


def _command(
    *,
    request_id: str = "request-save-rate-1",
    expected_revision: int = 0,
    fact_version_id: str = "fact-crude-rate-v1",
    edits: FactEdit | None = None,
    operation: str = "save",
) -> UserFactSaveCommand:
    return UserFactSaveCommand(
        request_id=request_id,
        project_id=PROJECT_ID,
        expected_revision=expected_revision,
        operation=operation,
        target=FactTargetIdentity(
            fact_id="fact-crude-rate",
            fact_version_id=fact_version_id,
            entity_id="entity-arm",
            field_id="safety.crude_rate",
        ),
        edits=edits or FactEdit(numerator=24, denominator=80),
        user_basis="根据已核对的病例汇总表，将事件人数修正为24例。",
        saved_by="medical-user",
        saved_at=NOW,
    )


def _projection(root: Path, report: str) -> dict[str, object]:
    current = UserFactEditService(root).read_current_delivery()
    entry = next(item for item in current.reports if item.report == report)
    text = (root / entry.site_relative_path / "data/report.js").read_text(encoding="utf-8")
    prefix = f"window.REPORT_{report}="
    assert text.startswith(prefix) and text.endswith(";\n")
    payload = json.loads(text[len(prefix) : -2])
    return payload


def _evidence_view_projection(root: Path, report: str, row_id: str) -> dict[str, object]:
    current = UserFactEditService(root).read_current_delivery()
    delivery = next(item for item in current.reports if item.report == report)
    page = "inclusion-criteria.html" if report == "C" else "safety.html"
    html = (root / delivery.site_relative_path / page).read_text(encoding="utf-8")
    marker = "window.__EVIDENCE_VIEWS__ = "
    payload = html.split(marker, 1)[1].split(";\n", 1)[0]
    views = json.loads(payload)
    return next(item for item in views if item["row"]["row_id"] == row_id)


def test_independent_review_real_portals_consume_revision_without_shadow_files(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path)
    result = UserFactEditService(root).save(_command())
    assert result.revision == 1
    assert result.rebuilt_reports == ("B",)
    current = UserFactEditService(root).read_current_delivery()
    page_by_report = {
        "A": "safety.html",
        "B": "safety.html",
        "C": "inclusion-criteria.html",
    }
    global_by_report = {"A": "REPORT_A", "B": "REPORT_B", "C": "REPORT_C"}
    for report in ("A", "B", "C"):
        delivery = next(item for item in current.reports if item.report == report)
        site = root / delivery.site_relative_path
        assert not tuple((site / "data").glob("w04-*.json"))
        report_js = (site / "data/report.js").read_text(encoding="utf-8")
        assert f"window.{global_by_report[report]}=" in report_js
        assert '"user_fact_revision"' not in report_js
        page = (site / page_by_report[report]).read_text(encoding="utf-8")
        assert "当前事实同步" not in page
        assert "user-fact-revision.js" not in page
        assert not (site / "assets/user-fact-revision.js").exists()
        if report == "B":
            receipt = json.loads((site / "data/consumer-receipt.json").read_text())
            assert receipt["revision"] == 1
            assert receipt["consumers"]
            for consumer in receipt["consumers"]:
                assert consumer["binding_identity"]["original_row_sha256"]
                assert consumer["original_row_sha256"]
                assert all(
                    consumer[key]
                    for key in (
                        "chart_consumer",
                        "table_consumer",
                        "narrative_consumer",
                        "index_consumer",
                        "source_binding_consumer",
                    )
                )
            search = (site / "data/search-index.js").read_text(encoding="utf-8")
            assert "30" in search
        effective = read_effective_delivery(root, report)
        assert isinstance(effective, CurrentReportDelivery)
        assert effective.revision == (1 if report == "B" else 0)
        with pytest.raises(ValueError, match="禁止通过latest.json旁路"):
            read_latest_delivery(root, report)


def test_rereview_original_domain_payload_changes_without_revision_metadata(
    tmp_path: Path,
) -> None:
    """P1-01: removing W04 metadata must still leave native consumer data changed."""
    root, _ = _project(tmp_path)
    baseline: dict[str, dict[str, object]] = {}
    current = UserFactEditService(root).read_current_delivery()
    for report in ("A", "B", "C"):
        delivery = next(item for item in current.reports if item.report == report)
        path = root / delivery.site_relative_path / "data/report.js"
        prefix = f"window.REPORT_{report}="
        baseline[report] = json.loads(path.read_text(encoding="utf-8")[len(prefix) : -2])

    UserFactEditService(root).save(_command())
    current = UserFactEditService(root).read_current_delivery()
    changed_reports: set[str] = set()
    for report in ("A", "B", "C"):
        delivery = next(item for item in current.reports if item.report == report)
        path = root / delivery.site_relative_path / "data/report.js"
        prefix = f"window.REPORT_{report}="
        payload = json.loads(path.read_text(encoding="utf-8")[len(prefix) : -2])
        payload.pop("user_fact_revision", None)
        if payload != baseline[report]:
            changed_reports.add(report)
    assert changed_reports == {"B"}


def test_rereview2_separate_same_origin_facts_rebuild_only_their_reports(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    service.save(
        UserFactSaveCommand(
            request_id="a-only",
            project_id=PROJECT_ID,
            expected_revision=0,
            target=FactTargetIdentity(
                fact_id="fact-a-safety",
                fact_version_id="fact-a-safety-v1",
                entity_id="entity-arm",
                field_id="safety.any_teae",
            ),
            edits=FactEdit(raw_value="67.0%", normalized_value=67.0),
            user_basis="同源A行修订。",
            saved_by="medical-user",
            saved_at=NOW,
        )
    )
    b_result = service.save(
        _command(request_id="b-only", expected_revision=1).model_copy(
            update={"saved_at": NOW + timedelta(minutes=1)}
        )
    )
    assert b_result.rebuilt_reports == ("B",)
    current = service.read_current_delivery()
    assert {item.report: item.revision for item in current.reports} == {
        "A": 1,
        "B": 2,
        "C": 0,
    }
    assert {item.report: item.request_id for item in current.reports} == {
        "A": "a-only",
        "B": "b-only",
        "C": None,
    }


def test_rereview_event_failure_keeps_raw_current_bytes(tmp_path: Path) -> None:
    """P1-02: a failed save cannot be hidden only by the Python reader."""
    root, _ = _project(tmp_path)
    pointer = root / "reports/current.json"
    before = pointer.read_bytes()
    service = UserFactEditService(root)

    def fail_event(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected event append failure")

    service.event_store.append = fail_event  # type: ignore[method-assign]
    with pytest.raises(OSError, match="injected event"):
        service.save(_command(request_id="raw-pointer-event-failure"))
    assert pointer.read_bytes() == before


def test_rereview_partial_event_tail_is_repaired_on_exact_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-02: a half record must be removed without losing valid history."""
    root, _ = _project(tmp_path)
    pointer = root / "reports/current.json"
    before = pointer.read_bytes()
    service = UserFactEditService(root)
    seed = service.event_store.append(
        WorkflowEvent(
            schema_version="1.0",
            event_id="event-before-partial",
            project_id=PROJECT_ID,
            run_id="test",
            event_type="test.before.partial",
            occurred_at=NOW,
            actor_id="test",
            idempotency_key="test.before.partial",
            payload={"preserve": True},
        )
    )
    failed = False

    def half_then_fail(self: EventStore, payload: bytes) -> None:
        nonlocal failed
        if not failed:
            failed = True
            path = self.path
            with path.open("ab") as stream:
                stream.write(payload[len(path.read_bytes()) :][:37])
                stream.flush()
                event_store_module.os.fsync(stream.fileno())
            raise OSError("injected partial event write")
        raise AssertionError("fault should be injected once")

    monkeypatch.setattr(event_store_module.EventStore, "_replace_stream", half_then_fail)
    command = _command(request_id="partial-event-retry")
    with pytest.raises(EventStoreError, match="无法追加"):
        service.save(command)
    assert pointer.read_bytes() == before
    monkeypatch.undo()
    result = UserFactEditService(root).save(command)
    assert result.revision == 1
    events = UserFactEditService(root).event_store.read_all()
    assert events[0] == seed
    assert [event.event_id for event in events].count(
        stable_id("user-fact-save", PROJECT_ID, command.request_id)
    ) == 1


def test_rereview_v4_manifest_declares_recomputable_dirty_digest() -> None:
    """P2-01: evidence must define, not merely state, the dirty digest."""
    manifest_path = Path(
        "packets/2026-09-22-sol-delivery/evidence/"
        "W04-remediation-real-portal-v4/evidence-manifest.json"
    )
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    spec = manifest["dirty_source_digest_spec"]
    assert spec["algorithm"] == "sha256"
    assert spec["encoding"] == "utf-8"
    assert spec["ordering"] == "unicode-codepoint-path-order"
    assert spec["record_format"] == "path + NUL + sha256(raw bytes) + LF"
    assert spec["inputs"]


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("product_id", "fixture-control"),
        ("drug_name", "错误药物"),
        ("trial_id", "nct-fixture-302"),
        ("registry_id", "NCT00000000"),
        ("group_id", "wrong-group"),
        ("arm", "对照组"),
        ("cohort_id", "wrong-cohort"),
        ("period", "错误周期"),
        ("event_definition", "严重不良事件"),
        ("statistical_form", "count"),
        ("unit", "例"),
        ("normalized_unit", "例"),
        ("source_version_id", "wrong-source-version"),
        ("source_pointer", "wrong/source/pointer"),
        ("original_row_sha256", "0" * 64),
    ),
)
def test_rereview2_same_row_id_scientific_identity_drift_fails_closed(
    tmp_path: Path,
    field: str,
    replacement: object,
) -> None:
    """P1-01: row_id alone cannot authorize a scientifically different row."""
    root, _ = _project(tmp_path, b_binding_override=(field, replacement))
    service = UserFactEditService(root)
    current = service.read_current_delivery()
    pointer = root / "reports/current.json"
    before_pointer = pointer.read_bytes()
    before_sites = {
        item.report: {
            relative: _digest((root / item.site_relative_path / relative).read_bytes())
            for relative in item.file_hashes
        }
        for item in current.reports
    }
    with pytest.raises(UserFactSaveError, match="科学身份|原行摘要"):
        service.save(_command(request_id=f"binding-drift-{field}"))
    assert pointer.read_bytes() == before_pointer
    for report in current.reports:
        for relative, digest in before_sites[report.report].items():
            assert _digest((root / report.site_relative_path / relative).read_bytes()) == digest


def test_rereview2_stale_row_id_fails_before_staging(tmp_path: Path) -> None:
    root, _ = _project(tmp_path, b_binding_override=("row_id", "stale-row-id"))
    with pytest.raises(UserFactSaveError, match="唯一领域行"):
        UserFactEditService(root).save(_command(request_id="stale-row-binding"))
    assert not any(root.glob("reports/*/v1-user-r1"))


@pytest.mark.parametrize("wrong_report", ("B", "C"))
def test_rereview2_cross_report_fact_binding_fails_closed(
    tmp_path: Path, wrong_report: str
) -> None:
    """P1-01: one A identity cannot be reused as authorization for B/C rows."""
    root, _ = _project(tmp_path, cross_report_binding=wrong_report)
    pointer = root / "reports/current.json"
    before = pointer.read_bytes()
    with pytest.raises(UserFactSaveError, match="科学身份"):
        UserFactEditService(root).save(
            UserFactSaveCommand(
                request_id=f"cross-report-binding-{wrong_report.lower()}",
                project_id=PROJECT_ID,
                expected_revision=0,
                target=FactTargetIdentity(
                    fact_id="fact-a-safety",
                    fact_version_id="fact-a-safety-v1",
                    entity_id="entity-arm",
                    field_id="safety.any_teae",
                ),
                edits=FactEdit(normalized_value=67.0, raw_value="67.0%"),
                user_basis="同一A事实不得借row_id绑定其他报告。",
                saved_by="medical-user",
                saved_at=NOW,
            )
        )
    assert pointer.read_bytes() == before
    assert not any(root.glob("reports/*/v1-user-r1"))


def test_same_source_fact_legally_rebuilds_a_and_b_without_touching_c(tmp_path: Path) -> None:
    root, fragments = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    old_c = next(item for item in before.reports if item.report == "C")
    result = service.save(
        _command(
            request_id="shared-a-b-rate",
            edits=FactEdit(numerator=24, denominator=62),
        )
    )
    assert result.rebuilt_reports == ("A", "B")
    assert result.derived_crude_rate == round(24 / 62 * 100, 10)
    current = service.read_current_delivery()
    assert next(item for item in current.reports if item.report == "C") == old_c
    for report, row_id in (("A", "safe-apply-t-1"), ("B", "safe-apply-t-1")):
        projection = _projection(root, report)
        row = next(item for item in projection["safety"] if item["row_id"] == row_id)
        assert row["value"] == result.derived_crude_rate
        assert (row["numerator"], row["denominator"]) == (24, 62)
        edit = projection["user_edits"][row_id]
        assert edit["original_value"].startswith("54.8%")
        assert edit["review_state"] == "user_modified"
        delivery = next(item for item in current.reports if item.report == report)
        assert delivery.revision == 1
        site = root / delivery.site_relative_path
        receipt = json.loads((site / "data/consumer-receipt.json").read_text())
        assert any(
            item["fact_id"] == "fact-crude-rate" and item["row_id"] == row_id
            and item["binding_identity"]["source_version_id"]
            == "nct04558918-safety-report-v1"
            for item in receipt["consumers"]
        )
        assert str(result.derived_crude_rate) in (
            site / "data/search-index.js"
        ).read_text(encoding="utf-8")
        assert (site / "safety.html").is_file()
    with open_database(root / "state/project.sqlite") as database:
        source = database.execute(
            "SELECT content_text FROM evidence_fragments WHERE fragment_id=?",
            (fragments["count"],),
        ).fetchone()
    assert source is not None and source[0] == "34/62例受试者发生任何TEAE（54.8%）。"


def test_shared_a_b_failure_never_publishes_half_updated_current(tmp_path: Path) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    pointer = root / "reports/current.json"
    old_pointer = pointer.read_bytes()
    command = _command(
        request_id="shared-a-b-retry",
        edits=FactEdit(numerator=24, denominator=62),
    )

    def interrupt(report: str) -> None:
        if report == "A":
            raise OSError("injected failure after first affected report")

    service._after_report_built = interrupt
    with pytest.raises(OSError, match="first affected report"):
        service.save(command)
    assert pointer.read_bytes() == old_pointer
    assert service.read_current_delivery() == before

    service._after_report_built = lambda _report: None
    retry = service.save(command)
    assert retry.rebuilt_reports == ("A", "B")
    assert service.read_current_delivery().revision == 1


def test_rereview2_current_protocol_uses_immutable_generation_selector(
    tmp_path: Path,
) -> None:
    """P1-02: current.json is a stable protocol descriptor, not a mutable revision pointer."""
    root, _ = _project(tmp_path)
    raw = json.loads((root / "reports/current.json").read_text(encoding="utf-8"))
    assert raw == {
        "schema_version": "2.0",
        "protocol": "sqlite-committed-generation",
        "database_relative_path": "state/project.sqlite",
        "selector_table": "current_delivery_state",
        "generations_relative_path": "reports/generations",
    }


def test_rereview2_post_fsync_and_rollback_double_fault_never_exposes_new_raw_current(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-02: no rollback replace is needed after publishing an immutable generation."""
    root, _ = _project(tmp_path)
    pointer = root / "reports/current.json"
    before = pointer.read_bytes()
    original_replace = latest_delivery_module.os.replace
    generation_replaced = False

    def replace_then_rollback_failure(source: str | Path, destination: str | Path) -> None:
        nonlocal generation_replaced
        target = Path(destination)
        if target.parent.name == "generations" and not generation_replaced:
            generation_replaced = True
            original_replace(source, destination)
            return
        if generation_replaced and "rollback" in Path(source).name:
            raise OSError("injected rollback replace failure")
        original_replace(source, destination)

    def fail_generation_directory_fsync(path: Path) -> None:
        if path.name == "generations":
            raise OSError("injected generation directory fsync failure")
        descriptor = latest_delivery_module.os.open(path, latest_delivery_module.os.O_RDONLY)
        try:
            latest_delivery_module.os.fsync(descriptor)
        finally:
            latest_delivery_module.os.close(descriptor)

    monkeypatch.setattr(latest_delivery_module.os, "replace", replace_then_rollback_failure)
    monkeypatch.setattr(latest_delivery_module, "_fsync_directory", fail_generation_directory_fsync)
    with pytest.raises(OSError, match="generation directory fsync"):
        UserFactEditService(root).save(_command(request_id="generation-double-fault"))
    assert pointer.read_bytes() == before
    assert UserFactEditService(root).read_current_delivery().revision == 0


def test_independent_review_publish_rejects_invalid_bundle_before_pointer_write(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    current = service.read_current_delivery()
    pointer = root / "reports/current.json"
    before = pointer.read_bytes()
    invalid = current.model_copy(
        update={
            "revision": 1,
            "request_id": "invalid-mixed",
            "reports": tuple(item.model_copy(update={"revision": 0}) for item in current.reports),
        }
    )
    with pytest.raises(ValueError, match="跨revision"):
        publish_current_delivery(root, invalid, expected_revision=0)
    assert pointer.read_bytes() == before


def test_independent_review_post_pointer_failure_is_not_visible_and_retry_recovers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)

    def fail_event(*_args: object, **_kwargs: object) -> None:
        raise OSError("injected event append failure")

    monkeypatch.setattr(service.event_store, "append", fail_event)
    with pytest.raises(OSError, match="injected event"):
        service.save(_command())
    assert UserFactEditService(root).read_current_delivery().revision == 0
    recovered = UserFactEditService(root).save(_command())
    assert recovered.revision == 1
    assert UserFactEditService(root).read_current_delivery().revision == 1


@pytest.mark.parametrize("failure", ("replace", "database", "event", "journal_commit"))
def test_independent_review_transaction_faults_keep_old_current_and_exact_retry_recovers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    pointer = root / "reports/current.json"
    before_bytes = pointer.read_bytes()
    if failure == "replace":
        original_replace = latest_delivery_module.os.replace
        failed = False

        def fail_current_replace(source: str | Path, destination: str | Path) -> None:
            nonlocal failed
            if not failed and Path(destination).parent.name == "generations":
                failed = True
                raise OSError("injected generation replace failure")
            original_replace(source, destination)

        monkeypatch.setattr(latest_delivery_module.os, "replace", fail_current_replace)
    elif failure == "database":
        original_complete = service._complete_request
        failed = False

        def fail_database(request_id: str, result: UserFactSaveResult) -> None:
            nonlocal failed
            if not failed:
                failed = True
                raise sqlite3.OperationalError("injected request completion failure")
            original_complete(request_id, result)

        monkeypatch.setattr(service, "_complete_request", fail_database)
    elif failure == "event":
        failed = False
        original_append = service.event_store.append

        def fail_event_once(event: WorkflowEvent) -> None:
            nonlocal failed
            if not failed:
                failed = True
                raise OSError("injected event failure")
            original_append(event)

        monkeypatch.setattr(service.event_store, "append", fail_event_once)
    else:
        failed = False
        original_commit = user_fact_edit_module.commit_current_transaction

        def fail_commit_once(
            project_root: Path,
            *,
            request_id: str,
            candidate: CurrentDeliveryBundle,
        ) -> CurrentDeliveryJournal:
            nonlocal failed
            if not failed:
                failed = True
                raise OSError("injected journal commit failure")
            return original_commit(
                project_root,
                request_id=request_id,
                candidate=candidate,
            )

        monkeypatch.setattr(user_fact_edit_module, "commit_current_transaction", fail_commit_once)

    with pytest.raises((OSError, sqlite3.OperationalError), match="injected"):
        service.save(_command(request_id=f"fault-{failure}"))
    assert pointer.read_bytes() == before_bytes
    assert UserFactEditService(root).read_current_delivery() == before
    monkeypatch.undo()
    recovered = UserFactEditService(root).save(_command(request_id=f"fault-{failure}"))
    assert recovered.revision == 1
    assert UserFactEditService(root).read_current_delivery().revision == 1


def test_independent_review_generation_directory_fsync_keeps_selector_and_raw_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _ = _project(tmp_path)

    pointer = root / "reports/current.json"
    before = pointer.read_bytes()

    def fail_directory_fsync(path: Path) -> None:
        if path == root / "reports/generations":
            raise OSError("injected generation directory fsync failure after replace")
        descriptor = latest_delivery_module.os.open(path, latest_delivery_module.os.O_RDONLY)
        try:
            latest_delivery_module.os.fsync(descriptor)
        finally:
            latest_delivery_module.os.close(descriptor)

    monkeypatch.setattr(latest_delivery_module, "_fsync_directory", fail_directory_fsync)
    command = _command(request_id="fault-directory-fsync")
    with pytest.raises(OSError, match="directory fsync"):
        UserFactEditService(root).save(command)
    assert pointer.read_bytes() == before
    monkeypatch.undo()
    assert UserFactEditService(root).save(command).revision == 1


def test_independent_review_generation_file_fsync_failure_keeps_old_and_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _ = _project(tmp_path)
    before = UserFactEditService(root).read_current_delivery()
    original_atomic_write = latest_delivery_module._atomic_write

    def fail_generation_file_fsync(path: Path, payload: bytes, *, prefix: str) -> None:
        if path.parent.name != "generations":
            original_atomic_write(path, payload, prefix=prefix)
            return

        def unavailable(_descriptor: int) -> None:
            raise OSError("injected generation file fsync failure")

        with monkeypatch.context() as patch:
            patch.setattr(latest_delivery_module.os, "fsync", unavailable)
            original_atomic_write(path, payload, prefix=prefix)

    monkeypatch.setattr(latest_delivery_module, "_atomic_write", fail_generation_file_fsync)
    command = _command(request_id="fault-current-file-fsync")
    with pytest.raises(OSError, match="generation file fsync"):
        UserFactEditService(root).save(command)
    assert UserFactEditService(root).read_current_delivery() == before
    monkeypatch.undo()
    assert UserFactEditService(root).save(command).revision == 1


def test_independent_review_complete_refresh_union_and_refresh_service_persistence(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    saved = service.save(
        _command(edits=FactEdit(numerator=24, denominator=80, timepoint="第28周"))
    )
    comparison = RefreshService(root).compare_user_fact_refresh(
        fact_id="fact-crude-rate",
        base_fact_version_id="fact-crude-rate-v1",
        user_fact_version_id=saved.fact_version_id,
        source_version_id="source-v2",
        source_fields={"numerator": 22},
        source_withdrawn=False,
        request_id="refresh-three-way-1",
        compared_at=NOW,
        actor_id="refresh-worker",
    )
    assert comparison.field_comparisons["numerator"].state is RefreshFieldState.CONFLICT
    assert comparison.field_comparisons["numerator"].base_value == 34
    assert comparison.field_comparisons["numerator"].user_value == 24
    assert comparison.field_comparisons["numerator"].source_value == 22
    assert comparison.field_comparisons["timepoint"].state is RefreshFieldState.USER_MODIFIED
    assert comparison.field_comparisons["timepoint"].source_inherited_from_base is True
    assert comparison.user_lineage == (saved.fact_version_id, "fact-crude-rate-v1")
    with open_database(root / "state/project.sqlite") as database:
        row = database.execute(
            "SELECT comparison_json,source_version_id FROM user_refresh_conflicts "
            "WHERE conflict_id=?",
            (comparison.conflict_id,),
        ).fetchone()
    assert row is not None and row[1] == "source-v2"
    assert json.loads(str(row[0]))["field_comparisons"]["timepoint"]["state"] == "user_modified"

    converged = RefreshService(root).compare_user_fact_refresh(
        fact_id="fact-crude-rate",
        base_fact_version_id="fact-crude-rate-v1",
        user_fact_version_id=saved.fact_version_id,
        source_version_id="source-v3",
        source_fields={"numerator": 24, "timepoint": "第28周"},
        source_withdrawn=False,
        request_id="refresh-three-way-converged",
        compared_at=NOW,
        actor_id="refresh-worker",
    )
    assert converged.field_states["numerator"] is RefreshFieldState.CONVERGED
    assert converged.field_states["timepoint"] is RefreshFieldState.CONVERGED
    withdrawn = RefreshService(root).compare_user_fact_refresh(
        fact_id="fact-crude-rate",
        base_fact_version_id="fact-crude-rate-v1",
        user_fact_version_id=saved.fact_version_id,
        source_version_id="source-v4",
        source_fields={},
        source_withdrawn=True,
        request_id="refresh-three-way-withdrawn",
        compared_at=NOW,
        actor_id="refresh-worker",
    )
    assert withdrawn.requires_explicit_resolution
    assert set(withdrawn.field_states.values()) == {RefreshFieldState.SOURCE_WITHDRAWN}


def test_independent_review_numeric_scope_and_import_alias_removed(tmp_path: Path) -> None:
    FactEdit(
        numerator=120,
        denominator=80,
        statistical_form="count",
        measure_object="events",
    )
    FactEdit(
        numerator=120,
        denominator=80,
        statistical_form="count",
        measure_object="person_time",
    )
    FactEdit(normalized_value=23.7, statistical_form="adjusted_rate", measure_object="estimate")
    FactEdit(normalized_value=20.0, statistical_form="ls_mean", measure_object="estimate")
    with pytest.raises(ValueError, match="人数粗率"):
        FactEdit(
            numerator=120,
            denominator=80,
            statistical_form="crude_rate",
            measure_object="participants",
        )

    root, _ = _project(tmp_path)
    server = LoopbackEditServer(UserFactEditService(root)).start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.port)
        connection.request("GET", "/", headers={"Host": f"127.0.0.1:{server.port}"})
        response = connection.getresponse()
        response.read()
        cookie = response.getheader("Set-Cookie", "").split(";", 1)[0]
        csrf = response.getheader("X-CSRF-Token", "")
        payload = _command().model_dump_json().encode()
        connection.request(
            "POST",
            "/api/import",
            body=payload,
            headers={
                "Host": f"127.0.0.1:{server.port}",
                "Origin": f"http://127.0.0.1:{server.port}",
                "Cookie": cookie,
                "X-CSRF-Token": csrf,
                "Content-Type": "application/json",
                "Content-Length": str(len(payload)),
            },
        )
        response = connection.getresponse()
        response.read()
        assert response.status == 404
    finally:
        server.close()


def test_save_is_typed_versioned_and_rebuilds_only_actual_consumers(tmp_path: Path) -> None:
    root, fragments = _project(tmp_path)
    service = UserFactEditService(root)
    source_before = {
        key: (root / "state/project.sqlite").read_bytes() if False else value
        for key, value in fragments.items()
    }
    with open_database(root / "state/project.sqlite") as database:
        quote_before = database.execute(
            "SELECT content_text,content_sha256 FROM evidence_fragments WHERE fragment_id=?",
            (fragments["count"],),
        ).fetchone()

    result = service.save(_command())

    assert result.revision == 1
    assert result.review_state == "user_modified"
    assert result.derived_crude_rate == 30.0
    assert result.independent_scientific_acceptance == "not_inherited"
    current = service.read_current_delivery()
    assert current.revision == 1
    assert {item.report for item in current.reports} == {"A", "B", "C"}
    assert {item.report: item.revision for item in current.reports} == {
        "A": 0,
        "B": 1,
        "C": 0,
    }
    assert result.rebuilt_reports == ("B",)
    assert all(item.file_hashes for item in current.reports)
    for report in ("A", "B", "C"):
        payload = _projection(root, report)
        assert "user_fact_revision" not in payload
        if report == "B":
            row = next(
                item for item in payload["safety"] if item["row_id"] == "safe-apply-t-1"
            )
            assert row["numerator"] == 24
            assert row["denominator"] == 80
            assert float(row["value"]) == 30.0
        elif report == "A":
            row = next(
                item for item in payload["safety"] if item["row_id"] == "safe-fixture-teae"
            )
            assert row["value"] == 66.2
        else:
            row = next(
                item for item in payload["observations"]
                if item["row_id"] == "c-nct04178967-inclusion"
            )
            assert row["threshold_value"] == "16"
        assert (
            root
            / next(i.site_relative_path for i in current.reports if i.report == report)
            / "data/report.js"
        ).is_file()

    with open_database(root / "state/project.sqlite") as database:
        rows = database.execute(
            "SELECT fact_version_id,review_state,supersedes_fact_version_id,primary_fragment_id "
            "FROM fact_versions WHERE fact_id='fact-crude-rate' ORDER BY created_at"
        ).fetchall()
        adjusted = database.execute(
            "SELECT normalized_value FROM fact_versions WHERE fact_id='fact-adjusted-rate'"
        ).fetchall()
        lsmean = database.execute(
            "SELECT normalized_value FROM fact_versions WHERE fact_id='fact-lsmean'"
        ).fetchall()
        unrelated = database.execute(
            "SELECT normalized_value FROM fact_versions WHERE fact_id='fact-unrelated-20'"
        ).fetchall()
        quote_after = database.execute(
            "SELECT content_text,content_sha256 FROM evidence_fragments WHERE fragment_id=?",
            (fragments["count"],),
        ).fetchone()
    assert rows[0][1:] == ("accepted", None, fragments["count"])
    assert rows[1][1:] == ("user_modified", "fact-crude-rate-v1", fragments["count"])
    assert adjusted == [("23.7",)]
    assert lsmean == [("20.0",)]
    assert unrelated == [("20",)]
    assert quote_after == quote_before
    assert source_before == fragments


def test_idempotency_stale_tabs_concurrency_and_payload_drift(tmp_path: Path) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    first = service.save(_command())
    assert service.save(_command()) == first
    with pytest.raises(UserFactSaveConflictError, match="同一请求"):
        service.save(_command(edits=FactEdit(numerator=25, denominator=80)))
    with pytest.raises(UserFactSaveConflictError, match="版本冲突"):
        service.save(_command(request_id="stale-tab", expected_revision=0))

    root2, _ = _project(tmp_path / "parallel")
    barrier = threading.Barrier(3)
    outcomes: list[str] = []

    def worker(request_id: str, numerator: int) -> None:
        barrier.wait()
        try:
            UserFactEditService(root2).save(
                _command(request_id=request_id, edits=FactEdit(numerator=numerator, denominator=80))
            )
            outcomes.append("saved")
        except UserFactSaveConflictError:
            outcomes.append("conflict")

    threads = [
        threading.Thread(target=worker, args=("tab-a", 24)),
        threading.Thread(target=worker, args=("tab-b", 25)),
    ]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["conflict", "saved"]
    assert UserFactEditService(root2).read_current_delivery().revision == 1


def test_c_threshold_semantics_undo_and_refresh_three_way_conflict(tmp_path: Path) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    saved = service.save(
        UserFactSaveCommand(
            request_id="threshold-save",
            project_id=PROJECT_ID,
            expected_revision=0,
            operation="save",
            target=FactTargetIdentity(
                fact_id="fact-c-threshold",
                fact_version_id="fact-c-threshold-v1",
                entity_id="entity-arm",
                field_id="eligibility.score_threshold",
            ),
            edits=FactEdit(
                threshold_operator="<=",
                threshold_value=18.0,
                threshold_unit="分",
            ),
            user_basis="方案修订版将同一入组量表阈值由16分修正为18分。",
            saved_by="medical-user",
            saved_at=NOW,
        )
    )
    assert saved.revision == 1
    projected = next(
        item
        for item in _projection(root, "C")["observations"]
        if item["row_id"] == "c-nct04178967-inclusion"
    )
    assert projected["threshold_value"] == "18.0"
    comparison = service.compare_refresh(
        fact_id="fact-c-threshold",
        base_fact_version_id="fact-c-threshold-v1",
        user_fact_version_id=saved.fact_version_id,
        source_fields={"threshold_value": 17.0, "threshold_operator": ">"},
        request_id="refresh-compare-1",
        compared_at=NOW,
    )
    assert comparison.field_states["threshold_value"] is RefreshFieldState.CONFLICT
    assert comparison.field_states["threshold_operator"] is RefreshFieldState.CONFLICT
    assert comparison.requires_explicit_resolution

    undone = service.save(
        _command(
            request_id="undo-threshold",
            expected_revision=1,
            fact_version_id=saved.fact_version_id,
            operation="undo",
            edits=FactEdit(),
        ).model_copy(
            update={
                "target": FactTargetIdentity(
                    fact_id="fact-c-threshold",
                    fact_version_id=saved.fact_version_id,
                    entity_id="entity-arm",
                    field_id="eligibility.score_threshold",
                ),
                "user_basis": "撤销上一版阈值修订，追加恢复到原始事实的新版本。",
            }
        )
    )
    assert undone.revision == 2
    assert undone.review_state == "user_modified"
    assert undone.fact_version_id != "fact-c-threshold-v1"
    projected = next(
        item
        for item in _projection(root, "C")["observations"]
        if item["row_id"] == "c-nct04178967-inclusion"
    )
    assert projected["threshold_value"] == "16.0"
    current = service.read_current_delivery()
    for delivery in current.reports:
        site = root / delivery.site_relative_path
        for page in site.glob("*.html"):
            html = page.read_text(encoding="utf-8")
            assert "当前事实同步" not in html
            assert "user-fact-revision.js" not in html
        if delivery.report == "C":
            assert delivery.revision == 2
            assert (site / "data/consumer-receipt.json").is_file()
        else:
            assert delivery.revision == 0


def test_rereview3_user_values_never_replace_original_source_layers(
    tmp_path: Path,
) -> None:
    """P1-01: user display values and immutable source evidence are separate layers."""
    root, _ = _project(tmp_path)
    baseline = {report: _projection(root, report) for report in ("A", "B", "C")}
    baseline_views = {
        "B": _evidence_view_projection(root, "B", "safe-apply-t-1"),
        "C": _evidence_view_projection(root, "C", "c-nct04178967-inclusion"),
    }
    service = UserFactEditService(root)
    a_saved = service.save(
        UserFactSaveCommand(
            request_id="rereview3-a",
            project_id=PROJECT_ID,
            expected_revision=0,
            target=FactTargetIdentity(
                fact_id="fact-a-safety",
                fact_version_id="fact-a-safety-v1",
                entity_id="entity-arm",
                field_id="safety.any_teae",
            ),
            edits=FactEdit(raw_value="67.0%", normalized_value=67.0),
            user_basis="同源A行用户修订。",
            saved_by="medical-user",
            saved_at=NOW,
        )
    )
    b_saved = service.save(
        _command(request_id="rereview3-b", expected_revision=1).model_copy(
            update={"saved_at": NOW + timedelta(minutes=1)}
        )
    )
    service.save(
        UserFactSaveCommand(
            request_id="rereview3-c",
            project_id=PROJECT_ID,
            expected_revision=2,
            target=FactTargetIdentity(
                fact_id="fact-c-threshold",
                fact_version_id="fact-c-threshold-v1",
                entity_id="entity-arm",
                field_id="eligibility.score_threshold",
            ),
            edits=FactEdit(
                threshold_operator="<=",
                threshold_value=18.0,
                threshold_unit="分",
            ),
            user_basis="同源C行用户修订。",
            saved_by="medical-user",
            saved_at=NOW + timedelta(minutes=2),
        )
    )

    expected = {
        "A": ("safe-fixture-teae", "67.0%", "66.2%"),
        "B": ("safe-apply-t-1", "30% (24/80)", "54.8% (34/62)"),
        "C": ("c-nct04178967-inclusion", "<=18 分", "≥16 分"),
    }
    for report, (row_id, current_value, original_value) in expected.items():
        payload = _projection(root, report)
        edits = payload["user_edits"]
        assert edits[row_id]["review_state"] == "user_modified"
        assert edits[row_id]["status_label_zh"] == "用户修订，未独立复核"
        assert edits[row_id]["current_value"] == current_value
        assert edits[row_id]["original_value"] == original_value
        assert edits[row_id]["primary_fragment_id"].startswith("fragment-")

    a_before = next(
        row for row in baseline["A"]["safety"] if row["row_id"] == "safe-fixture-teae"
    )
    a_after = next(
        row for row in _projection(root, "A")["safety"] if row["row_id"] == "safe-fixture-teae"
    )
    assert a_after["value"] == 67.0
    assert a_after["source_text"] == a_before["source_text"]
    assert a_after["source_field_path"] == a_before["source_field_path"]

    b_domain_before = next(
        row for row in baseline["B"]["safety"] if row["row_id"] == "safe-apply-t-1"
    )
    b_domain_after = next(
        row for row in _projection(root, "B")["safety"] if row["row_id"] == "safe-apply-t-1"
    )
    assert (
        b_domain_after["value"],
        b_domain_after["numerator"],
        b_domain_after["denominator"],
    ) == (
        30.0,
        24,
        80,
    )
    assert b_domain_after["source_text"] == b_domain_before["source_text"]
    assert b_domain_after["source_field_path"] == b_domain_before["source_field_path"]
    b_view_after = _evidence_view_projection(root, "B", "safe-apply-t-1")
    for field in ("original_text", "locator", "source_version_id"):
        assert b_view_after[field] == baseline_views["B"][field]

    c_before = next(
        row
        for row in baseline["C"]["observations"]
        if row["row_id"] == "c-nct04178967-inclusion"
    )
    c_after = next(
        row
        for row in _projection(root, "C")["observations"]
        if row["row_id"] == "c-nct04178967-inclusion"
    )
    assert (c_after["operator"], c_after["threshold_value"]) == ("<=", "18.0")
    for field in (
        "source_text",
        "source_locator",
        "source_version_id",
        "source_row_id",
    ):
        assert c_after[field] == c_before[field]
    c_view_after = _evidence_view_projection(root, "C", "c-nct04178967-inclusion")
    for field in ("original_text", "locator", "source_version_id"):
        assert c_view_after[field] == baseline_views["C"][field]

    current = service.read_current_delivery()
    for report in ("A", "B", "C"):
        delivery = next(item for item in current.reports if item.report == report)
        site = root / delivery.site_relative_path
        page = "inclusion-criteria.html" if report == "C" else "safety.html"
        html = (site / page).read_text(encoding="utf-8")
        assert "用户修订，未独立复核" in html
        assert expected[report][1] in html
        assert expected[report][2] in html
        if report == "B":
            assert '"_user_edit":' in html
    assert a_saved.rebuilt_reports == ("A",)
    assert b_saved.rebuilt_reports == ("B",)


def test_rereview3_v6_verifier_binds_every_builder_input_byte(
    tmp_path: Path,
) -> None:
    """P2-01: target, non-target and arbitrary builder-input drift all fail closed."""
    from tools.verify_w04_v6_evidence import verify_builder_inputs

    root, _ = _project(tmp_path)
    current = UserFactEditService(root).read_current_delivery().model_dump(mode="json")
    artifacts = []
    originals: dict[str, bytes] = {}
    for delivery in current["reports"]:
        relative = str(delivery["builder_input_relative_path"])
        data = (root / relative).read_bytes()
        originals[relative] = data
        artifacts.append({"path": relative, "sha256": _digest(data), "size": len(data)})
    assert verify_builder_inputs(root, current["reports"], artifacts) == []

    a_relative = next(
        str(item["builder_input_relative_path"])
        for item in current["reports"]
        if item["report"] == "A"
    )
    parsed = json.loads(originals[a_relative])
    target = next(row for row in parsed["safety"] if row["row_id"] == "safe-fixture-teae")
    target["value"] = 999
    target_tamper = json.dumps(parsed, ensure_ascii=False).encode()
    target_errors = verify_builder_inputs(
        root,
        current["reports"],
        artifacts,
        byte_overrides={a_relative: target_tamper},
    )
    assert any("builder input" in error for error in target_errors)

    parsed = json.loads(originals[a_relative])
    parsed["indication"] = "TAMPERED-NON-TARGET"
    non_target_errors = verify_builder_inputs(
        root,
        current["reports"],
        artifacts,
        byte_overrides={
            a_relative: json.dumps(parsed, ensure_ascii=False).encode(),
        },
    )
    assert any("builder input" in error for error in non_target_errors)
    arbitrary_errors = verify_builder_inputs(
        root,
        current["reports"],
        artifacts,
        byte_overrides={a_relative: originals[a_relative] + b"\n"},
    )
    assert any("builder input" in error for error in arbitrary_errors)


def test_impact_graph_rejects_cycle_dangling_and_cross_revision() -> None:
    fact = ImpactNode(layer=ImpactLayer.FACT, object_id="fact-1", revision=2)
    d1 = ImpactNode(layer=ImpactLayer.DERIVATION, object_id="derived-1", revision=2)
    d2 = ImpactNode(layer=ImpactLayer.DERIVATION, object_id="derived-2", revision=2)
    with pytest.raises(ImpactGraphError, match="环"):
        ImpactGraph(
            nodes=(fact, d1, d2),
            edges=(
                ImpactEdge(upstream=fact, downstream=d1),
                ImpactEdge(upstream=d1, downstream=d2),
                ImpactEdge(upstream=d2, downstream=d1),
            ),
        )
    with pytest.raises(ImpactGraphError, match="未登记"):
        ImpactGraph(nodes=(fact,), edges=(ImpactEdge(upstream=fact, downstream=d1),))
    with pytest.raises(ImpactGraphError, match="跨revision"):
        ImpactEdge(
            upstream=fact,
            downstream=ImpactNode(layer=ImpactLayer.DERIVATION, object_id="derived-r3", revision=3),
        )


def test_interruption_keeps_old_current_and_exact_retry_finishes(tmp_path: Path) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    before = service.read_current_delivery()

    def interrupt(report: str) -> None:
        if report == "B":
            raise RuntimeError("synthetic rebuild interruption")

    service._after_report_built = interrupt
    with pytest.raises(RuntimeError, match="interruption"):
        service.save(_command())
    assert UserFactEditService(root).read_current_delivery() == before

    recovered = UserFactEditService(root).save(_command())
    assert recovered.revision == 1
    assert UserFactEditService(root).read_current_delivery().revision == 1


def _request_http(
    server: LoopbackEditServer,
    method: str,
    path: str,
    *,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    payload = response.read()
    result_headers = {key.lower(): value for key, value in response.getheaders()}
    connection.close()
    return response.status, result_headers, payload


def test_loopback_editor_rejects_malicious_host_origin_csrf_session_and_import(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path)
    with LoopbackEditServer(UserFactEditService(root)) as server:
        good_host = f"127.0.0.1:{server.port}"
        status, headers, page = _request_http(server, "GET", "/", headers={"Host": good_host})
        assert status == 200
        cookie = headers["set-cookie"].split(";", 1)[0]
        csrf = headers["x-csrf-token"]
        assert b"fact-crude-rate" in page and b"fact-c-threshold" in page
        # The wire contract sends only explicit edit fields. Full model dumps
        # materialize default nulls and now correctly mean clear requests.
        encoded = _command().model_dump_json(exclude_unset=True).encode()

        attacks = (
            ({"Host": "evil.example"}, "/api/save", encoded),
            (
                {
                    "Host": good_host,
                    "Origin": "null",
                    "Cookie": cookie,
                    "X-CSRF-Token": csrf,
                    "Content-Type": "application/json",
                },
                "/api/save",
                encoded,
            ),
            (
                {
                    "Host": good_host,
                    "Origin": f"http://{good_host}",
                    "Cookie": "session=bad",
                    "X-CSRF-Token": csrf,
                    "Content-Type": "application/json",
                },
                "/api/save",
                encoded,
            ),
            (
                {
                    "Host": good_host,
                    "Origin": f"http://{good_host}",
                    "Cookie": cookie,
                    "X-CSRF-Token": "bad",
                    "Content-Type": "application/json",
                },
                "/api/save",
                encoded,
            ),
            (
                {
                    "Host": good_host,
                    "Origin": f"http://{good_host}",
                    "Cookie": cookie,
                    "X-CSRF-Token": csrf,
                    "Content-Type": "multipart/form-data",
                },
                "/api/import",
                b"x",
            ),
            (
                {
                    "Host": good_host,
                    "Origin": f"http://{good_host}",
                    "Cookie": cookie,
                    "X-CSRF-Token": csrf,
                    "Content-Type": "application/json",
                },
                "/../../etc/passwd",
                b"{}",
            ),
        )
        for attack_headers, path, attack_body in attacks:
            status, response_headers, _ = _request_http(
                server, "POST", path, body=attack_body, headers=attack_headers
            )
            assert status in {400, 403, 404, 413, 415}
            assert "access-control-allow-origin" not in response_headers

        status, _, payload = _request_http(
            server,
            "POST",
            "/api/save",
            body=encoded,
            headers={
                "Host": good_host,
                "Origin": f"http://{good_host}",
                "Cookie": cookie,
                "X-CSRF-Token": csrf,
                "Content-Type": "application/json",
            },
        )
        assert status == 200
        assert json.loads(payload)["revision"] == 1


def test_current_pointer_rejects_symlinked_artifact(tmp_path: Path) -> None:
    root, _ = _project(tmp_path)
    current = UserFactEditService(root).read_current_delivery()
    entry = current.reports[0]
    site = root / entry.site_relative_path
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (site / "data" / "link.txt").symlink_to(outside)
    with pytest.raises(CurrentDeliveryConflictError, match="符号链接"):
        UserFactEditService(root).read_current_delivery()


def test_invalid_edit_contract_fails_closed(tmp_path: Path) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    with pytest.raises((ValueError, UserFactSaveError)):
        service.save(
            _command(
                edits=FactEdit(
                    numerator=81,
                    denominator=80,
                    statistical_form="crude_rate",
                    measure_object="participants",
                )
            )
        )
    with pytest.raises(ValueError):
        FactEdit(statistical_form="reported_adjusted_rate")


def test_explicit_clear_is_not_silently_treated_as_omission(tmp_path: Path) -> None:
    assert FactEdit().changes() == {}
    assert FactEdit(normalized_value=None).changes() == {"normalized_value": None}
    omitted = _command(edits=FactEdit(numerator=24))
    cleared = _command(edits=FactEdit(numerator=24, normalized_value=None))
    assert omitted.model_dump_json(exclude_unset=True) != cleared.model_dump_json(
        exclude_unset=True
    )
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    with pytest.raises(UserFactSaveError, match="此字段尚不支持显式清除"):
        service.save(_command(edits=FactEdit(timepoint=None)))
    with pytest.raises(UserFactSaveError, match="同时清除和设置数值"):
        service.save(_command(edits=FactEdit(normalized_value=None, numerator=24)))
    assert service.read_current_delivery().revision == 0


def test_wire_schema_accepts_only_allowlisted_null_clears() -> None:
    schema = json.loads(Path("schemas/user-fact-save.schema.json").read_text())
    validator = Draft202012Validator(schema)
    for edits in (
        FactEdit(normalized_value=None),
        FactEdit(raw_value=None),
        FactEdit(numerator=None),
        FactEdit(denominator=None),
        FactEdit(threshold_value=None),
    ):
        payload = _command(edits=edits).model_dump(mode="json", exclude_unset=True)
        payload["schema_version"] = "1.0"
        validator.validate(payload)
    payload = _command(edits=FactEdit(timepoint=None)).model_dump(
        mode="json", exclude_unset=True
    )
    payload["schema_version"] = "1.0"
    assert list(validator.iter_errors(payload))


def test_clear_current_rate_preserves_source_and_invalidates_shared_a_b(
    tmp_path: Path,
) -> None:
    root, fragments = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    old_c = next(item for item in before.reports if item.report == "C")
    result = service.save(
        _command(request_id="shared-a-b-clear", edits=FactEdit(normalized_value=None))
    )
    assert result.derived_crude_rate is None
    assert result.rebuilt_reports == ("A", "B")
    current = service.read_current_delivery()
    assert next(item for item in current.reports if item.report == "C") == old_c
    fact = service.current_facts()["fact-crude-rate"]
    assert fact["raw_value"] is None
    assert fact["normalized_value"] is None
    assert fact["numerator"] is None
    assert fact["denominator"] is None
    assert fact["disclosure_state"] == "user_cleared"
    for report in ("A", "B"):
        projection = _projection(root, report)
        row = next(item for item in projection["safety"] if item["row_id"] == "safe-apply-t-1")
        assert row["value"] is None
        assert row["numerator"] is None
        assert row["denominator"] is None
        assert "用户清除，待重新核实" in json.dumps(row, ensure_ascii=False)
        edit = projection["user_edits"]["safe-apply-t-1"]
        assert edit["status_label_zh"] == "用户清除，待重新核实"
        assert edit["original_value"].startswith("54.8%")
        delivery = next(item for item in current.reports if item.report == report)
        html = (root / delivery.site_relative_path / "safety.html").read_text()
        assert "用户清除，待重新核实" in html
        assert "None" not in html
        if report == "B":
            view = _evidence_view_projection(root, "B", row["row_id"])
            assert view["row"]["disclosure_state"] == "user_cleared"
            assert view["value"] == {"value": None, "state": "user_cleared"}
            assert view["numerator"] == {"value": None, "state": "user_cleared"}
            assert view["denominator"] == {"value": None, "state": "user_cleared"}
    with open_database(root / "state/project.sqlite") as database:
        source = database.execute(
            "SELECT content_text FROM evidence_fragments WHERE fragment_id=?",
            (fragments["count"],),
        ).fetchone()
        derived = database.execute(
            "SELECT count(*) FROM user_fact_derivations WHERE revision=1"
        ).fetchone()
    assert source is not None and source[0] == "34/62例受试者发生任何TEAE（54.8%）。"
    assert derived is not None and derived[0] == 0


def test_clear_c_threshold_removes_current_numeric_but_preserves_source(
    tmp_path: Path,
) -> None:
    root, fragments = _project(tmp_path)
    service = UserFactEditService(root)
    command = UserFactSaveCommand(
        request_id="clear-c-threshold",
        project_id=PROJECT_ID,
        expected_revision=0,
        target=FactTargetIdentity(
            fact_id="fact-c-threshold",
            fact_version_id="fact-c-threshold-v1",
            entity_id="entity-arm",
            field_id="eligibility.score_threshold",
        ),
        edits=FactEdit(threshold_value=None),
        user_basis="阈值待核，暂不展示当前数值。",
        saved_by="medical-user",
        saved_at=NOW,
    )
    result = service.save(command)
    assert result.rebuilt_reports == ("C",)
    fact = service.current_facts()["fact-c-threshold"]
    assert fact["normalized_value"] is None
    assert fact["threshold_value"] is None
    assert fact["disclosure_state"] == "user_cleared"
    projection = _projection(root, "C")
    row = next(
        item for item in projection["observations"]
        if item["row_id"] == "c-nct04178967-inclusion"
    )
    assert row["threshold_value"] is None
    assert row["disclosure_state"] == "user_cleared"
    assert "用户清除，待重新核实" in row["display_text"]
    assert projection["user_edits"][row["row_id"]]["original_value"] == "≥16 分"
    view = _evidence_view_projection(root, "C", row["row_id"])
    assert view["row"]["disclosure_state"] == "user_cleared"
    assert view["threshold"] == {"value": None, "state": "user_cleared"}
    assert view["user_edit"]["original_value"] == "≥16 分"
    with open_database(root / "state/project.sqlite") as database:
        source = database.execute(
            "SELECT content_text FROM evidence_fragments WHERE fragment_id=?",
            (fragments["threshold"],),
        ).fetchone()
    assert source is not None and "16" in source[0]


def test_clear_restore_and_undo_restore_replays_effective_current_state(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    cleared = service.save(
        _command(request_id="clear-then-restore-1", edits=FactEdit(numerator=None))
    )
    with pytest.raises(UserFactSaveError, match="恢复当前数值必须提供完整数值"):
        service.save(
            _command(
                request_id="incomplete-restoration",
                expected_revision=1,
                fact_version_id=cleared.fact_version_id,
                edits=FactEdit(numerator=24),
            )
        )
    assert service.read_current_delivery().revision == 1
    restored = service.save(
        _command(
            request_id="clear-then-restore-2",
            expected_revision=1,
            fact_version_id=cleared.fact_version_id,
            edits=FactEdit(numerator=24, denominator=62),
        )
    )
    assert restored.derived_crude_rate == round(24 / 62 * 100, 10)
    for report in ("A", "B"):
        row = next(
            item for item in _projection(root, report)["safety"]
            if item["row_id"] == "safe-apply-t-1"
        )
        assert row["value"] == restored.derived_crude_rate
        assert row["numerator"] == 24
    undone = service.save(
        _command(
            request_id="clear-then-restore-3",
            expected_revision=2,
            fact_version_id=restored.fact_version_id,
            edits=FactEdit(),
            operation="undo",
        )
    )
    assert undone.derived_crude_rate is None
    assert service.read_current_delivery().revision == 3
    assert service.current_facts()["fact-crude-rate"]["disclosure_state"] == "user_cleared"
    for report in ("A", "B"):
        row = next(
            item for item in _projection(root, report)["safety"]
            if item["row_id"] == "safe-apply-t-1"
        )
        assert row["value"] is None
        assert row["numerator"] is None


def test_clear_failure_keeps_old_generation_and_same_request_retries(
    tmp_path: Path,
) -> None:
    root, _ = _project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    pointer = root / "reports/current.json"
    original_pointer = pointer.read_bytes()
    command = _command(request_id="clear-fault-retry", edits=FactEdit(denominator=None))

    def interrupt(report: str) -> None:
        if report == "A":
            raise OSError("injected clear interruption")

    service._after_report_built = interrupt
    with pytest.raises(OSError, match="clear interruption"):
        service.save(command)
    assert pointer.read_bytes() == original_pointer
    assert service.read_current_delivery() == before
    service._after_report_built = lambda _report: None
    result = service.save(command)
    assert result.rebuilt_reports == ("A", "B")
    assert service.read_current_delivery().revision == 1


def test_saved_event_preserves_sparse_edit_presence(tmp_path: Path) -> None:
    root, _ = _project(tmp_path)
    service = UserFactEditService(root)
    command = _command(request_id="sparse-event", edits=FactEdit(numerator=24))
    service.save(command)
    events = service.event_store.read_all()
    saved = next(event for event in events if event.event_type == "user.fact.saved")
    assert saved.payload["command"]["edits"] == {"numerator": 24}
