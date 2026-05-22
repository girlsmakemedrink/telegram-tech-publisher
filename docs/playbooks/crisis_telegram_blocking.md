# Crisis playbook — Telegram blocking in RU/BY

- **Status:** v1 (iter-27)
- **Last reviewed:** 2026-05-22
- **Review cadence:** every 6 months, OR within 7 days of any orange-tier trigger signal
- **Decision authority:** owner (no committee; this is a solo product)
- **Why this exists:** owner-required caveat #2 from iter-26b validation. Both distribution moat AND product-delivery mechanism depend on Telegram remaining unblocked in RU/BY. If Telegram is blocked, the business simultaneously loses (a) channel growth (no in-network referrals), (b) draft delivery (Bot API unreachable), and (c) revenue (Telegram Stars unreachable). This is the single highest-severity risk in the product per QA's risk register.

---

## Trigger signals

We watch for three signal classes. Detection is mostly manual at MVP; iter-32+ may automate signal-monitor cron jobs.

### Class 1 — Regulatory

- Roskomnadzor public announcements about Telegram blocking (track via official RKN channels + Russian tech press).
- New Russian federal laws targeting messaging platforms.
- Belarusian Ministry of Information actions against Telegram.
- Owner reads RU tech press 2x/week as baseline ops.

### Class 2 — Operational telemetry (build in iter-32+)

- Sudden drop in Telegram Bot API success rate from our worker (`5xx` rate >5% sustained 15 min).
- Sudden drop in webhook delivery success rate (`getUpdates` returning empty for >30 min when prior baseline was non-empty).
- Sustained latency spike on Bot API calls from RU/BY-hosted infra (>3x baseline).
- These thresholds are placeholders; calibrate after 30 days of baseline metrics post-launch.

### Class 3 — Ecosystem canaries

- SMMplanner-style retreats (already happened: March 2026). Watch for *other* SMM/dev-tool vendors publicly de-prioritizing Telegram.
- Mass-block reports in RU/BY dev Telegram channels (subjective signal — owner reads ~10 dev channels daily as part of distribution work, sees this organically).
- VPN-usage spike reports in RU/BY (TASS, Kommersant publish these sporadically).

---

## Severity tiers

| Tier | Definition | Owner action |
|---|---|---|
| **Green** | No signals in 90 days | Continue normal ops |
| **Yellow** | One regulatory rumor OR one ecosystem canary in past 30 days | Increase signal-watching to weekly; verify VPN-equivalent failover path works (manual test) |
| **Orange** | Operational telemetry confirms partial blocking (Bot API success drops 10–30% in a 7-day window) OR regulatory announcement of intent to block | Activate Bot API failover (see below); pause user growth marketing; notify existing users of "service may be degraded" |
| **Red** | Full Telegram blocking confirmed (Bot API success drops >50%) OR official RU/BY block order published | Activate English-channel pivot (see below); refund unused Telegram Stars subscription days; notify users via email + alternative comm channel |

---

## Quantitative pivot criteria (Red → English-channel pivot)

The English-channel pivot is the irreversible business decision. Trigger ALL of:

1. **Sustained CIS Bot API success rate <50% for 7 consecutive days** AND
2. **CIS new-user signup rate down >70% week-over-week** AND
3. **No public announcement from Telegram or RU regulators of restoration within 14 days**

Two of three is YELLOW (monitor). Three of three is RED (activate pivot).

---

## English-channel pivot plan

Pre-built so we can activate within 1 week, not 4–8 weeks. **Not built as code in iter-27 — just documented.** Build trigger: orange-tier event.

### What pre-exists
- Code already supports English-language voice defaults (5 templates per ADR-0004). One additional `english_dev.md` template suffices.
- Code already supports GitHub releases + HN sources (no Russian-language source assumption).
- MarkdownV2 escaping is language-agnostic.
- Postgres schema has no `language` constraint on any field.

### What activation requires
- New English-language landing page (deferred until trigger).
- Distribution: owner's English-speaking dev network on X, GitHub, Discord. ~10% of current CIS network reach, growing over time.
- Pricing: keep $15/$29/$59 tiers; payment switches from Telegram Stars to Stripe (Stripe NOT blocked outside RU/BY). Telegram Stars stays as one option for still-served CIS users via VPN.
- Marketing: target US/EU dev Telegram channels (smaller than CIS but exists, ~3000–5000 channels with 500+ subs per the MR scan).

### Cost / time to activate
- Engineering: ~1 week (landing page + Stripe integration).
- Owner-time: ~2 weeks of outreach to seed first 10 English-channel users.
- Total: ~3-week pivot window from Red trigger to first English-channel revenue. Acceptable.

---

## Bot API failover

Telegram Bot API may degrade before a full block (rate-limiting, regional routing changes). Fallback hierarchy:

1. **Primary:** standard `api.telegram.org` Bot API.
2. **Fallback A (Orange tier):** route Bot API calls through a VPN-equivalent egress (e.g., a small VPS in NL/DE). This eats latency but preserves delivery.
3. **Fallback B (Red tier, partial):** switch from Bot API to MTProto via `telethon` for outbound publishes. This is a different auth model (user-account not bot-account) — significantly more code work; estimated 2 weeks. Treat as last-resort.
4. **Fallback C (Red tier, full):** if all Telegram routes are dead, fall back to email-digest delivery. Build in iter-33+; not in iter-27 scope.

---

## Drill cadence

- **Quarterly tabletop:** owner walks through this document, updates anything stale.
- **Annual live drill:** simulate Red trigger — route Bot API through Fallback A egress for one full day, verify metrics, write a one-page postmortem.
- **Trigger drill:** within 7 days of any orange-tier signal, re-read this doc + verify each fallback is still feasible (deps installed, VPS available, etc.).

---

## What this playbook explicitly does NOT cover

- Full business pivot away from Telegram entirely (e.g., to Discord or Slack). That's a product redesign, not a crisis response.
- Legal response to a court order. Owner consults a lawyer when/if that becomes relevant; this playbook covers operational continuity, not legal.
- Customer communication tone / wording — write fresh when needed; templating crisis comms ages badly.

---

## Open questions

1. **VPN egress vendor for Fallback A:** Hetzner NL vs. DigitalOcean DE vs. Vultr Tokyo. Resolve at iter-32 ops setup.
2. **MTProto migration cost:** Is `telethon` mature enough to replace `python-telegram-bot` for outbound publishing? Spike at orange-tier trigger; do not pre-build.
3. **Refund mechanics on Telegram Stars:** Can we batch-refund all active subscriptions in a Red event? Telegram API research deferred until needed.
