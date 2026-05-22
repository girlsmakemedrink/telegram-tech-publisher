# ADR-0004 — Voice calibration

- **Status:** Accepted
- **Date:** 2026-05-22 (iter-27)

## Context

Voice mismatch is the dominant churn risk per both Architect (`tech_risk.md` LLM voice-tone drafting component, complexity 3) and PM (`revenue.md` Summary calls out "draft quality falling below manual bar" as primary churn driver). The architect proposed Sonnet 4.6 few-shot with 10–20 user-labeled past posts; embeddings-retrieval and fine-tuning were both rejected as overengineering for an MVP shipping ≤10 drafts/day per user.

The orthogonal problem is cold-start: requiring 10–20 labeled posts upfront is onboarding friction; risk #5 in `_validation_summary.md`.

## Decision

**Sonnet 4.6 with few-shot prompting + pre-built developer-channel voice defaults at onboarding.**

### Mechanics

- **Voice store:** per-user JSONB column on `users` table, schema `{ examples: [{text, label, weight}], defaults_template: str, last_retuned_at: timestamp }`.
- **Few-shot construction:** for each draft, sample up to 8 examples (weighted by recency × user-label-score), inject into the system prompt as "Past posts from this channel — match this voice."
- **Pre-built defaults:** 5 templates shipped with the codebase at `prompts/voice_defaults/`:
  - `python.md`
  - `devops.md`
  - `ai_ml.md`
  - `backend.md`
  - `security.md`
- User picks one default at onboarding; the default seeds the `examples` list with 3–5 archetype posts and a description of tone/cadence.
- As the user labels real posts (≥👍 / ≥👎 inline keyboard responses), examples accumulate. After 10 user-labeled posts, defaults are de-emphasized (weight=0.3); after 20, defaults are dropped entirely.
- **Re-tune command:** `/retune` admin command samples the last N approved posts and rebuilds the example set. Owner-triggered, not automatic.

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
