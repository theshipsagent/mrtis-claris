# Issues log — what building the concept reports exposed

Opened 2026-08-20 (session 8). MRTIS commit `2738601c9a87ff7be264f9c10cb1e1a618ef3436` at the time of finding; fixes built at `0c4ed0c`.

Every entry is something the reporting exercise **found**, not something it
fixed. Nothing in this log has been acted on — that is deliberate, and is the
whole reason the log exists: it is the input to a later build-fix session, so a
defect gets recorded with its evidence at the moment it is seen rather than
patched over in passing.

## How to read an entry

| Field | Meaning |
|---|---|
| **Severity** | `blocks-report` · `wrong-figure` · `gap` · `cosmetic` |
| **Where** | MRTIS pipeline, this package, or the source feed |
| **Evidence** | The query and counts that demonstrate it — reproducible, not asserted |
| **Effect on reports** | What a report has to do about it *today* |
| **Proposed fix** | For the build-fix session. A proposal only; nothing is ruled here. |

## Open issues

### I-1 · A second buoy carries the identical grain-only rule — `blocks-report`

**Severity** `blocks-report` (scope of the grain report cannot be fixed without a ruling)
**Where** MRTIS `dictionaries/zone_facility.csv`, or William's premise
**Found** 2026-08-20, session 8, scoping the grain report

William scoped the grain report as *"the grain loading elevators + midstream
MGMT the only buoy which exclusively loads grain"*. MGMT is indeed rule-flagged
grain-only. **So is `ARTCO Destrehan Buoys`, with a byte-identical rule.**

| raw_zone | facility | facility_type | ops | Cargo group | Rule | Note |
|---|---|---|---|---|---|---|
| Myrtle Grove Marine | MGMT | Mid-Stream | Load | Grain | Can never be a liquid cargo | Apply always |
| Mrytle Grove Marine Terminal | MGMT | Mid-Stream | Load | Grain | Can never be a liquid cargo | Apply always |
| ADM Destrehan Buoys Upper | ARTCO Destrehan Buoys | Mid-Stream | Load | Grain | Can never be a liquid cargo | Apply always |
| ADM Destrehan Buoys Lower | ARTCO Destrehan Buoys | Mid-Stream | Load | Grain | Can never be a liquid cargo | Apply always |

**Evidence** Both facilities run 100% Grain legs over all time — MGMT 424/424,
ARTCO Destrehan Buoys 622/622. They are distinct physical facilities (Myrtle
Grove vs Destrehan), not two spellings of one. No other Mid-Stream facility is
100% grain; the next closest, Cooper Darrow, is 262/999 (26%).

**Effect on reports** Either the grain report is missing 622 legs of buoy
grain, or a dictionary row asserts a grain-only rule that is not true of the
real facility. Both cannot be right.

**Proposed fix** For the build-fix session, once ruled: if ARTCO Destrehan
Buoys *is* grain-only, no fix — the report scope widens and William's "only
buoy" recollection was simply incomplete. If it is *not*, its two dictionary
rows need their `Cargo group` cleared, which would drop 445 dictionary-derived
grain legs (622 minus the 177 FGIS-confirmed) back to no cargo group.

**RULED — William, 2026-08-20** *"artco can occasionally add grain ships tagged
to that into the report, as we can't bake it in as it remains multi purpose
facility."*

So the dictionary row is **wrong**. `ARTCO Destrehan Buoys` is a multi-purpose
midstream facility that sometimes loads grain; it must not carry a grain-only
rule. What follows from that:

- **445 legs are currently mis-tagged `Grain`** — 622 total minus the 177 with
  genuine FGIS evidence. They are grain today *only* because the dictionary
  asserts it, and the ruling says that assertion is false.
- **Grain reports should include ARTCO legs that are tagged grain by evidence**
  (FGIS), and exclude the rest — rather than including all of them or none.
- MGMT's rule is **unaffected** and stands: William confirmed MGMT is grain-only.

**Proposed fix (build-fix session)** Clear `Cargo group` on the two
`ARTCO Destrehan Buoys` rows in `MRTIS/dictionaries/zone_facility.csv`
(raw zones `ADM Destrehan Buoys Upper` / `Lower`) and rebuild. Expected effect:
445 legs move from `cargo_group = 'Grain'` to NULL; 177 FGIS-evidenced legs keep
their grain tag and their tonnage. **Check before rebuilding** whether the same
over-assertion exists on other multi-purpose midstream rows — 17 dictionary rows
carry a Grain cargo group and only MGMT's is now confirmed correct at a
multi-purpose berth.

**FIXED — MRTIS commit `56ad9f5`, 2026-08-20** (`OPEN_QUESTIONS.md` §15.1).
`Cargo group` cleared on both `ARTCO Destrehan Buoys` dictionary rows; `ops = Load`
and the rule text left untouched, since the ruling was about cargo, not direction,
and `ops` is what resolves activity at that berth. Rebuilt with
`build_port_calls.py` only — `build_db.py` was not re-run, so surrogate keys were
not reassigned.

**Verified leg by leg against a pre-change copy of the database:** 445 legs moved
`cargo_group` from `Grain` to NULL; the 177 FGIS-evidenced legs kept their grain
tag and tonnage; **0 legs changed fee, activity, agency, hours or facility; 0 legs
added or removed**; billable total unchanged at $272,660,000. MGMT untouched.
Dictionary rows carrying a Grain cargo group: 17 → 15.

Downstream, **no published figure moved** — every file in this package re-derived
against the rebuild differs by exactly one line, the MRTIS commit stamp. The grain
reports had routed around the defect on FGIS evidence, so the fix confirmed them
rather than changing them.

**Status** CLOSED.

---

### I-2 · Grain tonnage exists only where FGIS matched, and coverage is very uneven — `wrong-figure`

**Severity** `wrong-figure` (a naive report states a false comparison)
**Where** MRTIS pipeline — `build_port_calls.py:652-661`
**Found** 2026-08-20, session 8, building the grain volume report

`cargo_group` is set from FGIS certificates where they matched, and otherwise
from the zone dictionary. **Tonnage is only ever set on the FGIS branch** —
`estimated_tons` comes from `fgis_record.metric_ton_total`; the dictionary
branch sets `cargo = destination = tons = None`. So a leg can be *known* grain
and carry no tons at all.

**Evidence** FGIS coverage of grain legs, all time:

| Facility group | Legs | FGIS-matched | Coverage |
|---|---:|---:|---:|
| The 9 elevators | 9,746 | 9,419 | 86.7% – 99.9% by facility |
| MGMT | 424 | 170 | **40.1%** |
| ARTCO Destrehan Buoys | 622 | 177 | **28.5%** |

Worst elevator is Bunge Destrehan at 86.7%; best is CHS Myrtle Grove at 99.9%.

**Effect on reports** Tons and ship count do **not** share a denominator. Put
them side by side unqualified and MGMT appears to move ~2.5x less grain per
ship than it does, ARTCO ~3.5x less — an artefact of unmatched certificates,
not of trade. Any tons-per-ship or tons-per-elevator comparison is invalid
across facilities unless coverage is shown or the denominator is matched.

**Effect handled how, in this exercise** Every volume report carries an
explicit FGIS-coverage column, reports ship count over *all* calls and tonnage
over *FGIS-matched calls only*, and states both denominators in its header.

**Proposed fix** For the build-fix session: investigate why buoy FGIS match
rates are 2-3x worse than elevator rates. Likely candidates are vessel-name
matching at midstream zones or the day-offset window in
`build_fgis_match.py`; both are testable. A lift here improves tonnage coverage
directly, with no rule change.

**Note** `actual_tons` is NULL on all 41,804 legs *by design* — MRTIS reserves
it for a genuine certified-actual source and warns "do not read NULL there as
zero". `estimated_tons` is FGIS certified tonnage, called an estimate per
William's original mapping. Not a defect; recorded so no report reads the NULL
as a shortfall.

**RULED — William, 2026-08-20** *"mgmt will have a split between fgis cargo and
by products which we don't have data on, so 40% is reasonable estimate."*

So MGMT's 40.3% is **not a matching defect** — it is a genuine cargo split. MGMT
loads FGIS-certifiable grain *and* grain by-products (meal, hulls, DDGS and the
like), and by-products are not FGIS-certified, so no certificate exists to match.
The tonnage gap there is a **source-data limit, not a pipeline bug**, and no fix
is available until a by-product tonnage source is ingested.

**What this does and does not settle**

- **Settled for MGMT.** Its coverage should not be "improved"; 40% is the right
  answer. Reports must state that MGMT tonnage covers certified grain only and
  omits by-products entirely, or they understate the berth.
- **Not settled for the elevators.** Bunge Destrehan at 85.6% and ADM Destrehan
  at 88.0% sit well below their peers (99.6-100%). Pure grain elevators have no
  by-product explanation, so that gap is still unexplained and still worth
  investigating in the build-fix session.
- **Opens a definitional question (see I-3).**

**RESOLVED, 2026-08-20 — not a defect, and not a property of those two
elevators.** Broken out by year, the "low coverage" is a **2023-shaped dip** that
recovers completely:

| | 2019 | 2022 | **2023** | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|
| ADM Destrehan | 97.7% | 93.1% | **75.4%** | 88.5% | **98.2%** |
| Bunge Destrehan | 89.3% | 86.1% | **69.4%** | 92.4% | **96.8%** |
| Zen-Noh (control) | 99.1% | 100.0% | 99.6% | 99.6% | 100.0% |

**It is not an FGIS matching failure.** 2023 has the *best* match rate in the
series — **99.8%**, against 93.9-99.4% elsewhere. The certificates that exist are
being matched; there are simply fewer of them (1,439 in 2023 against ~1,650
typical).

**System-wide at elevators, 2023 is the outlier year:**

| Year | Elevator legs | Certified | Coverage | Certified tonnage |
|---|---:|---:|---:|---:|
| 2021 | 1,277 | 1,254 | 98.2% | 61.65M t |
| 2022 | 1,253 | 1,216 | 97.0% | 57.74M t |
| **2023** | **1,245** | **1,140** | **91.6%** | **50.56M t** |
| 2024 | 1,327 | 1,275 | 96.1% | 56.50M t |
| 2025 | 1,422 | 1,374 | 96.6% | 59.40M t |

Leg counts held flat while certified tonnage fell ~12% from 2022 and ~18% from
2021 — the same number of vessels worked the elevators, but materially fewer
carried a certified grain export.

**What this leaves.** The pipeline is eliminated as a cause: the join works, the
matcher works, and the shape is a single year across multiple facilities rather
than a persistent property of two. The residue is a **trade question, not a data
question** — what happened to certified Gulf grain export in 2023 — and that is
William's to answer, not this repo's. Flagged for him; nothing to fix here.

**Status** CLOSED as a data defect. Open only as a trade observation for William.

---

### I-3 · `cargo_group = 'Grain'` at MGMT also covers non-grain by-products — `gap`

**Severity** `gap` (definitional, affects what a "grain" report means)
**Where** MRTIS `dictionaries/zone_facility.csv` + `build_port_calls.py:659`
**Found** 2026-08-20, session 8, from William's ruling on I-2

William's explanation of MGMT's FGIS coverage — a split between FGIS-certifiable
grain and by-products — means the dictionary's blanket `Cargo group = Grain` at
MGMT is tagging **by-product cargo as grain**. The rule is right that MGMT can
never load liquid; it is looser than the label suggests about what "Grain" means.

**Evidence** MGMT, all time: 424 legs, all tagged `Grain`; 170 (40.1%) carry FGIS
certificates, 254 (59.9%) do not. Per the ruling, a material share of those 254
are grain **by-products**, not grain.

**Effect on reports** A "grain tonnage" report is unaffected (by-product legs
carry no tonnage anyway). A **grain ship-count** report is affected: it counts
by-product loadings as grain loadings. That is arguably correct for an agency
revenue or berth-activity view and wrong for a grain-trade view — it depends on
the report's purpose, which is why this is logged rather than decided.

**Proposed fix (build-fix session)** Either (a) accept the broad reading and
rename the group to something like `Grain & by-products` so the label stops
over-claiming, or (b) introduce a `cargo_subgroup` distinguishing certified grain
from by-product where evidence allows. Needs William's ruling; both are cheap.

**RULED AND BUILT — William, 2026-08-20:** *"mgmt is grain and by products, add
cargo_subgroup."* Built at MRTIS `0c4ed0c` (`OPEN_QUESTIONS.md` §15.6).

**The design point worth keeping.** The obvious implementation — "no FGIS
certificate at a grain berth means by-product" — would have been wrong, because
the evidence is asymmetric. A certificate *proves* certified grain; its absence
proves by-product only at MGMT, and at Zen-Noh (99.6% coverage) proves nothing
but a failed match. Applied globally that rule would have **invented by-product
cargo at nine grain elevators**. So the fact is **declared per berth** in the zone
dictionary — 2 of 220 rows, both MGMT — and NULL everywhere it is genuinely not
known.

| `cargo_subgroup` | Legs | Facilities |
|---|---:|---:|
| `Certified grain` | 10,545 | 40 |
| `Grain by-product` | 254 | **1 — MGMT only** |
| NULL | 31,005 | 108 |

**Verified** Purely additive: 0 legs differ on `agency_fee`, `activity`,
`agency`, `cargo_group`, `cargo`, `cargo_source`, `destination` or
`estimated_tons`. Billable total unchanged at $272,660,000.

**Status** CLOSED.

---

### I-4 · Two agency columns give two different revenue answers — `wrong-figure`

**Severity** `wrong-figure` (a reasonable query returns a wrong total, silently)
**Where** MRTIS `port_call.agency` vs `port_call_leg.agency`
**Found** 2026-08-20, session 8, building the port-wide agency report

Agency exists at **both** grains. `docs/BUSINESS_RULES.md` §6 rules that the leg
grain is correct — the agency that brought the vessel in owns the leg — but
`port_call.agency` sits right there and is the more obvious column to reach for
when someone thinks "revenue by agent".

**Evidence** All time: **91 port calls carry more than one agency across their
legs**, and **91 legs disagree with their own call-level agency**, holding
**$939,000** of fee. Report revenue by `port_call.agency` and that $939,000 is
attributed to the wrong agent — not lost from the total, just credited to
whoever won the call-level pick.

**Effect on reports** Every report in this exercise uses the leg grain and says
so. The risk is downstream: a Claris/FileMaker developer building a fee-by-agent
layout will find `agency` on the port call table first, and nothing on that table
warns them off it.

**Proposed fix (build-fix session)** Cheapest and most durable is documentation
plus a name: rename or comment `port_call.agency` as the *call-level pick* it is
(e.g. `agency_primary`), so choosing it is a decision rather than an accident.
The alternative — dropping it — would break the existing call-grain roll-ups. It
should also be called out explicitly in `DATA_DICTIONARY.csv` for the reviewer,
which is a change **in this repo**, not in MRTIS.

**Status** OPEN.

---

### I-5 · $29.5M of revenue sits on legs where the agent changed mid-leg — `gap`

**Severity** `gap` (documented rule, undocumented scale)
**Where** MRTIS `port_call_leg.agent_changed_in_leg` / `agency_source`
**Found** 2026-08-20, session 8, checking agency attribution stability

**Not a defect — a ruled choice whose size was not written down.** The agency on
a leg is the **inbound** agency: `agency_source = 'inbound'` on 41,170 of 41,804
legs ($270,217,250). Where the agent changes during a leg, the inbound agent
still keeps the whole fee, per `docs/BUSINESS_RULES.md` §6.

**Evidence** All time:

| `agent_changed_in_leg` | Legs | Fee |
|---|---:|---:|
| False | 38,541 | $243,164,750 |
| **True** | **3,263 (7.8%)** | **$29,495,250 (10.8%)** |

Over **chargeable** legs only — the denominator `docs/FIGURES.md` publishes,
since a non-chargeable leg carries no revenue to attribute: **3,233 of 40,245
(8.03%)**, same $29,495,250, **10.82%** of the billable total. Both are correct;
they are stated together here because I-8 is exactly this failure mode.

| `agency_source` | Legs | Fee |
|---|---:|---:|
| `inbound` | 41,170 | $270,217,250 |
| `none` | 544 | $1,784,500 |
| `leg` | 89 | $647,750 |
| `call` | 1 | $10,500 |

**Effect on reports** One leg in thirteen, and **$1 in every $9 of agency
revenue**, is attributed to an agent where at least one other agent was also
involved in that leg. The attribution is correct by rule; the point is that a
by-agent revenue report is not a clean division of the book, and at ~11% the
effect is far too large to leave unstated in front of a reviewer or a principal.

**Proposed fix (build-fix session)** No rule change proposed — William ruled the
inbound agent owns the leg. What is missing is disclosure: surface
`agent_changed_in_leg` in the export's `DATA_DICTIONARY.csv` and state the 10.8%
in `docs/BUSINESS_RULES.md` §6, so the rule arrives with its magnitude attached.
Both are changes **in this repo**.

**Status** OPEN — disclosure, not correction.

---

### I-6 · Window basis: `leg_start` and `call_start` differ by $42,000 — `cosmetic`

**Severity** `cosmetic` (reconciliation footnote, no wrong figure)
**Where** This exercise's own report scripts
**Found** 2026-08-20, session 8, reconciling the grain and port-wide reports

Reports here window on `leg_start`, because facility, cargo and agency are
leg-grain attributes. Windowing on `call_start` instead moves the boundary for
calls that straddle it.

| Basis | Legs | Fee |
|---|---:|---:|
| `leg_start` (used here) | 16,890 | $110,360,250 |
| `call_start` | 16,886 | $110,318,250 |
| Delta | +4 | **+$42,000** |

**Effect on reports** None, as long as one basis is used consistently and stated.
Both report families here use `leg_start` and say so in their headers. Recorded
so the two figures are never mistaken for a discrepancy.

**Status** OPEN — documentation only; no fix required.


---

### I-7 · Does the gen-cargo discount survive a conversion to loading? — `wrong-figure` (potential, $3,492,500)

**Severity** `wrong-figure` if ruled one way, none if ruled the other
**Where** MRTIS `agency_fee_for()` — rule R5, `OPEN_QUESTIONS.md` §12.2 / §12.3.3
**Found** 2026-08-20, session 8, from William's explanation of the fee schedule

**What was explained (William, 2026-08-20)** — the commercial basis of R5, recorded
here because it was not previously written down anywhere:

> *"the marker for inbound is owners, and heavily discounted, then converts to
> loading outbound, its charterers agents and they apply full tariff, no
> discounts, so thats the only reason for that one deviation from defaulting fee
> per vessel type"*

and, narrowing it:

> *"discharging buoys, also full tariff, only ships at gen cargo docs are
> discounted"*

**What is built, and it matches the second statement exactly.** Bulk legs, all time:

| Facility type | Legs | Tiers billed |
|---|---:|---|
| **General Cargo** | 3,019 | **$5,000 only** |
| Mid-Stream | 6,447 | $10,500 (+2 Ro-Ro at $1,000) |
| Elevator | 9,726 | $10,500 |
| Bulk Cargo | 3,212 | $10,500 |
| Chemical Plant / Tank Storage / Refinery / Cruise | 150 | $10,500 |

Bulk **discharging at midstream buoys**: 2,621 legs, all $10,500. The discount does
not leak outside General Cargo docks.

**The ambiguity** The two statements diverge on one set of legs. Reading A — the
discount is a **berth-type** rule (built today). Reading B — the discount is the
*owner's-agent* rate, so a leg that converts to **loading** bills full tariff even
at a gen cargo dock.

**Evidence that this is a real distinction, not a quibble** Agent-change rate by
group — the highest figure in the entire dataset sits precisely on the legs in
question:

| Bulk group | Legs | Fee | Agent changed mid-leg |
|---|---:|---:|---:|
| Gen Cargo, **Load** | **635** | $3,175,000 | **32.9%** |
| Gen Cargo, Discharge | 1,693 | $8,465,000 | 8.2% |
| Gen Cargo, unresolved | 691 | $3,455,000 | 11.0% |
| Base $10,500, Load | 15,439 | $162,109,500 | 13.4% |
| Base $10,500, Discharge | 3,504 | $36,792,000 | 9.6% |

One in three gen-cargo Load legs records an agent handover — four times the rate of
gen-cargo discharge legs. That is the owner-to-charterer conversion William
described, concentrated exactly where reading B would charge full tariff.

**Value at stake** 635 legs at $5,000 = $3,175,000 today. At $10,500 = $6,667,500.
**Difference $3,492,500** — 1.3% of the $272,660,000 billable total.

**Effect on reports** None yet: every report here uses the fee MRTIS stored, and
`figures.py` confirms 0 attribution mismatches against it. If reading B is ruled
correct, every fee figure in the **review package** moves, not just this exercise.

**Proposed fix (build-fix session)** Ruling required before any code. If A, no
change — record the ruling so the question is closed rather than rediscovered. If
B, `agency_fee_for()` needs `activity` as an input, which it does not currently
take, and R5 becomes conditional on direction. Note the 691 gen-cargo legs with
**unresolved** activity would then need their own answer, since direction is
unknown for them.

**RULED — William, 2026-08-20: reading A.** *"vessel type rules, then after that,
can modify for bulk ships at gen cargo facs."*

The fee is decided by **vessel type first**, and the gen-cargo variant is a
**modifier applied afterwards on the berth**, not on the direction of the cargo.
So the discount is a berth-type rule: the 635 bulk legs loading at a General
Cargo dock correctly bill $5,000, and the $3,492,500 does not move.

**Consequences**

- **No code change. No published figure moves.** What is built was already right;
  this ruling closes the question so it is not rediscovered.
- The 691 gen-cargo legs with unresolved activity need no direction answer, since
  direction is not an input to the fee. That follow-on question is void.
- The commercial explanation (owner's agent inbound at a discount, charterer's
  agent on the outbound load at full tariff) is the *reason* the gen-cargo tier
  exists — it is not itself an input to the calculation. Recorded so the rule
  arrives with its rationale, per `docs/BUSINESS_RULES.md` §9.3.

**Status** CLOSED — ruled A, matches the build, nothing to fix.

### I-8 · "Turnover rate" has three defensible values, 7.5% / 31.3% / 48.6% — `gap`

**Severity** `gap` (no wrong figure yet; a wrong figure is one careless report away)
**Where** Reporting definition, not MRTIS
**Found** 2026-08-20, session 8, checking William's trade expectation

William, 2026-08-20: *"from experience 24-35% bulk ships turn over in the river
from discharge to load."* Measured against the data, that is **exactly right** —
on the correct denominator, and badly wrong on two others.

| Definition | Rate |
|---|---:|
| Split calls / **all bulk calls** | 7.5% (1,628 / 21,565) |
| Next-call discharge→load ≤30d / all bulk calls | 4.8% |
| **In-call turnover / bulk calls that discharge** | **31.3% (1,628 / 5,197)** |
| + next-call turnover ≤30d, same denominator | 48.6% |

**This validates the pipeline.** 31.3% sits mid-range of a 24-35% trade
expectation formed independently of this data, which is strong evidence that
split-call detection is neither under- nor over-firing. Cross-checked further:
**zero** bulk calls carry a Discharge leg alongside an unresolved-activity leg,
so no turnover is hidden behind unresolved activity.

Rate by year is flat (6.8-9.2% on the all-calls denominator, no trend), which is
what a real commercial behaviour should look like and what a data-quality
artefact should not.

**Effect on reports** None today. The risk is that "turnover rate" is a phrase
that sounds self-defining and is not: the same true phenomenon yields 7.5% or
31.3% depending on the denominator — a **4.2x spread**. Either could be published
without anyone noticing the choice was made.

**Proposed fix (this repo, not MRTIS)** When a turnover or split-rate figure is
published, state its denominator in the same sentence. Worth adding to
`docs/BUSINESS_RULES.md` §4 alongside the split-call definition, since the Claris
reviewer will hit exactly this.

**Status** OPEN — definition discipline, no code change.

---

### I-9 · Source-data quality did not improve monotonically; `tpc = 0` degraded 4.4x — `gap`

**Severity** `gap` (affects which years are safe to report on)
**Where** MRTIS source feed + ships register coverage
**Found** 2026-08-20, session 8, testing William's recollection

William, 2026-08-20: *"if you look at 2019, its a diaster, from 2020 on, the
source data quality improved consistently till now."* **Half confirmed.**

| Year | Incomplete | Unresolved | No berth | No agency | Geofence artifacts | `tpc = 0` |
|---|---:|---:|---:|---:|---:|---:|
| 2019 | **2.8%** | **15.9%** | 1.4% | 1.3% | 11.3% | 4.3% |
| 2020 | 0.7% | 13.2% | 2.4% | 1.6% | 10.8% | 4.0% |
| 2021 | 0.6% | **11.7%** | 4.1% | 1.2% | 9.7% | 5.5% |
| 2022 | 0.5% | 13.8% | 3.4% | 1.1% | 10.4% | 9.7% |
| 2023 | 0.7% | 13.9% | 3.0% | 1.6% | 10.2% | 10.7% |
| 2024 | 0.5% | 13.7% | 2.2% | 0.9% | 11.8% | 14.2% |
| 2025 | 0.6% | 13.8% | **6.3%** | 1.5% | 12.7% | 15.8% |
| 2026 | 4.2%* | 15.0% | 4.6% | 1.1% | 9.9% | **18.9%** |

\* 2026's incomplete rate is the window edge — calls still open when the data
ends on 2026-07-31 — not a quality regression.

**Confirmed** 2019 is the worst year on the two measures that matter most:
incomplete calls at 2.8% (4-5x every later year) and unresolved activity at 15.9%
(series high). The correction was immediate and durable — completeness drops to
0.7% in 2020 and holds.

**Not confirmed** Improvement was not consistent after 2020. Unresolved activity
bottomed at 11.7% in 2021 and drifted back to ~13.8%. Three measures got worse:

- **never-berthed legs 1.4% → 6.3%** (2019 → 2025)
- **geofence artifacts 11.3% → 12.7%**
- **`tpc = 0` 4.3% → 18.9% — rising every year without exception**

The `tpc = 0` trend is **monotonic across eight years**, which makes it structural
rather than noise. It reads as ships-register coverage failing to keep pace with
newer vessels entering the trade, not as a feed defect — and it is already a
known-deferred item upstream (`OPEN_QUESTIONS.md` §11.3, still unbuilt).

**Effect on reports** The window chosen for this exercise (2023-08 onward)
excludes 2019 entirely, so no report here carries the disaster year. But any
report reaching back before 2020 should say so, and any report using TPC should
note that a fifth of 2026 calls carry the placeholder.

**Proposed fix (build-fix session)** Three separable investigations: (a) why
never-berthed legs quadrupled, (b) whether the geofence-artifact drift is real or
a zone-dictionary drift, (c) §11.3 `tpc = 0`, which is the largest and the only
monotonic one. (c) is the one worth doing first.

---

**(c) `tpc = 0` — INVESTIGATED AND RESOLVED, 2026-08-20.** MRTIS commit
`0c4ed0c` (`OPEN_QUESTIONS.md` §15.7, which also closes the long-deferred §11.3).

**Ruled by William:** *"if is there we can populate as available, if becomes a
larger effort to fix, am ok dropping it."*

**Traced to the raw vendor files, and the value is not there.**
`Ships_Register`'s 150 raw S&P Global exports were harvested for every IMO/TPC
pair — 64,870 rows across 53,904 distinct IMOs:

| | |
|---|---:|
| Raw files carrying a TPC column at all | **58 of 150** |
| Register vessels showing `tpc = 0` | 20,163 |
| — with a real TPC anywhere in raw | **1** |
| **River-calling vessels showing `tpc = 0`** | **1,110** |
| — **with a real TPC anywhere in raw** | **0 (0.0%)** |

So the earlier hypothesis in this log — *"ships-register coverage lagging newer
tonnage"* — was **wrong**. It is not a coverage trend at all: S&P simply does not
supply TPC for these hulls, and 92 of its 150 export files omit the field
entirely. Neither MRTIS's join nor Ships_Register's build was losing anything.

**And `0` was never a measurement.** TPC is a function of waterplane area, so a
floating hull always has TPC > 0. It appeared on hulls up to **182,288 dwt**
(real figure ≈ 120), with **2,417 of 4,045 affected calls (59.8%) on vessels of
20,000+ dwt** — physically impossible.

**Built** `load_register()` maps `0` → NULL. 4,045 calls moved; 36,010 keep a
real value. Blank now means *unknown*, which is true.

**Verified** This needed a **full rebuild** (`tpc` lives on `dim_vessel`),
rehearsed on scratch first. Despite every surrogate key being reassigned,
**nothing content-addressed moved**: 0 legs added or removed and **0 differences
across eleven leg columns** including fee, activity, agency, cargo, tonnage and
hours. Billable total unchanged at $272,660,000.

A useful by-product: this is the first demonstration that a **full MRTIS rebuild
is content-stable** despite the key reassignment its README warns about — and the
chain runs offline in 36 seconds, since `fgis_source/` is cached.

---

**(a) never-berthed legs 1.4% → 6.3% — INVESTIGATED AND EXPLAINED, 2026-08-20.
Not an MRTIS defect: a gap in the source feed. See I-12, which it turned into.**

The drift is real but it is not decay. 2025's 356 never-berthed legs include
**274 calls with two events or fewer** (against 49 in 2024) — vessels that
crossed into the SWP and out again with nothing recorded between. **161 of
those, 58.5%, are Gas carriers**, against only 941 Gas calls in the entire
eight-year dataset.

Traced to a single cause: a new LNG terminal the feed could not see. Full
finding and its commercial consequence in **I-12** below.

---

**(b) geofence artifacts — INVESTIGATED, 2026-08-20. Overstated in this log, and
not a trend.**

**Correction to the figure recorded above.** The "11.3% → 12.7%" in this entry
was computed against `sum(berth_stop_count)`, which is not the artifact
denominator. Measured against berth events proper, the rate is:

| 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5.2% | 5.2% | 4.7% | 5.0% | 4.9% | 5.7% | **6.0%** | **4.9%** |

A 1.3-point band over eight years with **2026 already back to 4.9%** — noise, not
drift. The 2025 bump is concentrated at named facilities (Zen-Noh 174 artifacts,
DRAX 52 — DRAX being new to the feed), consistent with new or re-drawn geofences
bedding in rather than with systematic decay.

**Nothing to fix.** The finding here is that this log carried a wrong figure for
two sessions; `figures.py`'s published geofence numbers (5.23% of all berth
events, 5.27% of placed) were always correct and are unaffected.

**Status** ALL THREE PARTS CLOSED. (a) → I-12, (b) not a defect, (c) fixed.


---

### I-10 · Recommended: split the fee schedule into a stable non-bulk branch and an active bulk branch — `gap`

**Severity** `gap` (maintainability; no figure moves)
**Where** MRTIS `agency_fee_for()` in `scripts/build_port_calls.py`
**Raised** 2026-08-20 by William; checked and recommended the same day

William, 2026-08-20: *"vessel type > fee apply, excluding bulk and run that
separately... down the road we may make further adds on the fee per a type or
specific berth, but the other vessel types will stand true, as our only focus are
the bulk carriers."*

**Checked: the split is clean.** Fee tier x vessel type, all time:

| Tier | Vessel type | Legs | Fee |
|---:|---|---:|---:|
| $10,500 | **Bulk** | 19,533 | $205,096,500 |
| $10,500 | (unknown) | 19 | $199,500 |
| $5,000 | **Bulk** (R5) | 3,019 | $15,095,000 |
| $5,000 | Reefer (R4) | 36 | $180,000 |
| $5,000 | (unknown) | 4 | $20,000 |
| $3,500 | Tanker | 12,606 | $44,121,000 |
| $3,500 | Gas | 726 | $2,541,000 |
| $3,500 | Other | 72 | $252,000 |
| $3,500 | (unknown) | 56 | $196,000 |
| $3,500 | Container | 1 | $3,500 |
| $2,500 | Passenger (R1) | 1,042 | $2,605,000 |
| $2,500 | (unknown) | 1 | $2,500 |
| $1,000 | **Bulk** (R2 Ro-Ro) | 2 | $2,000 |
| $750 | Container (R3) | 3,124 | $2,343,000 |
| $750 | (unknown) | 4 | $3,000 |

Bulk branch would carry **22,554 legs / $220,193,500**; non-bulk **17,607 legs /
$52,062,000** (plus 84 `(unknown)` legs, $421,000 — see below).

**Recommendation: do it, and make it a reorganisation that reprices nothing.**

Three reasons it is worth doing:

1. **It isolates where change is going to happen.** Every future addition
   William named — a fee per trade, a fee per specific berth — lands on bulk.
   Splitting means a bulk rule change cannot reach passenger, container or tanker
   fees by accident.
2. **It separates two rules that collide on a number.** R4 (Reefer) and R5 (Bulk
   at General Cargo) both bill **$5,000** for entirely unrelated reasons. Today
   "change the $5,000 tier" would silently move reefers. After a split it cannot.
3. **It matches how the reports are framed.** Bulk — and grain within it — is the
   subject; the other types are the comparison base. Code shaped like the
   question is easier to keep correct.

**Three things the refactor must handle**

- **`(unknown)` vessel type — 84 legs, $421,000, spread across five tiers.** They
  are priced today by `ship_type_group` / `ship_type` fallbacks, not by
  `vessel_type`. A naive `if vessel_type == 'Bulk'` split would reroute the 19
  legs currently at $10,500 and reprice them. The branch test must use the same
  evidence `agency_fee_for()` uses now.
- **The 1 Container leg at $3,500.** R3 keys on *Fully Cellular*; a container
  vessel that is not fully cellular falls to base. Correct, but it proves the
  branch cannot key on `vessel_type` alone.
- **Regression is already built.** `figures.py` re-implements the schedule
  independently and asserts, leg by leg, that it reproduces the stored fee —
  currently **0 mismatches across 40,245 chargeable legs**. After the split it
  must still report 0. That is the acceptance test, and it exists already.

**Proposed fix (build-fix session)** Restructure `agency_fee_for()` into
`_fee_bulk(...)` and `_fee_by_vessel_type(...)` behind the existing signature,
routing on today's evidence order. **Zero fee changes expected; `figures.py` must
still report 0 mismatches.** Nothing else in either repo changes.

**BUILT — MRTIS commit `56ad9f5`, 2026-08-20** (`OPEN_QUESTIONS.md` §15.2).
`agency_fee_for()` now routes the §12 layer through `_fee_2026_rules()`, which
calls `_fee_bulk_berth_rules()` (R5 — the branch that will grow) then
`_fee_vessel_type_rules()` (R1-R4 — the branch that should stay still).

**One correction to the recommendation, found before building it.** The split
could **not** fork on `vessel_type == "Bulk"`: **R2 (Ro-Ro) fires on bulk-typed
hulls** — both R2 legs carry `vessel_type = 'Bulk'` — so a vessel-class fork would
have repriced them. The branches divide by what each rule is *about* (a bulk
carrier at a kind of berth, vs a vessel type at any berth), not by hull class.
The `(unknown)` vessel-type hazard flagged above was avoided the same way: the
base tiers below the rule layer were not touched at all.

**Verified: 0 legs changed fee.** Leg-by-leg against a pre-change copy, 0 differing
cells across the whole fee-tier × vessel-type grid, the build's own `[PASS] fee
matches its vessel's tier -- 0 legs`, and `figures.py` still reporting **0
attribution mismatches across 40,245 chargeable legs**.

**Status** CLOSED.

---

### I-11 · The port-call build was not deterministic — `wrong-figure` (reproducibility)

**Severity** `wrong-figure` — not a wrong number, a **false guarantee**
**Where** MRTIS `scripts/build_port_calls.py:219-221`
**Found** 2026-08-20, while verifying the I-1 fix — not by looking for it

The sample export changed on rebuild in columns the ARTCO fix could not have
touched. A controlled test — **two builds of identical code against identical
data** — showed the build itself was non-deterministic.

| Column | Legs differing between two builds |
|---|---:|
| `cargo` | **524** |
| `destination` | **19** |
| `cargo_group`, `cargo_source`, `estimated_tons`, `fgis_record_count`, `agency_fee`, `activity`, `agency` | **0** |

**Cause** `string_agg(DISTINCT x, ', ')` with no `ORDER BY`. DuckDB does not
guarantee iteration order for a distinct aggregate, so identical certificates
produced differently-ordered strings run to run — the same leg reading
`CORN, SOYBEANS` in one build and `SOYBEANS, CORN` in the next. The duplicates
visible in some values (`CORN, SOYBEANS, SOYBEANS`) are a second consequence: the
leg-level aggregate joins already-joined per-stop strings.

**Why it mattered more than it looks.** No figure was ever wrong — every numeric
and categorical column was stable, so nothing this package has published moved.
What it broke was **reproducibility**, and this package has published a
byte-identical guarantee for its sample export since session 5. That guarantee
was false, through no fault of the code here, and nobody had tested it across an
actual MRTIS rebuild — only across re-runs of the export against an unchanged
database, which could never have caught it.

**FIXED — MRTIS commit `0c4ed0c`, 2026-08-20** (`OPEN_QUESTIONS.md` §15.5).
`ORDER BY` added to all three aggregates, with a comment recording that it is
load-bearing rather than cosmetic — exactly the kind of clause a later tidy-up
deletes as noise.

**Verified** Two consecutive MRTIS builds now agree on **every column of every
leg**: `cargo` 524 → **0**, `destination` 19 → **0**. And end-to-end, for the
first time: a full MRTIS rebuild followed by re-running `figures.py`, both
`report_concepts/` scripts, `reports/build_reports.py` and
`export/build_review_package.py --sample` reproduces **byte-identical output
including the gzipped sample data**.

**Status** CLOSED.

---

### I-12 · A new LNG terminal was invisible to the feed for 13 months — $931,000 of agency fee never billed — `gap` (source feed)

**Severity** `gap` — not a defect in any code; a hole in the source data
**Where** The Zone Report feed. **Not** MRTIS, and not this package.
**Found** 2026-08-20, chasing I-9(a)'s never-berthed drift

**The pattern.** Never-berthed Gas-carrier calls ramp from 6 in January 2025 to
25 in January 2026 — then **collapse to 4 in February 2026** and 0-2 a month
thereafter.

**The cause, and the correlation is exact.** `Venture Global` — the Plaquemines
LNG terminal — **first appears anywhere in the feed on 2026-02-04**. Every
Venture Global event in the database falls on or after that date; there is one
raw zone spelling and it has no earlier history. The month the geofence appears
is the month the never-berthed calls stop.

**What was happening in the meantime.** Gas traffic tripled as the terminal came
up — 103 calls in 2024, **308 in 2025** — and distinct gas vessels went 21 → 93
→ 113. For thirteen months those vessels crossed into the SWP, spent an average
of **50.3 hours** inside it, and crossed out again, with **no berth event of any
kind recorded**. Their only events are `SWP Cross` Enter and Exit.

| The blind window, 2025-01 → 2026-01 | |
|---|---:|
| Calls with no berth recorded | **266** |
| Distinct vessels | 108 |
| Average time inside the SWP | 49.9 hours |
| Tier | $3,500 / leg |
| **Agency fee never billed** | **$931,000** |

That is **0.34%** of the $272,660,000 billable total, concentrated in thirteen
months and one trade.

> **This figure was corrected upward the same day, from $707,000.** The first
> count was scoped on `vessel_type = 'Gas'`. The sweep below showed that too
> narrow: **64 further calls are LNG hulls the Zone Report types as `Tanker`**,
> whose register `ship_type` is `LNG Tanker`. Identical signature — two-event
> calls, no berth, stopping dead at 2026-01. Counting on LNG evidence rather than
> on the feed's own type label adds **$224,000**. A reminder that
> `vessel_type` is the feed's label and `ship_type` is the register's, and the
> two disagree about LNG.

**MRTIS behaved correctly throughout.** William's rule is that a leg bills only
if it reached a berth (`docs/BUSINESS_RULES.md` §9). No berth was recorded, so no
fee accrued — the pipeline applied the rule faithfully to the data it was given.
The data was incomplete.

**Effect on reports** Every figure in this package for 2025 understates gas
activity and gas revenue by this amount. The port-wide report shows those calls
(they exist, with fee $0); the fee totals do not include them.

**Proposed fix** None available in code — no rule change can invent a berth event
that was never recorded. Two real options, both William's:

1. **Ask the feed provider to backfill the Venture Global geofence** to the
   terminal's actual start of operations. If they can, a rebuild recovers all 202
   calls and the $931,000 automatically, with no change to MRTIS.
2. **Accept and annotate.** Treat 2025-01 → 2026-01 gas figures as known-low and
   say so wherever they are published.

### The systematic sweep — is Venture Global the only one?

Done 2026-08-20 at William's direction. Every facility first appearing after
2019-07 — **15 of them** — profiled on the signature that separates a **newly
built** terminal (traffic ramps up from near zero, which is *expected and fine*)
from a **newly geofenced** one (traffic starts at full volume, because the
vessels were always there and only the visibility is new).

| Facility | First seen | Events/mo | First six months | Verdict |
|---|---|---:|---|---|
| **Venture Global** | 2026-02-04 | **58.7** | 51, 65, 60, 62, 58, 56 | **Newly geofenced — the gap** |
| Mile 110 Buoys | 2024-05-15 | 25.1 | 2, 29, 28, 26, 39, 39 | Added capacity — see below |
| MPLX Mt Airy | 2022-06-14 | 6.5 | 2, 4, 6, 4, 4, 2 | Genuine ramp |
| Willow Glen | 2022-08-02 | 3.3 | 2, 2, 4, 2, 3, 1 | Genuine ramp |
| Mile 112 Buoys | 2024-07-27 | 3.0 | 1, 1, 2, 2, 2, 4 | Genuine ramp |
| 10 others | 2020–2023 | ≤1.8 | — | Low traffic, no signature |

**Only Venture Global carries the signature**, and it is not a close call: it
opens at 51 events in its first partial month and holds 56–65 thereafter.

**William, 2026-08-20:** *"some terminals are new since begining of the data
set."* Confirmed and expected — that is precisely why the test is the *shape of
the ramp* rather than the mere fact of a late first appearance. A genuinely new
terminal ramping from zero produces no missing calls and needs no fix; four of
the five above are exactly that.

`Mile 110 Buoys` reaches volume fast but total buoy traffic **rose** when it
appeared (97 → 114 events/month) instead of shifting from another facility, and
no never-berthed population drops when it arrives — added capacity, not recovered
visibility.

**Three further hypotheses tested and rejected**, recorded so nobody re-opens
them:

1. **Facilities going dark are closures, not lost geofences.** `LIT Violet`,
   `Aramco Convent`, `Occidental Convent`, `Axiall Plaquemine` and `Apex Mt Airy`
   all stop appearing. But their vessels' never-berthed calls occur *before* the
   facility goes dark, not after — LIT Violet **109 before / 2 after**. The
   vessels stopped calling; the geofence did not vanish underneath them.
2. **The 2021–22 tanker episode is real behaviour.** Never-berthed tanker calls
   hit 8.7% in 2022-Q1 against 2.4% a year later, but **84% carry anchorage
   events** (91 of 108 in 2021) — vessels anchoring and departing without
   berthing. The gap signature is a *two-event* call with **no** anchorage; this
   is the opposite shape.
3. **The 2026-07 spike is the window edge.** 13 of its 14 two-event tanker calls
   are `open_end`, and 25% of that month's calls are incomplete because the data
   ends 2026-07-31.

**One question only William can close.** The evidence says LNG carriers were
working *something* through 2025 — 266 calls, 108 vessels, ~50 hours each inside
the SWP — and that the feed had no berth for them until Venture Global appeared.
If Plaquemines was genuinely not receiving ships until February 2026, then those
266 calls went somewhere else and the gap is at a different facility. **Was
Venture Global working vessels during 2025?** His answer either confirms the
attribution or redirects the search.

**Status** OPEN — no code fix exists; needs a decision from William, plus the
attribution question above.

---

### I-13 · Tankers entering and leaving with no berth — mostly real, but a coverage hole at miles 114-117 in 2021-22 — `gap` (source feed)

**Severity** `gap` — no code fix; a question for the feed provider
**Where** The Zone Report feed, AMA / Kenner Bend anchorage reach
**Found** 2026-08-20, at William's direction: *"i am curious abiut tankers
entering and exiting no faility docking, it could be a gap in ais coverage, how
many ships / calls does this occure per year ? it could be one specifc dock"*

**First, the count — with LNG hulls removed.** The 2025 tanker figure previously
reported (102) was inflated by Venture Global LNG carriers the feed types as
`Tanker`. Stripping them on register `ship_type`:

| Year | Tanker calls | No berth | Rate | 2-event | Anchored | Vessels |
|---|---:|---:|---:|---:|---:|---:|
| 2019 | 1,949 | 32 | 1.6% | 7 | 24 | 31 |
| 2020 | 1,756 | 44 | 2.5% | 7 | 34 | 37 |
| **2021** | 1,656 | **108** | **6.5%** | 16 | 91 | 101 |
| **2022** | 1,736 | **100** | **5.8%** | 16 | 84 | 98 |
| 2023 | 1,662 | 44 | 2.6% | 6 | 35 | 42 |
| 2024 | 1,678 | 46 | 2.7% | 12 | 34 | 41 |
| 2025 | 1,600 | 46 | 2.9% | 13 | 33 | 38 |
| 2026 | 998 | 49 | 4.9% | 24 | 35 | 46 |

**So ~32-49 calls a year is the baseline**, roughly 2% of tanker traffic, with a
**2021-22 episode that doubles it**.

**Second, are they really unberthed?** Split by the gap between a call's last
recorded event and its SWP exit:

| | Calls | Reading |
|---|---:|---|
| Left within 12h of last event | **161 (39%)** | Genuinely departed — no room for a missed berth |
| 12-48h gap | 66 (16%) | Ambiguous |
| **2-7 day unexplained gap** | **183 (44%)** | **Room for an unrecorded berth visit** |

So William's AIS hypothesis is right for roughly **two calls in five**, and wrong
for the other two — a real share of these vessels simply anchored, waited on
orders and were redirected without ever berthing.

**Third — not one dock, but one *reach*.** Grouping the gap-calls by where the
vessel was **last seen** before vanishing:

| Last seen | 2019 | 2020 | **2021** | **2022** | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **AMA / Kenner Bend reach** | 2 | 3 | **16** | **17** | 1 | 1 | 9 | 4 |
| Everywhere else combined | 7 | 7 | 35 | 24 | 14 | 12 | 14 | 17 |

Three adjacent anchorages — **Lwr Kenner Bend (mile 114), Upr Kenner Bend (115),
AMA (117)** — carry a **5-8x spike across 2021-22 and fall back to a single call
a year in 2023-24.** A three-mile stretch, a two-year window, then clean. That is
the shape of a coverage hole that was fixed, not of vessel behaviour.

Checked and excluded: it is **not** one dock. The no-berth vessels' *other* calls
berth in exactly the proportions all tankers do (IMTT St Rose, Valero St Charles,
MPLX Garyville lead both lists), so no single facility's geofence is implicated
at the vessel level.

**Also checked, and benign:** 36 calls show ~0 duration. All are `open_end` with a
single event — vessels seen entering and not seen leaving, running a steady 10-24
a year across every year in the series. Window-edge behaviour, not a defect.

**Effect on reports** Small and bounded. These calls carry no fee (correctly — no
berth was reached), so at ~2% of tanker calls in normal years the understatement
is minor. The 2021-22 episode is the exception, where up to 51 calls a year may
represent unrecorded berth visits.

**Proposed fix** None in code. A question for the feed provider: **was AIS or
geofence coverage degraded in the AMA / Kenner Bend reach (miles 114-117) during
2021-2022?** If so, that period's tanker figures are known-low by up to ~30 calls
a year. Otherwise the effect is real vessel behaviour and nothing is missing.

**Status** OPEN — informational; needs no decision unless William wants the feed
provider asked.

---

### I-14 · Inactive and decommissioned berths are deliberate, not gaps — `reference`

**Severity** `reference` — recorded so no future session mistakes this for a defect
**Where** The zone dictionary, by design
**Recorded** 2026-08-20 from William

Several facilities in the dictionary carry almost no traffic, and several stop
appearing entirely. **This is intentional and must not be "cleaned up".**

**William, 2026-08-20:** *"some berths are inactive or maybe get 1 call every
year or 2, that is ok, as did not want to have a gap in the data capture, should
traffic reappear."*

Named examples and their reasons:

| Facility | Why it looks dead |
|---|---|
| **LIT Violet** (last seen 2025-03-04) | **Decommissioned** — the site of the port's new container terminal |
| **Marlex** (2 events in 6 years) | Ties up **naval reserve vessels**, some of which do not move for years |
| Port NOLA avenue/street docks (`Esplanade Ave`, `Gov Nicholls St`, `Alabo St`, `Henry Clay Ave`, …) | Rarely, if ever, receive traffic |

**Consequences for this exercise**

- A facility's **first or last appearance date is not evidence of a feed gap** on
  its own. I-12's sweep is sound precisely because it tests the *shape of the
  traffic ramp*, not the mere fact of a late arrival — a genuinely new terminal
  ramping from zero produces no missing calls.
- **A facility going dark is usually a closure, not a lost geofence.** Confirmed
  independently for LIT Violet before William said so: its vessels' never-berthed
  calls occur 109 *before* it went dark and 2 after.
- **Low-traffic rows are not dictionary clutter.** Removing them would create the
  very blind spot Venture Global demonstrates (I-12) if traffic returned.

**Status** REFERENCE — no action, ever. Recorded to prevent a well-meaning tidy-up.

---

### I-15 · Most "no-berth" tankers are lightering at anchorage — real cargo work billing $0 — `gap` (business rule)

**Severity** `gap` — a business-rule question, worth ~$1.04M over the series
**Where** Not a defect anywhere. `docs/BUSINESS_RULES.md` §9 applied exactly as ruled.
**Found** 2026-08-20, following William's question about tanker size and type

**William's hypothesis, tested:** *"my guess, only a guess, it will be smaller
chemical type carriers."* The data says the opposite, and the opposite is more
interesting.

**By type — chemical carriers are exactly proportional, not over-represented:**

| `ship_type` | No-berth | % | All tankers | % | Index |
|---|---:|---:|---:|---:|---:|
| Chemical/Products Tanker | 324 | 69.1% | 9,020 | 69.2% | **1.00** |
| **Crude Oil Tanker** | 92 | 19.6% | 1,570 | 12.0% | **1.63** |
| Crude/Oil Products Tanker | 28 | 6.0% | 952 | 7.3% | 0.82 |
| Products Tanker | 17 | 3.6% | 560 | 4.3% | 0.84 |
| Asphalt/Bitumen Tanker | 6 | 1.3% | 474 | 3.6% | 0.35 |
| LPG Tanker | **0** | 0.0% | 421 | 3.2% | **0.00** |

Chemical carriers lead the list only because they dominate the fleet. **Crude oil
tankers are the over-represented type**, and LPG never does this at all.

**By size — the biggest ships, not the smallest:**

| Band | No-berth % | Berthed % | Index |
|---|---:|---:|---:|
| under 20k | 9.8% | 18.4% | 0.53 |
| 20-40k (Handy) | 11.5% | 21.1% | 0.55 |
| 40-60k (MR) | 49.9% | 39.4% | 1.27 |
| 60-85k (LR1/Panamax) | 7.0% | 7.2% | 0.97 |
| 85-125k (LR2/Aframax) | 14.9% | 12.2% | 1.22 |
| **125k+ (Suezmax/VLCC)** | **6.8%** | **1.7%** | **3.95** |

Mean DWT 62,138 for no-berth against 50,044 for berthed. **The largest class is
four times over-represented; the smallest are half as likely.**

**Why: they are lightering.** Draft on no-berth calls, by band:

| Band | Median draft in → out | Draft dropped >1ft |
|---|---|---:|
| 85-125k | **39ft → 31ft** | **54%** |
| 125k+ | **42ft → 35ft** | **50%** |
| 40-85k | 28ft → **37ft** ↑ | 19% |
| under 40k | 26ft → **30ft** ↑ | 33% |

Large ships arrive deep and leave 7-8 feet shallower **without ever berthing**.
Smaller ships on the same population go the other way — arriving light, leaving
deeper. That is the two halves of a lightering operation: the mother ship
discharges to lighter vessels at anchor because the river cannot take her loaded.

**The scale of the cargo work:**

| No-berth tanker calls | |
|---|---:|
| Total | 469 |
| With both drafts recorded | 408 |
| **Draft moved >1ft — cargo worked** | **298 (73%)** |
| — lightered down (gave cargo) | 119 |
| — loaded up (received cargo) | 179 |
| Had an anchorage stop | 370 of 469 |

**The question this raises is William's, not this repo's.** These 298 calls did
real cargo work in the river and bill **$0**, because §9 rules that a leg bills
only if it reached a berth. MRTIS applied that rule exactly as written — nothing
is broken. But the rule was framed around berth work, and lightering at anchor
was very likely not in view when it was set.

At the $3,500 tanker tier the 298 calls would be **$1,043,000** across the series
— roughly **$130,000 a year**. Whether they *should* bill is a commercial matter:
does the agency work a lightering call the way it works a berth call?

**Confidence note.** AIS draft is self-reported and noisy, so individual calls
may be wrong. The population signal is not noise: the direction splits cleanly
(119 down / 179 up rather than a random 50/50 of small wobbles), the magnitudes
are 7-8 feet on the large ships, and the >1ft threshold is the same one MRTIS
itself uses for draft-based activity resolution.

**This also refines I-13.** The 39% of no-berth tanker calls that left within 12
hours are not idle vessels — a large share were working cargo at anchor. The
2021-22 AMA/Kenner Bend coverage question in I-13 still stands separately.

**Proposed fix** None in code until ruled. If William rules lightering billable,
the fee logic needs a concept it does not currently have — cargo work evidenced
by draft change at an anchorage rather than a berth stop — which is a real
change to §9, not a tweak.

**Status** OPEN — needs a business ruling from William.

---

### I-16 · Pre-arrival waiting at `SWP Anch` is invisible to every port call — 294,293 hours — `gap` (scope)

**Severity** `gap` — not a defect; an unstated boundary with a large number behind it
**Where** The port-call boundary itself (`PORT_CALL_SPEC.md` §2), by construction
**Found** 2026-08-20 by William, reading the raw 2025 event rows: *"see how many
of the flagged vessels are for swp anch as the zone?"*

**`SWP Anch` behaves unlike every other anchorage in the data.**

| | Events | Never placed in a call | |
|---|---:|---:|---:|
| **`SWP Anch`** | 14,476 | **14,331** | **99.0%** |
| All other anchorages combined | 97,952 | 1,467 | 1.5% |

And it is not a drift or a bad year — the rate is 98.6-99.5% in **every single
year** from 2019 to 2026.

**Why: the anchorage sits outside the boundary.** A port call opens at the
`SWP Cross` entry. `SWP Anch` is seaward of it, so a vessel riding at anchor
waiting for a berth, a pilot or orders has not yet entered — its anchor and weigh
events precede the call and land nowhere. `unassigned_reason` records this
faithfully as `before_first_entry` or `no_open_call`.

**What that boundary excludes.** Pairing `Anchor` → `Weigh Anchor` per vessel at
that zone:

| Year | Anchor stints | Hours | Median stint |
|---|---:|---:|---:|
| 2019 | 1,842 | 111,645 | 35.6h |
| 2020 | 872 | 36,109 | 17.9h |
| 2021 | 720 | 26,346 | 18.9h |
| 2022 | 584 | 27,065 | 24.1h |
| 2023 | 575 | 26,777 | 23.6h |
| 2024 | 564 | 24,949 | 20.3h |
| 2025 | 531 | 25,771 | 26.9h |
| 2026 (7 months) | 330 | 15,631 | 25.1h |
| **Total** | **6,018** | **294,293 hrs** | **12,262 vessel-days** |

Against the **2,470,459 hours** of `waiting_hours` MRTIS *does* count on legs,
this is **11% of the two combined** — a ninth of all waiting in the dataset,
sitting outside the model entirely.

**This is almost certainly the right boundary, and that is the point.** A vessel
at the sea buoy is not in the river and not yet the agent's berth problem, so
excluding it from a port call is defensible. What was missing is that the
exclusion was never *stated*, and nobody knew its size. A reader of
`docs/BUSINESS_RULES.md` §7 would reasonably assume `waiting_hours` is waiting
time, full stop.

**Effect on reports** No published figure is wrong — `waiting_hours` measures
what it says it measures, in-call waiting after the SWP entry. But any report or
conversation about *how long ships wait* understates it by roughly a ninth, and
2019's 111,645 hours would dominate a like-for-like year comparison if it were
ever added.

**Direct bearing on the parked KPI work.** `docs/KPI_DESIGN_BRIEF.md` frames the
question as **SWP-to-SWP**. This finding shows that framing has a hard edge:
a SWP-to-SWP clock structurally cannot see pre-arrival waiting, no matter how the
other eight questions are answered. That belongs in the brief as a ninth
decision — *does the KPI start at the SWP crossing, or at first contact with the
anchorage?* — because the answer changes the denominator of every wait metric
built on it.

**RULED — William, 2026-08-20:** *"we can keep the swp anch in the records for
posterity in event some anlaysis is needed, but otherwise can exclude from any
and all operations/functions are not relevant, the ships wait there but it's
before they tender nor and commence the port call, so we can ignore."*

**This confirms the existing behaviour rather than changing it.** `SWP Anch`
events are already retained in `port_call_event` with an `unassigned_reason` and
already excluded from every call, leg, fee and time calculation. The ruling makes
that deliberate and gives it the commercial reason it was missing: **the vessel
has not tendered NOR, so the port call has not commenced.**

**What the ruling does to the completeness picture.** Setting `SWP Anch` aside as
out of scope rather than counting it as an unplaced event:

| | Events in scope | Placed | Unplaced |
|---|---:|---:|---:|
| Counting `SWP Anch` as in-scope | 290,305 | 273,336 (**94.2%**) | 16,969 (5.8%) |
| **`SWP Anch` out of scope (ruled)** | 275,974 | 273,336 (**99.04%**) | **2,638 (0.96%)** |

**And the residue is largely a cold start, not a defect:**

| Reason | Count | Character |
|---|---:|---|
| `before_first_entry` | 1,901 | **975 are 2019** — vessels already in the river when collection began. 2023-2026 contribute 13, 17, 27 and 3. |
| `no_open_call` | 737 | Spread across the series |

**Checked: the rule does not extend to a second zone.** `Pilottown Anch` was the
obvious candidate and is **not** a sister to `SWP Anch`:

| Zone | Mile | Events | Unplaced | Rate |
|---|---:|---:|---:|---:|
| **`SWP Anch`** | **−19** | 14,476 | 14,331 | **99.0%** |
| `Pilottown Anch` | **+1** | 1,557 | 408 | 26.2% |
| Next highest (White Castle) | 191 | 1,472 | 92 | 6.2% |

`SWP Anch` sits at **negative mile** — seaward of the crossing — and is 99%
pre-call. Pilottown is *inside* the river and **74% of its events legitimately
belong to calls**; excluding it wholesale would discard 1,149 valid rows to
recover 408, moving completeness only 0.96% → 0.81%. **`SWP Anch` alone is the
clean rule.**

**Clean separation from the fee question.** **Zero** of the fee-bearing unplaced
departure events are at `SWP Anch`, so this ruling leaves
`OPEN_QUESTIONS.md` §11.2 ($2,835,000 across 360 events) exactly as it was.

**Still to do — documentation only, both in this repo:** state the boundary and
its 294,293 hours in `docs/BUSINESS_RULES.md` §7, and add the start-of-clock
question to the KPI brief. The ruling settles *operations*; it does not settle
whether a **KPI** should start at the crossing or at the anchorage, and 294,293
hours still ride on that.

**Status** RULED for operations. Documentation outstanding; KPI start-of-clock
still open.

## Closed

- **I-1** — **fixed** in MRTIS `56ad9f5` (§15.1). 445 legs corrected; nothing else in the database moved.
- **I-7** — ruled A by William 2026-08-20; the build was already correct, $3,492,500 does not move (§15.3).
- **I-10** — **built** in MRTIS `56ad9f5` (§15.2), behaviour-preserving: 0 legs changed fee.
- **I-11** — **fixed** in MRTIS `0c4ed0c` (§15.5). Found while verifying I-1; the build was non-deterministic and the package's byte-identical guarantee was false. Now verified end-to-end across a real rebuild.

### Still open — three investigations and one ruling

| Ref | What it needs |
|---|---|
| **I-2** | Investigation. Bunge Destrehan 85.6% / ADM Destrehan 88.0% FGIS coverage vs 99.6-100% at peer elevators. MGMT's 40% is explained; these two are not. |
| **I-9 (a) and (b)** | Investigation. Never-berthed legs 1.4% → 6.3% and geofence artifacts 11.3% → 12.7%. Part (c), `tpc = 0`, is **closed** — see above. |
| **I-4 / I-5 / I-6 / I-8** | Already disclosed in this package (commit `511c763`); no MRTIS change intended. |
