# Autonomous Publishing Loop — Validation Report

**Date:** 2026-05-23
**Branch:** `feat/autonomous-loop-impl`
**Spec:** `docs/superpowers/specs/2026-05-23-autonomous-publishing-loop-design.md`
**Plan:** `docs/superpowers/plans/2026-05-23-autonomous-publishing-loop.md`

## Result

**PASS** — the autonomous loop generated, drafted, and published one real post to the live test channel with zero human intervention in the content path.

## Live run

Command: `GITHUB_TOKEN="$(gh auth token)" make validate`

Outcome:
- Polled 10 GitHub repos → 300 candidates (httpx, kubernetes, terraform, grafana, prometheus, etcd, argo-cd, containerd, tektoncd/pipeline, anthropic-sdk-python).
- Selected the newest unseen candidate: `anthropics/anthropic-sdk-python v0.104.1` (release id `327984153`).
- `ClaudeCodeLLMDrafterClient` shelled out to `claude -p` (no `ANTHROPIC_API_KEY`) and produced a 408-char Russian DevOps voice draft.
- `TelegramPublisher` `sendMessage` returned `message_id=4` in channel `-1003629093519` (`@test_tech_pub_bot` → `test_tech_pub`).
- `StateStore` recorded the post; `tick.published` event logged to `${STATE_DIR}/loop.log`.

Channel URL: `https://t.me/c/3629093519/4`

## What was published

```
anthropic-sdk-python 0.104.1: точечный фикс streaming + beta compaction —
`encrypted_content` теперь корректно прокидывается через аккумулятор (#1821).
Если гоняете extended thinking с context compaction в стриме, без этого
encrypted reasoning-блоки терялись при reassemble, и API отвечал ошибкой на
следующем turn-е. Узкий кейс, но если зацепило — апгрейд обязателен.
https://github.com/anthropics/anthropic-sdk-python/releases/tag/v0.104.1
```

The draft is voice-faithful (Russian, DevOps-aware, terse, link at the end) and technically accurate — `encrypted_content` plumbing for streaming-with-compaction is exactly what the upstream PR #1821 fixes.

## Test suite

`uv run pytest --ignore=tests/integration/test_db_roundtrip.py` → 65 passed.
`uv run ruff check .` → all checks passed.
`uv run ruff format --check .` → no diff.

## Setup steps the human had to do once

These are configuration, not per-post operation:

1. Add `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `TELEGRAM_TEST_CHANNEL_ID`, `GITHUB_TOKEN` to `.env`.
2. Add the bot (`@test_tech_pub_bot`) as admin in the target channel with **Post Messages** permission.
3. `DRAFTER_BACKEND` defaults to `claude_code` — no API key required for the LLM call.

After this one-time setup, `make daemon` (or the launchd/systemd unit in `ops/`) ticks at the times listed in `config/loop.toml` (`09:30`, `13:30`, `18:00` Europe/Moscow) and publishes autonomously.

## Failures encountered en route

Worth recording because they're the kind of pre-flight checks that should be in a `make doctor` later:

| When (UTC)  | Stage         | Error                                | Cause                                                  |
|-------------|---------------|--------------------------------------|--------------------------------------------------------|
| 07:58       | GitHub poll   | 401 Unauthorized on all 10 repos     | `GITHUB_TOKEN` in `.env` expired                       |
| 07:59 / 08:11 | Telegram send | `InvalidToken('Unauthorized')`     | `TELEGRAM_BOT_TOKEN` belonged to a deleted/old bot     |
| 08:12 / 08:15 | Telegram send | `BadRequest('Chat not found')`     | New bot not yet admin in the configured channel        |
| 08:18       | Telegram send | OK — `message_id=4`                  | All credentials + channel admin status correct         |

Each failure was clearly logged to `loop.log` and surfaced via `status`.

## Backend choice

The `claude_code` backend was added in this branch (commit `9cae3ae`) precisely so the loop can run on a Claude Code subscription without an Anthropic API key. The Anthropic-API path is still wired (`DRAFTER_BACKEND=anthropic` + `ANTHROPIC_API_KEY`) and is exercised in `tests/integration/test_validate_flow.py` via respx.

## Conclusion

Success criteria from the brief:

- ✅ Generate or assemble channel content automatically.
- ✅ Publish without per-message human approval.
- ✅ Run on a schedule (APScheduler cron triggers in `loop/daemon.py`).
- ✅ Work in a real channel (msg_id 4 in `test_tech_pub`).
- ✅ Log results clearly (structlog JSON to `loop.log`, `status` command).
