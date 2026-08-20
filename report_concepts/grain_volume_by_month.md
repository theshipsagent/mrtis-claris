# Concept report G1 — Grain volume trended against ship count

MRTIS commit `68b3a6f` · window **2023-08-01 → 2026-07-31** (trailing 36 months, anchored on the data's last date `2026-07-31`, not on today) · scope **9 grain elevators + MGMT**

> **Read the two denominators before the numbers.** Ship count is complete: every one of the **4,254 loadings** (2,467 distinct vessels) is counted. Tonnage is not — tons exist only where an FGIS certificate matched, which is **4,001 of 4,254 loadings (94.1%)**. The tonnage column therefore measures a *subset* of the ships in the same row. Comparing tons across facilities without reading the coverage column will mislead you — see `ISSUES.md` I-2.

**Grain moved (FGIS-certified, in-scope, 36 months): 175,369,154 metric tonnes** across 4,001 certified loadings.

## G1a — Port total, by month

| Month | Loadings | Vessels | FGIS matched | Coverage | Tonnes (matched) | Tonnes / matched loading |
|---|---:|---:|---:|---:|---:|---:|
| 2023-08 | 79 | 77 | 67 | 85% | 2,540,074 | 37,912 |
| 2023-09 | 102 | 96 | 92 | 90% | 4,554,285 | 49,503 |
| 2023-10 | 118 | 115 | 111 | 94% | 5,768,027 | 51,964 |
| 2023-11 | 102 | 99 | 83 | 81% | 3,979,148 | 47,942 |
| 2023-12 | 133 | 128 | 120 | 90% | 5,528,982 | 46,075 |
| 2024-01 | 139 | 131 | 129 | 93% | 5,948,920 | 46,116 |
| 2024-02 | 111 | 108 | 98 | 88% | 4,487,605 | 45,792 |
| 2024-03 | 119 | 115 | 108 | 91% | 4,742,960 | 43,916 |
| 2024-04 | 103 | 97 | 94 | 91% | 3,718,090 | 39,554 |
| 2024-05 | 92 | 90 | 81 | 88% | 3,092,742 | 38,182 |
| 2024-06 | 87 | 85 | 79 | 91% | 2,990,977 | 37,860 |
| 2024-07 | 109 | 103 | 102 | 94% | 3,913,595 | 38,369 |
| 2024-08 | 107 | 103 | 102 | 95% | 3,964,207 | 38,865 |
| 2024-09 | 124 | 121 | 120 | 97% | 5,377,933 | 44,816 |
| 2024-10 | 138 | 133 | 132 | 96% | 6,227,470 | 47,178 |
| 2024-11 | 148 | 147 | 144 | 97% | 7,309,696 | 50,762 |
| 2024-12 | 134 | 130 | 127 | 95% | 6,221,396 | 48,987 |
| 2025-01 | 132 | 129 | 130 | 98% | 5,992,303 | 46,095 |
| 2025-02 | 122 | 116 | 119 | 98% | 5,460,494 | 45,887 |
| 2025-03 | 126 | 121 | 122 | 97% | 5,194,270 | 42,576 |
| 2025-04 | 106 | 102 | 104 | 98% | 4,006,139 | 38,521 |
| 2025-05 | 113 | 110 | 103 | 91% | 4,168,513 | 40,471 |
| 2025-06 | 112 | 111 | 103 | 92% | 3,884,411 | 37,713 |
| 2025-07 | 117 | 114 | 108 | 92% | 4,249,810 | 39,350 |
| 2025-08 | 132 | 127 | 128 | 97% | 5,109,646 | 39,919 |
| 2025-09 | 137 | 132 | 132 | 96% | 5,852,149 | 44,334 |
| 2025-10 | 131 | 127 | 122 | 93% | 5,608,499 | 45,971 |
| 2025-11 | 129 | 122 | 124 | 96% | 5,559,953 | 44,838 |
| 2025-12 | 128 | 121 | 122 | 95% | 5,755,535 | 47,177 |
| 2026-01 | 144 | 141 | 141 | 98% | 6,796,461 | 48,202 |
| 2026-02 | 117 | 114 | 113 | 97% | 5,055,722 | 44,741 |
| 2026-03 | 138 | 136 | 133 | 96% | 5,705,812 | 42,901 |
| 2026-04 | 116 | 109 | 112 | 97% | 4,679,433 | 41,781 |
| 2026-05 | 116 | 108 | 113 | 97% | 4,506,217 | 39,878 |
| 2026-06 | 101 | 98 | 95 | 94% | 3,951,701 | 41,597 |
| 2026-07 | 92 | 90 | 88 | 96% | 3,465,979 | 39,386 |

## G1b — By elevator (and MGMT), full window

| Facility | Type | Loadings | Vessels | FGIS matched | Coverage | Tonnes (matched) | Tonnes / matched loading |
|---|---|---:|---:|---:|---:|---:|---:|
| Zen-Noh | Elevator | 834 | 699 | 831 | 99.6% | 43,685,012 | 52,569 |
| ADM AMA | Elevator | 588 | 490 | 558 | 94.9% | 21,336,549 | 38,238 |
| ADM Destrehan | Elevator | 523 | 427 | 460 | 88.0% | 11,804,877 | 25,663 |
| Cargill Reserve | Elevator | 487 | 420 | 465 | 95.5% | 20,676,682 | 44,466 |
| Cargill Westwego | Elevator | 383 | 353 | 380 | 99.2% | 19,996,519 | 52,622 |
| CHS Myrtle Grove | Elevator | 362 | 324 | 362 | 100.0% | 13,564,880 | 37,472 |
| ADM Reserve | Elevator | 342 | 319 | 341 | 99.7% | 19,384,677 | 56,847 |
| Bunge Destrehan | Elevator | 306 | 278 | 262 | 85.6% | 10,738,785 | 40,988 |
| LDC Port Allen | Elevator | 227 | 202 | 226 | 99.6% | 10,114,606 | 44,755 |
| MGMT | Mid-Stream | 144 | 130 | 58 | 40.3% | 1,449,141 | 24,985 |
| ARTCO Destrehan Buoys | Mid-Stream | 58 | 58 | 58 | 100.0% | 2,617,426 | 45,128 |

> **MGMT's coverage is the outlier.** At 40.3% it is roughly half the elevators' rate, so its tonnes-per-loading is not comparable with theirs. The gap is a certificate-matching gap, not a trade difference. Ship count for MGMT is sound; tonnage is a partial view.

## G1c — Certified grain vs grain by-product

**Ruled by William, 2026-08-20:** *"mgmt is grain and by products."* MRTIS now carries `cargo_subgroup`, so the grain group can be split where the evidence allows it — and only there.

Read the three columns as three different statements. `Certified grain` is **proven** by an FGIS certificate. `By-product` is **declared by the berth** in MRTIS's zone dictionary, not inferred from a missing certificate. `Not known` is exactly that — a certificate that did not match, at a berth that has declared nothing, so the cargo could be either.

| Facility | Loadings | Certified grain | By-product (declared) | Not known |
|---|---:|---:|---:|---:|
| Zen-Noh | 834 | 831 | · | 3 |
| ADM AMA | 588 | 558 | · | 30 |
| ADM Destrehan | 523 | 460 | · | 63 |
| Cargill Reserve | 487 | 465 | · | 22 |
| Cargill Westwego | 383 | 380 | · | 3 |
| CHS Myrtle Grove | 362 | 362 | · | · |
| ADM Reserve | 342 | 341 | · | 1 |
| Bunge Destrehan | 306 | 262 | · | 44 |
| LDC Port Allen | 227 | 226 | · | 1 |
| MGMT | 144 | 58 | 86 | · |
| ARTCO Destrehan Buoys | 58 | 58 | · | · |

> **Only MGMT declares by-product**, and it is the only berth in scope where the uncertified remainder has a known identity — 86 loadings in this window. The elevators' unmatched loadings stay `Not known` rather than being relabelled: 167 of them. Calling those by-product would have invented a cargo type at nine grain elevators, which is precisely what the per-berth declaration exists to prevent.

> **This changes what a grain ship-count means at MGMT.** Before the split, all of its loadings counted as grain. They are still all *cargo* at a grain berth — the fee and the berth activity are unaffected — but a report about the **grain trade** should now use the certified column, and a report about **berth activity** should use loadings.

## G1d — Loadings by facility and year

| Facility | 2023 loadings | 2024 loadings | 2025 loadings | 2026 loadings |
|---|---:|---:|---:|---:|
| Zen-Noh | 122 | 284 | 280 | 148 |
| ADM AMA | 63 | 209 | 206 | 110 |
| ADM Destrehan | 65 | 156 | 191 | 111 |
| Cargill Reserve | 55 | 161 | 163 | 108 |
| Cargill Westwego | 54 | 116 | 134 | 79 |
| CHS Myrtle Grove | 39 | 102 | 156 | 65 |
| ADM Reserve | 45 | 126 | 110 | 61 |
| Bunge Destrehan | 43 | 96 | 105 | 62 |
| LDC Port Allen | 30 | 77 | 77 | 43 |
| MGMT | 12 | 62 | 45 | 25 |
| ARTCO Destrehan Buoys | 6 | 22 | 18 | 12 |

> 2023 and 2026 are **part years** — the window opens 1 Aug 2023 and closes 31 Jul 2026, so each shows five and seven months respectively. Only 2024 and 2025 are whole calendar years and only those two are comparable like for like.

