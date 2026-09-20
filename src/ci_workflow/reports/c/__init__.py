"""C 类报告设计事实合同与设计视图投影。

对外公开 Task 7.1 设计观察类型、登记优先门槛判定与稳定失败码，Task 7.2
入排精确下钻投影入口，Task 7.3 设计图谱/终点三元/逐试验档案投影入口，
以及 Task 7.4 多路径综合入口。本包不生成 HTML、fixture 或草稿输出。
"""

from ci_workflow.reports.c.contracts import (
    SCHEMA_PATH,
    DesignEvidenceScope,
    DesignFieldFamily,
    DesignGateDecision,
    DesignGateFailure,
    DesignGateResult,
    DesignNonblockingGap,
    DesignObservation,
    DesignObservationError,
    evaluate_design_gate,
    validate_design_observation,
)
from ci_workflow.reports.c.design import (
    EligibilityDesignError,
    EligibilityDrilldownRow,
    EligibilityDrilldownView,
    EligibilityEvidenceLink,
    FieldApplicability,
    project_eligibility_drilldown,
)
from ci_workflow.reports.c.pages import (
    DesignFactRow,
    DesignPagesError,
    DesignTopic,
    DesignTopicView,
    EndpointDefinitionTimepointRow,
    EndpointDefinitionTimepointView,
    TrialDossierView,
    project_design_map,
    project_endpoint_definition_timepoint,
    project_exclusion_view,
    project_inclusion_view,
    project_intervention_view,
    project_population_view,
    project_statistics_view,
    project_trial_dossier,
    project_visit_schedule_view,
)
from ci_workflow.reports.c.synthesis import (
    CandidateDesignPath,
    DesignPathSynthesisResult,
    DesignSynthesisError,
    SourcedDesignFactItem,
    synthesize_design_paths,
)

__all__ = [
    "SCHEMA_PATH",
    "CandidateDesignPath",
    "DesignEvidenceScope",
    "DesignFactRow",
    "DesignFieldFamily",
    "DesignGateDecision",
    "DesignGateFailure",
    "DesignGateResult",
    "DesignNonblockingGap",
    "DesignObservation",
    "DesignObservationError",
    "DesignPagesError",
    "DesignPathSynthesisResult",
    "DesignSynthesisError",
    "DesignTopic",
    "DesignTopicView",
    "EligibilityDesignError",
    "EligibilityDrilldownRow",
    "EligibilityDrilldownView",
    "EligibilityEvidenceLink",
    "EndpointDefinitionTimepointRow",
    "EndpointDefinitionTimepointView",
    "FieldApplicability",
    "SourcedDesignFactItem",
    "TrialDossierView",
    "evaluate_design_gate",
    "project_design_map",
    "project_eligibility_drilldown",
    "project_endpoint_definition_timepoint",
    "project_exclusion_view",
    "project_inclusion_view",
    "project_intervention_view",
    "project_population_view",
    "project_statistics_view",
    "project_trial_dossier",
    "project_visit_schedule_view",
    "synthesize_design_paths",
    "validate_design_observation",
]
