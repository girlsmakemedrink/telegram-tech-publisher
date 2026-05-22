"""Deterministic stub matching LLMDrafterClient — for unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from telegram_tech_publisher.llm.client import Draft, Example

if TYPE_CHECKING:
    from telegram_tech_publisher.sources.base import Candidate


class MockLLMDrafterClient:
    def __init__(
        self,
        *,
        model: str = "mock",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> None:
        self._model = model
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._cache_read_tokens = cache_read_tokens

    async def draft(
        self,
        voice_block: str,
        examples: list[Example],
        candidate: Candidate,
    ) -> Draft:
        return Draft(
            text=(
                f"[{candidate.title}] (mock draft, "
                f"voice_len={len(voice_block)}, n_examples={len(examples)})"
            ),
            model=self._model,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            cache_read_tokens=self._cache_read_tokens,
        )
