"""Skill 输入输出的类型合同。LLM 只能通过 submit_result 提交这些模型，Python 负责校验。"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

Region = Literal["china", "global"]
Phase = Literal["preclinical", "phase1", "phase1_2", "phase2", "phase2_3", "phase3", "nda_bla",
                "approved", "phase4", "unknown"]
StatType = Literal[
    "count_participants",   # 发生事件的受试者人数
    "count_events",         # 事件次数（不可除以人数当比例）
    "proportion",           # 受试者比例 (%)
    "mean", "median", "ls_mean", "ls_mean_change", "mean_change", "percent_change",
    "geometric_mean", "geometric_ls_mean",
    "hazard_ratio", "odds_ratio", "risk_difference", "rate_per_patient_year",
    "number",               # 来源仅给出数值，统计形式未知
    "text",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IntakeResult(Strict):
    indication: str = Field(description="标准中文适应症名")
    indication_en: str
    aliases: list[str] = Field(default_factory=list, description="中英文同义词、缩写、ICD 相关名")
    reports: list[Literal["A", "B", "C"]]
    focus: str = Field(default="", description="用户关注点（原话归纳）")
    cutoff_date: str | None = None
    needs_user_choice: bool = Field(default=False, description="报告类型确实无法判断时为 true")
    question_to_user: str | None = None


class DrugCandidate(Strict):
    name: str = Field(description="来源正式药名、INN或研发代号；仅中文或复合名完整保留，不强造英文或只取首项")
    name_zh: str | None = Field(default=None, description="已核实的正式中文名；未核实留空，禁止音译猜测")
    aliases: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    modality: str | None = None
    companies: list[str] = Field(default_factory=list, description="研发/权益方，原法律实体名")
    china_mah: str | None = None
    china_mah_group: str | None = None
    highest_phase_global: Phase = "unknown"
    highest_phase_china: Phase = "unknown"
    innovative: bool | None = Field(default=None, description=(
        "有具体产品的正向创新/原研来源时为true，明确仿制/生物类似时为false，未知为null；"
        "不能由非类似、在研或临床期别反推。独立临床开发的改良剂型仍须保留及记录来源"))
    evidence_urls: list[str] = Field(default_factory=list)
    route_id: str = Field(description="发现该候选的检索路线")


class UniverseResult(Strict):
    region: Region
    candidates: list[DrugCandidate]
    routes_run: list[str]
    routes_failed: list[str] = Field(default_factory=list)
    expansion_queries: list[str] = Field(default_factory=list, description="反向扩展（靶点/企业/别名）用过的查询")
    notes: str = ""


class ScopeDecision(Strict):
    entity_id: str | None = Field(default=None, description='当前候选ID；与药物原名或已知别名一致')
    drug: str
    in_scope: bool | None
    reason: str


class ScopeResult(Strict):
    decisions: list[ScopeDecision]


class SourceContext(Strict):
    legal_entity: str | None = None
    relationship: str | None = None
    as_of: str | None = None
    jurisdiction: str | None = None
    indication: str | None = None


class ExtractedFact(Strict):
    entity: str = Field(description="实体名：NCT 号 / 药物名 / 公司名")
    field: str = Field(description="字段路径，例如 result.primary.value、design.primary_endpoint")
    value: Any
    endpoint: str | None = Field(default=None, description="终点/指标的来源原文名称（结果类事实必填）")
    unit: str | None = None
    stat_type: StatType | None = None
    arm: str | None = Field(default=None, description="来源中的组/臂原名，不得改写")
    timepoint: str | None = None
    population: str | None = Field(default=None, description="分析人群原文")
    denominator: int | None = Field(default=None, description="仅当来源明确给出该组分析 N 时填写")
    enrollment_type: Literal['ESTIMATED', 'ACTUAL'] | None = Field(
        default=None, description='样本量为计划还是实际入组；仅照录来源明确含义，不由数值猜测')
    source_url: str
    source_id: str | None = Field(default=None, description='实际读取的精确来源版本ID；同一URL含多个研究/版本时必须指定，不得编造')
    quote: str = Field(description="来源原文中逐字复制的支持片段（≤400 字）")
    supersedes: str | None = Field(default=None, description='明确取代的既有事实 ID；无依据时留空')
    source_context: SourceContext | None = Field(default=None,
        description='药物身份/集团/开发状态的原文范围；法律实体、关系、截至日期、辖区和适应症不得猜测')

    @model_serializer(mode='wrap')
    def _source_presence(self, handler: Any) -> dict[str, Any]:
        data=handler(self)
        # Legacy omitted ID is not an explicit failed source binding. Preserve
        # presence so verification never borrows a source for an explicit null.
        if 'source_id' not in self.model_fields_set:
            data.pop('source_id',None)
        return data


class ExtractionResult(Strict):
    facts: list[ExtractedFact]
    gaps: list[str] = Field(default_factory=list, description="应有但来源中找不到的信息")


class Finding(Strict):
    title: str = Field(description="中文临床问题式标题；内部事实编号只放fact_refs，不写入正文")
    bullets: list[str]
    fact_refs: list[str] = Field(min_length=1)

    @model_validator(mode='after')
    def _no_internal_reference_in_narrative(self) -> Finding:
        marker = r'(?<![A-Za-z0-9_])(?:fct_[0-9a-f]{12}|summary_ref_[0-9]+)(?![A-Za-z0-9_])'
        if any(re.search(marker, text) for text in (self.title, *self.bullets)):
            raise ValueError('内部事实编号应只放在fact_refs，不进入摘要标题或正文')
        return self


class AnalysisResult(Strict):
    report: Literal["A", "B", "C"]
    findings: list[Finding] = Field(max_length=6)
