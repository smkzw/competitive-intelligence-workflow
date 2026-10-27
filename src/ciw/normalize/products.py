"""干预 → 产品。只认配置里的别名（一对一）；不认识的创新干预单列为“未归类”，不静默丢弃。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ciw.config import IndicationConfig, normalize_name

_DOSE_TAIL = re.compile(r"\b\d+(\.\d+)?\s*(mg|µg|ug|mcg|ml|mg/kg|mg/ml)\b.*$", re.I)
_PREFIX = re.compile(r"^(drug|biological|other|combination product)\s*:\s*", re.I)


@dataclass
class ProductResolver:
    cfg: IndicationConfig
    _exact: dict[str, str] = field(default_factory=dict)
    _tokens: list[tuple[re.Pattern[str], str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        for p in self.cfg.products:
            for name in p.all_names():
                self._exact[normalize_name(name)] = p.id
                if len(normalize_name(name)) >= 3:
                    pat = re.compile(r"(?<![0-9a-z])" + re.escape(name.casefold()) + r"(?![0-9a-z])")
                    self._tokens.append((pat, p.id))
        self._tokens.sort(key=lambda t: -len(t[0].pattern))

    def resolve_intervention(self, name: str) -> str | None:
        """干预名 → product_id。先精确别名，再去掉剂量尾巴，再在名称中按词边界找别名。"""
        clean = _PREFIX.sub("", name).strip()
        for cand in (clean, _DOSE_TAIL.sub("", clean).strip()):
            pid = self._exact.get(normalize_name(cand))
            if pid:
                return pid
        if self.cfg.is_background(clean):
            return None
        return self.find_in_text(clean)

    def find_in_text(self, text: str) -> str | None:
        """在任意文本（例如结果组标题）里按词边界找唯一的产品别名；命中多个产品返回 None。"""
        low = text.casefold()
        hits = {pid for pat, pid in self._tokens if pat.search(low)}
        return hits.pop() if len(hits) == 1 else None

    def find_all_in_text(self, text: str) -> set[str]:
        low = text.casefold()
        return {pid for pat, pid in self._tokens if pat.search(low)}


def is_unclassified_candidate(cfg: IndicationConfig, name: str, itype: str, sponsor_class: str) -> bool:
    """企业申办的药物/生物制品干预，既不是已知产品也不是背景治疗：需要补进配置或判定排除。"""
    if itype not in ("DRUG", "BIOLOGICAL", "COMBINATION_PRODUCT"):
        return False
    clean = _PREFIX.sub("", name).strip()
    return sponsor_class == "INDUSTRY" and not cfg.is_background(clean)
