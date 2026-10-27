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
    indication: str = Field("", description="原文写明的适应症")
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
    endpoint: str = Field(description="原文终点名称")
    timepoint: str = Field("", description="原文时间点，例如 Week 24")
    stat_type: Literal[
        "ls_mean", "mean", "median", "proportion", "count", "difference", "hazard_ratio", "odds_ratio", "other"
    ]
    value: float
    ci_lower: float | None = None
    ci_upper: float | None = None
    n: int | None = Field(None, description="该组分析人数；原文没写留空，不要用总样本量代替")
