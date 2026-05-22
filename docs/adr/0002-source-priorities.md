# ADR-0002 — Source priorities

- **Status:** Accepted
- **Date:** 2026-05-22 (iter-27)

## Context

`tech_risk.md` ranked four source classes by complexity:
- GitHub releases / stars / commits (complexity 2) — REST + GraphQL API, 5000 req/hr per token
- Hacker News (complexity 1) — free Firebase API, ~10 req/s safe
- RSS (complexity 1) — `feedparser` + readability, no API limits, charset sniffing required for CIS feeds
- X / Twitter (complexity 5) — TOS-prohibited scraping, API v2 Basic ($100/mo) caps at ~50–100 users, Pro tier ($5000/mo) unaffordable until >3000 paying users

QA verdict was `feasible_with_caveats` driven primarily by X being descoped.

## Decision

MVP ships **two sources only: GitHub releases + Hacker News.** RSS deferred to iter-29+. X deferred indefinitely with an rss.app bridge as a placeholder fallback for community-submitted X content.

### Per-source scope

**GitHub releases (in MVP):**
- Per-channel repo allowlist (3 in Starter / 10 in Pro / unlimited in Studio).
- Poll cadence: 15 min (well under the 5000 req/hr per-token limit even at 1000 active users).
- Per-channel GitHub token required at scale (post-MVP); single shared token at MVP if user count ≤50.
- Pull `releases` endpoint only at MVP; `stars` and `commits` deferred (firehose noise, requires LLM filter).

**Hacker News (in MVP):**
- Firebase `topstories` endpoint, polled every 10 min.
- Each candidate runs through Haiku-tier relevance filter against channel's interest taxonomy.
- `newstories` deferred — too noisy, latency-sensitive use case.

**RSS (deferred to iter-29):**
- Win1251 / KOI8-R charset sniffing not in MVP critical path.
- Broken-feed handling (malformed XML) not in MVP critical path.

**X / Twitter (descoped):**
- No code path in MVP.
- `rss.app` bridge URL accepted as a "custom feed" input post-iter-29 RSS landing.
- Revisit native X API at >3000 paying users when Pro tier ($5000/mo) is affordable.

## Consequences

### Positive
- MVP build window stays at 8–12 weeks per QA estimate.
- Avoids X/Twitter legal + cost cliff entirely.
- Both MVP sources have free quotas that absorb the first ~1000 active users.

### Negative
- Some users will ask for X day-one; canned response: "rss.app bridge supported via custom feed (post-iter-29)."
- RSS deferral may leak ~10% of CIS dev channels whose content originates from non-API feeds; acceptable churn risk for MVP.

## References

- `tech_risk.md` (iter-26b) — X risk component, severity 5
- PRD MVP-scope section
