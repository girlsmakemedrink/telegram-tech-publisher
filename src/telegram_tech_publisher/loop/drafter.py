"""Adapter: Candidate → Draft via LLMDrafterClient + a loaded Voice."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram_tech_publisher.llm.client import Draft, LLMDrafterClient
    from telegram_tech_publisher.llm.voice import Voice
    from telegram_tech_publisher.sources.base import Candidate


class Drafter:
    def __init__(self, client: LLMDrafterClient, voice: Voice) -> None:
        self._client = client
        self._voice = voice

    async def draft(self, candidate: Candidate) -> Draft:
        return await self._client.draft(
            voice_block=self._voice.voice_block,
            examples=list(self._voice.examples),
            candidate=candidate,
        )
