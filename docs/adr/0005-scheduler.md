# ADR-0005 — Scheduler

- **Status:** Accepted
- **Date:** 2026-05-22 (iter-27)

## Context

The publishing pipeline is per-user, per-channel, on a per-user timezone-aware schedule. `tech_risk.md` ranked the scheduler/queue component at complexity 2/5. Telegram rate limits (1 msg/s per chat, 30/s across chats, 20 msg/min per group) are non-binding for the MVP target of 3 drafts/day per channel — the bottleneck is per-user scheduling and idempotency on worker restarts.

## Decision

**Postgres-as-queue + in-process APScheduler.** No Redis, no SQS, no Celery.

### Mechanics

- `scheduled_jobs` table: `(id UUID PK, user_id FK, payload JSONB, scheduled_at TIMESTAMPTZ, status enum, attempts int, locked_until TIMESTAMPTZ, last_error TEXT)`.
- Worker is an `asyncio` task inside the FastAPI uvicorn process. APScheduler ticks every 30s; on each tick, `SELECT … FOR UPDATE SKIP LOCKED` claims due jobs with a 5-minute lock.
- Per-user timezone via `zoneinfo.ZoneInfo(user.timezone)` (default `Europe/Moscow` is wrong for half the CIS market — onboarding must collect it explicitly).
- Retry policy: exponential backoff `2s × 2^attempts`, capped at 4 attempts. Retry on Telegram 5xx + 429 (rate limit); fail-fast on 4xx.
- **Idempotency:** every outbound Telegram send carries the `scheduled_jobs.id` as the message's `client_request_id` (Telegram supports this for some endpoints; for those that don't, we de-dupe at our layer via `(user_id, target_channel, scheduled_at)` unique constraint on a `published_messages` table). Worker restart mid-send WILL NOT double-post.

### Worker placement (MVP)

In-process inside the FastAPI uvicorn process. Single replica. Single worker task. Acceptable up to ~100 active users; revisit when scheduled jobs exceed ~5000/day.

### Worker placement (post-MVP, iter-32+)

Separate `worker` service (still Python, same codebase, separate uvicorn-less entrypoint) when (a) the API and worker have meaningfully different scaling profiles, or (b) we need >1 replica for redundancy.

## Consequences

### Positive
- One infra primitive (Postgres) for state, queue, and pubsub. Drastically simpler than the ai_team Redis + Postgres + audit-log split.
- `SELECT … FOR UPDATE SKIP LOCKED` is well-understood and fast at this scale.
- Idempotency primitive is concrete and testable.

### Negative
- Postgres polling at 30s tick is not free; at 10000+ jobs/day with multiple workers we'll see lock contention. Acceptable for the MVP user-count target; revisit at iter-32.
- In-process worker means a long-running Telegram send blocks request handling. Mitigated by `asyncio` concurrency + bounded semaphore on `send_message`.
- No DLQ visualization. A failed job sits in `scheduled_jobs.status = 'failed'` with `last_error`; ops on this is `psql` + a `make` target for now.

## Alternatives rejected

- **Redis + Celery / RQ / Dramatiq:** Adds an entire infra primitive. Unjustified at MVP scale.
- **Cron jobs:** Doesn't survive worker restart; doesn't track per-job state; no retry envelope.
- **Cloud queue (SQS / Cloud Tasks):** Vendor lock-in; cost > $0 from day one; latency to Telegram from the queue worker is unpredictable.

## References

- `tech_risk.md` (iter-26b) — scheduler/queue component, complexity 2
- ai_team's Redis Streams + audit-log approach (intentionally NOT copied here)
