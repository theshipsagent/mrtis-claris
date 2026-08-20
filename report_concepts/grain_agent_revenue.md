# Concept report G2 — Ship count and revenue by agent, grain berths

MRTIS commit `699a9fc` · window **2023-08-01 → 2026-07-31** · scope **9 grain elevators + MGMT** · leg-level agency (`port_call_leg.agency`) — the agency that brought the vessel in owns the leg (`docs/BUSINESS_RULES.md` §6)

**Total agency fee on grain berths, 36 months: $44,646,000** across 4,254 chargeable legs of 4,254 loadings.

## G2a — By agent, all grain berths

| Agency | Loadings | Vessels | Chargeable legs | Agency fee | Avg fee / chargeable leg | Share of fee |
|---|---:|---:|---:|---:|---:|---:|
| Southport | 1,071 | 909 | 1,071 | $11,245,500 | $10,500 | 25.2% |
| Norton Lilly | 1,032 | 817 | 1,032 | $10,836,000 | $10,500 | 24.3% |
| Blue Water | 783 | 672 | 783 | $8,221,500 | $10,500 | 18.4% |
| Nova | 392 | 315 | 392 | $4,116,000 | $10,500 | 9.2% |
| Newship | 273 | 223 | 273 | $2,866,500 | $10,500 | 6.4% |
| HOST | 177 | 167 | 177 | $1,858,500 | $10,500 | 4.2% |
| General Maritime | 156 | 97 | 156 | $1,638,000 | $10,500 | 3.7% |
| General Steamship | 135 | 120 | 135 | $1,417,500 | $10,500 | 3.2% |
| Gulf Inland | 68 | 53 | 68 | $714,000 | $10,500 | 1.6% |
| Tricon | 54 | 54 | 54 | $567,000 | $10,500 | 1.3% |
| NordSud | 28 | 24 | 28 | $294,000 | $10,500 | 0.7% |
| (no agency) | 19 | 14 | 19 | $185,500 | $9,763 | 0.4% |
| Celtic | 14 | 14 | 14 | $147,000 | $10,500 | 0.3% |
| Maritime Endeavors | 12 | 12 | 12 | $126,000 | $10,500 | 0.3% |
| Capes | 8 | 8 | 8 | $84,000 | $10,500 | 0.2% |
| Riverside | 7 | 7 | 7 | $73,500 | $10,500 | 0.2% |
| Moran Shipping | 6 | 6 | 6 | $63,000 | $10,500 | 0.1% |
| Wilhelmsen | 6 | 6 | 6 | $63,000 | $10,500 | 0.1% |
| Inchcape | 3 | 3 | 3 | $31,500 | $10,500 | 0.1% |
| Valhalla | 3 | 3 | 3 | $31,500 | $10,500 | 0.1% |
| Biehl | 2 | 2 | 2 | $21,000 | $10,500 | 0.0% |
| Fillette Green | 2 | 2 | 2 | $21,000 | $10,500 | 0.0% |
| Gulf Harbor | 2 | 2 | 2 | $21,000 | $10,500 | 0.0% |
| Bertel | 1 | 1 | 1 | $3,500 | $3,500 | 0.0% |

## G2b — Loadings by agent and facility

Fee per cell is in `grain_agent_by_facility.csv`; loadings shown here for legibility.

| Agency | Zen-Noh | ADM AMA | ADM Destrehan | C.Reserve | C.Westwego | CHS Myrtle Grove | ADM Reserve | Bunge Destrehan | LDC Port Allen | MGMT | ARTCO Destrehan | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Southport | 293 | 68 | 41 | 90 | 100 | 90 | 34 | 222 | 70 | 63 | · | 1,071 |
| Norton Lilly | 30 | 336 | 363 | 22 | 21 | 15 | 225 | 5 | 1 | · | 14 | 1,032 |
| Blue Water | 332 | 52 | 25 | 58 | 60 | 124 | 29 | 42 | 45 | 8 | 8 | 783 |
| Nova | 7 | 1 | 4 | 216 | 137 | 9 | 3 | 5 | 4 | 2 | 4 | 392 |
| Newship | 77 | 65 | 34 | 17 | 14 | 17 | 18 | 1 | 27 | 3 | · | 273 |
| HOST | 29 | 16 | 7 | 12 | 12 | 13 | 10 | 11 | 8 | 58 | 1 | 177 |
| General Maritime | 10 | 17 | 19 | 16 | 13 | 29 | 7 | 5 | 38 | 2 | · | 156 |
| General Steamship | 25 | 8 | 6 | 14 | 12 | 30 | 3 | 4 | 25 | 1 | 7 | 135 |
| Gulf Inland | 7 | 6 | 5 | 21 | 2 | 13 | 2 | 5 | 1 | 2 | 4 | 68 |
| Tricon | 6 | 6 | 2 | 7 | · | 7 | 1 | 3 | 2 | 1 | 19 | 54 |
| NordSud | 2 | 3 | 3 | 5 | 8 | · | 4 | · | · | 3 | · | 28 |
| (no agency) | 1 | 4 | 8 | 2 | · | 3 | 1 | · | · | · | · | 19 |
| Celtic | 4 | 1 | · | 2 | 1 | 3 | 1 | 2 | · | · | · | 14 |
| Maritime Endeavors | 3 | · | · | 1 | 3 | 3 | · | · | 2 | · | · | 12 |
| Capes | · | 2 | · | 2 | · | 2 | · | · | 1 | 1 | · | 8 |
| Riverside | 2 | · | · | 1 | · | · | 2 | · | 2 | · | · | 7 |
| Moran Shipping | · | 1 | 3 | · | · | 1 | · | 1 | · | · | · | 6 |
| Wilhelmsen | 1 | 1 | 1 | · | · | 1 | 2 | · | · | · | · | 6 |
| Inchcape | 3 | · | · | · | · | · | · | · | · | · | · | 3 |
| Valhalla | · | · | 1 | · | · | 1 | · | · | · | · | 1 | 3 |
| Biehl | · | 1 | · | · | · | · | · | · | 1 | · | · | 2 |
| Fillette Green | 1 | · | · | · | · | 1 | · | · | · | · | · | 2 |
| Gulf Harbor | 1 | · | 1 | · | · | · | · | · | · | · | · | 2 |
| Bertel | · | · | · | 1 | · | · | · | · | · | · | · | 1 |

> A `·` is a genuine zero — that agent did not work that berth in the window, rather than a missing value.

