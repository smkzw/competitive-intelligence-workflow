"""微信公众号搜索适配器（外部 Skill/命令）。
约定：CIW_WECHAT_SEARCH_CMD 指向一个命令，调用方式 `<cmd> "<query>"`，stdout 输出 JSON 数组：
[{"title":..., "url":..., "account":..., "date":..., "content": "正文（可选）"}]
平台只把它当「线索来源」：公众号内容可以发现候选药物/进展，但 critical 字段仍需权威来源原文核验。
"""
from __future__ import annotations

import json
import shlex
import subprocess
from typing import Any

from pydantic import BaseModel, Field

from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.sources.http import register_text


def run_cmd(cmd: str, query: str, timeout: float = 90) -> list[dict[str, Any]]:
    proc = subprocess.run([*shlex.split(cmd), query], capture_output=True, text=True, timeout=timeout,
                          check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"微信搜索命令失败（{proc.returncode}）：{proc.stderr[:300]}")
    data = json.loads(proc.stdout or "[]")
    if not isinstance(data, list):
        raise TypeError("微信搜索命令输出不是 JSON 数组")
    return data


class WechatArgs(BaseModel):
    query: str = Field(description="中文检索词，如 'PNH 补体 抑制剂 临床' 或企业名+管线")
    route_id: str = "china:wechat"


@REGISTRY.register("wechat_search", "搜索微信公众号文章（中国企业管线、学术会议报道、获批新闻）。仅作线索来源。", WechatArgs)
def _wechat(ctx: ToolContext, a: WechatArgs) -> Any:
    cmd = getattr(ctx.settings, "wechat_search_cmd", "")
    if not cmd:
        if ctx.db and ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, a.route_id, "china", a.query, "blocked", note="未配置 CIW_WECHAT_SEARCH_CMD")
        return {"status": "blocked", "error": "未配置微信公众号搜索"}
    try:
        rows = run_cmd(cmd, a.query)
    except Exception as exc:
        if ctx.db and ctx.run_id:
            ctx.db.log_coverage(ctx.run_id, a.route_id, "china", a.query, "failed", note=str(exc)[:300])
        raise
    out = []
    for r in rows[:20]:
        sid = None
        if r.get("content") and r.get("url"):
            sid = register_text(ctx, kind="wechat", url=r["url"], text=r["content"], title=r.get("title", ""),
                                meta={"account": r.get("account"), "date": r.get("date")})
        out.append({"title": r.get("title"), "url": r.get("url"), "account": r.get("account"),
                    "date": r.get("date"), "source_id": sid, "excerpt": (r.get("content") or "")[:600]})
    if ctx.db and ctx.run_id:
        ctx.db.log_coverage(ctx.run_id, a.route_id, "china", a.query, "ok", hits=len(out))
    return {"count": len(out), "articles": out}
