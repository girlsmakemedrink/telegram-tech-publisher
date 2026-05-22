# ADR-0004 — Voice calibration

- **Status:** Accepted (amended 2026-05-22 pre iter-29)
- **Date:** 2026-05-22 (iter-27); amended 2026-05-22 (iter-29 pre-flight)

> **Amendment (2026-05-22):** Tightening the schema and command surface before iter-29a/b implementation. Substantive deltas vs. the original iter-27 ADR:
> 1. `examples` → `samples` (in JSONB schema, prompt-construction wording, and threshold rules).
> 2. Per-sample shape changed from `{text, label, weight}` to `{id, candidate_external_id, draft_text, kind, score, created_at}` — unifies seeded defaults and user-labeled real posts under one collection, distinguished by `kind`.
> 3. `defaults_template: str` (template literal) → `default_voice: str | None` (key into a static `VOICE_DEFAULTS: dict[str, VoiceDefault]` map in code; `None` once defaults are dropped).
> 4. Threshold simplified: single cut-off at 20 labeled samples (defaults dropped). Removed the two-tier 10-then-20 step — at MVP scale the intermediate de-emphasis is more bookkeeping than signal.
> 5. `/retune` allowlist made explicit: gated by `ADMIN_TELEGRAM_USER_IDS` env (comma-separated Telegram user IDs).

## Context

Voice mismatch is the dominant churn risk per both Architect (`tech_risk.md` LLM voice-tone drafting component, complexity 3) and PM (`revenue.md` Summary calls out "draft quality falling below manual bar" as primary churn driver). The architect proposed Sonnet 4.6 few-shot with 10–20 user-labeled past posts; embeddings-retrieval and fine-tuning were both rejected as overengineering for an MVP shipping ≤10 drafts/day per user.

The orthogonal problem is cold-start: requiring 10–20 labeled posts upfront is onboarding friction; risk #5 in `_validation_summary.md`.

## Decision

**Sonnet 4.6 with few-shot prompting + pre-built developer-channel voice defaults at onboarding.**

### Mechanics

- **Voice store:** per-user JSONB column `voice_store` on `users` table, shape:
  ```jsonc
  {
    "samples": [
      {
        "id": "uuid",
        "candidate_external_id": "string | null",  // null for seeded defaults; source ref otherwise
        "draft_text": "string",
        "kind": "default | approved | rejected",
        "score": "number",                          // +1 / -1 / seed-weight
        "created_at": "iso8601"
      }
    ],
    "default_voice": "string | null",               // key into VOICE_DEFAULTS map; null once dropped
    "last_retuned_at": "iso8601 | null"
  }
  ```
- **Few-shot construction:** for each draft, sample up to 8 entries from `samples` (weighted top-k by recency × `score`, with `kind="rejected"` contributing negative weight as "avoid this voice" exemplars), inject into the system prompt as "Past posts from this channel — match this voice."
- **Pre-built defaults:** static `VOICE_DEFAULTS: dict[str, VoiceDefault]` in code (`llm/voice_defaults.py`), 5 entries keyed by slug:
  - `python`
  - `devops`
  - `ai_ml`
  - `backend`
  - `security`

  Each `VoiceDefault` carries a tone/cadence description plus 3–5 archetype draft texts. Source markdown lives at `prompts/voice_defaults/<slug>.md` and is loaded at import time.
- User picks one slug at onboarding; `voice_store.default_voice` is set to that key, and the matching `VOICE_DEFAULTS[slug]` archetype posts are inserted into `samples` with `kind="default"` and a seed `score` (e.g. 0.5).
- As the user labels real posts (👍 / 👎 inline-keyboard responses), new samples accumulate with `kind="approved"` / `kind="rejected"` and `score=±1`. **After 20 user-labeled samples** (`kind in ("approved", "rejected")`), default samples are dropped from the prompt and `default_voice` is set to `null`. There is no intermediate de-emphasis step.
- **Re-tune command:** `/retune` admin command samples the last N approved posts and rebuilds the sample set. Owner-triggered, not automatic. Allowlisted via the `ADMIN_TELEGRAM_USER_IDS` env (comma-separated Telegram user IDs) — non-allowlisted users get a no-op reply.

### Prompt cache strategy

- Voice-example block is the largest static chunk of the prompt → goes at the top, behind the cache marker.
- 5-minute TTL on the Anthropic prompt cache means same-day repeated drafts on the same user reuse cache, cutting cost ~50% on the voice-block portion.
- Cache invalidation when user adds/relabels examples is implicit (next request sees new voice block, builds new cache).

## Consequences

### Positive
- No onboarding cold-start: user can publish from minute 1 via the default they picked.
- No fine-tuning infrastructure to build / maintain / pay for.
- Cost / latency stays in the Sonnet single-shot envelope ($0.25–$0.30/user/day per the LLM opex projection).

### Negative
- Voice drift on topics user hasn't covered before is real — mitigated by the `/retune` command but not eliminated. Worst case: a user reviewing/rejecting 3 drafts in a row, which we'll catch in the approval-rate metric.
- Pre-built defaults need refresh every ~6 months as Python/DevOps/AI-ML idiom evolves. Tracked as a quarterly maintenance task.

## Alternatives rejected

- **Per-user fine-tune:** Unavailable at Anthropic's current API tier and overkill for ≤10 drafts/day/user. Recurring infra cost would dominate gross margin.
- **Embeddings retrieval:** Adds vector DB infra (Pinecone / pgvector) for marginal gain over few-shot at this scale. Premature.
- **Cold-start with no defaults (require 10 labeled posts upfront):** Eliminates risk of bad defaults but adds 30–60 min onboarding before first publish. Conversion-killing.

## References

- `tech_risk.md` (iter-26b) — LLM voice-tone drafting component, complexity 3
- `revenue.md` (iter-26b) — Summary, churn-risk drivers
- `_validation_summary.md` (iter-26b) — risk #5
