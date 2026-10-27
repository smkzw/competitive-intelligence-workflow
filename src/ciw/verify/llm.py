"""模型后端：OpenAI 兼容 chat/completions；按 (模型, prompt) 缓存在工作区 SQLite。

key 只从环境变量或 key 文件路径读取，不写日志、不进 release。测试使用 FakeBackend。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Protocol

import yaml

from ciw.store import Workspace, now_iso


class Backend(Protocol):
    family: str
    model: str

    def chat(self, system: str, user: str) -> str: ...


@dataclass
class OpenAICompatBackend:
    family: str
    model: str
    base_url: str
    api_key: str | None
    timeout: float = 600
    no_proxy: bool = True
    max_tokens: int = 8192

    def chat(self, system: str, user: str) -> str:
        body = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
        )
        handlers = [urllib.request.ProxyHandler({})] if self.no_proxy else []
        with urllib.request.build_opener(*handlers).open(req, timeout=self.timeout) as resp:
            data = json.load(resp)
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("模型返回为空（无 choices）")
        return choices[0].get("message", {}).get("content") or ""


@dataclass
class FakeBackend:
    """离线测试用：responder(system, user) -> JSON 字符串。"""

    family: str
    model: str
    responder: Callable[[str, str], str]

    def chat(self, system: str, user: str) -> str:
        return self.responder(system, user)


class CachedBackend:
    def __init__(self, inner: Backend, ws: Workspace):
        self.inner, self.ws = inner, ws
        self.family, self.model = inner.family, inner.model

    def chat(self, system: str, user: str) -> str:
        prompt_sha = hashlib.sha256((system + "\x00" + user).encode()).hexdigest()
        key = hashlib.sha256(f"{self.family}|{self.model}|{prompt_sha}".encode()).hexdigest()
        with self.ws.db() as con:
            row = con.execute("SELECT response FROM llm_cache WHERE cache_key=?", (key,)).fetchone()
        if row:
            return row[0]
        text = self.inner.chat(system, user)
        with self.ws.db() as con:
            con.execute(
                "INSERT OR REPLACE INTO llm_cache VALUES (?,?,?,?,?,?)",
                (key, self.model, self.family, prompt_sha, text, now_iso()),
            )
        return text


def _read_key(spec: dict[str, Any]) -> str | None:
    for name in spec.get("key_env", []):
        if os.environ.get(name):
            return os.environ[name]
    files = [os.environ[n] for n in spec.get("key_file_env", []) if os.environ.get(n)]
    if spec.get("default_key_file"):
        files.append(spec["default_key_file"])
    for f in files:
        path = Path(f).expanduser()
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    return None


def load_roles(config_path: str | Path | None = None) -> dict[str, Backend]:
    """读取 config/llm.yaml，返回 {role: backend}；校验三个角色来自三个不同家族。"""
    text = (
        Path(config_path).read_text(encoding="utf-8")
        if config_path
        else resources.files("ciw").joinpath("data/llm.yaml").read_text(encoding="utf-8")
    )
    cfg = yaml.safe_load(text)
    roles: dict[str, Backend] = {}
    for role, spec in cfg["roles"].items():
        ep = cfg["endpoints"][spec["endpoint"]]
        roles[role] = OpenAICompatBackend(
            family=spec["family"],
            model=spec["model"],
            base_url=ep["base_url"],
            api_key=_read_key(ep),
            no_proxy=ep.get("no_proxy", True),
            max_tokens=spec.get("max_tokens", 8192),
        )
    check_heterogeneous(roles)
    return roles


def check_heterogeneous(roles: dict[str, Backend]) -> None:
    need = {"extractor_a", "extractor_b", "arbiter"}
    if not need <= roles.keys():
        raise ValueError(f"模型角色缺失：{sorted(need - roles.keys())}")
    fams = {roles[r].family for r in need}
    if len(fams) != 3:
        raise ValueError("extractor_a / extractor_b / arbiter 必须来自三个不同模型家族")


def parse_json(text: str) -> Any:
    """容忍 ```json 围栏和前后空白；仍然解析失败就抛 ValueError。"""
    s = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", s, re.S)
    if m:
        s = m.group(1).strip()
    return json.loads(s)
