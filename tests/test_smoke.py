"""Smoke test for the package entry point — `main` aliases the Click CLI."""

from click.testing import CliRunner

from telegram_tech_publisher import main


def test_main_is_the_click_cli() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "telegram-tech-publisher" in result.output.lower()
