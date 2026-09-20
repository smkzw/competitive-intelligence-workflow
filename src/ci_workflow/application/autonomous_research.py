"""Portable task contract for host-owned autonomous research."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ci_workflow.application.intake import YaozhAccessRecord
from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.domain.ids import stable_id
from ci_workflow.sources.policy import ClaimDomain, SourceAuthority, SourcePolicy

ReportName = Literal["A", "B", "C"]

_REPORT_DOMAINS: dict[ReportName, tuple[ClaimDomain, ...]] = {
    "A": tuple(ClaimDomain),
    "B": (
        ClaimDomain.TRIAL_IDENTITY_DESIGN_STATUS,
        ClaimDomain.EFFICACY_SAFETY_RESULTS,
        ClaimDomain.BASELINE_DISPOSITION,
    ),
    "C": (ClaimDomain.TRIAL_IDENTITY_DESIGN_STATUS,),
}
_REPORT_COMPLETION: dict[ReportName, tuple[str, ...]] = {
    "A": (
        "全部适格创新竞品进入闭包或有逐项排除依据",
        "产品身份、机制、阶段、全球和中国状态均有原位来源",
        "存在公开结果的产品已核对疗效与安全性；真实不适用字段不造空值",
    ),
    "B": (
        "结果试验的人群、终点、时间窗、分析集、方向和分母作为完整语义单元",
        "主要、延长期和关键安全性论文已分类并完成必要补件判断",
        "疗效、安全性、基线、亚组、暴露和处置的适用单元均有状态",
    ),
    "C": (
        "试验架构、人群、入排、终点、时间点、访视和统计设计均以登记或方案为先",
        "终点定义与时间窗成对保存，完整入排和方案参数可下钻",
        "只输入适应症时输出多条证据支持的设计路径，不输出唯一最佳方案",
    ),
}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResearchRouteSpec(_StrictModel):
    route_id: str
    purpose_zh: str
    region: Literal["global", "china", "cross_region"]
    source_ids: tuple[str, ...] = ()
    claim_domains: tuple[ClaimDomain, ...]
    required: bool
    completion_zh: str


class ReportResearchSpec(_StrictModel):
    report: ReportName
    claim_domains: tuple[ClaimDomain, ...]
    completion_conditions_zh: tuple[str, ...]


class YaozhAccessAsk(_StrictModel):
    state: Literal["answer_required_once"] = "answer_required_once"
    question_zh: str = "本项目是否具备药智网已登录访问条件？"
    options: tuple[Literal["available", "unavailable", "skipped"], ...] = (
        "available",
        "unavailable",
        "skipped",
    )
    required_for_core_research: Literal[False] = False
    credential_fields_allowed: Literal[False] = False


class YaozhAccessResolution(_StrictModel):
    state: Literal["route_enabled", "route_not_applicable"]
    answer: Literal["available", "unavailable", "skipped"]
    route_id: Literal["yaozh-optional-browser"] = "yaozh-optional-browser"
    result_class: Literal["pending", "not_applicable"]
    rationale_zh: str
    required_for_core_research: Literal[False] = False
    credential_fields_allowed: Literal[False] = False

    @model_validator(mode="after")
    def _state_matches_answer(self) -> Self:
        enabled = self.answer == "available"
        if enabled != (self.state == "route_enabled"):
            raise ValueError("药智路线状态与项目回答不一致")
        if enabled != (self.result_class == "pending"):
            raise ValueError("药智路线结果与项目回答不一致")
        return self


class ResearchPackageTarget(_StrictModel):
    ctgov_fetch_command: str = (
        "ci-workflow research fetch-ctgov --project <项目目录> "
        "--condition <英文适应症或别名检索式>"
    )
    capture_command: str = (
        "ci-workflow research capture --project <项目目录> "
        "--input <公开来源原始文件> --media-type <原始媒体类型>"
    )
    required_review_digest_version: Literal["2"] = "2"
    audit_schema: Literal["schemas/research-package.schema.json"] = (
        "schemas/research-package.schema.json"
    )
    audit_path: Literal["evidence/library/research-package.json"] = (
        "evidence/library/research-package.json"
    )
    report_payload_paths: dict[ReportName, str]
    submit_command: str
    completion_conditions_zh: tuple[str, ...] = (
        "全球和中国必查路线均有回执，网络失败不得改写为真实无数据",
        "CT.gov可使用fetch-ctgov逐页获取；当前查询完成不是竞品闭包或历史版本还原，失败继续恢复",
        "别名、靶点、企业和试验反向扩展完成并经独立干净上下文复核",
        "关键缺口完成两轮不同策略恢复；必需论文补件门已终结",
        "审计包与全部报告科学载荷字节摘要一致",
        "独立复核使用来源元数据摘要v2；来源/时间或补件改变后必须重新复核",
        "原始PDF必须经capture保留字节与文本派生回执；扫描件无可靠文本层时进入恢复，不得冒充已提取",
        "每次药智访问前执行yaozh check；观察绑定返回run_id和当前宿主，失败立即observe再重检",
    )


class AutonomousResearchTask(_StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    task_id: str
    project_id: str
    contract_version: int
    indication: str
    reports: tuple[ReportName, ...] = Field(min_length=1)
    data_cutoff: date
    source_policy_id: str
    source_policy_version: str
    routes: tuple[ResearchRouteSpec, ...] = Field(min_length=1)
    report_specs: tuple[ReportResearchSpec, ...] = Field(min_length=1)
    yaozh_access: YaozhAccessAsk | YaozhAccessResolution
    package_target: ResearchPackageTarget
    state: Literal["awaiting_host_research"] = "awaiting_host_research"
    next_action_zh: str = (
        "当前 Agent 按来源计划完成研究与独立复核，再通过 submit_command 提交；用户不填写内部字段。"
    )

    @model_validator(mode="after")
    def _bindings_are_closed(self) -> Self:
        if {item.report for item in self.report_specs} != set(self.reports):
            raise ValueError("报告研究要求未恰好覆盖项目报告集合")
        if set(self.package_target.report_payload_paths) != set(self.reports):
            raise ValueError("研究包目标未恰好覆盖项目报告集合")
        route_ids = tuple(item.route_id for item in self.routes)
        if len(route_ids) != len(set(route_ids)):
            raise ValueError("来源计划路线不得重复")
        return self


def _direct_sources(policy: SourcePolicy, domains: tuple[ClaimDomain, ...]) -> tuple[str, ...]:
    return tuple(
        item.source_id
        for item in policy.sources
        if any(item.authorities[domain] is SourceAuthority.DIRECT for domain in domains)
    )


def build_autonomous_research_task(
    contract: ProjectContract,
    *,
    source_policy: SourcePolicy,
    yaozh_record: YaozhAccessRecord | None = None,
) -> AutonomousResearchTask:
    if yaozh_record is not None and yaozh_record.project_id != contract.project_id:
        raise ValueError("药智访问回答与当前项目身份不一致")
    reports = cast(tuple[ReportName, ...], tuple(item.value for item in contract.reports))
    global_sources = tuple(
        item.source_id for item in source_policy.sources if item.required_global_baseline
    )
    china_sources = tuple(
        item.source_id for item in source_policy.sources if item.required_for_china
    )
    all_domains = tuple(
        dict.fromkeys(domain for report in reports for domain in _REPORT_DOMAINS[report])
    )
    expansion_sources = _direct_sources(source_policy, all_domains)
    routes = [
        ResearchRouteSpec(
            route_id="global-baseline",
            purpose_zh="全球官方登记与适用监管来源基线检索",
            region="global",
            source_ids=global_sources,
            claim_domains=all_domains,
            required=True,
            completion_zh="每个策略单元均有成功、真实不适用、访问受限或可诊断失败回执",
        ),
        ResearchRouteSpec(
            route_id="china-baseline",
            purpose_zh="中国登记、CDE/NMPA 与适用权威来源基线检索",
            region="china",
            source_ids=china_sources,
            claim_domains=all_domains,
            required=True,
            completion_zh="中国来源与全球来源分别闭合，不用境外结果替代中国状态",
        ),
    ]
    for dimension in ("alias", "target", "company", "trial"):
        routes.append(
            ResearchRouteSpec(
                route_id=f"reverse-{dimension}",
                purpose_zh=f"按 {dimension} 维度反向扩展竞品宇宙",
                region="cross_region",
                source_ids=expansion_sources,
                claim_domains=all_domains,
                required=True,
                completion_zh="记录新增实体；最后连续两轮零新增并经独立复核才可声明收敛",
            )
        )
    for report in reports:
        domains = _REPORT_DOMAINS[report]
        routes.append(
            ResearchRouteSpec(
                route_id=f"report-{report.lower()}-evidence",
                purpose_zh=f"{report} 类报告专属证据检索与 Publication 识别",
                region="cross_region",
                source_ids=_direct_sources(source_policy, domains),
                claim_domains=domains,
                required=True,
                completion_zh="报告专属关键单元均有来源、缺失状态或恢复终态",
            )
        )
    if yaozh_record is not None and yaozh_record.answer == "available":
        source_policy.source("yaozh_enterprise")
        routes.append(
            ResearchRouteSpec(
                route_id="yaozh-optional-browser",
                purpose_zh="通过已登录浏览器补充药智网线索与交叉核验",
                region="cross_region",
                source_ids=("yaozh_enterprise",),
                claim_domains=all_domains,
                required=False,
                completion_zh=(
                    "记录线索、交叉核验或技术访问受限状态；不得作为关键结论的唯一依据"
                ),
            )
        )
    payload_paths = {
        report: f"evidence/library/{report.lower()}-research-package.json" for report in reports
    }
    return AutonomousResearchTask(
        task_id=stable_id(
            "autonomous-research-task",
            contract.project_id,
            str(contract.contract_version),
            yaozh_record.answer if yaozh_record is not None else "answer-pending",
        ),
        project_id=contract.project_id,
        contract_version=contract.contract_version,
        indication=contract.indication,
        reports=reports,
        data_cutoff=contract.data_cutoff.date(),
        source_policy_id=source_policy.policy_id,
        source_policy_version=source_policy.version,
        routes=tuple(routes),
        report_specs=tuple(
            ReportResearchSpec(
                report=report,
                claim_domains=_REPORT_DOMAINS[report],
                completion_conditions_zh=_REPORT_COMPLETION[report],
            )
            for report in reports
        ),
        yaozh_access=(
            YaozhAccessAsk()
            if yaozh_record is None
            else YaozhAccessResolution(
                state=(
                    "route_enabled"
                    if yaozh_record.answer == "available"
                    else "route_not_applicable"
                ),
                answer=yaozh_record.answer,
                result_class=(
                    "pending" if yaozh_record.answer == "available" else "not_applicable"
                ),
                rationale_zh=(
                    "药智网可选浏览器路线已启用；仅用于线索与交叉核验。"
                    if yaozh_record.answer == "available"
                    else "本项目未启用药智网可选路线；其他适格来源继续完成核心研究。"
                ),
            )
        ),
        package_target=ResearchPackageTarget(
            report_payload_paths=payload_paths,
            submit_command=(
                "ci-workflow research submit --project <项目目录> "
                "--package <审计包> "
                + " ".join(f"--{report.lower()}-package <{report}类科学载荷>" for report in reports)
            ),
        ),
    )


def load_default_source_policy(package_root: Path) -> SourcePolicy:
    return SourcePolicy.from_yaml(package_root / "policies/sources/source-policy-v1.yaml")


__all__ = [
    "AutonomousResearchTask",
    "ReportResearchSpec",
    "ResearchPackageTarget",
    "ResearchRouteSpec",
    "YaozhAccessAsk",
    "YaozhAccessResolution",
    "build_autonomous_research_task",
    "load_default_source_policy",
]
