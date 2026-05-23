"""Tests for MultiGitHubSource fan-out + per-repo isolation."""

from __future__ import annotations

import httpx
import pytest
import respx

from telegram_tech_publisher.sources.multi_github import MultiGitHubSource


def _release_json(release_id: int, name: str, repo: str) -> dict[str, object]:
    return {
        "id": release_id,
        "name": name,
        "tag_name": f"v{release_id}",
        "body": "body",
        "html_url": f"https://github.com/{repo}/releases/tag/v{release_id}",
        "published_at": "2026-05-23T10:00:00Z",
    }


@respx.mock
@pytest.mark.asyncio
async def test_poll_aggregates_across_repos() -> None:
    respx.get("https://api.github.com/repos/a/x/releases").respond(
        200, json=[_release_json(1, "x-1", "a/x")]
    )
    respx.get("https://api.github.com/repos/b/y/releases").respond(
        200, json=[_release_json(2, "y-2", "b/y")]
    )

    src = MultiGitHubSource(repos=["a/x", "b/y"], token="ghp_test")
    candidates = await src.poll()

    titles = sorted(c.title for c in candidates)
    assert titles == ["x-1", "y-2"]


@respx.mock
@pytest.mark.asyncio
async def test_poll_dedupes_by_source_and_external_id() -> None:
    duplicate = _release_json(42, "dup", "a/x")
    respx.get("https://api.github.com/repos/a/x/releases").respond(200, json=[duplicate])
    respx.get("https://api.github.com/repos/b/y/releases").respond(200, json=[duplicate])

    src = MultiGitHubSource(repos=["a/x", "b/y"], token="ghp_test")
    candidates = await src.poll()

    assert len(candidates) == 1


@respx.mock
@pytest.mark.asyncio
async def test_one_repo_failure_does_not_kill_others() -> None:
    respx.get("https://api.github.com/repos/a/x/releases").respond(
        500, json={"message": "boom"}
    )
    respx.get("https://api.github.com/repos/b/y/releases").respond(
        200, json=[_release_json(7, "y-7", "b/y")]
    )

    src = MultiGitHubSource(repos=["a/x", "b/y"], token="ghp_test")
    candidates = await src.poll()

    assert [c.title for c in candidates] == ["y-7"]


@respx.mock
@pytest.mark.asyncio
async def test_all_repos_failing_returns_empty_list() -> None:
    respx.get("https://api.github.com/repos/a/x/releases").respond(500)
    respx.get("https://api.github.com/repos/b/y/releases").mock(
        side_effect=httpx.ConnectError("network down")
    )

    src = MultiGitHubSource(repos=["a/x", "b/y"], token="ghp_test")
    candidates = await src.poll()

    assert candidates == []
