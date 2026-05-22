"""TelegramPublisher: send a message to a channel with MarkdownV2 escaping."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram_tech_publisher.publishers.telegram import TelegramPublisher, escape_markdown_v2


def test_escape_markdown_v2_escapes_all_specials() -> None:
    raw = "Hello *world*! (test) [link] _under_"
    escaped = escape_markdown_v2(raw)
    assert escaped == r"Hello \*world\*\! \(test\) \[link\] \_under\_"


def test_escape_markdown_v2_passthrough_when_no_specials() -> None:
    assert escape_markdown_v2("Hello world") == "Hello world"


def test_escape_markdown_v2_empty_string() -> None:
    assert escape_markdown_v2("") == ""


def test_escape_markdown_v2_escapes_periods_in_urls() -> None:
    # Telegram MarkdownV2 requires escaping `.` even mid-URL.
    raw = "https://github.com/foo/bar"
    escaped = escape_markdown_v2(raw)
    assert escaped == r"https://github\.com/foo/bar"


@pytest.mark.asyncio
async def test_publisher_sends_to_configured_channel() -> None:
    fake_bot = MagicMock()
    fake_bot.send_message = AsyncMock(return_value=MagicMock(message_id=999))

    publisher = TelegramPublisher(bot=fake_bot, channel_id="@test_channel")
    msg_id = await publisher.send("iter-27 smoke")

    assert msg_id == 999
    fake_bot.send_message.assert_awaited_once_with(
        chat_id="@test_channel",
        text=r"iter\-27 smoke",
        parse_mode="MarkdownV2",
    )
