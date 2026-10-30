"""Assemble one streamed chat completion. Transport, retry, and cache stay outside."""

import json


def assemble_sse(text: str) -> dict:
    """Join delta.content for choice 0. Reasoning text is ignored and not returned."""
    content, identity = [], {}
    finish = usage = None
    done = False
    for payload in _payloads(text):
        if done:
            _fail()
        if payload == "[DONE]":
            done = True
            continue
        event = _object(payload)
        if "error" in event:
            _fail(event.get("error"))
        _identity(identity, event)
        usage = _usage(usage, event)
        if "choices" in event:
            finish = _choice(content, finish, event.get("choices"))
        elif "usage" not in event:
            _fail()
    if not done or finish is None:
        _fail()
    return {
        "id": identity.get("id"),
        "model": identity.get("model"),
        "choices": [{"index": 0, "finish_reason": finish, "message": {"content": "".join(content)}}],
        "usage": usage,
        "reasoning_effort": identity.get("reasoning_effort"),
        "response_transport": "sse",
    }


def completion_from_json(data):
    """Accept one already-received JSON completion. Never describes its private body."""
    choices = data.get("choices") if isinstance(data, dict) else None
    choice = choices[0] if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict) else None
    message = choice.get("message") if choice else None
    if (not isinstance(message, dict) or not isinstance(message.get("content"), str)
            or choice.get("index", 0) != 0 or choice.get("finish_reason") not in ("stop", "length")
            or "error" in data):
        error = data.get("error", data.get("detail")) if isinstance(data, dict) else None
        _fail(error)
    return {**data, "response_transport": "json"}


def _payloads(text: str):
    data = []
    for line in text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            value = line[5:]
            data.append(value[1:] if value.startswith(" ") else value)
            continue
        if line == "":
            if data:
                yield "\n".join(data)
                data = []
            continue
        if line.split(":", 1)[0] not in {"event", "id", "retry"}:
            _fail()
    if data:
        _fail()


def _object(payload: str) -> dict:
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        _fail()
    if not isinstance(event, dict):
        _fail()
    return event


def _identity(identity, event):
    for field in ("id", "model", "reasoning_effort"):
        value = event.get(field)
        if value is not None and identity.setdefault(field, value) != value:
            _fail()


def _usage(current, event):
    if "usage" not in event or event["usage"] is None:
        return current
    if not isinstance(event["usage"], dict):
        _fail()
    return event["usage"]


def _choice(content, finish, choices):
    if choices == [] or choices is None:
        return finish
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        _fail()
    choice = choices[0]
    if choice.get("index", 0) != 0 or finish is not None:
        _fail()
    delta = choice.get("delta") or {}
    if not isinstance(delta, dict):
        _fail()
    piece = delta.get("content")
    if piece is not None:
        if not isinstance(piece, str):
            _fail()
        content.append(piece)
    reason = choice.get("finish_reason")
    if reason is None:
        return finish
    if reason not in ("stop", "length"):
        _fail()
    return reason


def _fail(error=None):
    exc = OSError("模型流式响应失败")
    if error is None:
        exc.rejection_kind = "unclassified"
    else:
        from ciw.verify.transport import rejection_kind
        exc.rejection_kind = rejection_kind(error)
    raise exc
