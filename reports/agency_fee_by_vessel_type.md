# Sample report: Agency fee by vessel type

MRTIS commit `0c4ed0c` · billable basis = one fee per leg with a berth stop (docs/BUSINESS_RULES.md §9).

**Total billable agency fee: $272,660,000**

Two averages are given because two denominators are in play. Most vessel
types include calls that never berthed and so never billed; averaging over
all calls and averaging over fee-bearing calls give materially different
answers, and only the second is the average fee of an actual job.

| Vessel type | Port calls | Fee-bearing calls | Legs | Billable fee | Per-departure (comparison) | Avg fee / fee-bearing call | Avg fee / call |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bulk | 21,565 | 20,924 | 23,195 | $220,193,500 | $268,978,500 | $10,523 | $10,211 |
| Tanker | 13,139 | 12,606 | 13,139 | $44,121,000 | $59,139,500 | $3,500 | $3,358 |
| Passenger | 1,047 | 1,042 | 1,047 | $2,605,000 | $3,752,000 | $2,500 | $2,488 |
| Gas | 941 | 726 | 941 | $2,541,000 | $2,544,500 | $3,500 | $2,700 |
| Container | 3,138 | 3,125 | 3,138 | $2,346,500 | $11,291,000 | $751 | $748 |
| (unknown) | 199 | 80 | 203 | $421,000 | $483,000 | $5,263 | $2,116 |
| Other | 85 | 72 | 85 | $252,000 | $346,500 | $3,500 | $2,965 |
| Reefer | 56 | 36 | 56 | $180,000 | $157,500 | $5,000 | $3,214 |

The per-departure column sums `port_call.agency_fee_departures_total` — the
**call-level** roll-up, $346,692,500. The event-level frozen basis is $349,527,500, $2,835,000 higher: the difference is the fee on
360 departure events that never landed in a call, which a call-level column structurally cannot hold
(MRTIS OPEN_QUESTIONS.md §11.2, ruled: leave as is).
