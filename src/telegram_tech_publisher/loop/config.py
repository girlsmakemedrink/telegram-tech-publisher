"""TOML-backed runtime config for the autonomous publishing loop."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

VOICE_DIR = Path(__file__).resolve().parent.parent / "llm" / "voice"

_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class LoopConfigError(ValueError):
    pass


@dataclass(frozen=True)
class LoopConfig:
    voice: str
    timezone: str
    schedule: list[str]
    github_repos: list[str]

    @classmethod
    def load(cls, path: Path) -> LoopConfig:
        try:
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        except FileNotFoundError as exc:
            raise LoopConfigError(f"loop config not found at {path}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise LoopConfigError(f"invalid TOML in {path}: {exc}") from exc

        voice = data.get("voice")
        if not isinstance(voice, str) or not voice:
            raise LoopConfigError("`voice` must be a non-empty string")
        voice_file = VOICE_DIR / f"{voice}.md"
        if not voice_file.exists():
            raise LoopConfigError(f"voice slug {voice!r} has no matching file at {voice_file}")

        timezone = data.get("timezone")
        if not isinstance(timezone, str) or not timezone:
            raise LoopConfigError("`timezone` must be a non-empty IANA tz string")

        schedule = data.get("schedule")
        if not isinstance(schedule, list) or not schedule:
            raise LoopConfigError("`schedule` must be a non-empty list of HH:MM strings")
        for entry in schedule:
            if not isinstance(entry, str) or not _HHMM_RE.match(entry):
                raise LoopConfigError(f"schedule entry {entry!r} is not a valid HH:MM (24h) string")

        sources = data.get("sources", {})
        github_repos_raw = sources.get("github_repos", [])
        if not isinstance(github_repos_raw, list) or not github_repos_raw:
            raise LoopConfigError("at least one [[sources.github_repos]] entry is required")
        repos: list[str] = []
        for item in github_repos_raw:
            if not isinstance(item, dict) or "repo" not in item:
                raise LoopConfigError(
                    "each [[sources.github_repos]] entry must have a `repo` field"
                )
            r = item["repo"]
            if not isinstance(r, str) or not _REPO_RE.match(r):
                raise LoopConfigError(f"repo {r!r} is not a valid owner/repo string")
            repos.append(r)

        return cls(voice=voice, timezone=timezone, schedule=list(schedule), github_repos=repos)
