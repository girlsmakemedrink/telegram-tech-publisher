"""Telegram Bot publisher (MarkdownV2)."""

import re

from telegram import Bot

_MD_V2_SPECIALS = re.compile(r"([_*\[\]()~`>#+\-=|{}.!])")


def escape_markdown_v2(text: str) -> str:
    return _MD_V2_SPECIALS.sub(r"\\\1", text)


class TelegramPublisher:
    def __init__(self, bot: Bot, channel_id: str) -> None:
        self._bot = bot
        self._channel_id = channel_id

    async def send(self, text: str) -> int:
        result = await self._bot.send_message(
            chat_id=self._channel_id,
            text=escape_markdown_v2(text),
            parse_mode="MarkdownV2",
        )
        return result.message_id
