# iter-29a substrate — implementation plan

> **Status:** Architect-issued plan for Backend. File-by-file contract for the DB + LLM substrate. Approved spec lives upstream at `ai_team:docs/iterations/iter_29a.md`; this doc is the product-repo-local pin-down.
>
> **Scope reminder.** No `voice/`, no `drafter/`, no `bot/`, no `real_llm` test. The `real_llm` pytest marker is registered in 29a so 29b can drop a test in without touching `pyproject.toml`; the `AnthropicLLMDrafterClient` ships dark and is first exercised in 29b. See `iter_29a.md` "Non-Goals" for the full out-of-scope list.

## Module layout

```
src/telegram_tech_publisher/
├── db/
│   ├── __init__.py           # re-exports Base, User, make_engine, make_session_factory
│   ├── models.py             # DeclarativeBase + User
│   └── session.py            # make_engine, make_session_factory (factories only)
└── llm/
    ├── __init__.py           # re-exports LLMDrafterClient, Example, Draft,
    │                         # MockLLMDrafterClient, AnthropicLLMDrafterClient
    ├── client.py             # Protocol + Example + Draft (no SDK import)
    ├── mock.py               # MockLLMDrafterClient (deterministic stub)
    └── anthropic_client.py   # AnthropicLLMDrafterClient + _build_request (only file
                              # in the repo that imports `anthropic`)

alembic/
├── env.py                    # async-mode env, target_metadata = Base.metadata
├── script.py.mako            # default alembic template, unmodified
└── versions/
    └── 20260522_0001_init.py # creates users table; downgrade drops it

alembic.ini                   # at repo root; sqlalchemy.url = ${DATABASE_URL}
.env.local.example            # ANTHROPIC_API_KEY schema only (the real .env.local is gitignored)
```

### Why these directory names

- `db/` and `llm/` are siblings of the existing `sources/` and `publishers/` packages — same one-word, one-responsibility shape. No `services/` umbrella package; flat layout matches what's already in the repo.
- `alembic/` lives at repo root (sibling of `src/`), the canonical layout for SQLAlchemy 2.0 projects. It is not inside `src/telegram_tech_publisher/` because migrations are operational state, not importable library code.

## `db/models.py` — SQLAlchemy 2.0 typed mapped-column choices

```python
import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    voice_store: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    labeled_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
```

### Column-by-column rationale

- **`id`** — `postgresql.UUID(as_uuid=True)` (not the dialect-agnostic `Uuid` type). Pinned to Postgres because the substrate is Postgres-only — no SQLite fallback in 29a. `default=uuid.uuid4` (Python-side) so no `pgcrypto`/`uuid-ossp` extension is required at DB level. Bare `UUID` from `uuid` module for the typing annotation.
- **`telegram_user_id`** — `BigInteger`. Telegram user IDs are now routinely > 2^31 (post-2023 migration to int64), so `Integer` would silently truncate. `unique=True` + `index=True`; SQLAlchemy emits both the UNIQUE constraint and a separate b-tree index, which alembic transcribes.
- **`voice_store`** — `JSONB` from the Postgres dialect (not `JSON`). JSONB stores parsed, indexable, and slightly larger; iter-29b's voice store will benefit from `?` containment queries. Python-side default is `dict` (callable, evaluated per-row) — not `{}` (shared instance, classic mutable-default footgun). No `server_default` here: the model owns the default; the migration also emits `server_default=text("'{}'::jsonb")` so direct INSERTs from psql work, but the ORM path uses the Python default.
- **`labeled_count`** — plain `int` (`Integer` is inferred from the annotation). `default=0`. Not nullable. iter-29b's voice prompt assembly reads this to decide when to drop defaults.
- **`created_at` / `updated_at`** — `datetime` typed mapped, `TIMESTAMP WITH TIME ZONE` in Postgres (SA 2.0 default when `Mapped[datetime]` is used). `server_default=func.now()` makes Postgres own the timestamp on INSERT. `updated_at` adds `onupdate=func.now()` so ORM-driven updates bump it; raw SQL UPDATEs would need to set it explicitly. Acceptable — there's no raw-SQL writer in the substrate.

### Why typed `Mapped[...]` style and not the legacy `Column(...)` style

SQLAlchemy 2.0 typed `mapped_column` gives mypy real types end-to-end. The project runs `mypy --strict`; the legacy `Column(...)` style requires per-call `# type: ignore` or `cast` boilerplate. The cost is one extra import line and `Mapped[...]` annotations — paid once, collected forever.

## `db/session.py` — factory-only, no module-level engine

```python
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def make_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
```

### Why factories and not a module-level engine

A module-level `engine = create_async_engine(...)` couples library code to import order and to a specific `DATABASE_URL` lookup. Two callers need different DSNs:

1. The integration test fixture, which points at a per-suite Postgres (real, dockerised, or `testcontainers` later).
2. iter-29b's bot CLI, which constructs an engine from `Settings`.

Factories also let us keep `db/session.py` import-time side-effect-free, so `import telegram_tech_publisher.db` doesn't try to dial a database that may not exist yet.

### `expire_on_commit=False`

After `session.commit()`, ORM-loaded objects must remain usable without a second round-trip. Default `True` re-loads on attribute access, which surprises async callers and breaks the integration test (post-commit `.voice_store` lookup would re-query inside a closed session). The trade-off — slight risk of reading stale data after commit — is acceptable for a single-writer service.

### `pool_pre_ping=True`

Cheap insurance against connections killed by an idle-timeout (common with managed Postgres). One extra round-trip per connection-checkout; worth it.

## `llm/client.py` — Protocol + DTOs

```python
from typing import Protocol

from pydantic import BaseModel

from telegram_tech_publisher.sources.base import Candidate


class Example(BaseModel):
    input_title: str
    input_body: str
    output_text: str


class Draft(BaseModel):
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int


class LLMDrafterClient(Protocol):
    async def draft(
        self,
        voice_block: str,
        examples: list[Example],
        candidate: Candidate,
    ) -> Draft: ...
```

### Per ADR-008 (Protocol + Mock + Real)

The Protocol is the only surface 29b's `Drafter` service is allowed to depend on. Concrete classes are constructed at the composition root (29b's bot CLI / DI wiring); everything downstream sees `LLMDrafterClient`. Mirrors `ai_team:core/llm/base.py:LLMClient`.

### Why a `Protocol`, not an ABC

Structural typing means `MockLLMDrafterClient` doesn't need to inherit from anything — it just implements `async def draft(...)`. Removes a forced inheritance chain and keeps the mock dead-simple. mypy still type-checks the conformance via the `Protocol`.

### Token-count fields on `Draft`

`input_tokens`, `output_tokens`, `cache_read_tokens` are surfaced so 29b can log per-draft cost and monitor cache-hit rate (the whole point of `cache_control` below). The mock returns zeros by default but accepts injected counts so tests can assert on the wiring.

### `Candidate` coupling

`llm/client.py` imports `Candidate` from `sources/base.py`. Acceptable — `Candidate` is the canonical "thing we draft from" type and is already shared by `sources/` and `publishers/`. If iter-29b ever splits `Candidate` into a separate `core/types` module, this import follows; no 29a action needed.

## `llm/mock.py` — `MockLLMDrafterClient`

```python
from telegram_tech_publisher.llm.client import Draft, Example, LLMDrafterClient
from telegram_tech_publisher.sources.base import Candidate


class MockLLMDrafterClient:
    def __init__(
        self,
        *,
        model: str = "mock",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> None:
        self._model = model
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._cache_read_tokens = cache_read_tokens

    async def draft(
        self,
        voice_block: str,
        examples: list[Example],
        candidate: Candidate,
    ) -> Draft:
        return Draft(
            text=(
                f"[{candidate.title}] (mock draft, "
                f"voice_len={len(voice_block)}, n_examples={len(examples)})"
            ),
            model=self._model,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            cache_read_tokens=self._cache_read_tokens,
        )
```

Constructor args (keyword-only) let tests inject specific token counts to assert cache-behavior reporting end-to-end. Static-type conformance to `LLMDrafterClient` is implicit via the Protocol — no inheritance needed; mypy checks it where the mock is passed into something typed as `LLMDrafterClient`.

## `llm/anthropic_client.py` — the only file that imports `anthropic`

```python
import os
from typing import Any

from anthropic import AsyncAnthropic

from telegram_tech_publisher.llm.client import Draft, Example
from telegram_tech_publisher.sources.base import Candidate


class AnthropicLLMDrafterClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> None:
        resolved = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        if not resolved:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = AsyncAnthropic(api_key=resolved)

    def _build_request(
        self,
        voice_block: str,
        examples: list[Example],
        candidate: Candidate,
    ) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": [
                {
                    "type": "text",
                    "text": voice_block,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": _format_examples_and_candidate(examples, candidate),
                }
            ],
        }

    async def draft(
        self,
        voice_block: str,
        examples: list[Example],
        candidate: Candidate,
    ) -> Draft:
        request = self._build_request(voice_block, examples, candidate)
        response = await self._client.messages.create(**request)
        return Draft(
            text=response.content[0].text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_read_tokens=getattr(response.usage, "cache_read_input_tokens", 0),
        )


def _format_examples_and_candidate(
    examples: list[Example],
    candidate: Candidate,
) -> str:
    blocks = []
    for i, ex in enumerate(examples, start=1):
        blocks.append(
            f"Past post {i}:\n"
            f"  source title: {ex.input_title}\n"
            f"  source body: {ex.input_body}\n"
            f"  published post: {ex.output_text}\n"
        )
    blocks.append(
        f"Draft a Telegram post for:\n"
        f"  title: {candidate.title}\n"
        f"  body: {candidate.body}\n"
    )
    return "\n".join(blocks)
```

### Prompt-caching strategy — ephemeral cache_control on the system block

The voice block is the **only** content marked `cache_control: {"type": "ephemeral"}`. Rationale:

- **What changes least often.** A user's voice block is stable between drafts within a session; the candidate (source post) changes every call. The system block is exactly the right granule.
- **`ephemeral` is the right tier.** Anthropic offers `ephemeral` (5-minute TTL, low-cost write) — fits a polling cadence on the order of seconds-to-minutes per user. `persistent` is overkill and would cost more on the write side without payoff at MVP cadence.
- **Examples stay inside `messages`, not `system`.** Few-shot examples will rotate per labeling round; caching them gains nothing and complicates invalidation. Plain string formatting, no XML/JSON.
- **`cache_read_tokens` is surfaced in `Draft`.** 29b's smoke + ops can verify cache hits in production by reading `response.usage.cache_read_input_tokens`. Bare-zero across all calls = caching is broken; non-zero on call 2+ = working as designed.

### Async SDK

`AsyncAnthropic` (not `Anthropic`). Matches the async DB layer and the async source/publisher protocols already in the repo. Avoids `asyncio.to_thread` around blocking calls.

### `_build_request` is the unit-test seam

Public API is `draft()`. Internal `_build_request` is the part of `draft()` that can be unit-tested without an SDK call. Tests assert the dict shape; the SDK round-trip is exempt from unit coverage (per project standard — thin third-party-SDK glue, exercised by 29b's `real_llm` smoke).

### No retry, no circuit breaker

`anthropic.APIError` and subclasses propagate. iter-30+ wraps this when the polling loop wires the drafter into production. iter-29a deliberately stops short.

### `_format_examples_and_candidate`

Module-level private helper (not a method) — pure function over its inputs, no `self` needed, easier to test in isolation if 29b ever adds a focused test for it. Plain-text formatting, no XML/JSON tags. Newlines between sections to keep the prompt human-readable in logs.

## Settings vs `AnthropicLLMDrafterClient` decoupling

`config.py` change is one line:

```python
anthropic_api_key: str | None = None
```

Default `None` is critical: it means **importing `Settings` never requires `ANTHROPIC_API_KEY` to be set**. Tests, unit and integration alike, instantiate `Settings()` without an API key. Only the 29b bot CLI (and a future `real_llm` smoke) wires `AnthropicLLMDrafterClient(api_key=settings.anthropic_api_key)`.

### Why the client itself does the env-fallback (not `Settings`)

Two reasons:

1. **`AnthropicLLMDrafterClient` is library-grade.** It must construct without dragging `pydantic-settings` into the LLM module's dependency graph. A consumer who just wants the client (say, a one-off script) can do `AnthropicLLMDrafterClient()` and rely on `ANTHROPIC_API_KEY` in env — no `Settings()` round-trip required.
2. **Clean error surface at construction time.** `ValueError("ANTHROPIC_API_KEY not set")` fires at `__init__`, not at the first `draft()` call. Misconfiguration is loud and immediate.

Order of resolution: explicit `api_key=` kwarg → `os.environ["ANTHROPIC_API_KEY"]` → raise. No `Settings` lookup inside the client; if a caller wants the Settings-driven flow, they pass `api_key=settings.anthropic_api_key` from the composition root.

### Test seam

Unit test for the "missing key" path uses `monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)` before calling `AnthropicLLMDrafterClient(api_key=None)` so the test is hermetic regardless of the runner's environment.

## Alembic config

### `alembic.ini` (repo root)

Single non-default knob: read DSN from env.

```ini
[alembic]
script_location = alembic
sqlalchemy.url = ${DATABASE_URL}

[loggers]
# default alembic logger config — copy from `alembic init` output, unmodified
```

`${DATABASE_URL}` uses alembic's built-in `${VAR}` interpolation (no `env_from_config` Python hook needed). Same DSN as the runtime engine, so `alembic upgrade head` and the integration test see the same database.

### `alembic/env.py` — async mode

Canonical SQLAlchemy 2.0 async recipe. Sketch:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from telegram_tech_publisher.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### `alembic/versions/20260522_0001_init.py`

Hand-written (not `--autogenerate`) so the file is small and deterministic. Schema must match `User` exactly:

```python
"""init users table

Revision ID: 20260522_0001
Revises:
Create Date: 2026-05-22
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260522_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "voice_store",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("labeled_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),
    )
    op.create_index("ix_users_telegram_user_id", "users", ["telegram_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_telegram_user_id", table_name="users")
    op.drop_table("users")
```

The UNIQUE constraint and the explicit index coexist by design: the constraint guarantees uniqueness; the named index is what the SA model's `index=True` declaration intends. Naming both makes future autogenerate diffs stable.

### Why hand-written and not `alembic revision --autogenerate`

- Backend doesn't have a populated Postgres at the moment of running the generator. `--autogenerate` against an empty DB produces a near-identical file, but with non-deterministic constraint names. Hand-writing the file pins the names and removes one generator step from the build.
- Future migrations (29b+) can use `--autogenerate`; the workflow is supported, just deferred until we have an existing schema to diff against.

## `pyproject.toml` diffs

Two changes, one section each:

1. `[project].dependencies` — append:
   ```toml
   "anthropic>=0.40",
   "sqlalchemy[asyncio]>=2.0",
   "alembic>=1.14",
   "asyncpg>=0.30",
   ```
2. `[tool.pytest.ini_options].markers` — append:
   ```toml
   "real_llm: tests that call the real Anthropic API (paid, opt-in)",
   ```

No dev-deps changed in 29a. No `aiosqlite`. No new lint/type plugins. `uv lock` re-runs as a side-effect of `uv sync`.

## `.env.local.example`

```
# Paid Anthropic API key — required for AnthropicLLMDrafterClient.
# Get yours from https://console.anthropic.com.
# This file is committed as an example; copy to `.env.local` (gitignored)
# and fill in the real value. Required for 29b's real_llm smoke; optional
# for unit + integration suites in 29a.
ANTHROPIC_API_KEY=
```

### Why a separate `.env.local.example` and not just extending `.env.example`

`.env.example` is for developer-bootstrap defaults (Telegram bot token, DB URL — things every dev needs to set to run anything). `.env.local.example` is for **paid-API keys that may stay unset for most workflows** and are loaded only when explicitly wired. Keeping the two files separate signals the cost asymmetry. `.gitignore` already covers `.env*` patterns; QA should verify `.env.local` is ignored (it is, but a one-line check belongs in the QA verdict).

Also update `.env.example` to append the `ANTHROPIC_API_KEY=` line with the same "optional in dev" comment, per the iter-29a spec — this is the developer-friendliness path. Both files end up advertising the variable; only `.env.local.example` doubles as the canonical "paid-key home".

## Test plan — Backend's deliverable, not Architect's

Spec lives in `ai_team:docs/iterations/iter_29a.md#test-plan` and is not re-litigated here. Backend implements the four unit files + one integration file as listed; coverage gates per project standard (80% diff-cover, with `db/session.py` exempt-via-integration and `draft()` SDK call site exempt-via-29b-smoke).

## Branch + commit shape — Backend's contract

Branch: `iter-29a/substrate` (this design doc commits as the first commit on the branch).
Commits (squash-merged into one on `main`):

1. `docs(iter-29a): substrate design` — this file. **Architect's commit.**
2. `chore(deps): add alembic, sqlalchemy[asyncio], asyncpg, anthropic`
3. `feat(db): bootstrap alembic + users table with JSONB voice_store`
4. `feat(llm): drafter client protocol + mock + anthropic impl`
5. `feat(config): add anthropic_api_key setting + .env.local schema`
6. `test: unit suite + db roundtrip integration test`

PR title: `feat(iter-29a): DB + LLM substrate`. PR base: `main`. Backend opens via `GitHubTargetRepo.open_pr` per iter-28's substrate. QA reviews on PR.

## What this design doc explicitly does NOT decide

- Wire-level shape of the eventual voice prompt (defaults, sample formatting, drop-defaults threshold) — that lives in ADR-0004 and lands in 29b.
- The `Drafter` service that consumes `LLMDrafterClient` — 29b.
- Retry / circuit breaker / rate-limit handling around `AsyncAnthropic` — iter-30+.
- The CI matrix changes for the integration test — none in 29a; integration test is owner/QA-run, not in CI.

## References

- `ai_team:docs/iterations/iter_29a.md` — upstream spec for this iteration.
- `ai_team:docs/adr/0008-llm-access-strategy.md` — Protocol + Mock + Real pattern this substrate replicates.
- `ai_team:docs/adr/0009-target-repo.md` — `GitHubTargetRepo` substrate this chain runs on.
- `telegram-tech-publisher:docs/adr/0004-voice-calibration.md` (amended 2026-05-22) — voice store schema this `User.voice_store` will eventually hold.
- `telegram-tech-publisher:src/telegram_tech_publisher/sources/base.py` — `Candidate` model, imported by `llm/client.py`.
- `telegram-tech-publisher:src/telegram_tech_publisher/config.py` — `Settings`, extended by one field in 29a.
