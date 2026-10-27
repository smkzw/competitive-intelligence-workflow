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
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError

import yaml

from ciw.store import Workspace, now_iso
from ciw.verify.transport import model_opener


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
    response_format: str | None = "json_object"
    receipt: dict[str, Any] = field(default_factory=dict, init=False)

    def chat(self, system: str, user: str) -> str:
        self.receipt = {}
        body = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if self.response_format:
            body["response_format"] = {"type": self.response_format}
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
        )
        transport = {}
        try:
            with model_opener(self.base_url, self.no_proxy, transport).open(req, timeout=self.timeout) as resp:
                data = json.load(resp)
        except HTTPError as exc:
            self.receipt = {"http_status": exc.code}
            try:
                error = json.load(exc).get("error", {})
                message = str(error.get("message", "")) if isinstance(error, dict) else ""
                for parameter in ("response_format", "temperature", "max_tokens", "reasoning_effort"):
                    if parameter in message:
                        self.receipt["provider_parameter"] = parameter
                        break
            except (ValueError, OSError, AttributeError):
                pass
            raise
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("模型返回为空（无 choices）")
        self.receipt = {
            **transport,
            "response_model": data.get("model"),
            "response_id": data.get("id"),
            "finish_reason": choices[0].get("finish_reason"),
            "usage": data.get("usage"),
            "response_format": self.response_format,
        }
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
        self.receipt: dict[str, Any] = {}

    def chat(self, system: str, user: str) -> str:
        prompt_sha = hashlib.sha256((system + "\x00" + user).encode()).hexdigest()
        key = hashlib.sha256(f"{self.family}|{self.model}|{prompt_sha}".encode()).hexdigest()
        with self.ws.db() as con:
            row = con.execute("SELECT response, metadata FROM llm_cache WHERE cache_key=?", (key,)).fetchone()
        if row:
            self.receipt = {**json.loads(row[1] or "{}"), "cached": True}
            return row[0]
        self.receipt = {}
        try:
            text = self.inner.chat(system, user)
        except (OSError, ValueError):
            self.receipt = dict(getattr(self.inner, "receipt", {}))
            raise
        self.receipt = {**getattr(self.inner, "receipt", {}), "cached": False}
        with self.ws.db() as con:
            con.execute(
                "INSERT OR REPLACE INTO llm_cache "
                "(cache_key,model,family,prompt_sha,response,created_at,metadata) VALUES (?,?,?,?,?,?,?)",
                (key, self.model, self.family, prompt_sha, text, now_iso(), json.dumps(self.receipt)),
            )
        return text


def _read_key(spec: dict[str, Any]) -> str | None:
    if (
        set(spec.get("key_env", [])) - {"CIW_DGX_API_KEY", "CMS_SMK_API_KEY"}
        or set(spec.get("key_file_env", [])) - {"CIW_DGX_KEY_FILE"}
        or spec.get("default_key_file")
    ):
        raise ValueError("凭据仅允许CIW_DGX_API_KEY、CIW_DGX_KEY_FILE或CMS_SMK_API_KEY")
    for name in spec.get("key_env", []):
        if os.environ.get(name):
            return os.environ[name]
    files = [os.environ[n] for n in spec.get("key_file_env", []) if os.environ.get(n)]
    for f in files:
        path = Path(f).expanduser()
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    return None


def load_roles(config_path: str | Path | None = None) -> dict[str, Backend]:
    """读取 config/llm.yaml，返回 {role: backend}；校验主抽取和核对来自两个不同家族。"""
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
            timeout=spec.get("timeout", 600),
            response_format=spec.get("response_format", "json_object"),
        )
    check_heterogeneous(roles)
    return roles


def check_heterogeneous(roles: dict[str, Backend]) -> None:
    need = {"extractor_a", "verifier"}
    if set(roles) != need:
        raise ValueError("模型角色必须且仅有extractor_a与verifier")
    if len({roles[r].family for r in need}) != 2:
        raise ValueError("主抽取与核对必须来自两个不同模型家族")


def parse_json(text: str) -> Any:
    """容忍 ```json 围栏和前后空白；仍然解析失败就抛 ValueError。"""
    s = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", s, re.S)
    if m:
        s = m.group(1).strip()
    return json.loads(s)
