# telegram-tech-publisher

AI content engine for Telegram developer channels. Curates from GitHub releases, drafts in the channel's voice (via the Claude Code CLI by default, or the Anthropic API), ships posts on a schedule.

**Status:** autonomous publishing loop (single channel) shipped 2026-05-23. PRD-MVP scheduler + multi-tenant + approval queue parked until iter-30+. See `docs/PRD.md` for product scope and `docs/superpowers/specs/2026-05-23-autonomous-publishing-loop-design.md` for the loop spec.

## Quickstart (dev)

```bash
make dev                                # uv sync + cp .env.example .env
# edit .env: add TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, GITHUB_TOKEN
# DRAFTER_BACKEND defaults to "claude_code" (uses the local `claude` CLI; no API key).
# Set DRAFTER_BACKEND=anthropic + ANTHROPIC_API_KEY to use api.anthropic.com instead.
make smoke-github                       # poll one repo, print candidates
make smoke-telegram                     # send "iter-27 smoke" message to test channel
```

## Autonomous publishing loop

Edit `config/loop.toml` to set the timezone, daily fire times, and repo list.

```bash
make validate                           # one end-to-end tick into TELEGRAM_CHANNEL_ID
make status                             # last 10 posts + failed ticks (24h)
make dry-run                            # one tick, skip send_message (prints draft)
make tick                               # one tick, publish if fresh candidate
make daemon                             # blocking long-running daemon
```

To run the daemon as a system service (survives logout/reboot), see `ops/README.md` (`launchd` on macOS, `systemd` on Linux).

## License

MIT — see [LICENSE](LICENSE).
