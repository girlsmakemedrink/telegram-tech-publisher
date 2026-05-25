"""Tests for the voice markdown loader/parser."""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from telegram_tech_publisher.llm.voice import VoiceLoadError, load_voice

if TYPE_CHECKING:
    from pathlib import Path


def _write_voice(tmp_path: Path, body: str, slug: str = "test") -> Path:
    p = tmp_path / f"{slug}.md"
    p.write_text(dedent(body).lstrip())
    return p


def test_loads_tone_and_examples(tmp_path: Path) -> None:
    p = _write_voice(
        tmp_path,
        """
        ---
        # tone description
        ---
        Voice: terse, code-literate.
        Length: 400-800 chars.
        ---
        # few-shot examples
        ---
        input_title: httpx 0.28 released
        input_body: Adds HTTP/3 support.
        output_text: httpx 0.28 ships HTTP/3.
        ---
        input_title: Terraform 1.10
        input_body: New providers.
        output_text: TF 1.10 adds providers.
        """,
        slug="example",
    )
    voice = load_voice(p)
    assert "terse" in voice.voice_block
    assert len(voice.examples) == 2
    assert voice.examples[0].input_title == "httpx 0.28 released"
    assert voice.examples[0].output_text == "httpx 0.28 ships HTTP/3."


def test_rejects_missing_examples(tmp_path: Path) -> None:
    p = _write_voice(
        tmp_path,
        """
        ---
        # tone description
        ---
        Voice only, no examples.
        """,
    )
    with pytest.raises(VoiceLoadError, match="examples"):
        load_voice(p)


def test_rejects_malformed_example(tmp_path: Path) -> None:
    p = _write_voice(
        tmp_path,
        """
        ---
        tone
        ---
        ---
        input_title: missing other fields
        ---
        """,
    )
    with pytest.raises(VoiceLoadError, match="example"):
        load_voice(p)
