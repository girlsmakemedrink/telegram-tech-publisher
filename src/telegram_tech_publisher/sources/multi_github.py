"""Fan-out wrapper over per-repo GitHubReleasesSource instances."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from telegram_tech_publisher.sources.github_releases import GitHubReleasesSource

if TYPE_CHECKING:
    from telegram_tech_publisher.sources.base import Candidate

log = logging.getLogger(__name__)


class MultiGitHubSource:
    name = "github_releases"

    def __init__(self, repos: list[str], token: str) -> None:
        if not repos:
            raise ValueError("MultiGitHubSource requires at least one repo")
        self._repos = list(repos)
        self._sources = [GitHubReleasesSource(repo=r, token=token) for r in repos]

    async def poll(self) -> list[Candidate]:
        results = await asyncio.gather(*(s.poll() for s in self._sources), return_exceptions=True)
        aggregated: list[Candidate] = []
        seen: set[tuple[str, str]] = set()
        failures: list[BaseException] = []
        for repo, result in zip(self._repos, results, strict=True):
            if isinstance(result, BaseException):
                failures.append(result)
                log.warning(
                    "poll.repo_failed",
                    extra={
                        "repo": repo,
                        "error_type": type(result).__name__,
                        "error": str(result),
                    },
                )
                continue
            for c in result:
                key = (c.source, c.external_id)
                if key in seen:
                    continue
                seen.add(key)
                aggregated.append(c)
        # If every repo failed, re-raise the first error so the tick records `failed`
        # (and the retry layer can decide whether the error type is transient).
        if failures and len(failures) == len(self._sources):
            raise failures[0]
        return aggregated
