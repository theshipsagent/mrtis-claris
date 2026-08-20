# Sample report: Agency fee by vessel type

MRTIS commit `0c4ed0c` · billable basis = one fee per leg with a berth stop (docs/BUSINESS_RULES.md §9).

**Total billable agency fee: $272,660,000**

> **Vessel type is taken from the ships register, not from the feed.** William, 2026-08-20: *"the source data [got] the ship type wrong, gas are considered tankers, but we added the ships register, so can pick up the rest of the lng tankers."* The feed types **529 of 1,467 gas-carrier calls (36%) as `Tanker`** — 425 LPG and 104 LNG — so a by-type report built on the feed alone understates Gas by 56% in calls and 64% in fee. **No fee moves:** Gas and Tanker both price at $3,500, so this is a reclassification between rows and the billable total is unchanged. See `report_concepts/ISSUES.md` I-18.

Two averages are given because two denominators are in play. Most vessel
types include calls that never berthed and so never billed; averaging over
all calls and averaging over fee-bearing calls give materially different
answers, and only the second is the average fee of an actual job.

| Vessel type | Port calls | Fee-bearing calls | Legs | Billable fee | Per-departure (comparison) | Avg fee / fee-bearing call | Avg fee / call |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bulk | 21,565 | 20,924 | 23,195 | $220,193,500 | $268,978,500 | $10,523 | $10,211 |
| Tanker | 12,610 | 12,141 | 12,610 | $42,493,500 | $57,452,500 | $3,500 | $3,370 |
| Gas | 1,471 | 1,192 | 1,471 | $4,172,000 | $4,235,000 | $3,500 | $2,836 |
| Passenger | 1,047 | 1,042 | 1,047 | $2,605,000 | $3,752,000 | $2,500 | $2,488 |
| Container | 3,138 | 3,125 | 3,138 | $2,346,500 | $11,291,000 | $751 | $748 |
| (unknown) | 198 | 79 | 202 | $417,500 | $479,500 | $5,285 | $2,109 |
| Other | 85 | 72 | 85 | $252,000 | $346,500 | $3,500 | $2,965 |
| Reefer | 56 | 36 | 56 | $180,000 | $157,500 | $5,000 | $3,214 |

The per-departure column sums `port_call.agency_fee_departures_total` — the
**call-level** roll-up, $346,692,500. The event-level frozen basis is $349,527,500, $2,835,000 higher: the difference is the fee on
360 departure events that never landed in a call, which a call-level column structurally cannot hold
(MRTIS OPEN_QUESTIONS.md §11.2, ruled: leave as is).
