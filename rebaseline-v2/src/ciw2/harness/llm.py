"""OpenAI 兼容的 Chat Completions 客户端（支持 tools / function calling）。

任何兼容 /chat/completions 的服务都可用：DeepSeek、智谱 GLM、通义 Qwen、Moonshot、OpenAI。
测试使用 ScriptedLLM，不访问网络。
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMReply:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def as_message(self) -> dict[str, Any]:
        msg: dict[str, Any] = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            msg["tool_calls"] = [
                {"id": c.id, "type": "function",
                 "function": {"name": c.name, "arguments": json.dumps(c.arguments, ensure_ascii=False)}}
                for c in self.tool_calls
            ]
        return msg


class LLM(Protocol):
    model: str

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMReply: ...


class LLMError(RuntimeError):
    pass


class OpenAICompatLLM:
    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: float = 120.0,
                 max_retries: int = 3, temperature: float = 0.1) -> None:
        if not api_key:
            raise LLMError("未配置 CIW_LLM_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self._client = httpx.Client(timeout=timeout_s, headers={"Authorization": f"Bearer {api_key}"})

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMReply:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": self.temperature}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        last: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                r = self._client.post(f"{self.base_url}/chat/completions", json=body)
                if r.status_code in (429, 500, 502, 503, 504):
                    raise LLMError(f"HTTP {r.status_code}: {r.text[:200]}")
                r.raise_for_status()
                return _parse_reply(r.json())
            except (httpx.HTTPError, LLMError) as exc:
                last = exc
                time.sleep(2 ** attempt)
        raise LLMError(f"LLM 调用失败：{last}")


def _parse_reply(data: dict[str, Any]) -> LLMReply:
    msg = data["choices"][0]["message"]
    calls = []
    for c in msg.get("tool_calls") or []:
        raw_args = c["function"].get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            args = {"__invalid_json__": raw_args}
        calls.append(ToolCall(id=c.get("id") or f"call_{len(calls)}", name=c["function"]["name"], arguments=args))
    return LLMReply(content=msg.get("content") or "", tool_calls=calls, raw=data)


class ScriptedLLM:
    """测试用：按顺序返回预置回复；也可传入函数根据 messages 动态生成。"""

    model = "scripted"

    def __init__(self, script: list[LLMReply] | Callable[[list[dict[str, Any]]], LLMReply]) -> None:
        self.script = script
        self.calls: list[list[dict[str, Any]]] = []

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMReply:
        self.calls.append(list(messages))
        if callable(self.script):
            return self.script(messages)
        if not self.script:
            raise LLMError("ScriptedLLM 脚本已用完")
        return self.script.pop(0)
