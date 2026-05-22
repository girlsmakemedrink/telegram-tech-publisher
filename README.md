# telegram-tech-publisher

AI content engine for Telegram developer channels. Curates from GitHub releases + HN, drafts in the channel's voice, ships 3 posts/day.

**Status:** iter-27 bootstrap (2026-05-22). Foundational docs + two smoke pipelines only — not production-ready. See `docs/PRD.md` for product scope and `docs/iterations/` (in the [ai_team repo](https://github.com/girlsmakemedrink/ai_team)) for iteration history.

## Quickstart (dev)

```bash
uv sync
cp .env.example .env  # fill in TELEGRAM_BOT_TOKEN + TELEGRAM_TEST_CHANNEL_ID + GITHUB_TOKEN
make smoke-github     # poll one repo's releases, print candidates to stdout
make smoke-telegram   # send "iter-27 smoke" message to test channel
```

## Smoke pipelines

- **`make smoke-github`** — polls GitHub releases for one configured repo and prints post candidates to stdout; verifies the GitHub polling substrate (token, API connectivity, release-feed parsing).
- **`make smoke-telegram`** — sends a test message to the configured Telegram test channel; verifies the publish substrate (bot token, channel permissions, Telegram API connectivity).

## License

MIT — see [LICENSE](LICENSE).
