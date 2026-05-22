"""GitHub releases source: polls one repo's /releases endpoint."""

from datetime import datetime

import httpx

from telegram_tech_publisher.sources.base import Candidate


class GitHubReleasesSource:
    name = "github_releases"

    def __init__(self, repo: str, token: str) -> None:
        self._repo = repo
        self._token = token

    async def poll(self) -> list[Candidate]:
        url = f"https://api.github.com/repos/{self._repo}/releases"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=15.0)
            response.raise_for_status()
        return [
            Candidate(
                source=self.name,
                external_id=str(release["id"]),
                title=release["name"] or release.get("tag_name", "unnamed"),
                body=release.get("body") or "",
                url=release["html_url"],
                published_at=datetime.fromisoformat(release["published_at"].replace("Z", "+00:00")),
            )
            for release in response.json()
        ]
