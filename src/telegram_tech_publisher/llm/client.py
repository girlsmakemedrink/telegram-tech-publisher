"""LLMDrafterClient Protocol + the Example/Draft DTOs. No SDK import here."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel

if TYPE_CHECKING:
    from telegram_tech_publisher.sources.base import Candidate


class Example(BaseModel):
    input_title: str
    input_body: str
    output_text: str


class Draft(BaseModel):
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int


class LLMDrafterClient(Protocol):
    async def draft(
        self,
        voice_block: str,
        examples: list[Example],
        candidate: Candidate,
    ) -> Draft: ...
