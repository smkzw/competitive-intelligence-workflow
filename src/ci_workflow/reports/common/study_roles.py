"""B/C 研究角色策略与确定性判定合同。

研究角色只消费已经结构化的研究事实；论文角色由来源连接器独立判定，
本模块不读取论文内容，也不接受调用方注入最终角色。
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any, Self, cast

import yaml
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ci_workflow.domain.enums import ReportKind


class StudyRolePolicyError(ValueError):
    """研究角色策略或判定输入不符合失败关闭合同。"""


class StudyRole(StrEnum):
    """B/C 研究角色封闭集合。"""

    CORE = "core"
    SPECIAL_CORE = "special_core"
    SUPPORTING = "supporting"
    EXCLUDED = "excluded"

    # 语义别名只保留一个序列化值，兼容调用方的自然命名。
    SUPPORT = "supporting"
    DEFAULT_EXCLUDED = "excluded"


class IndicationRelation(StrEnum):
    TARGET = "target"
    ADJACENT = "adjacent"
    UNRELATED = "unrelated"


class StudyPhase(StrEnum):
    PHASE_I = "phase_i"
    PHASE_I_II = "phase_i_ii"
    PHASE_II = "phase_ii"
    PHASE_II_III = "phase_ii_iii"
    PHASE_III = "phase_iii"
    EARLY = "early"


class StudyDesignCategory(StrEnum):
    INTERVENTIONAL = "interventional"
    HEALTHY_VOLUNTEER = "healthy_volunteer"
    PURE_PK_OR_BE = "pure_pk_or_be"
    OBSERVATIONAL = "observational"
    EAP_OR_COMPASSIONATE_USE = "eap_or_compassionate_use"

    # 输入别名归一到策略文件使用的五类边界。
    PURE_PK = "pure_pk_or_be"
    PURE_BE = "pure_pk_or_be"
    EAP = "eap_or_compassionate_use"
    COMPASSIONATE_USE = "eap_or_compassionate_use"


class StudyEvidenceType(StrEnum):
    """研究事实相对核心试验的证据层角色。"""

    STANDARD = "standard"
    EXTENSION = "extension"
    SUBGROUP = "subgroup"
    POST_HOC = "post_hoc"
    REAL_WORLD = "real_world"


class DevelopmentContext(StrEnum):
    ORDINARY = "ordinary"
    RARE_DISEASE = "rare_disease"
    ONCOLOGY = "oncology"
    ACCELERATED_DEVELOPMENT = "accelerated_development"


class ProblemDomain(StrEnum):
    SAFETY = "safety"
    REGULATORY = "regulatory"
    SPECIAL_POPULATION = "special_population"


class DecisionDomain(StrEnum):
    DOSE = "dose"
    ENDPOINT = "endpoint"
    ADAPTIVE_DESIGN = "adaptive_design"
    POPULATION = "population"
    ESTIMAND = "estimand"
    REGISTRATION_LOGIC = "registration_logic"


_DECISION_DOMAINS = frozenset(DecisionDomain)
_DECISION_DOMAIN_TERMS: dict[DecisionDomain, tuple[str, ...]] = {
    DecisionDomain.DOSE: ("剂量", "给药"),
    DecisionDomain.ENDPOINT: ("终点", "疗效指标", "安全性指标"),
    DecisionDomain.ADAPTIVE_DESIGN: ("适应性", "停步", "扩展", "无缝"),
    DecisionDomain.POPULATION: ("人群", "受试者", "入选", "分层"),
    DecisionDomain.ESTIMAND: ("estimand", "估计目标", "伴发事件"),
    DecisionDomain.REGISTRATION_LOGIC: ("注册", "申报", "监管"),
}
_GENERIC_RATIONALES = frozenset(
    {
        "重要",
        "很重要",
        "相关",
        "可参考",
        "具有参考价值",
        "值得关注",
    }
)
_GENERIC_RATIONALE_RE = re.compile(
    r"^(?:(?:本|该|这项)研究)?(?:很|较|非常)?"
    r"(?:重要|相关|可参考|有参考价值|具有参考价值|值得关注)$"
)


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("研究角色合同文本不能为空")
    return normalized


def _normalize_enum_token(value: Any, aliases: Mapping[str, str]) -> Any:
    if not isinstance(value, str):
        return value
    normalized = "_".join(value.strip().casefold().replace("-", "_").replace("/", "_").split())
    return aliases.get(normalized, value)


def _normalize_contexts(value: Any) -> Any:
    if value is None:
        return ()
    if isinstance(value, str):
        value = (value,)
    return tuple(
        _normalize_enum_token(
            item,
            {
                "rare": "rare_disease",
                "rare_disease": "rare_disease",
                "oncology": "oncology",
                "cancer": "oncology",
                "accelerated": "accelerated_development",
                "accelerated_development": "accelerated_development",
                "ordinary": "ordinary",
            },
        )
        for item in value
    )


class StudyCandidate(BaseModel):
    """已结构化的研究事实；不包含可由调用方指定的 ``study_role``。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    study_id: str = Field(validation_alias=AliasChoices("study_id", "trial_id", "research_id"))
    report_kind: ReportKind = Field(
        validation_alias=AliasChoices("report_kind", "report_type", "report")
    )
    indication_relation: IndicationRelation = Field(
        validation_alias=AliasChoices(
            "indication_relation", "indication_relationship", "indication"
        )
    )
    phase: StudyPhase = Field(validation_alias=AliasChoices("phase", "study_phase"))
    design_category: StudyDesignCategory = Field(
        validation_alias=AliasChoices("design_category", "study_design", "design_kind", "design")
    )
    evidence_type: StudyEvidenceType = Field(
        default=StudyEvidenceType.STANDARD,
        validation_alias=AliasChoices("evidence_type", "study_evidence_type", "study_subtype"),
    )
    has_results: bool = Field(
        validation_alias=AliasChoices("has_results", "result_bearing", "has_observed_results")
    )
    is_key_or_registration: bool = Field(
        validation_alias=AliasChoices(
            "is_key_or_registration",
            "key_or_registration",
            "is_pivotal_or_registration",
            "pivotal_or_registration",
        )
    )
    development_contexts: tuple[DevelopmentContext, ...] = Field(
        default_factory=tuple,
        validation_alias=AliasChoices("development_contexts", "development_context", "contexts"),
    )
    named_issue: str | None = Field(
        default=None,
        validation_alias=AliasChoices("named_issue", "named_problem", "problem"),
    )
    issue_domain: ProblemDomain | None = Field(
        default=None,
        validation_alias=AliasChoices("issue_domain", "problem_domain", "named_issue_domain"),
    )
    decision_domain: DecisionDomain | None = Field(
        default=None,
        validation_alias=AliasChoices("decision_domain", "design_decision_domain"),
    )
    evidence_is_irreplaceable: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "evidence_is_irreplaceable",
            "non_substitutable",
            "irreplaceable_evidence",
            "evidence_irreplaceable",
        ),
    )
    inclusion_rationale_zh: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "inclusion_rationale_zh", "inclusion_rationale", "rationale_zh"
        ),
    )
    evidence_version: str = Field(
        validation_alias=AliasChoices("evidence_version", "evidence_version_id", "source_version")
    )

    @field_validator("study_id", "evidence_version")
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _text(value)

    @field_validator("named_issue", "inclusion_rationale_zh")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @field_validator("indication_relation", mode="before")
    @classmethod
    def _indication_alias(cls, value: Any) -> Any:
        return _normalize_enum_token(
            value,
            {
                "target_indication": "target",
                "target": "target",
                "adjacent": "adjacent",
                "unrelated_indication": "unrelated",
                "unrelated": "unrelated",
            },
        )

    @field_validator("phase", mode="before")
    @classmethod
    def _phase_alias(cls, value: Any) -> Any:
        return _normalize_enum_token(
            value,
            {
                "i": "phase_i",
                "phase_1": "phase_i",
                "phase1": "phase_i",
                "phase_i": "phase_i",
                "i_ii": "phase_i_ii",
                "phase_1_2": "phase_i_ii",
                "phase_i_ii": "phase_i_ii",
                "ii": "phase_ii",
                "phase_2": "phase_ii",
                "phase2": "phase_ii",
                "phase_ii": "phase_ii",
                "ii_iii": "phase_ii_iii",
                "phase_2_3": "phase_ii_iii",
                "phase_ii_iii": "phase_ii_iii",
                "iii": "phase_iii",
                "phase_3": "phase_iii",
                "phase3": "phase_iii",
                "phase_iii": "phase_iii",
                "early": "early",
            },
        )

    @field_validator("design_category", mode="before")
    @classmethod
    def _design_alias(cls, value: Any) -> Any:
        return _normalize_enum_token(
            value,
            {
                "intervention": "interventional",
                "interventional": "interventional",
                "interventional_trial": "interventional",
                "healthy": "healthy_volunteer",
                "healthy_volunteer": "healthy_volunteer",
                "pure_pk": "pure_pk_or_be",
                "pk": "pure_pk_or_be",
                "pharmacokinetic": "pure_pk_or_be",
                "pure_be": "pure_pk_or_be",
                "be": "pure_pk_or_be",
                "bioequivalence": "pure_pk_or_be",
                "pk_be": "pure_pk_or_be",
                "pk_or_be": "pure_pk_or_be",
                "pure_pk_or_be": "pure_pk_or_be",
                "observational": "observational",
                "observational_study": "observational",
                "eap": "eap_or_compassionate_use",
                "expanded_access": "eap_or_compassionate_use",
                "compassionate_use": "eap_or_compassionate_use",
                "eap_compassionate_use": "eap_or_compassionate_use",
                "eap_or_compassionate_use": "eap_or_compassionate_use",
            },
        )

    @field_validator("development_contexts", mode="before")
    @classmethod
    def _context_aliases(cls, value: Any) -> Any:
        return _normalize_contexts(value)

    @field_validator("evidence_type", mode="before")
    @classmethod
    def _evidence_type_alias(cls, value: Any) -> Any:
        return _normalize_enum_token(
            value,
            {
                "standard": "standard",
                "extension": "extension",
                "ole": "extension",
                "open_label_extension": "extension",
                "subgroup": "subgroup",
                "subgroup_analysis": "subgroup",
                "post_hoc": "post_hoc",
                "posthoc": "post_hoc",
                "real_world": "real_world",
                "rwe": "real_world",
            },
        )

    @field_validator("issue_domain", mode="before")
    @classmethod
    def _issue_alias(cls, value: Any) -> Any:
        return _normalize_enum_token(
            value,
            {
                "safety": "safety",
                "regulatory": "regulatory",
                "special_population": "special_population",
                "special_population_problem": "special_population",
            },
        )

    @field_validator("decision_domain", mode="before")
    @classmethod
    def _decision_alias(cls, value: Any) -> Any:
        return _normalize_enum_token(
            value,
            {
                "dose": "dose",
                "endpoint": "endpoint",
                "adaptive_design": "adaptive_design",
                "adaptive": "adaptive_design",
                "population": "population",
                "estimand": "estimand",
                "registration_logic": "registration_logic",
                "registration": "registration_logic",
            },
        )

    @property
    def development_context(self) -> tuple[DevelopmentContext, ...]:
        """兼容单数输入命名；实际合同始终保存完整上下文集合。"""

        return self.development_contexts


class StudyRoleRule(BaseModel):
    """一个版本化角色规则；空条件表示该维度适用于全部候选。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    rule_id: str = Field(validation_alias=AliasChoices("rule_id", "id"))
    role: StudyRole
    priority: int = 0
    report_kinds: tuple[ReportKind, ...] = Field(
        default_factory=tuple,
        validation_alias=AliasChoices("report_kinds", "report_types", "applies_to"),
    )
    indication_relations: tuple[IndicationRelation, ...] = Field(
        default_factory=tuple,
        validation_alias=AliasChoices("indication_relations", "indication_relationships"),
    )
    phases: tuple[StudyPhase, ...] = Field(default_factory=tuple)
    design_categories: tuple[StudyDesignCategory, ...] = Field(
        default_factory=tuple,
        validation_alias=AliasChoices("design_categories", "design_kinds"),
    )
    evidence_types: tuple[StudyEvidenceType, ...] = Field(
        default_factory=tuple,
        validation_alias=AliasChoices("evidence_types", "study_evidence_types"),
    )
    development_contexts: tuple[DevelopmentContext, ...] = Field(
        default_factory=tuple,
        validation_alias=AliasChoices("development_contexts", "contexts"),
    )
    excluded_development_contexts: tuple[DevelopmentContext, ...] = Field(
        default_factory=tuple,
        validation_alias=AliasChoices("excluded_development_contexts", "excluded_contexts"),
    )
    requires_results: bool | None = None
    requires_key_or_registration: bool | None = None
    requires_named_issue: bool = False
    required_problem_domains: tuple[ProblemDomain, ...] = Field(
        default_factory=tuple,
        validation_alias=AliasChoices(
            "required_problem_domains", "problem_domains", "issue_domains"
        ),
    )
    requires_irreplaceable_evidence: bool = False
    requires_decision_domain: bool = False
    required_decision_domains: tuple[DecisionDomain, ...] = Field(
        default_factory=tuple,
        validation_alias=AliasChoices("required_decision_domains", "decision_domains"),
    )
    requires_specific_rationale: bool = False
    rationale_zh: str = Field(validation_alias=AliasChoices("rationale_zh", "reason_zh", "reason"))

    @field_validator("rule_id", "rationale_zh")
    @classmethod
    def _rule_text(cls, value: str) -> str:
        return _text(value)

    @field_validator(
        "report_kinds",
        "indication_relations",
        "phases",
        "design_categories",
        "evidence_types",
        "development_contexts",
        "excluded_development_contexts",
        "required_problem_domains",
        "required_decision_domains",
    )
    @classmethod
    def _rule_values_unique(cls, values: tuple[Any, ...]) -> tuple[Any, ...]:
        if len(set(values)) != len(values):
            raise ValueError("研究角色规则条件不得重复")
        return values

    @field_validator("phases", mode="before")
    @classmethod
    def _rule_phase_aliases(cls, value: Any) -> Any:
        return tuple(
            StudyCandidate._phase_alias(item)
            for item in (() if value is None else ((value,) if isinstance(value, str) else value))
        )

    @field_validator("design_categories", mode="before")
    @classmethod
    def _rule_design_aliases(cls, value: Any) -> Any:
        return tuple(
            StudyCandidate._design_alias(item)
            for item in (() if value is None else ((value,) if isinstance(value, str) else value))
        )

    @field_validator("evidence_types", mode="before")
    @classmethod
    def _rule_evidence_type_aliases(cls, value: Any) -> Any:
        return tuple(
            StudyCandidate._evidence_type_alias(item)
            for item in (() if value is None else ((value,) if isinstance(value, str) else value))
        )

    @field_validator("development_contexts", mode="before")
    @classmethod
    def _rule_context_aliases(cls, value: Any) -> Any:
        return _normalize_contexts(value)

    @field_validator("excluded_development_contexts", mode="before")
    @classmethod
    def _excluded_context_aliases(cls, value: Any) -> Any:
        return _normalize_contexts(value)

    @model_validator(mode="after")
    def _conditional_rules_are_complete(self) -> Self:
        if (
            self.role in {StudyRole.SUPPORTING, StudyRole.SPECIAL_CORE}
            and not self.requires_specific_rationale
        ):
            raise ValueError("支持层或特殊核心规则必须要求具体纳入理由")
        if self.role is StudyRole.SPECIAL_CORE and not self.requires_irreplaceable_evidence:
            raise ValueError("特殊核心规则必须要求不可替代证据")
        if self.requires_named_issue and not self.requires_irreplaceable_evidence:
            raise ValueError("默认排除研究进入支持层必须要求不可替代证据")
        if self.requires_decision_domain and not self.required_decision_domains:
            raise ValueError("要求决策域的规则必须声明允许的决策域")
        if not set(self.required_decision_domains) <= _DECISION_DOMAINS:
            raise ValueError("研究角色规则包含未知决策域")
        return self

    def matches(self, candidate: StudyCandidate) -> bool:
        if self.report_kinds and candidate.report_kind not in self.report_kinds:
            return False
        if (
            self.indication_relations
            and candidate.indication_relation not in self.indication_relations
        ):
            return False
        if self.phases and candidate.phase not in self.phases:
            return False
        if self.design_categories and candidate.design_category not in self.design_categories:
            return False
        if self.evidence_types and candidate.evidence_type not in self.evidence_types:
            return False
        if self.development_contexts and not set(candidate.development_contexts) & set(
            self.development_contexts
        ):
            return False
        if set(candidate.development_contexts) & set(self.excluded_development_contexts):
            return False
        if self.requires_results is not None and candidate.has_results != self.requires_results:
            return False
        if (
            self.requires_key_or_registration is not None
            and candidate.is_key_or_registration != self.requires_key_or_registration
        ):
            return False
        if self.requires_named_issue:
            if not candidate.named_issue or candidate.issue_domain is None:
                return False
            if (
                self.required_problem_domains
                and candidate.issue_domain not in self.required_problem_domains
            ):
                return False
        if self.requires_irreplaceable_evidence and not candidate.evidence_is_irreplaceable:
            return False
        if self.requires_decision_domain:
            if candidate.decision_domain is None:
                return False
            if (
                self.required_decision_domains
                and candidate.decision_domain not in self.required_decision_domains
            ):
                return False
        return not self.requires_specific_rationale or _specific_rationale(
            candidate.inclusion_rationale_zh,
            decision_domain=(candidate.decision_domain if self.requires_decision_domain else None),
        )


class StudyRolePolicy(BaseModel):
    """研究角色规则集合；规则身份和内容均必须唯一。"""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_version: str
    policy_id: str
    version: str = Field(validation_alias=AliasChoices("version", "policy_version"))
    rules: tuple[StudyRoleRule, ...] = Field(
        min_length=1,
        validation_alias=AliasChoices("rules", "study_role_rules", "role_rules"),
    )

    @field_validator("schema_version", "policy_id", "version")
    @classmethod
    def _policy_text(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _rules_unique(self) -> Self:
        rule_ids = tuple(rule.rule_id for rule in self.rules)
        if len(set(rule_ids)) != len(rule_ids):
            raise ValueError("研究角色规则标识不得重复")
        bodies = tuple(
            json.dumps(
                rule.model_dump(mode="json", exclude={"rule_id", "rationale_zh"}),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for rule in self.rules
        )
        if len(set(bodies)) != len(bodies):
            raise ValueError("研究角色规则条目不得重复")
        eligibility_signatures: dict[str, StudyRole] = {}
        for rule in self.rules:
            signature = json.dumps(
                rule.model_dump(
                    mode="json",
                    exclude={
                        "rule_id",
                        "rationale_zh",
                        "role",
                        "priority",
                        "requires_named_issue",
                        "required_problem_domains",
                        "requires_irreplaceable_evidence",
                        "requires_decision_domain",
                        "required_decision_domains",
                        "requires_specific_rationale",
                    },
                ),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            previous_role = eligibility_signatures.get(signature)
            if previous_role is not None and previous_role is not rule.role:
                raise ValueError("研究角色规则适用条件相同但角色冲突")
            eligibility_signatures[signature] = rule.role
        return self

    @property
    def policy_version(self) -> str:
        return self.version

    @classmethod
    def from_yaml(cls, path: Path | str) -> Self:
        try:
            payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise StudyRolePolicyError("研究角色策略顶层必须是对象")
            return cls.model_validate(cast(dict[str, Any], payload))
        except StudyRolePolicyError:
            raise
        except (OSError, yaml.YAMLError, ValidationError) as error:
            raise StudyRolePolicyError(f"研究角色策略加载失败：{error}") from error


class StudyRoleDecision(BaseModel):
    """从当前候选和策略重新计算出的不可变研究角色结果。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: StudyCandidate
    study_role: StudyRole
    inclusion_rationale_zh: str
    matched_rule_ids: tuple[str, ...]
    policy_id: str
    policy_version: str
    evidence_version: str

    @property
    def role(self) -> StudyRole:
        return self.study_role

    @property
    def study(self) -> StudyCandidate:
        return self.candidate

    @property
    def rationale_zh(self) -> str:
        return self.inclusion_rationale_zh

    @property
    def inclusion_rationale(self) -> str:
        return self.inclusion_rationale_zh

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return self.matched_rule_ids

    @property
    def rule_version(self) -> str:
        return self.policy_version

    @property
    def study_id(self) -> str:
        return self.candidate.study_id

    @property
    def matched_rule_id(self) -> str | None:
        return self.matched_rule_ids[0] if self.matched_rule_ids else None


StudyRoleCandidate = StudyCandidate
StudyRoleResult = StudyRoleDecision
StudyRolePolicySpec = StudyRolePolicy


def _specific_rationale(
    value: str | None, *, decision_domain: DecisionDomain | None = None
) -> bool:
    if value is None:
        return False
    normalized = re.sub(r"[\s，。！？、；：,.!?;:]+", "", _text(value)).casefold()
    specific = (
        normalized not in {item.casefold() for item in _GENERIC_RATIONALES}
        and _GENERIC_RATIONALE_RE.fullmatch(normalized) is None
    )
    if not specific or decision_domain is None:
        return specific
    return any(term.casefold() in normalized for term in _DECISION_DOMAIN_TERMS[decision_domain])


def _default_policy_path() -> Path:
    return Path(__file__).resolve().parents[4] / "policies" / "studies" / "study-role-v1.yaml"


def load_study_role_policy(path: Path | str | None = None) -> StudyRolePolicy:
    """加载并严格重新验证版本化研究角色策略。"""

    return StudyRolePolicy.from_yaml(_default_policy_path() if path is None else path)


def _validated_candidate(candidate: StudyCandidate | Mapping[str, Any]) -> StudyCandidate:
    try:
        raw = dict(vars(candidate)) if isinstance(candidate, StudyCandidate) else dict(candidate)
        return StudyCandidate.model_validate(raw)
    except ValidationError as error:
        raise StudyRolePolicyError(f"研究事实重新校验失败：{error}") from error


def _validated_policy(policy: StudyRolePolicy) -> StudyRolePolicy:
    try:
        raw = dict(vars(policy))
        raw["rules"] = tuple(dict(vars(rule)) for rule in policy.rules)
        return StudyRolePolicy.model_validate(raw)
    except ValidationError as error:
        raise StudyRolePolicyError(f"研究角色策略重新校验失败：{error}") from error


def evaluate_study_role(
    candidate: StudyCandidate | Mapping[str, Any],
    *,
    policy: StudyRolePolicy | None = None,
) -> StudyRoleDecision:
    """按当前策略确定性判定研究角色，未命中或证据不足时默认排除。"""

    current_candidate = _validated_candidate(candidate)
    current_policy = _validated_policy(policy or load_study_role_policy())
    matches = [
        (index, rule)
        for index, rule in enumerate(current_policy.rules)
        if rule.matches(current_candidate)
    ]
    matches.sort(key=lambda item: (-item[1].priority, item[0]))
    matched_rule_ids = tuple(rule.rule_id for _, rule in matches)
    if matches:
        winning_rule = matches[0][1]
        role = winning_rule.role
        rationale = current_candidate.inclusion_rationale_zh or winning_rule.rationale_zh
    else:
        role = StudyRole.EXCLUDED
        rationale = "未命中适格研究角色规则，证据不足时默认排除。"
    return StudyRoleDecision(
        candidate=current_candidate,
        study_role=role,
        inclusion_rationale_zh=rationale,
        matched_rule_ids=matched_rule_ids,
        policy_id=current_policy.policy_id,
        policy_version=current_policy.version,
        evidence_version=current_candidate.evidence_version,
    )


def classify_study_role(
    candidate: StudyCandidate | Mapping[str, Any],
    *,
    policy: StudyRolePolicy | None = None,
) -> StudyRoleDecision:
    """``evaluate_study_role`` 的语义别名。"""

    return evaluate_study_role(candidate, policy=policy)


def derive_study_role(
    candidate: StudyCandidate | Mapping[str, Any],
    *,
    policy: StudyRolePolicy | None = None,
) -> StudyRoleDecision:
    """``evaluate_study_role`` 的语义别名。"""

    return evaluate_study_role(candidate, policy=policy)


__all__ = [
    "DecisionDomain",
    "DevelopmentContext",
    "IndicationRelation",
    "ProblemDomain",
    "ReportKind",
    "StudyCandidate",
    "StudyDesignCategory",
    "StudyEvidenceType",
    "StudyPhase",
    "StudyRole",
    "StudyRoleCandidate",
    "StudyRoleDecision",
    "StudyRolePolicy",
    "StudyRolePolicyError",
    "StudyRolePolicySpec",
    "StudyRoleResult",
    "StudyRoleRule",
    "classify_study_role",
    "derive_study_role",
    "evaluate_study_role",
    "load_study_role_policy",
]
