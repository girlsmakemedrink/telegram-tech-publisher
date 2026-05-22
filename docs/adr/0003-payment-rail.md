# ADR-0003 — Payment rail

- **Status:** Accepted (owner-locked at iter-26b approval, 2026-05-22)
- **Date:** 2026-05-22 (iter-27)

## Context

Stripe is blocked in RU/BY (the primary MVP buyer geography). `tech_risk.md` ranked the CIS payment-rail complexity at 4/5 — second-highest in the whole architecture. Three viable options were on the table:

| Option | Pros | Cons |
|---|---|---|
| Telegram Stars | Zero-friction, in-Telegram UX, no KYC | 50% Telegram cut on every transaction |
| YooKassa (RUB) | Industry-standard CIS gateway, ~2% fees | Requires RU legal entity (IP or OOO), 4–8 week setup |
| CryptoPay (USDT) | No KYC, no fees | Niche audience; few CIS devs paid in crypto |

Owner approval comment from iter-26b pending_review `b467307c`:

> "proceed per QA recommendation; descope X from MVP, **commit to Telegram Stars payment rail upfront with parallel YooKassa legal-entity track**, draft Telegram-blocking crisis playbook before launch."

## Decision

**Telegram Stars is the only MVP payment rail.** YooKassa is a parallel post-MVP track started in iter-27 (owner-side legal work, not code), expected to land in iter-33+ once the legal entity is established. CryptoPay is rejected.

### MVP scope

- Telegram Stars used for monthly subscription invoicing.
- Telegram doesn't natively support recurring billing; we build a state machine (`subscription_state` table) that issues a fresh `sendInvoice` each billing cycle.
- Refund policy follows Telegram's 21-day window. Service policy on refunds beyond that: case-by-case at MVP (revisit at iter-31 per PRD open question #3).
- All financial state is single-source-of-truth on **our Postgres**, not Telegram. We treat Telegram Stars admin panel as a check, not a source.

### Post-MVP (iter-33+)

- YooKassa integration goes live once owner's legal entity (IP or OOO) is registered.
- Users see both rails; default to Telegram Stars; YooKassa offered as an alternative for ≥Pro tier (justifies the legal-entity friction).
- Migration of existing Stars subscribers to YooKassa is opt-in (lower fees), never forced.

## Consequences

### Positive
- Zero blockers on MVP launch — Stars is live the day the bot is registered.
- 50% cut on a $15 Starter is still 69–70% gross margin per the revenue model (LLM opex is the dominant cost, ~$0.30/user/day).
- Owner-friendly: one rail to support at MVP, one process to operationalize.

### Negative
- 50% Telegram cut is a meaningful drag on unit economics. At Studio tier ($59), absolute fee = $29.50/user/month vs YooKassa's ~$1.18/user/month. Limits us from running aggressive pricing experiments below $15 until YooKassa lands.
- Telegram-Stars-only puts all eggs in the Telegram-blocking-event basket. Mitigated by `docs/playbooks/crisis_telegram_blocking.md` — but if Telegram fully blocks in RU/BY, our payment rail dies the same day as our delivery rail. This is by design (the MVP is a Telegram-native product) but it's the dominant risk.

## Alternatives rejected

- **Stripe + Paddle fallback:** Stripe blocked in RU/BY for the primary buyer; Paddle requires similar legal entity to YooKassa with worse CIS gateway integration.
- **CryptoPay (USDT):** Considered, rejected — CIS dev audience adoption of crypto payment is <5% per owner's network sampling; UX friction (wallet install, gas understanding) higher than the legal-entity friction of YooKassa.

## References

- `tech_risk.md` (iter-26b) — payment-rail component, complexity 4
- `revenue.md` (iter-26b) — gross-margin sensitivity table
- Owner approval comment on iter-26b pending_review `b467307c`
