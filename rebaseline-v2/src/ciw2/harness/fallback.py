"""Sequential user-configured routes, with explicit identity on every reply."""
from __future__ import annotations

from typing import Any

from ciw2.harness.llm import LLM, LLMError, LLMReply


class FallbackLLM:
    def __init__(self, routes: list[LLM]) -> None:
        if not routes:
            raise ValueError('At least one explicitly configured route is required')
        self.routes = routes
        self.index = 0
        self.failures: list[str] = []
        self.failure_details: list[dict[str, Any]] = []

    @property
    def model(self) -> str:
        return self.routes[self.index].model

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMReply:
        while self.index < len(self.routes):
            route = self.routes[self.index]
            try:
                reply = route.chat(messages, tools)
            except LLMError as exc:
                self.failures.append(route.model)
                self.failure_details.append({'requested_model': route.model, 'error_type': type(exc).__name__,
                                             **getattr(exc, 'metadata', {})})
                if self.index + 1 == len(self.routes):
                    raise
                self.index += 1
                continue
            reply.raw = {**reply.raw, '_ciw_route': {
                'index': self.index, 'model': route.model, 'previous_failures': list(self.failures),
                'failure_details': list(self.failure_details)}}
            return reply
        raise LLMError('All configured model routes are unavailable')
