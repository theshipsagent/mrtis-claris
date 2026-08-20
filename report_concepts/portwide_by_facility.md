# Concept report P1 — Port calls and agency revenue, by facility and by agency

MRTIS commit `95ff34b` · window **2023-08-01 → 2026-07-31** (trailing 36 months, anchored on the data's last date) · **every vessel, every cargo, whole port**

Ruled by William, 2026-08-20: *"the fee's apply to every ship... the second sample test will be total port calls by facility and agency against count and rev$ as we don't yet have all cargoes into split out by cargo."* So there is **no cargo dimension here** — cargo is carried on only 67% of legs port-wide and is well-evidenced only for grain, so splitting by it would report coverage as if it were trade.

## The window at a glance

| Measure | Value |
|---|---:|
| Port calls | 16,237 |
| Legs (berth visits — the unit revenue is earned in) | 16,867 |
| Distinct vessels | 6,254 |
| Chargeable legs | 16,208 |
| **Agency revenue** | **$110,546,250** |
| Facilities with activity | 103 |
| Agencies with activity | 36 |

> **Two counts, on purpose.** A split call works more than one berth, so it appears under each facility it visited. `Port calls` therefore does **not** sum down the facility column — the leg does. Revenue is per leg (`docs/BUSINESS_RULES.md` §9), so the revenue column *does* sum, exactly, to $110,546,250. That is asserted by the build, not asserted in prose.

## P1a — By facility (top 25 of 103 by revenue; full list in `portwide_by_facility.csv`)

| Facility | Type | Port calls | Legs | Vessels | Chargeable | Revenue | Avg / chargeable leg | Share |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Zen-Noh | Elevator | 835 | 835 | 699 | 835 | $8,767,500 | $10,500 | 7.9% |
| ADM AMA | Elevator | 589 | 589 | 491 | 589 | $6,177,500 | $10,488 | 5.6% |
| ADM Destrehan | Elevator | 525 | 525 | 429 | 525 | $5,505,500 | $10,487 | 5.0% |
| Cargill Reserve | Elevator | 487 | 487 | 420 | 487 | $5,106,500 | $10,486 | 4.6% |
| Cooper Darrow | Mid-Stream | 485 | 486 | 400 | 486 | $5,096,000 | $10,486 | 4.6% |
| Cargill Westwego | Elevator | 384 | 384 | 354 | 384 | $4,032,000 | $10,500 | 3.6% |
| CHS Myrtle Grove | Elevator | 363 | 363 | 325 | 363 | $3,811,500 | $10,500 | 3.4% |
| AST St James | Mid-Stream | 352 | 353 | 329 | 353 | $3,706,500 | $10,500 | 3.4% |
| ADM Reserve | Elevator | 343 | 343 | 320 | 343 | $3,601,500 | $10,500 | 3.3% |
| UBT Davant | Bulk Cargo | 325 | 325 | 297 | 325 | $3,412,500 | $10,500 | 3.1% |
| Convent Marine Terminal | Bulk Cargo | 308 | 308 | 281 | 308 | $3,234,000 | $10,500 | 2.9% |
| Bunge Destrehan | Elevator | 306 | 306 | 278 | 306 | $3,213,000 | $10,500 | 2.9% |
| Mile 110 Buoys | Mid-Stream | 292 | 292 | 274 | 292 | $3,059,000 | $10,476 | 2.8% |
| AST Meraux Buoys | Mid-Stream | 289 | 290 | 273 | 290 | $3,038,000 | $10,476 | 2.7% |
| ARTCO Destrehan Buoys | Mid-Stream | 236 | 236 | 227 | 236 | $2,471,000 | $10,470 | 2.2% |
| LDC Port Allen | Elevator | 228 | 228 | 203 | 228 | $2,394,000 | $10,500 | 2.2% |
| Nashville Ave | General Cargo | 1,356 | 1,356 | 411 | 1,356 | $2,330,250 | $1,718 | 2.1% |
| Reserve Buoys | Mid-Stream | 205 | 205 | 195 | 205 | $2,152,500 | $10,500 | 1.9% |
| Valero St Charles | Refinery | 583 | 583 | 431 | 583 | $2,040,500 | $3,500 | 1.8% |
| IMTT St Rose | Tank Storage | 573 | 573 | 384 | 573 | $2,005,500 | $3,500 | 1.8% |
| ABT Burnside | Bulk Cargo | 171 | 171 | 161 | 171 | $1,795,500 | $10,500 | 1.6% |
| AST Chalmette Slip | General Cargo | 351 | 354 | 243 | 354 | $1,770,000 | $5,000 | 1.6% |
| MGMT | Mid-Stream | 144 | 144 | 130 | 144 | $1,512,000 | $10,500 | 1.4% |
| AST Chalmette Buoys | Mid-Stream | 136 | 136 | 114 | 136 | $1,428,000 | $10,500 | 1.3% |
| Exxon Baton Rouge | Refinery | 394 | 394 | 255 | 394 | $1,379,000 | $3,500 | 1.2% |

## P1b — By agency (all 36, by revenue)

| Agency | Port calls | Legs | Vessels | Facilities served | Chargeable | Revenue | Avg / chargeable leg | Share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Norton Lilly | 2,928 | 3,012 | 1,559 | 63 | 2,858 | $17,288,500 | $6,049 | 15.6% |
| Southport | 1,661 | 1,680 | 1,262 | 56 | 1,659 | $16,258,500 | $9,800 | 14.7% |
| HOST | 1,769 | 1,874 | 1,381 | 58 | 1,803 | $15,329,000 | $8,502 | 13.9% |
| Blue Water | 1,002 | 1,058 | 842 | 31 | 1,042 | $10,909,000 | $10,469 | 9.9% |
| Gulf Inland | 669 | 717 | 456 | 52 | 705 | $5,636,000 | $7,994 | 5.1% |
| General Steamship | 656 | 720 | 526 | 52 | 670 | $5,413,500 | $8,080 | 4.9% |
| Tricon | 634 | 686 | 431 | 42 | 682 | $4,926,500 | $7,224 | 4.5% |
| Nova | 443 | 450 | 356 | 21 | 441 | $4,623,500 | $10,484 | 4.2% |
| General Maritime | 465 | 483 | 219 | 47 | 476 | $3,487,500 | $7,327 | 3.2% |
| Newship | 335 | 366 | 242 | 17 | 362 | $3,392,500 | $9,372 | 3.1% |
| Bertel | 820 | 820 | 425 | 37 | 803 | $2,810,500 | $3,500 | 2.5% |
| Inchcape | 711 | 714 | 336 | 48 | 695 | $2,422,500 | $3,486 | 2.2% |
| NordSud | 270 | 314 | 195 | 30 | 311 | $2,035,500 | $6,545 | 1.8% |
| GAC | 705 | 705 | 358 | 32 | 561 | $1,998,500 | $3,562 | 1.8% |
| Moran Shipping | 410 | 421 | 305 | 39 | 415 | $1,760,500 | $4,242 | 1.6% |
| Celtic | 230 | 252 | 106 | 28 | 251 | $1,681,500 | $6,699 | 1.5% |
| Biehl | 341 | 344 | 174 | 26 | 322 | $1,138,250 | $3,535 | 1.0% |
| NolaPort | 450 | 450 | 11 | 2 | 450 | $1,125,000 | $2,500 | 1.0% |
| Capes | 142 | 149 | 129 | 33 | 146 | $1,001,000 | $6,856 | 0.9% |
| Gulf Harbor | 208 | 209 | 163 | 27 | 207 | $871,500 | $4,210 | 0.8% |
| Riverside | 74 | 82 | 68 | 14 | 82 | $751,000 | $9,159 | 0.7% |
| K3 Maritime | 180 | 180 | 151 | 19 | 178 | $630,000 | $3,539 | 0.6% |
| Navigo | 57 | 57 | 57 | 10 | 57 | $598,500 | $10,500 | 0.5% |
| VertomCory | 179 | 179 | 20 | 5 | 169 | $593,000 | $3,509 | 0.5% |
| (no agency) | 201 | 201 | 72 | 40 | 133 | $577,500 | $4,342 | 0.5% |
| Valhalla | 108 | 109 | 81 | 16 | 107 | $555,500 | $5,192 | 0.5% |
| Maritime Endeavors | 86 | 86 | 80 | 22 | 85 | $400,000 | $4,706 | 0.4% |
| Lott | 110 | 110 | 7 | 5 | 109 | $381,500 | $3,500 | 0.3% |
| Mentz | 30 | 30 | 30 | 4 | 30 | $315,000 | $10,500 | 0.3% |
| Wilhelmsen | 43 | 47 | 42 | 17 | 45 | $309,000 | $6,867 | 0.3% |
| Fillette Green | 43 | 44 | 31 | 18 | 44 | $282,000 | $6,409 | 0.3% |
| Riverbend | 77 | 77 | 59 | 9 | 76 | $266,000 | $3,500 | 0.2% |
| Lighthouse | 67 | 67 | 63 | 13 | 67 | $234,500 | $3,500 | 0.2% |
| Seaport Hub | 69 | 69 | 54 | 9 | 65 | $227,500 | $3,500 | 0.2% |
| Riley-Sherman | 63 | 63 | 45 | 16 | 61 | $213,500 | $3,500 | 0.2% |
| Intercruises | 42 | 42 | 8 | 3 | 41 | $102,500 | $2,500 | 0.1% |

## P1c — Agency × facility

The full cross-tab is `portwide_agency_by_facility.csv` (990 populated cells of 36 × 103 possible — 26.7% density). Shown here: each agency's single largest facility by revenue, which is the shape of the book most reports actually want.

| Agency | Largest facility by revenue | Legs there | Revenue there | = share of that agency's revenue |
|---|---|---:|---:|---:|
| Norton Lilly | ADM Destrehan | 365 | $3,832,500 | 22% |
| Southport | Zen-Noh | 293 | $3,076,500 | 19% |
| HOST | Convent Marine Terminal | 256 | $2,688,000 | 18% |
| Blue Water | Zen-Noh | 333 | $3,496,500 | 32% |
| Gulf Inland | Noranda Alumina | 126 | $1,323,000 | 23% |
| General Steamship | Nashville Ave | 120 | $600,000 | 11% |
| Tricon | ARTCO Destrehan Buoys | 61 | $640,500 | 13% |
| Nova | Cargill Reserve | 216 | $2,268,000 | 49% |
| General Maritime | PCS Nitrogen | 40 | $413,000 | 12% |
| Newship | Zen-Noh | 77 | $808,500 | 24% |
| Bertel | IMTT St Rose | 246 | $861,000 | 31% |
| Inchcape | Exxon Baton Rouge | 240 | $840,000 | 35% |
| NordSud | AST Chalmette Slip | 129 | $645,000 | 32% |
| GAC | IMTT Geismar | 161 | $563,500 | 28% |
| Moran Shipping | AST St James | 28 | $294,000 | 17% |
| Celtic | Crosstex Energy | 113 | $395,500 | 24% |
| Biehl | KM IMT Myrtle Grove | 19 | $199,500 | 18% |
| NolaPort | Erato St | 369 | $922,500 | 82% |
| Capes | Cooper Darrow | 17 | $178,500 | 18% |
| Gulf Harbor | MPLX Garyville | 43 | $150,500 | 17% |
| Riverside | ABT Burnside | 36 | $378,000 | 50% |
| K3 Maritime | Valero St Charles | 51 | $178,500 | 28% |
| Navigo | UBT Davant | 31 | $325,500 | 54% |
| VertomCory | Crosstex Energy | 123 | $430,500 | 73% |
| (no agency) | ADM Destrehan | 8 | $77,000 | 13% |
| Valhalla | IMTT St Rose | 35 | $122,500 | 22% |
| Maritime Endeavors | Valero St Charles | 18 | $63,000 | 16% |
| Lott | IMTT St Rose | 47 | $164,500 | 43% |
| Mentz | KM IMT Myrtle Grove | 25 | $262,500 | 83% |
| Wilhelmsen | AST Meraux Buoys | 5 | $52,500 | 17% |
| Fillette Green | AST St James | 6 | $63,000 | 22% |
| Riverbend | MPLX Garyville | 23 | $80,500 | 30% |
| Lighthouse | Valero St Charles | 24 | $84,000 | 36% |
| Seaport Hub | Exxon Baton Rouge | 28 | $98,000 | 43% |
| Riley-Sherman | PBF Chalmette | 17 | $59,500 | 28% |
| Intercruises | Julia St | 39 | $97,500 | 95% |

