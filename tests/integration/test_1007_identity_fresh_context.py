"""A new Python process must not forget a prior source-bound identity input."""

from datetime import UTC, datetime

import pytest

from ci_workflow.application.run_service import (
    ContractConfigError,
    RunContext,
    _finalize_run,
    _project_identity,
)
from ci_workflow.storage.event_store import EventStore
from tests.integration.test_1007_identity_run_entry import _run_input


def _record(tmp_path, *, legacy=False):
    root, canonical, _receipt, ctx = _run_input(tmp_path, "A")
    (root / "logs").mkdir()
    _project_identity(ctx)
    if legacy:
        ctx.runtime_metadata.pop("identity_input_digest")
    _finalize_run(root, "identity-initial", ctx.contract, datetime.now(UTC), False,
        ctx, {}, [], [], "renderer_unavailable", EventStore(root))
    return root, canonical, ctx


@pytest.mark.parametrize("remove_manifest", [False, True])
def test_new_context_refuses_deleted_previously_bound_identity(tmp_path, remove_manifest):
    root, canonical, ctx = _record(tmp_path)
    canonical.unlink()
    if remove_manifest:
        (root / "manifests/current_run.json").unlink()
    fresh = RunContext(project_root=root, contract=ctx.contract)
    with pytest.raises(ContractConfigError, match="身份来源输入.*丢失"):
        _project_identity(fresh)
    assert not fresh.run_inputs and not fresh.source_input_paths


def test_recorded_identity_requirement_is_bound_to_real_run_event(tmp_path):
    root, _canonical, ctx = _record(tmp_path)
    events = EventStore(root).read_all()
    recorded = next(event for event in events if event.event_type == "run.manifest.recorded")
    expected = ctx.runtime_metadata["identity_input_digest"]
    assert recorded.payload["identity_input_digest"] == expected


def test_fresh_context_reopens_existing_identity_without_reusing_old_memory(tmp_path):
    root, _canonical, ctx = _record(tmp_path)
    fresh = RunContext(project_root=root, contract=ctx.contract)
    projected = _project_identity(fresh)
    assert projected is not None
    expected = ctx.runtime_metadata["identity_input_digest"]
    assert fresh.runtime_metadata["identity_input_digest"] == expected


def test_never_bound_legacy_context_keeps_identity_optional(tmp_path):
    root, canonical, _receipt, ctx = _run_input(tmp_path, "A")
    canonical.unlink()
    fresh = RunContext(project_root=root, contract=ctx.contract)
    assert _project_identity(fresh) is None


def test_legacy_manifest_without_new_marker_still_requires_its_bound_input(tmp_path):
    root, canonical, ctx = _record(tmp_path, legacy=True)
    canonical.unlink()
    fresh = RunContext(project_root=root, contract=ctx.contract)
    with pytest.raises(ContractConfigError, match="身份来源输入.*丢失"):
        _project_identity(fresh)
