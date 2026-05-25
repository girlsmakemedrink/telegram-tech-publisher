"""Voice loader: parses `<slug>.md` files into a tone block + few-shot examples."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from telegram_tech_publisher.llm.client import Example

if TYPE_CHECKING:
    from pathlib import Path


class VoiceLoadError(ValueError):
    pass


@dataclass(frozen=True)
class Voice:
    voice_block: str
    examples: list[Example]


_SEPARATOR_RE = re.compile(r"^---\s*$", re.MULTILINE)
_FIELD_RE = re.compile(
    r"^input_title:\s*(?P<title>.+?)\s*\n"
    r"input_body:\s*(?P<body>.+?)\s*\n"
    r"output_text:\s*(?P<output>.+?)\s*$",
    re.DOTALL | re.MULTILINE,
)


def load_voice(path: Path) -> Voice:
    if not path.exists():
        raise VoiceLoadError(f"voice file not found: {path}")

    text = path.read_text(encoding="utf-8")
    blocks = [b.strip() for b in _SEPARATOR_RE.split(text) if b.strip()]
    if len(blocks) < 2:
        raise VoiceLoadError(
            f"voice file {path} must contain at least one tone block and one examples block"
        )

    non_heading_blocks = [b for b in blocks if not b.startswith("#")]
    if len(non_heading_blocks) < 2:
        raise VoiceLoadError(
            f"voice file {path} must contain a tone body and at least one example body"
        )

    voice_block = non_heading_blocks[0]

    examples: list[Example] = []
    for chunk in non_heading_blocks[1:]:
        m = _FIELD_RE.search(chunk)
        if not m:
            raise VoiceLoadError(
                f"voice file {path}: malformed example chunk "
                f"(need input_title / input_body / output_text):\n{chunk}"
            )
        examples.append(
            Example(
                input_title=m.group("title").strip(),
                input_body=m.group("body").strip(),
                output_text=m.group("output").strip(),
            )
        )
    if not examples:
        raise VoiceLoadError(f"voice file {path} has no parsable examples")

    return Voice(voice_block=voice_block, examples=examples)
