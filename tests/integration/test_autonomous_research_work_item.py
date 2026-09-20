from __future__ import annotations

from pathlib import Path

import pytest

from ci_workflow.application.autonomous_research import (
    build_autonomous_research_task,
    load_default_source_policy,
)
from ci_workflow.application.intake import record_yaozh_answer
from ci_workflow.domain.contracts import create_project_contract


def test_task_is_host_executable_and_does_not_require_yaozh() -> None:
    contract = create_project_contract(
        indication="IgA 肾病",
        reports=["A", "B", "C"],
        outputs=["html"],
        cutoff="2026-09-05",
    )
    policy = load_default_source_policy(Path(__file__).parents[2])
    task = build_autonomous_research_task(contract, source_policy=policy)

    assert task.reports == ("A", "B", "C")
    assert task.yaozh_access.required_for_core_research is False
    assert task.yaozh_access.credential_fields_allowed is False
    assert set(task.package_target.report_payload_paths) == {"A", "B", "C"}
    assert "research submit" in task.package_target.submit_command
    assert all(route.completion_zh for route in task.routes)
    assert len({route.route_id for route in task.routes}) == len(task.routes)
    assert task.package_target.required_review_digest_version == "2"
    assert all(
        "连续两轮零新增" in route.completion_zh
        for route in task.routes if route.route_id.startswith("reverse-")
    )


def test_available_yaozh_answer_enables_only_an_optional_auxiliary_route() -> None:
    contract = create_project_contract(
        indication="IgA 肾病", reports=["A", "B", "C"], outputs=["html"]
    )
    policy = load_default_source_policy(Path(__file__).parents[2])
    record = record_yaozh_answer(contract.project_id, "available")

    task = build_autonomous_research_task(
        contract, source_policy=policy, yaozh_record=record
    )

    assert task.yaozh_access.state == "route_enabled"
    assert task.yaozh_access.result_class == "pending"
    route = next(item for item in task.routes if item.route_id == "yaozh-optional-browser")
    assert route.required is False
    assert route.source_ids == ("yaozh_enterprise",)
    assert "唯一" in route.completion_zh


@pytest.mark.parametrize("answer", ["unavailable", "skipped"])
def test_unavailable_or_skipped_yaozh_answer_is_explicitly_nonblocking(
    answer: str,
) -> None:
    contract = create_project_contract(
        indication="IgA 肾病", reports=["A"], outputs=["html"]
    )
    policy = load_default_source_policy(Path(__file__).parents[2])
    record = record_yaozh_answer(contract.project_id, answer)  # type: ignore[arg-type]

    task = build_autonomous_research_task(
        contract, source_policy=policy, yaozh_record=record
    )

    assert task.yaozh_access.state == "route_not_applicable"
    assert task.yaozh_access.result_class == "not_applicable"
    assert task.yaozh_access.required_for_core_research is False
    assert all(item.route_id != "yaozh-optional-browser" for item in task.routes)
