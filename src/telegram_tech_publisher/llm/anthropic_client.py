"""AnthropicLLMDrafterClient — only file in the repo that imports `anthropic`."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from anthropic import AsyncAnthropic

from telegram_tech_publisher.llm.client import Draft, Example

if TYPE_CHECKING:
    from telegram_tech_publisher.sources.base import Candidate


class AnthropicLLMDrafterClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> None:
        resolved = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        if not resolved:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = AsyncAnthropic(api_key=resolved)

    def _build_request(
        self,
        voice_block: str,
        examples: list[Example],
        candidate: Candidate,
    ) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": [
                {
                    "type": "text",
                    "text": voice_block,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": _format_examples_and_candidate(examples, candidate),
                }
            ],
        }

    async def draft(
        self,
        voice_block: str,
        examples: list[Example],
        candidate: Candidate,
    ) -> Draft:
        request = self._build_request(voice_block, examples, candidate)
        response = await self._client.messages.create(**request)
        return Draft(
            text=response.content[0].text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_read_tokens=getattr(response.usage, "cache_read_input_tokens", 0),
        )


def _format_examples_and_candidate(
    examples: list[Example],
    candidate: Candidate,
) -> str:
    blocks = []
    for i, ex in enumerate(examples, start=1):
        blocks.append(
            f"Past post {i}:\n"
            f"  source title: {ex.input_title}\n"
            f"  source body: {ex.input_body}\n"
            f"  published post: {ex.output_text}\n"
        )
    blocks.append(
        f"Draft a Telegram post for:\n"
        f"  title: {candidate.title}\n"
        f"  body: {candidate.body}\n"
    )
    return "\n".join(blocks)
