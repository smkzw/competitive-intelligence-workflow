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
    assert task.shared_source_route_ids == (
        "global-baseline",
        "china-baseline",
        "reverse-alias",
        "reverse-target",
        "reverse-company",
        "reverse-trial",
    )
    assert {
        spec.report: spec.analysis_route_id for spec in task.report_specs
    } == {
        "A": "report-a-evidence",
        "B": "report-b-evidence",
        "C": "report-c-evidence",
    }
    assert len(task.shared_source_route_ids) == len(set(task.shared_source_route_ids))


@pytest.mark.parametrize("report", ["A", "B", "C"])
def test_single_report_plan_reuses_shared_sources_without_creating_other_branches(
    report: str,
) -> None:
    contract = create_project_contract(
        indication="阵发性睡眠性血红蛋白尿症",
        reports=[report],
        outputs=["html"],
    )
    task = build_autonomous_research_task(
        contract,
        source_policy=load_default_source_policy(Path(__file__).parents[2]),
    )

    assert task.reports == (report,)
    assert tuple(spec.report for spec in task.report_specs) == (report,)
    assert tuple(
        route.route_id for route in task.routes if route.route_id.startswith("report-")
    ) == (f"report-{report.lower()}-evidence",)


def test_c_completion_accepts_a_complete_single_study_precedent_library() -> None:
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["C"],
        outputs=["html"],
    )
    task = build_autonomous_research_task(
        contract,
        source_policy=load_default_source_policy(Path(__file__).parents[2]),
    )

    completion = "".join(task.report_specs[0].completion_conditions_zh)
    assert "单项有效研究即可使用" in completion
    assert "多条" not in completion


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
