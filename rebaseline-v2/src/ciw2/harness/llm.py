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


class LLMIdentityError(LLMError):
    pass


class LLMProtocolError(LLMError):
    def __init__(self, message: str, metadata: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.metadata = metadata or {}


class OpenAICompatLLM:
    def __init__(self, base_url: str, api_key: str, model: str, timeout_s: float = 120.0,
                 max_retries: int = 3, temperature: float = 0.1, max_output_tokens: int = 8192) -> None:
        if not api_key:
            raise LLMError("未配置 CIW_LLM_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.max_output_tokens = max_output_tokens
        self._client = httpx.Client(timeout=timeout_s, headers={"Authorization": f"Bearer {api_key}"})

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMReply:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": self.temperature,
                                'max_tokens': self.max_output_tokens}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = ({'type': 'function', 'function': {'name': 'submit_result'}}
                                   if len(tools) == 1 and tools[0]['function']['name'] == 'submit_result'
                                   else 'auto')
        last: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                r = self._client.post(f"{self.base_url}/chat/completions", json=body)
                if r.status_code in (429, 500, 502, 503, 504):
                    raise LLMError(f"HTTP {r.status_code}")
                r.raise_for_status()
                try:
                    data = r.json()
                except ValueError as exc:
                    raise LLMProtocolError('模型服务未返回有效JSON') from exc
                reply = _parse_reply(data)
                actual = str(reply.raw.get('model') or '').casefold().rsplit('/', 1)[-1]
                requested = self.model.casefold().rsplit('/', 1)[-1]
                matches = actual.startswith(requested) if requested in {'deepseek', 'qwen'} else actual == requested
                if not actual or not matches:
                    raise LLMIdentityError('实际响应模型身份缺失或与指定模型不一致')
                required = isinstance(body.get('tool_choice'), dict)
                valid_submit = len(reply.tool_calls) == 1 and reply.tool_calls[0].name == 'submit_result' and (
                    isinstance(reply.tool_calls[0].arguments, dict) and '__invalid_json__' not in reply.tool_calls[0].arguments)
                if (not reply.content.strip() and not reply.tool_calls) or (required and not valid_submit):
                    usage = data.get('usage') if isinstance(data.get('usage'), dict) else {}
                    raise LLMProtocolError('模型未返回可用正文或所要求的结构化提交', {
                        'actual_model': reply.raw['model'], 'finish_reason': data['choices'][0].get('finish_reason'),
                        'usage': {key: value for key, value in usage.items()
                                  if key in {'prompt_tokens', 'completion_tokens', 'total_tokens'} and isinstance(value, int)}})
                return reply
            except (LLMIdentityError, LLMProtocolError):
                raise
            except (httpx.HTTPError, LLMError) as exc:
                last = exc
                if attempt + 1 < self.max_retries:
                    time.sleep(2 ** attempt)
        reason = str(last) if isinstance(last, LLMError) else type(last).__name__
        if isinstance(last, httpx.HTTPStatusError):
            reason = f'HTTP {last.response.status_code}'
        raise LLMError(f"LLM 调用失败：{reason}")


def _parse_reply(data: dict[str, Any]) -> LLMReply:
    try:
        msg = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMProtocolError('模型响应缺少choices/message') from exc
    if not isinstance(msg, dict) or (msg.get('content') is not None and not isinstance(msg['content'], str)):
        raise LLMProtocolError('模型正文结构不兼容')
    raw_calls = msg.get('tool_calls') or []
    if not isinstance(raw_calls, list):
        raise LLMProtocolError('模型工具调用结构不兼容')
    calls = []
    for c in raw_calls:
        if not isinstance(c, dict) or not isinstance(c.get('function'), dict) or not isinstance(c['function'].get('name'), str):
            raise LLMProtocolError('模型工具调用缺少函数名')
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
