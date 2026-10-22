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

    @property
    def model(self) -> str:
        return self.routes[self.index].model

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMReply:
        while self.index < len(self.routes):
            route = self.routes[self.index]
            try:
                reply = route.chat(messages, tools)
            except LLMError:
                self.failures.append(route.model)
                if self.index + 1 == len(self.routes):
                    raise
                self.index += 1
                continue
            reply.raw = {**reply.raw, '_ciw_route': {
                'index': self.index, 'model': route.model, 'previous_failures': list(self.failures)}}
            return reply
        raise LLMError('All configured model routes are unavailable')
