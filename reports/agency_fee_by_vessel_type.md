# Sample report: Agency fee by vessel type

MRTIS commit `95ff34b` · billable basis = one fee per leg with a berth stop (docs/BUSINESS_RULES.md §9).

**Total billable agency fee: $274,869,500**

> **Vessel type is taken from the ships register, not from the feed.** William, 2026-08-20: *"the source data [got] the ship type wrong, gas are considered tankers, but we added the ships register, so can pick up the rest of the lng tankers."* The feed types **529 of 1,467 gas-carrier calls (36%) as `Tanker`** — 425 LPG and 104 LNG — so a by-type report built on the feed alone understates Gas by 56% in calls and 64% in fee. **No fee moves:** Gas and Tanker both price at $3,500, so this is a reclassification between rows and the billable total is unchanged. See `report_concepts/ISSUES.md` I-18.

Two averages are given because two denominators are in play. Most vessel
types include calls that never berthed and so never billed; averaging over
all calls and averaging over fee-bearing calls give materially different
answers, and only the second is the average fee of an actual job.

| Vessel type | Port calls | Fee-bearing calls | Legs | Billable fee | Per-departure (comparison) | Avg fee / fee-bearing call | Avg fee / call |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bulk | 21,685 | 21,102 | 23,331 | $222,087,500 | $271,341,000 | $10,524 | $10,242 |
| Tanker | 12,658 | 12,218 | 12,658 | $42,763,000 | $57,816,500 | $3,500 | $3,378 |
| Gas | 1,473 | 1,196 | 1,473 | $4,186,000 | $4,249,000 | $3,500 | $2,842 |
| Passenger | 1,045 | 1,043 | 1,045 | $2,607,500 | $3,755,500 | $2,500 | $2,495 |
| Container | 3,145 | 3,139 | 3,145 | $2,357,000 | $11,343,500 | $751 | $749 |
| (unknown) | 207 | 83 | 211 | $431,500 | $514,500 | $5,199 | $2,085 |
| Other | 85 | 72 | 85 | $252,000 | $346,500 | $3,500 | $2,965 |
| Reefer | 57 | 37 | 57 | $185,000 | $161,000 | $5,000 | $3,246 |

The per-departure column sums `port_call.agency_fee_departures_total` — the
**call-level** roll-up, $349,527,500. The event-level frozen basis is $349,527,500, $0 higher: the difference is the fee on
0 departure events that never landed in a call, which a call-level column structurally cannot hold
(MRTIS OPEN_QUESTIONS.md §11.2, ruled: leave as is).
