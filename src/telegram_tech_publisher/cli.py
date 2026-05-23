"""Click CLI."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import click
from rich.console import Console
from rich.table import Table
from telegram import Bot

from telegram_tech_publisher.config import Settings
from telegram_tech_publisher.llm.anthropic_client import AnthropicLLMDrafterClient
from telegram_tech_publisher.llm.voice import load_voice
from telegram_tech_publisher.loop.config import VOICE_DIR, LoopConfig
from telegram_tech_publisher.loop.daemon import run_daemon
from telegram_tech_publisher.loop.drafter import Drafter
from telegram_tech_publisher.loop.logging import configure_logging
from telegram_tech_publisher.loop.state import StateStore
from telegram_tech_publisher.loop.tick import TickOutcome, TickResult, tick
from telegram_tech_publisher.publishers.telegram import TelegramPublisher
from telegram_tech_publisher.sources.github_releases import GitHubReleasesSource
from telegram_tech_publisher.sources.multi_github import MultiGitHubSource

console = Console()


@click.group()
def cli() -> None:
    """telegram-tech-publisher."""


# ----- existing smoke commands (kept for triage) -----


@cli.command("smoke-github")
@click.option("--repo", default="anthropics/anthropic-sdk-python", help="owner/repo to poll")
def smoke_github(repo: str) -> None:
    """Poll one repo's /releases and print candidates."""
    settings = Settings()  # type: ignore[call-arg]
    source = GitHubReleasesSource(repo=repo, token=settings.github_token)
    candidates = asyncio.run(source.poll())
    console.print(f"[bold]{len(candidates)}[/bold] candidates from {repo}:")
    for c in candidates[:5]:
        console.print(f"  {c.published_at:%Y-%m-%d} [cyan]{c.title}[/cyan] → {c.url}")


@cli.command("smoke-telegram")
def smoke_telegram() -> None:
    """Send one hardcoded message to the test channel."""
    settings = Settings()  # type: ignore[call-arg]
    bot = Bot(token=settings.telegram_bot_token)
    publisher = TelegramPublisher(bot=bot, channel_id=settings.telegram_test_channel_id)
    msg_id = asyncio.run(publisher.send("iter-27 smoke from telegram-tech-publisher"))
    console.print(f"[green]sent[/green] message_id={msg_id} to {settings.telegram_test_channel_id}")


# ----- loop commands -----


def _build_loop_components(
    *, dry_run: bool
) -> tuple[Settings, StateStore, MultiGitHubSource, Drafter, TelegramPublisher]:
    settings = Settings()  # type: ignore[call-arg]
    if not settings.anthropic_api_key and not dry_run:
        raise click.UsageError("ANTHROPIC_API_KEY is required for tick / validate / daemon")
    configure_logging(settings.state_dir, level=settings.log_level)

    loop_cfg = LoopConfig.load(settings.loop_config_path)
    voice = load_voice(VOICE_DIR / f"{loop_cfg.voice}.md")

    state = StateStore(settings.state_dir / "state.db")
    source = MultiGitHubSource(repos=loop_cfg.github_repos, token=settings.github_token)
    llm = AnthropicLLMDrafterClient(api_key=settings.anthropic_api_key or "dry-run")
    drafter = Drafter(client=llm, voice=voice)

    bot = Bot(token=settings.telegram_bot_token)
    publisher = TelegramPublisher(bot=bot, channel_id=settings.telegram_channel_id)
    return settings, state, source, drafter, publisher


@cli.command("tick")
def tick_cmd() -> None:
    """Run one tick of the autonomous loop synchronously."""
    settings, state, source, drafter, publisher = _build_loop_components(dry_run=False)
    result = asyncio.run(
        tick(
            source=source,
            state=state,
            drafter=drafter,
            publisher=publisher,
            channel_id=settings.telegram_channel_id,
        )
    )
    _print_tick_result(result)
    raise SystemExit(0 if result.outcome is not TickOutcome.FAILED else 1)


@cli.command("dry-run")
def dry_run_cmd() -> None:
    """Run one tick with publish skipped; prints the drafted text."""
    settings, state, source, drafter, publisher = _build_loop_components(dry_run=True)
    result = asyncio.run(
        tick(
            source=source,
            state=state,
            drafter=drafter,
            publisher=publisher,
            channel_id=settings.telegram_channel_id,
            dry_run=True,
        )
    )
    _print_tick_result(result)


@cli.command("status")
def status_cmd() -> None:
    """Print recent posts + failed ticks (last 24h)."""
    settings = Settings()  # type: ignore[call-arg]
    state = StateStore(settings.state_dir / "state.db")
    posts = state.recent_posts(limit=10)
    failed = state.failed_ticks(since=datetime.now(UTC) - timedelta(hours=24))

    if not posts:
        console.print("[dim]no posts recorded yet[/dim]")
    else:
        table = Table(title=f"Recent posts ({len(posts)})")
        table.add_column("when")
        table.add_column("source")
        table.add_column("title")
        table.add_column("channel")
        table.add_column("msg_id")
        for p in posts:
            table.add_row(
                p.published_at.strftime("%Y-%m-%d %H:%M"),
                p.source,
                p.candidate_title[:60],
                p.channel_id,
                str(p.message_id),
            )
        console.print(table)

    if failed:
        console.print(f"[red]{len(failed)} failed tick(s) in last 24h[/red]")
        for f in failed:
            console.print(f"  {f.started_at:%H:%M} {f.error}")
    else:
        console.print("[green]0 failed ticks in last 24h[/green]")


@cli.command("validate")
def validate_cmd() -> None:
    """One-shot end-to-end smoke into the configured channel. Exits non-zero on any failure."""
    settings, state, source, drafter, publisher = _build_loop_components(dry_run=False)
    result = asyncio.run(
        tick(
            source=source,
            state=state,
            drafter=drafter,
            publisher=publisher,
            channel_id=settings.telegram_channel_id,
        )
    )
    _print_tick_result(result)

    if result.outcome is TickOutcome.PUBLISHED and result.message_id is not None:
        url = _telegram_message_url(settings.telegram_channel_id, result.message_id)
        console.print(f"[bold green]channel URL:[/bold green] {url}")
        raise SystemExit(0)
    if result.outcome is TickOutcome.NOOP:
        console.print("[yellow]no fresh candidates — validate cannot complete[/yellow]")
        raise SystemExit(2)
    raise SystemExit(1)


def _telegram_message_url(channel_id: str, message_id: int) -> str:
    """Compose a viewable URL from chat_id + message_id."""
    if channel_id.startswith("@"):
        return f"https://t.me/{channel_id[1:]}/{message_id}"
    if channel_id.startswith("-100"):
        return f"https://t.me/c/{channel_id[4:]}/{message_id}"
    return f"chat_id={channel_id} message_id={message_id}"


@cli.command("daemon")
def daemon_cmd() -> None:
    """Run the autonomous publishing daemon. Blocks until SIGTERM/SIGINT."""
    settings, state, source, drafter, publisher = _build_loop_components(dry_run=False)
    loop_cfg = LoopConfig.load(settings.loop_config_path)

    async def _run_one_tick() -> None:
        await tick(
            source=source,
            state=state,
            drafter=drafter,
            publisher=publisher,
            channel_id=settings.telegram_channel_id,
        )

    asyncio.run(
        run_daemon(
            loop_cfg=loop_cfg,
            channel_id=settings.telegram_channel_id,
            tick_callable=_run_one_tick,
        )
    )


def _print_tick_result(result: TickResult) -> None:
    outcome_color = {
        TickOutcome.PUBLISHED: "green",
        TickOutcome.NOOP: "yellow",
        TickOutcome.FAILED: "red",
    }[result.outcome]
    console.print(
        f"[{outcome_color}]{result.outcome.value}[/{outcome_color}] "
        f"candidate={result.candidate_external_id} msg_id={result.message_id}"
    )
    if result.drafted_text:
        console.print("[bold]drafted text:[/bold]")
        console.print(result.drafted_text)
    if result.error:
        console.print(f"[red]error:[/red] {result.error}")


if __name__ == "__main__":
    cli()
