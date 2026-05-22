"""Click CLI for smoke commands."""

import asyncio

import click
from rich.console import Console
from telegram import Bot

from telegram_tech_publisher.config import Settings
from telegram_tech_publisher.publishers.telegram import TelegramPublisher
from telegram_tech_publisher.sources.github_releases import GitHubReleasesSource

console = Console()


@click.group()
def cli() -> None:
    """telegram-tech-publisher smoke commands."""


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


if __name__ == "__main__":
    cli()
