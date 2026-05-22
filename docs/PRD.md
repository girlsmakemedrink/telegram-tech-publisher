# Product Requirements — telegram-tech-publisher

> **Status:** v1 (iter-27 bootstrap, 2026-05-22)
> **Source of truth:** `docs/products/telegram-tech-publisher/_validation_summary.md` in the [ai_team repo](https://github.com/girlsmakemedrink/ai_team/tree/main/docs/products/telegram-tech-publisher), owner-approved `go_with_caveats` on 2026-05-22.
> **Validators (upstream):** competitors scan (MR), tech-risk register (Architect), revenue model (PM), synthesis (QA) — all under the same path.

---

## Problem

Russian-speaking backend / DevOps / AI engineers running technical Telegram channels (500–50k subscribers) spend 30–60 minutes/day sourcing material from GitHub releases, Hacker News, and developer feeds, rewriting it into their channel's voice, and formatting for Telegram MarkdownV2. The work is repetitive but high-stakes: a poorly worded post loses subscriber trust in a tight, code-literate audience. No existing tool serves them. Western schedulers (Buffer, Hootsuite, Typefully, SocialBee, Hypefury — 6 of the leading 15 competitors scanned) have **zero Telegram support**. Global Telegram-aware tools (Postly, PostSyncer, Social Champ) ship generic AI that produces marketing captions, not technically accurate developer posts. CIS-native SMM tools (SMMplanner, SmmBox, PostMyPost) target brand-agency workflows for non-technical accounts, and SMMplanner publicly retreated from Telegram in March 2026.

The CIS developer-influencer is paying $0 for purpose-built tooling today (Notion at $8/month is the closest substitute) and earning $0–500/month from sponsorships on a 30–60 min/day investment. The market is **structurally underserved** per the competitive scan: zero competitors combine Telegram publishing, code-aware AI drafting, and developer-source curation for this buyer.

---

## Solution

A Python service that polls GitHub releases + Hacker News on a schedule, runs a Haiku-tier relevance filter against each channel's interest taxonomy, drafts in the channel's voice with Sonnet 4.6 + few-shot from 10–20 user-labeled past posts (with pre-built developer-channel defaults to eliminate cold-start), formats for Telegram MarkdownV2 (with Telegra.ph fallback for long-form), and publishes via the Telegram Bot API on a per-user schedule respecting per-user timezone. Owner reviews drafts in a "ready for publish" queue inside Telegram itself (one bot command per channel). Three drafts per day at the entry tier is the calibration anchor — enough to keep a small channel alive, low enough to fit a $15 ARPU.

---

## MVP scope (locked, do not expand)

These items are in scope for the first revenue-bearing release. Anything not listed is out of scope (see next section).

- **Sources:** GitHub releases polling (per-channel repo list) + Hacker News (per-channel topstories filter via Haiku-tier classifier). RSS support deferred to iter-29+.
- **Channels:** Single channel per user. Multi-channel is a Studio-tier upsell post-launch.
- **Drafts per day:** 3 (configurable: 1 / 3 / 5 by tier).
- **Voice calibration:** 10–20 user-labeled past posts + 5 pre-built developer-channel voice defaults (Python/DevOps/AI-ML/backend/security niches). User picks one default at onboarding, then progressively refines via labeled posts.
- **Publishing:** Telegram Bot API + Telegra.ph fallback for posts exceeding 4096 chars. MarkdownV2 escaping required for every outbound message.
- **Approval flow:** Each draft goes to a per-user "review queue" Telegram channel (owner adds the bot). User approves / edits / rejects via inline keyboard buttons. Approved drafts publish to the target channel on schedule.
- **Payment:** Telegram Stars (50% Telegram cut accepted at MVP scale). YooKassa as a parallel legal-entity track for post-MVP (owner-side workstream).
- **Multi-tenancy:** Single Postgres, row-level keyed on `user_id`. GitHub tokens encrypted at rest (Fernet). Voice samples stored as JSONB.

## Out of scope for MVP (explicit)

- **X/Twitter source:** TOS-prohibited scraping; API v2 Basic ($100/mo) caps at ~50–100 users. rss.app bridge as placeholder; revisit X API at >3000 paying users when $5k/mo Pro tier becomes affordable.
- **RSS source:** Deferred to iter-29+. Charset sniffing (Win1251 / KOI8-R) and malformed-feed handling adds non-trivial scope.
- **Free tier:** $0 hobbyist tier is in the pricing model but the conversion-funnel mechanics (rate-limited drafts, weekly upsell prompts) deferred to post-MVP iteration.
- **Multi-channel / Studio tier:** Single channel only at launch.
- **YooKassa integration:** Awaiting owner's legal entity setup. Telegram Stars is the only payment rail at MVP.
- **Voice fine-tuning / embeddings retrieval:** Few-shot is sufficient for v1 per the architect's analysis (complexity-3, premature otherwise).
- **CryptoPay (USDT) payment rail:** Niche audience, deferred.
- **English-channel pivot product:** Pre-built in the crisis playbook but not built as code until activated.

---

## Success metrics (90 days post-launch)

| Metric | Target | Source of truth |
|---|---|---|
| Paying users | 10 | Stripe (no, wait — Telegram Stars admin panel) |
| Conversion rate from trial to paid | 5%+ | Internal app metrics |
| Post-approval rate (drafts user approves vs rejects) | 90%+ | Internal app metrics |
| LLM opex per user per day | <$0.30 | Anthropic billing rollup |
| P95 publish latency (draft-ready → channel-sent post user approval) | <30s | Application logs |
| Churn (paying user → cancel within 30 days) | <10% monthly | Telegram Stars admin panel |

90-day target of 10 paying users is intentionally conservative. It maps to the QA-flagged 12–18 month runway to break-even (324 users), with the first 90 days dominated by owner's CIS-network direct outreach.

---

## Pricing

Four tiers per PM revenue model (see `revenue.md`). Anchored against competitor pricing rather than cost-plus.

| Tier | $/month | Drafts/day | Sources | Channels | Notes |
|---|---|---|---|---|---|
| Free | $0 | 1 | 1 | 1 | Acquisition funnel. Telegram Stars not required (web onboarding only). Post-MVP. |
| Starter | $15 | 3 | 3 | 1 | MVP default tier. CIS-friendly price point. |
| Pro | $29 | 5 | 10 | 1 | For 2k–50k channels with sponsorship income. Adds voice-tuning runs. |
| Studio | $59 | 10 | unlimited | multi | Post-MVP. Multi-channel agency tier. |

ARPU at the Starter+Pro mix is $24.30. LTV is ~$405 (gross margin 69–70% × average retention 24 months). CAC is $0 via owner's CIS Telegram channel network.

---

## Top risks (full register: `docs/risks.md`)

1. **CIS Telegram blocking event (severity 4)** — both distribution moat AND product-delivery channel die simultaneously. Mitigation: crisis playbook drafted pre-launch (`docs/playbooks/crisis_telegram_blocking.md`), parallel English-channel pivot pre-built, Bot API failover documented. SMMplanner's March 2026 retreat is the canary.
2. **CIS payment rail complexity (severity 3)** — Stripe blocked in RU/BY. Mitigation: Telegram Stars committed as MVP rail (zero-friction, 50% cut accepted); YooKassa legal-entity track in parallel for post-MVP. Owner already initiated legal-entity setup.
3. **Break-even at 324 users requires 12–18 months (severity 3)** — month-6 base-case MRR is $1166 (~48 paid users); $0 CAC means no runway burn but owner must treat this as asset-building phase, not income replacement. Owner's primary income covers runway.

---

## Caveats (owner-required, locked at iter-26b approval)

1. **Telegram Stars as primary MVP payment rail.** YooKassa is the post-MVP track once legal entity is established. CryptoPay rejected. See `docs/adr/0003-payment-rail.md`.
2. **Crisis playbook drafted before launch.** Covers monitoring signals, English-channel pivot criteria, Bot API failover logic, and drill cadence. See `docs/playbooks/crisis_telegram_blocking.md`.

---

## Build timeline

QA estimate: 8–12 weeks solo build window from iter-27 wrap. Iteration plan (rough — locked at iter-27 wrap, refined per-iter):

| Iter | Focus | Done criteria |
|---|---|---|
| 27 | Bootstrap (this iter) | Repo + PRD + ADRs + crisis playbook + 2 smoke pipelines |
| 28 | LLM voice drafting | Sonnet 4.6 few-shot drafter takes a `Candidate` + voice samples → markdown draft; ≥10 unit tests, ≥3 integration tests against real LLM |
| 29 | Scheduler + queue | Postgres-as-queue + APScheduler; per-user timezone; exponential backoff; idempotency on worker restart |
| 30 | Multi-tenant + onboarding | User model, voice-sample upload, channel-link flow, source config UI (bot-driven, no web UI yet) |
| 31 | Telegram Stars payment | Subscription state machine, monthly invoice re-issuance, free → starter conversion |
| 32 | First-10 paying-user push | Owner direct outreach via CIS dev-channel network, retention dashboards, churn analysis |
| 33+ | Polish + scale | YooKassa integration when legal entity ready, RSS source, multi-channel Studio tier |

Total wall-clock target: end-of-iter-32 = first 10 paying users = ~12 weeks from iter-27 start (2026-05-22 + 12w ≈ 2026-08-14). This is the QA-blessed upper bound; aim for end-of-iter-31 = ~10 weeks = ~2026-07-31 if no scope surprises.

---

## Out-of-scope reminders (do not let scope creep)

The following appear in adjacent thinking but are NOT in iter-27..32 MVP scope:
- Web UI / dashboard. Bot inline keyboards are the only UX.
- Push notifications outside Telegram. Telegram itself is the notification mechanism.
- Analytics dashboard for users (their channel performance). Telegram already shows this.
- Multi-language drafting beyond Russian + English defaults. Other CIS languages (Ukrainian, Kazakh) are post-MVP.
- LLM fine-tuning per user. Few-shot is sufficient.
- A/B testing infrastructure for draft variants. Premature.
- Public API. Telegram is the API.
- Marketplace for voice templates. Premature.

---

## Open questions (resolve before iter-30)

1. **Per-channel onboarding UX:** What's the minimum interaction count to get a new user from `/start` → first scheduled post? Target ≤10 messages.
2. **Free tier:** Whether to ship it at all in MVP, or skip directly to Starter. Decision deadline: iter-30 start.
3. **Telegram Stars refund policy:** Telegram allows refunds within 21 days. What's our service policy? Decision deadline: iter-31 start.
4. **CIS legal entity:** What form (IP vs OOO) is required for YooKassa? Affects 2026 H2 timeline. Owner-side workstream.
