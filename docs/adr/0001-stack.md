# ADR-0001 — Stack

- **Status:** Accepted
- **Date:** 2026-05-22 (iter-27)

## Context

This is the first product repo in the `ai_team`-driven portfolio. Choosing a stack here sets a precedent for future products. The owner's existing expertise + the QA architect's `tech_risk.md` analysis both point to a boring, mostly-synchronous Python service that polls a few APIs, runs LLM calls, and writes to Postgres + Telegram.

## Decision

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.11 | Owner expertise; matches ai_team. `match` statements + structural pattern matching available. |
| Dep manager | `uv` | Fast; lockfile committed; matches ai_team. |
| Web framework | FastAPI + uvicorn | For Telegram Bot API webhook receiver + future admin endpoints. Async-first. |
| CLI | Click + Rich | Matches ai_team. Click for arg parsing, Rich for terminal output. |
| Telegram Bot API client | `python-telegram-bot` v22+ | De facto standard. Async-native. Inline keyboards + MarkdownV2 support. |
| HTTP client | `httpx` | Async + sync, respx for testing. |
| DB | Postgres 15 + SQLAlchemy 2.x async + Alembic | Boring; matches ai_team. Async driver `asyncpg`. |
| Settings | `pydantic-settings` | Type-safe env loading. |
| Logging | `structlog` (JSON output) | Correlation IDs; matches ai_team. |
| Metrics | `prometheus-client` | Defer until iter-29 (no metrics needed for smoke pipelines). |
| Test framework | `pytest` + `pytest-asyncio` + `testcontainers[postgres]` | Matches ai_team. |
| Lint / type | `ruff` (strict select) + `mypy` (strict) | Matches ai_team. |
| Security | `bandit` (high-only gate) | Matches ai_team. Low/medium advisory. |

## Consequences

### Positive
- Identical mental model to `ai_team` reduces context-switch cost for the same owner.
- Async-first stack is the right shape for a poller + LLM + Telegram service.
- No framework debt: every dep is widely used and stable.

### Negative
- Two repos to keep in sync on dep upgrades (Python, ruff, mypy). Acceptable cost given solo dev.
- No web UI in this stack choice. Intentional — bot inline keyboards are the only UX (see PRD "Out-of-scope").

## Alternatives rejected

- **Node.js / TypeScript:** `python-telegram-bot` is more mature than `telegraf`; owner has deeper Python expertise; LLM tooling is Python-first.
- **Go:** Better runtime characteristics but ecosystem (LLM clients, Telegram clients) is weaker. Owner not fluent.
- **LangGraph / CrewAI / OpenAI SDK:** Rejected per ai_team ADR-001 — premature abstraction for what is fundamentally a request/response service with a polling worker.
- **SQLite for MVP:** Single-user multi-tenancy requires concurrent writes; Postgres is the right floor.

## References

- [ai_team ADR-001 — orchestrator + stack rationale](https://github.com/girlsmakemedrink/ai_team/blob/main/docs/adr/0001-orchestrator-choice.md)
- `_validation_summary.md` (iter-26b)
