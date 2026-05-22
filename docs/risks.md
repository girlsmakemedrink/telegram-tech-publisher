# Risk register

- **Last reviewed:** 2026-05-22 (iter-27 bootstrap)
- **Review cadence:** end of every iter (during retro)
- **Source:** ported from `_validation_summary.md` (iter-26b) `## Risk register` section. Owner-approved with `go_with_caveats`, 2026-05-22.

| # | Risk | Severity (1-5) | Mitigation | Owner |
|---|---|---|---|---|
| 1 | CIS Telegram blocking event | 4 | Build parallel English-language global dev channel track from day one; monitor blocking signals; draft a Bot API failover/geo-pivot playbook. SMMplanner's March 2026 retreat is the canary. Neither Architect nor PM modeled this scenario in their forecasts — it is an emergent cross-agent risk that could simultaneously destroy distribution and delivery. **iter-27 mitigation shipped:** `docs/playbooks/crisis_telegram_blocking.md`. | solo |
| 2 | CIS payment rail complexity (Stripe blocked in RU/BY) | 3 | Start with Telegram Stars for zero-friction MVP onboarding (accept 50% cut at early scale); initiate YooKassa legal entity setup in parallel as post-MVP track. Both Architect (complexity=4) and PM (primary churn risk) flag this independently — it is a compounding cross-agent risk. **iter-27 mitigation:** locked in `docs/adr/0003-payment-rail.md`; YooKassa parallel track is owner-side legal work, not iter-27 code. | solo |
| 3 | Break-even timeline of 12-18 months post-launch | 3 | Month-6 base case is only 48 paid users ($1,166 MRR); break-even at 324 users. $0 CAC means no acquisition burn — owner's primary income covers runway. Frame explicitly as asset-building phase, not near-term income replacement. **iter-27 mitigation:** PRD success-metrics section frames the 90-day target as 10 paying users (conservative), not break-even. | solo |
| 4 | X/Twitter source descoped from MVP (TOS violation + API cost cliff) | 2 | Implement rss.app bridge for X-sourced content and community-submitted links in MVP. Revisit X API at >3k paid users when Pro tier ($5k/mo) becomes affordable. GitHub + HN sources are sufficient for developer channels at launch. **iter-27 mitigation:** locked in `docs/adr/0002-source-priorities.md`; rss.app bridge deferred to post-iter-29 RSS landing. | solo |
| 5 | Voice onboarding friction (requires 10-20 labeled past posts) | 2 | Pre-build developer-channel voice defaults to eliminate cold-start; progressive refinement UX; 'retune from last N posts' admin command. Both Architect and PM (as churn risk) note draft quality is critical to retention. **iter-27 mitigation:** locked in `docs/adr/0004-voice-calibration.md`; 5 pre-built default templates planned for iter-28. | solo |

---

## Risks added during iter-27 (none yet)

> Append rows here as new risks emerge during execution. Each risk gets a severity (1-5), a mitigation owner, and a link to either an ADR / playbook / iter-spec that operationalizes the mitigation.
