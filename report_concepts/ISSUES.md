# Issues log — what building the concept reports exposed

Opened 2026-08-20 (session 8). MRTIS commit `2738601c9a87ff7be264f9c10cb1e1a618ef3436`.

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

**Status** OPEN — ruled, not yet fixed. MRTIS is read-only from this repo.

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

**Status** PARTLY RESOLVED — explained at MGMT, still open at two elevators.

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

**Status** OPEN — needs a ruling, blocks nothing.

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

**Status** OPEN.


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

**Status** OPEN — recommended, awaiting the build-fix session.

## Closed

- **I-7** — ruled A by William 2026-08-20; the build was already correct, $3,492,500 does not move.
