"""ClaudeCodeLLMDrafterClient — drafts via `claude -p` subprocess (no API key)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol

from telegram_tech_publisher.llm.client import Draft, Example

if TYPE_CHECKING:
    from telegram_tech_publisher.sources.base import Candidate


class ClaudeCodeError(RuntimeError):
    """Raised when the `claude` subprocess fails or returns empty output."""


class SubprocessRunner(Protocol):
    async def __call__(
        self, argv: list[str], stdin_text: str, timeout: float
    ) -> tuple[int, str, str]: ...


async def _default_runner(argv: list[str], stdin_text: str, timeout: float) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(stdin_text.encode("utf-8")), timeout=timeout
        )
    except TimeoutError:
        proc.kill()
        await proc.wait()
        raise ClaudeCodeError(f"claude subprocess timed out after {timeout}s") from None
    return proc.returncode or 0, stdout_bytes.decode("utf-8"), stderr_bytes.decode("utf-8")


class ClaudeCodeLLMDrafterClient:
    """Drafts Telegram posts by piping a prompt into `claude -p`.

    Uses the user's Claude Code subscription (OAuth) — no ANTHROPIC_API_KEY required.
    Token counts are not exposed by the CLI; they are reported as 0.
    """

    def __init__(
        self,
        *,
        binary: str = "claude",
        model_label: str = "claude-code-cli",
        timeout_seconds: float = 120.0,
        extra_args: list[str] | None = None,
        runner: SubprocessRunner | None = None,
    ) -> None:
        self._binary = binary
        self._model_label = model_label
        self._timeout = timeout_seconds
        self._extra_args = list(extra_args) if extra_args else []
        self._runner = runner or _default_runner

    async def draft(
        self,
        voice_block: str,
        examples: list[Example],
        candidate: Candidate,
    ) -> Draft:
        prompt = _build_prompt(voice_block, examples, candidate)
        argv = [self._binary, "-p", *self._extra_args]
        code, stdout, stderr = await self._runner(argv, prompt, self._timeout)
        if code != 0:
            raise ClaudeCodeError(f"claude exited {code}: {stderr.strip() or stdout.strip()}")
        text = stdout.strip()
        if not text:
            raise ClaudeCodeError(f"claude returned empty output (stderr={stderr.strip()!r})")
        return Draft(
            text=text,
            model=self._model_label,
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
        )


def _build_prompt(
    voice_block: str,
    examples: list[Example],
    candidate: Candidate,
) -> str:
    parts = [voice_block.strip(), ""]
    for i, ex in enumerate(examples, start=1):
        parts.append(
            f"Past post {i}:\n"
            f"  source title: {ex.input_title}\n"
            f"  source body: {ex.input_body}\n"
            f"  published post: {ex.output_text}\n"
        )
    parts.append(
        f"Draft a Telegram post for:\n  title: {candidate.title}\n  body: {candidate.body}\n"
    )
    parts.append("Output ONLY the post text. No preamble, no commentary, no surrounding quotes.")
    return "\n".join(parts)
