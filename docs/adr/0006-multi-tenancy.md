# ADR-0006 — Multi-tenancy

- **Status:** Accepted (foundational; locked at iter-27 even though code lands iter-30)
- **Date:** 2026-05-22 (iter-27)

## Context

Multi-tenant code doesn't ship until iter-30 (User onboarding), but every schema and API decision before then depends on the tenancy model. Without an ADR, iter-28's voice-drafting and iter-29's scheduler code will silently assume something — and retrofitting the wrong choice is more expensive than picking now.

`tech_risk.md` ranked the per-tenant state DB at complexity 2/5 with these gotchas: encrypt OAuth tokens at rest, voice samples 10–50KB/user, ~1GB Postgres at 10000 users.

## Decision

**Single Postgres instance, row-level tenancy keyed on `user_id`.** No schema-per-tenant. No database-per-tenant. No partitioning at MVP.

### Schema convention

- Every business table has `user_id UUID NOT NULL REFERENCES users(id)` as the second column (after `id`).
- Every query against business tables MUST include `WHERE user_id = :user_id`. Enforced by:
  - Code review (no `SELECT … FROM <business_table>` without `user_id` in `WHERE`).
  - A `pg_audit`-style policy in iter-31+ (post-MVP; deferred).
- No RLS (row-level security) at MVP. Adds complexity; one missed `WHERE` slips through anyway; we trust the code.

### Encryption at rest

- **GitHub PATs:** Fernet-encrypted via `cryptography` library; key in `GITHUB_TOKEN_FERNET_KEY` env (32 bytes, base64). Stored in `users.github_token_encrypted BYTEA`.
- **Voice samples:** stored as plaintext JSONB (`users.voice_samples`). Not encrypted — content is the user's own posts, already public on their Telegram channel.
- **Telegram Bot tokens (per-user, if/when we move from single shared bot to per-user bot in Studio tier):** Fernet-encrypted, same convention as GitHub PATs.
- **Telegram Stars transaction IDs:** plaintext (not sensitive — they're invoice IDs, not credentials).

### Per-user storage budget

Voice samples 10–50KB/user. Source configs ~1KB/user. Published messages history (90-day retention) ~5MB/user at 3 posts/day. Scheduled jobs (transient) negligible. **Total: ~5–6MB/user.** At 10000 users → ~60GB. Within boring-Postgres single-instance comfort.

### Data retention

- Published messages: 90 days, then archived to S3/R2-equivalent (deferred, iter-33).
- Voice samples: indefinite (user-owned data, deletion on account delete).
- Telegram Stars transactions: 7 years (CIS bookkeeping requirement; check legal once entity established).
- Application logs: 30 days in app, 1 year in cold storage.

## Consequences

### Positive
- Simplest possible tenancy model — easy to reason about, easy to migrate.
- Backup/restore is one operation (one DB).
- Cross-user analytics (e.g., "which sources have highest approval rate?") is a simple `GROUP BY`, no cross-DB joins.

### Negative
- One missed `WHERE user_id = ?` is a data leak. Mitigated by code review + a pre-commit grep hook (deferred to iter-29).
- One slow-query from one user can affect all users. At MVP scale (≤1000 users) this is theoretical; revisit at iter-32+.
- Vertical scaling only at MVP. Postgres can handle 10000+ users on a single instance at our access pattern; no horizontal sharding needed for the foreseeable future.

## Alternatives rejected

- **Schema-per-tenant:** Adds migration complexity (every Alembic migration must run N times); Postgres has a documented hard limit around ~10000 schemas; benefits (clearer isolation) don't outweigh costs.
- **Database-per-tenant:** Same complexity worse, plus connection-pool fragmentation.
- **Row-level security (RLS):** Considered, deferred to iter-31+. Adds a meaningful learning curve; one missed `SET LOCAL app.current_user_id = …` undermines the entire scheme.

## References

- `tech_risk.md` (iter-26b) — per-tenant state DB component, complexity 2
- PRD MVP-scope: "Multi-tenancy: Single Postgres, row-level keyed on `user_id`."
