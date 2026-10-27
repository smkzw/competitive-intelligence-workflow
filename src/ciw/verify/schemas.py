"""交叉核对用的抽取结构。每个结构都有 quote；数值字段必须字面出现在 quote 里。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Item(BaseModel):
    model_config = ConfigDict(extra="ignore")
    quote: str = Field(description="原文逐字片段，必须支持本条的全部关键字段")


class EventItem(_Item):
    """公告/公众号/新闻稿中的产品里程碑。"""

    product_mention: str = Field(description="原文中出现的产品名或代号，原样照抄")
    event_type: Literal["approval", "filing", "topline", "phase_start", "licensing", "other"]
    region: str = Field("", description="中国/美国/欧盟/日本/全球 等；原文没写留空")
    date: str = Field("", description="事件日期 YYYY-MM-DD 或 YYYY-MM；原文没写留空，不用发布日期代替")
    event_date_quote: str = Field(
        "",
        description=(
            "明确将日期归属于实际事件动作的同一段连续原文；只有发稿日或‘某日宣布已获批’时，date与本字段均留空"
        ),
    )
    indication: str = Field("", description="原文写明的适应症，逐字照抄，不翻译、不扩展")
    detail: str = Field("", description="一句话概括，不加原文没有的信息")


class ProductAttrItem(_Item):
    """产品属性（靶点、分子类型、机制），来自登记干预描述或企业/监管原文。"""

    product_mention: str
    target: str = Field("", description="原文写明的靶点，例如 IL-4Rα、TSLP；没写留空")
    modality: str = Field("", description="原文写明的分子类型，例如 单克隆抗体、双特异性抗体、小分子；没写留空")
    mechanism: str = Field("", description="原文写明的作用机制；没写留空")


class PublicationResultItem(_Item):
    """论文/摘要中的结果数值（用于 CT.gov 未公布结果的试验）。"""

    arm_label: str = Field(description="原文中的组别名称")
    registry_id: str = Field(description="摘要明确写出的本条所属NCT或CTR号，不从搜索排序推断")
    endpoint: str = Field(description="原文终点名称")
    timepoint: str = Field("", description="原文时间点，例如 Week 24")
    population: str = Field("", description="原文分析人群限定；总体与亚组分开，未说明留空")
    unit: str = Field("", description="原文明确单位；不能从量表或数值猜单位")
    comparator_label: str = Field("", description="difference/ratio的对照组原名；其他统计量留空")
    contrast_direction: Literal["arm_minus_comparator", "unknown"] = Field(
        "unknown", description="仅原文明示试验组减对照组时填arm_minus_comparator；不由正负号猜方向"
    )
    base_stat_type: Literal["ls_mean", "mean", "median", "proportion", "other"] = Field(
        "other", description="difference对应的基础统计量，只按原文明确说明填写；单组数值忽略此字段"
    )
    outcome_type: Literal["PRIMARY", "SECONDARY", "OTHER_PRE_SPECIFIED"] = "OTHER_PRE_SPECIFIED"
    stat_type: Literal[
        "ls_mean", "mean", "median", "proportion", "count", "difference", "hazard_ratio", "odds_ratio", "other"
    ]
    value: float
    ci_lower: float | None = None
    ci_upper: float | None = None
    ci_pct: float | None = Field(None, description="来源明确的置信水平，如95；未写留空")
    n: int | None = Field(None, description="该组分析人数；原文没写留空，不要用总样本量代替")
