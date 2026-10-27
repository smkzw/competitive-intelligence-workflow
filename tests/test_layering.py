"""分层依赖守卫：只能从上往下依赖（见 docs/ARCHITECTURE.md §2）。"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "ciw"
ORDER = [
    "config",
    "models",
    "store",
    "http",
    "sources",
    "extract",
    "normalize",
    "verify",
    "analyze",
    "release",
    "render",
    "pipeline",
    "api",
    "cli",
]
# 允许的跨层例外：extract 需要 normalize 的确定性判定；sources/captures 需要 verify 做交叉核对
ALLOWED = {("extract", "normalize"), ("sources", "normalize"), ("sources", "verify"), ("sources", "extract")}


def _layer(mod: str) -> str | None:
    parts = mod.split(".")
    return parts[1] if len(parts) > 1 and parts[0] == "ciw" and parts[1] in ORDER else None


def test_no_upward_imports():
    bad = []
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC).with_suffix("")
        me = rel.parts[0]
        if me not in ORDER:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                other = _layer(node.module)
                if other and other != me and ORDER.index(other) > ORDER.index(me) and (me, other) not in ALLOWED:
                    bad.append(f"{rel} → {node.module}")
    assert not bad, bad


def test_render_has_no_science():
    """渲染层只投影：不得出现翻译表、角色推断或数值计算关键词。"""
    text = "".join(p.read_text(encoding="utf-8") for p in (SRC / "render").rglob("*.js") if p.name != "echarts.min.js")
    for forbidden in ('indexOf("treat")', 'indexOf("ctrl")', "translate(", "_zh(", 'placebo")'):
        assert forbidden not in text
