"""Sequential user-configured routes, with explicit identity on every reply."""
from __future__ import annotations

from collections.abc import Callable
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
        self._cancel_check: Callable[[], None] | None = None

    def set_cancel_check(self, check: Callable[[], None]) -> None:
        self._cancel_check = check

    @property
    def model(self) -> str:
        return self.routes[self.index].model

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> LLMReply:
        self.failure_details = []  # This call owns its evidence; old failures are not new attempts.
        while self.index < len(self.routes):
            if self._cancel_check is not None:
                self._cancel_check()  # Do not enter another configured route after a stop request.
            route = self.routes[self.index]
            try:
                reply = route.chat(messages, tools)
            except LLMError as exc:
                if route.model not in self.failures:
                    self.failures.append(route.model)
                self.failure_details.append({'requested_model': route.model, 'error_type': type(exc).__name__,
                                             'call_scope': 'current_chat',
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
