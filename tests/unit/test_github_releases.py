"""GitHubReleasesSource: poll one repo's releases, return Candidates."""

import respx
from httpx import Response

from telegram_tech_publisher.sources.github_releases import GitHubReleasesSource


@respx.mock
async def test_poll_returns_candidates_for_repo() -> None:
    respx.get("https://api.github.com/repos/anthropics/anthropic-sdk-python/releases").mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": 12345,
                    "name": "v0.42.0",
                    "tag_name": "v0.42.0",
                    "body": "## What's Changed\n- Added X",
                    "html_url": "https://github.com/anthropics/anthropic-sdk-python/releases/tag/v0.42.0",
                    "published_at": "2026-05-22T10:00:00Z",
                },
            ],
        )
    )

    source = GitHubReleasesSource(
        repo="anthropics/anthropic-sdk-python",
        token="ghp_test_xxxxxxxxxxxxxxxx",
    )
    candidates = await source.poll()

    assert len(candidates) == 1
    assert candidates[0].source == "github_releases"
    assert candidates[0].external_id == "12345"
    assert candidates[0].title == "v0.42.0"
    assert "Added X" in candidates[0].body
    assert (
        str(candidates[0].url)
        == "https://github.com/anthropics/anthropic-sdk-python/releases/tag/v0.42.0"
    )


@respx.mock
async def test_poll_falls_back_to_tag_name_when_name_missing() -> None:
    respx.get("https://api.github.com/repos/foo/bar/releases").mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": 1,
                    "name": None,
                    "tag_name": "v1.0.0",
                    "body": "",
                    "html_url": "https://github.com/foo/bar/releases/tag/v1.0.0",
                    "published_at": "2026-05-22T00:00:00Z",
                },
            ],
        )
    )
    source = GitHubReleasesSource(repo="foo/bar", token="ghp_test_xxxxxxxxxxxxxxxx")
    candidates = await source.poll()
    assert candidates[0].title == "v1.0.0"


@respx.mock
async def test_poll_returns_empty_when_no_releases() -> None:
    respx.get("https://api.github.com/repos/empty/repo/releases").mock(
        return_value=Response(200, json=[])
    )
    source = GitHubReleasesSource(repo="empty/repo", token="ghp_test_xxxxxxxxxxxxxxxx")
    assert await source.poll() == []
