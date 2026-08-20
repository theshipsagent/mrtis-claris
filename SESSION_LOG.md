# mrtis-claris session log

## 2026-08-20 (session 9) — The build-fix: three findings closed, one found in the act of fixing

**MRTIS moved, deliberately, for the first time since this repo existed.**
`2738601` → **`68b3a6f`**. William: *"lets fix the 6 findings."*

`CLAUDE.md` directive 2 forbids this repo from writing to MRTIS, so the
suspension was **recorded in the manual before anything was touched**, scoped to
this work and with three conditions carried over from MRTIS's own standing
practice: scratch-copy first, MRTIS's governance for MRTIS's changes, and
`figures.py`'s 0-mismatch self-check as the acceptance test.

### Method

MRTIS's CHANGELOG records the protocol: *"Scratch-copy rebuild and full
reverification before the real repo was touched."* Followed exactly — an isolated
copy of the database, scripts and dictionaries in the scratchpad, every change
built and verified there first, plus a rollback copy of the real database taken
before promotion. **Every claim below is a leg-by-leg comparison against a
pre-change copy, not a comparison of summary totals** — which is precisely why
I-11 was caught.

Only `build_port_calls.py` was re-run. `build_db.py` was **not**, so surrogate
keys were never reassigned and the FGIS layer was never rebuilt.

### Fixed

**I-1 — `ARTCO Destrehan Buoys` no longer asserts grain** (MRTIS §15.1). Both
dictionary rows had `Cargo group = Grain` / *"Apply always"*; William ruled the
berth multi-purpose. **445 legs moved from `Grain` to no cargo group**; the 177
FGIS-evidenced legs kept their tag and tonnage. `ops = Load` and the rule text
left alone — the ruling was about cargo, not direction.

**I-10 — the §12 rule layer split by rule subject** (MRTIS §15.2).
`_fee_bulk_berth_rules()` (R5, the branch that grows) and
`_fee_vessel_type_rules()` (R1-R4, the branch that shouldn't move).

> **One correction to William's proposal, found before building it.** It could
> **not** fork on `vessel_type == "Bulk"`: **R2 (Ro-Ro) fires on bulk-typed
> hulls** — both R2 legs carry `vessel_type = 'Bulk'` — so a vessel-class fork
> would have repriced them. The branches divide by what each rule is *about*
> instead. Built as proposed, it would have been a silent regression.

**I-11 — the port-call build was not deterministic** (MRTIS §15.5). **Found while
verifying I-1, not by looking for it.** The sample export changed on rebuild in
columns the ARTCO fix could not have touched; a controlled two-build test proved
the build itself was the cause.

| Column | Legs differing between two builds of identical code |
|---|---:|
| `cargo` | **524** |
| `destination` | **19** |
| everything numeric and categorical | **0** |

Cause: `string_agg(DISTINCT x, ', ')` with no `ORDER BY` — DuckDB does not
guarantee iteration order, so the same certificates produced `CORN, SOYBEANS` in
one build and `SOYBEANS, CORN` in the next.

**No figure was ever wrong. What was wrong was a guarantee.** This package has
published byte-identical reproducibility for its sample export since session 5.
It was false — and untestable by the way it had been checked, since every prior
test re-ran the export against an *unchanged* database. Only a real MRTIS rebuild
could expose it, and this was the first one.

### Ruled, no change needed

**I-7** (MRTIS §15.3) — the General Cargo discount is a **berth** rule, not a
direction rule. *"vessel type rules, then after that, can modify for bulk ships at
gen cargo facs."* The 635 bulk legs loading at gen-cargo docks keep $5,000;
**$3,492,500 does not move.** The build was already correct. Also recorded: the
commercial reason for the tier — owner's agent inbound at a discount, charterer's
agent on the outbound load at full tariff — which had never been written down.

### Verified

- **Nothing was repriced.** Leg by leg against the pre-change database: **0 legs
  changed `agency_fee`, activity, agency, hours or facility; 0 added or removed; 0
  differing cells across the whole fee-tier × vessel-type grid.** Billable total
  unchanged at **$272,660,000** over 40,245 chargeable legs.
- **`figures.py` still reports 0 attribution mismatches** — an independent
  re-implementation of the schedule, unchanged and still agreeing.
- **No published figure moved.** Every file in this package differs against the
  rebuild by exactly one line: the MRTIS commit stamp.
- **Reproducibility now verified end-to-end, for the first time.** A full MRTIS
  rebuild followed by `figures.py`, `kpi/kpi_baseline.py`, both `report_concepts/`
  scripts, `reports/build_reports.py` and `export/build_review_package.py --sample`
  reproduces **byte-identical output, gzipped sample data included**.

### Added after the fixes: `cargo_subgroup` (I-3)

William ruled the last blocked finding the same day: *"mgmt is grain and by
products, add cargo_subgroup."* Built at MRTIS `68b3a6f` (§15.6).

**The design point is the whole finding.** The obvious implementation — "no FGIS
certificate at a grain berth means by-product" — would have been wrong, because
**the evidence is asymmetric**. A certificate *proves* certified grain; its
absence proves by-product at MGMT and proves nothing at all at Zen-Noh, which
runs 99.6 per cent coverage. Applied globally that rule would have **invented
by-product cargo at nine grain elevators**.

So the fact is **declared per berth** in MRTIS's zone dictionary — a new
`Cargo subgroup uncertified` column, 2 of 220 rows populated, both MGMT — and
NULL everywhere it is genuinely unknown.

| `cargo_subgroup` | Legs | Facilities |
|---|---:|---:|
| `Certified grain` | 10,545 | 40 |
| `Grain by-product` | 254 | **1 — MGMT only** |
| NULL | 31,005 | 108 |

Purely additive: 0 legs differ on `agency_fee`, `activity`, `agency`,
`cargo_group`, `cargo`, `cargo_source`, `destination` or `estimated_tons`.

Downstream, the payoff is visible in **G1c**, a new section of the grain report:
MGMT resolves to 58 certified + 86 declared by-product, while the elevators' 167
unmatched loadings stay **"Not known"** rather than being relabelled. The
reviewer's `DATA_DICTIONARY.csv` and `docs/BUSINESS_RULES.md` §8 both carry the
rule and the reason it is shaped that way.

### And the `tpc = 0` question, traced to the vendor (I-9c)

William: *"as far as i know it was ingressed into the ships register data, noting
its not consistent, some do some dont, so if is there we can populate as
available, if becomes a larger effort to fix, am ok dropping it."*

**Populating was impossible, and the earlier hypothesis in this log was wrong.**
Session 8 guessed this was *"ships-register coverage lagging newer tonnage"*.
It is not a coverage trend at all. Harvesting every IMO/TPC pair from
`Ships_Register`'s 150 raw S&P Global exports — 64,870 rows, 53,904 IMOs:

| | |
|---|---:|
| Raw files carrying a TPC column at all | **58 of 150** |
| Register vessels showing `tpc = 0` | 20,163 |
| — with a real TPC anywhere in raw | **1** |
| **River-calling vessels showing `tpc = 0`** | **1,110** |
| — **with a real TPC anywhere in raw** | **0 (0.0 per cent)** |

S&P does not supply it for these hulls. Neither MRTIS's join nor
Ships_Register's build was losing anything.

**And `0` was never a measurement.** TPC is a function of waterplane area, so a
floating hull always has TPC above zero. It appeared on hulls up to **182,288
dwt** where the real figure is about 120 — **2,417 of 4,045 affected calls (59.8
per cent) on vessels over 20,000 dwt**. Now stored as NULL: 4,045 calls moved,
36,010 keep a real value, and blank means *unknown*, which is true.

**It turned out not to be the "larger effort" you were ready to drop.** `tpc`
lives on `dim_vessel`, so this needed a full rebuild — `build_db` reassigning
every surrogate key, dropping the FGIS and port-call layers. Rehearsed on scratch
first. The chain runs **offline in 36 seconds** (`fgis_source/` is cached, so no
vendor data can shift underneath it), and despite every key being reassigned,
**nothing content-addressed moved**: 0 legs added or removed, 0 differences
across eleven leg columns, billable total unchanged at $272,660,000.

That is worth keeping as a result in itself: **a full MRTIS rebuild is
content-stable**, which the README's key-reassignment warning had left an open
question. This package is now verified byte-identical across one.

**Downstream here:** `figures.py` publishes TPC coverage honestly (36,010 usable,
4,160 not supplied, and a standing assertion that zero placeholders remain), and
the reviewer's data dictionary explains *why* blank is not zero, with the
evidence attached.

### The last two drifts — investigated, and one is a $707,000 finding

Neither was a defect in MRTIS. One was not a defect anywhere.

**Never-berthed legs, 1.4% → 6.3%: a hole in the source feed.** 2025's 356
never-berthed legs include **274 calls of two events or fewer** (49 in 2024) —
vessels crossing into the SWP and out again with nothing recorded between. **161
of those, 58.5 per cent, are Gas carriers**, against 941 Gas calls in the entire
eight-year dataset.

`Venture Global` — Plaquemines LNG — **first appears anywhere in the feed on
2026-02-04**. Never-berthed gas calls ramp 6/month (2025-01) → 25/month
(2026-01), then **collapse to 4 the month the geofence appears** and 0-2
thereafter. Meanwhile gas traffic tripled as the terminal came up: 103 calls in
2024, 308 in 2025, distinct vessels 21 → 93 → 113.

| The blind window, 2025-01 → 2026-01 | |
|---|---:|
| Gas calls with no berth recorded | **202** |
| Distinct vessels | 78 |
| Average time inside the SWP | 50.3 hours |
| **Agency fee never accrued** | **$707,000** |

**MRTIS was right the whole time.** A leg bills only if it reached a berth
(§9). No berth was recorded, so no fee accrued — the rule applied faithfully to
incomplete data. No code fix can invent an event that was never recorded, so this
became **I-12**, which needs a decision from William rather than an
investigation: ask the feed provider to backfill the geofence (a rebuild then
recovers the $707,000 automatically) or annotate the window as known-low.

**Geofence artifacts: this log had the wrong denominator.** The "11.3% → 12.7%"
recorded in session 8 was computed against `sum(berth_stop_count)`. Measured
against berth events proper it is **5.2 / 5.2 / 4.7 / 5.0 / 4.9 / 5.7 / 6.0 /
4.9** per cent across 2019-2026 — a 1.3-point band with 2026 already back down,
and the 2025 bump sitting at named facilities (Zen-Noh, and DRAX which is new to
the feed). Not a trend. `figures.py`'s published geofence figures were always on
the correct denominator and are unaffected; the error was confined to the issues
log.

**Elevator FGIS coverage (I-2): a 2023 dip, not a facility property.** ADM
Destrehan 75.4% in 2023 against 98.2% in 2026; Bunge 69.4% against 96.8%;
Zen-Noh flat at 99-100% as a control. **Not a matching failure** — 2023 posts the
*best* FGIS match rate in the series at 99.8%. There were simply fewer
certificates (1,439 against ~1,650 typical), with elevator certified tonnage at
50.56M t against 61.65M in 2021 while leg counts held flat. The pipeline is
eliminated; what remains is a trade question for William.

### The read-only directive is back in force

`CLAUDE.md` directive 2 was suspended on 2026-08-20 for this work and is
**restored**, with a note recording that it was lifted, why, and that anything
further in MRTIS needs a fresh explicit suspension. MRTIS ends at **`68b3a6f`**,
seven commits on from the `2738601` this package had been built against since
session 3.

### Still open — the honest remainder

"Fix the 6" was never 6 fixes. **All of them are now resolved** — four built, three explained as not-defects, one ruled with no change needed. What is left is not a fix at all:

| Ref | What it needs |
|---|---|
| **I-12** | **A decision from William, not an investigation.** No code fix exists. Ask the feed provider to backfill the Venture Global geofence — a rebuild then recovers 202 calls and $707,000 automatically — or accept the 13-month gap and annotate 2025 gas figures as known-low. |

`CLAUDE.md`'s read-only suspension **stays in force** until those close, and must
be restored when they do.

### Next session

**Nothing is left to investigate.** I-12 needs a decision from William, and the
2023 grain-export question is his trade knowledge rather than this repo's work.
Neither blocks the handover, which remains the outstanding item: **nobody has
imported the sample into Claris yet.**
Unchanged behind all of it: **nobody has imported the sample into Claris yet.**

---

## 2026-08-20 (session 8) — The reporting exercise: ten findings, one closed

**MRTIS commit unchanged at `2738601c9a87ff7be264f9c10cb1e1a618ef3436`** — the
same commit sessions 3-7 built against, verified at open and again at close.
Read-only throughout; every connection opened `read_only=True`. MRTIS ends the
session as it started: same commit, same five untracked `sample_port_calls*.csv`
files, `mrtis.duckdb` mtime still 2026-08-19 22:59 — earlier than this session's
first command.

Session 7 scoped this session as building reports on the proof-of-concept
footing, opening with a Q&A. That is what happened, but the Q&A did not stay a
scoping exercise: **William's answers turned into rulings, and the reports turned
into a defect-finding instrument.** Ten issues logged, one ruled and closed, none
acted on.

### What William ruled, and what it cost or saved

| | Ruling | Effect |
|---|---|---|
| Scope | Three years is enough for this exercise | Window 2023-08-01 → 2026-07-31 |
| Folder | Concept reports get a dedicated folder, apart from the deliverable | `report_concepts/` |
| I-1 | `ARTCO Destrehan Buoys` is **multi-purpose, not grain-only** — the dictionary rule is wrong | 445 legs mis-tagged; reports route around it on FGIS evidence |
| I-2 | MGMT's 40% FGIS coverage is a **grain/by-product split**, not a matching bug | No fix available; two elevators still unexplained |
| I-7 | **Vessel type rules first, then the gen-cargo modifier** — the discount is a berth rule, not a direction rule | **$3,492,500 does not move.** Build was already correct |
| I-10 | Split the schedule: stable non-bulk branch, active bulk branch | Recommended and checked clean; reorganise, do not reprice |

### What shipped

**[`report_concepts/`](report_concepts/)** — deliberately *not* part of the
Claris review package, and its [`README.md`](report_concepts/README.md) says so.
Three report families, all reproducing byte-identically:

| Report | Figures |
|---|---|
| [G1 — grain volume vs ship count](report_concepts/grain_volume_by_month.md) | 4,254 loadings · 2,443 vessels · **175,369,154 tonnes** certified · monthly, per-facility, per-facility x year |
| [G2 — grain revenue by agent](report_concepts/grain_agent_revenue.md) | **$44,646,000** over the same loadings · by agent and agent x facility |
| [P1 — port-wide by facility and agency](report_concepts/portwide_by_facility.md) | **16,260 calls · 103 facilities · 36 agencies · $110,360,250** |
| [Addendum — ARTCO held-out legs](report_concepts/addendum_artco_destrehan.md) | 176 legs · $1,841,000, excluded on the I-1 ruling |

**[`report_concepts/ISSUES.md`](report_concepts/ISSUES.md)** — the actual point of
the exercise. Ten entries, each with severity, reproducible evidence, effect on
reports, and a proposed fix that is **explicitly not applied**. It is the input to
a later build-fix session, which is how William scoped it at the outset.

### The architecture question, answered from the pipeline

William raised the sharpest question of the session mid-way: had the port-call
and KPI work over-complicated what is fundamentally a pivot — measures (count,
tons, revenue) against dimensions (facility, cargo, agent, destination)? He
proposed a seven-phase flow he had proven by hand, and asked whether MRTIS
follows it.

**It does, phase for phase**, and the answer was read out of the database rather
than asserted:

| His phase | MRTIS | Materialised as |
|---|---|---|
| 1 Raw ingest | `build_db.py`, 47 `Zone Report*.csv` | — |
| 2 Staging: 4 sources → one table | Cross In/Out, Anchor, Terminal are `source_category` in the zone dictionary, already unified | **`fact_zone_event`, 290,305 rows** |
| 3 Transformations, canonical rolls | vessel type, zone→facility, agency normalisation | `dim_zone`, `dim_agent` |
| 4 Ships register matching | IMO/name with alias table | `dim_vessel` |
| 5 FGIS matching (extensible) | `build_fgis.py` → `build_fgis_match.py` | **`fgis_record`, 14,528** |
| 6 Unique voyage record ID | `build_port_calls.py` | `port_call`, `port_call_leg` |
| 7 Agency revenue | `agency_fee_for()` | `port_call_leg.agency_fee` |

**All 12 objects in the database are `BASE TABLE`. Zero views.** Nothing is
re-matched at report time; every report this session was a single `GROUP BY`. The
one honest deviation from "one output table" is that MRTIS materialises *three*
grains — event, leg, call — because the fee rule lives at leg grain while time
analysis needs event grain. All three are materialised, so it costs nothing.

The counter-proposal — a flat departures table — is the thing MRTIS already
disproved: per-departure billing totals **$349,527,500 against the ruled
$272,660,000, over-billing by 28.2%**, with 18.8% of fee-bearing calls charged
2-10 times for one job.

### Two of William's trade claims, tested

**Turnover — confirmed precisely, and it validates the pipeline.** William:
*"24-35% bulk ships turn over in the river from discharge to load."* Measured on
the discharge denominator: **1,628 of 5,197 bulk discharge calls = 31.3%**,
mid-range of a expectation formed independently of this data. Strong evidence
split-call detection neither under- nor over-fires. Zero bulk calls carry a
Discharge leg alongside an unresolved leg, so nothing is hidden. Logged as **I-8**
because the same phenomenon yields 7.5%, 31.3% or 48.6% depending on denominator
— a 4.2x spread that could be published without anyone noticing a choice was made.

**Quality trend — half confirmed.** 2019 *is* the worst year (2.8% incomplete,
4-5x every later year; 15.9% unresolved, series high), and the correction was
immediate and durable. But improvement was **not** consistent after 2020: never-
berthed legs 1.4% → 6.3%, geofence artifacts 11.3% → 12.7%, and **`tpc = 0` 4.3%
→ 18.9%, rising every year without exception**. The monotonicity makes that
structural — ships-register coverage lagging newer tonnage — and it is already
deferred upstream as §11.3. Logged as **I-9**.

### Verified

- **MRTIS untouched** — commit, working tree and database mtime identical at
  close to open.
- **Everything reproduces byte-identically** — both new scripts, plus
  `figures.py`, `charts/build_charts.py` and `reports/build_reports.py`. A full
  re-run at close produced no diff at all.
- **The review package did not move.** No file under `sample/`, `charts/`,
  `reports/`, `export/` or `docs/FIGURES.md` changed.
- **Reports reconcile to each other.** G2's grain revenue and P1's port-wide
  revenue share a basis: grain berths are **$44,646,000 of $110,360,250 = 40.5%**
  of the river's agency market over 36 months.
- **Two clean bills of health.** Agency names have **zero** near-duplicates at an
  0.80 similarity threshold; the only near-duplicate facility names are Mile
  110/111/112 Buoys, which are genuinely distinct mile markers.
- **Fee rules observed firing correctly at a single berth** — Nashville Ave bills
  1,047 legs at $750 (R3 container) and 309 at $5,000 (R5 bulk at gen cargo),
  side by side. A better demonstration for a reviewer than prose about the
  schedule.

### Open

The ten issues, of which one is closed:

- **I-1** ARTCO grain rule wrong — **ruled**, 445 legs mis-tagged, unfixed.
- **I-2** FGIS coverage — explained at MGMT, **unexplained at Bunge Destrehan
  (85.6%) and ADM Destrehan (88.0%)**.
- **I-3** `Grain` at MGMT also covers by-products — needs a ruling, blocks nothing.
- **I-4** `port_call.agency` vs `port_call_leg.agency` — $939,000 mis-attributable.
- **I-5** $29,495,250 (10.8%) of revenue on legs where the agent changed mid-leg —
  disclosure, not correction.
- **I-6** `leg_start` vs `call_start` window basis, $42,000 — documentation only.
- **I-7** **CLOSED** — ruled A, build already correct.
- **I-8** Turnover denominator discipline.
- **I-9** Quality trend; `tpc = 0` the priority.
- **I-10** Fee-schedule split — recommended, checked clean, reprices nothing.

Plus, unchanged from session 7: **nobody has imported the sample into Claris
yet** — still the one thing this repo cannot verify for itself.

### The governance point raised and not acted on

Mid-session William said *"it sounds like we need to pause reports and go back to
build."* That was flagged rather than done: **`CLAUDE.md` directive 2 forbids this
repo from writing anything under `/Users/billy/Documents/MRTIS`**, and session 7
recorded William's own confirmation that MRTIS stays parked. Fixing the ARTCO
dictionary row needs either an MRTIS session in that repo or an explicit
amendment here. The recommendation given — and accepted by continuing — was to
keep building reports and batch the fixes, because `build_db.py` reassigns
surrogate keys and drops the downstream layers, so every rebuild forces a full
revalidation of the review package. One batched fix is one rebuild.

### Closing addendum — the three in-repo disclosures, done before push

Asked whether to fix before pushing, the recommendation was: push the known-good
state first, because the MRTIS fixes force a rebuild that would disturb every
figure in the review package. But three of the ten findings are **disclosures
that belong to the reviewer's package, not to MRTIS**, and those were done first.

- **I-4** — `DATA_DICTIONARY.csv` now warns off `PORT_CALL::agency` explicitly
  ("NOT THE COLUMN FOR REVENUE-BY-AGENT REPORTING"), names
  `PORT_CALL_LEG::agency` as the one to use, and quantifies the $939,000 at
  stake. `docs/BUSINESS_RULES.md` §6 gained the same warning.
- **I-5** — §6 now states the magnitude alongside the rule: **3,233 chargeable
  legs (8.03%) carrying $29,495,250 — 10.82% of the billable total** — are legs
  where the agent changed mid-leg. About $1 in $9 of agency revenue is
  attributed to an agent where another agency was also involved. Also surfaced
  on `agent_changed_in_leg` in the data dictionary.
- **I-8** — §5 now publishes the split rate at all three denominators (4.06% of
  all calls / 7.55% of bulk calls / **31.33% of bulk discharge calls**) and says
  plainly that a rate quoted without its denominator is a different number here,
  not a small imprecision.

**All three figures are derived, not hand-keyed.** `figures.py` gained
`agency_grain`, `agent_changed` and `bulk_turnover` derivations, and
`docs/FIGURES.md` two new sections. The package's own discipline applied to its
own disclosures.

**Verified after the change:** `figures.py` still reports **0 attribution
mismatches across 40,245 chargeable legs**, and the only file to move under
`sample/` was `DATA_DICTIONARY.csv` — three field descriptions. **No sample data
row changed**, no chart moved, no report figure moved.

### Next session

Two candidates, both scoped this session and neither started:

1. **The pivot demo** — any measure (count · tonnes · revenue · hours) against any
   dimension (facility · cargo · agent · destination · vessel type · month). It is
   what William described as the platform's whole purpose, and it would stress
   cargo, destination and vessel type, which nothing has exercised yet.
2. **Time analysis** — berth, waiting and idle hours by facility and agent. High
   value, and it does **not** need the parked KPI question settled: those columns
   sit on the same leg row, and the 20.7%-unattributed problem only bites when the
   buckets are required to sum to elapsed time.

Then **the build-fix session**, which now has ten measured findings waiting for it.

Standing entry conditions unchanged: re-check MRTIS's commit before trusting any
figure here, and if it has moved, re-run `figures.py`, both `report_concepts/`
scripts and both export modes before quoting anything.

---

## 2026-08-20 (session 7) — The SWP-to-SWP KPI design brief

**MRTIS commit unchanged at `2738601c9a87ff7be264f9c10cb1e1a618ef3436`** — the
same commit sessions 3-6 built against, verified at open and again at close.
Read-only throughout; every connection opened `read_only=True`. MRTIS's working
tree ends the session as it started: same commit, same five untracked
`sample_port_calls*.csv` files (17:19-17:24 on 2026-08-19, before this repo
existed), `mrtis.duckdb` mtime still 2026-08-19 22:59.

Session 6 left the package as ready as it can get without a reviewer in the
loop, and named two next moves: hand it over, or pick up the parked SWP-to-SWP
KPI framework. Handover is William's action; the KPI framework is a design
conversation with him, not a build task. So the objective was the part that can
be advanced without him in the room: **prepare that conversation** — read what
MRTIS already stores, measure it, and write up the decisions it forces.

### What shipped

**[`docs/KPI_DESIGN_BRIEF.md`](docs/KPI_DESIGN_BRIEF.md)** — eight decisions,
each with options, measured impact and a recommendation where the choice is
technical rather than commercial. It takes no rulings and defines no KPI, and
says so in its opening: a KPI definition is a business rule, and CLAUDE.md's
directive 1 makes that William's, not this repo's.

**[`kpi/kpi_baseline.py`](kpi/kpi_baseline.py) →
[`docs/KPI_BASELINE.md`](docs/KPI_BASELINE.md)** — the derivation behind it. A
design brief carrying hand-keyed numbers is precisely the defect session 4
removed from this package, so the brief quotes and the script derives.
`--check-brief` re-derives and asserts the eleven load-bearing figures the brief
quotes still appear in it, so a rebuilt MRTIS reports the brief as stale rather
than letting it rot quietly.

### The finding that shapes the framework: the clock does not close

The five leg time buckets do not add up to the elapsed time they partition.

| | Hours |
|---|---:|
| Elapsed leg time | 7,232,805 |
| Sum of the five stored buckets | 5,736,739 |
| **Unattributed** | **1,496,066 — 20.7%** |

Not a bug: dwell is recorded only where the feed records a *stop*, and transit
and SWP-crossing rows carry no dwell at all, so a vessel underway between two
stops is in no bucket. It sits in two places — **573,877** hours between leg
start and first berth arrival, **547,466** between last sailing and leg end —
and legs that never reached a berth are 67.9% unattributed.

It matters because it collides with the ruling the framework rests on. William,
2026-08-19: *"as long as time [is] accounted for, otherwise they need no
acknowledgement either by fee or count."* Today one hour in five between the SWP
crossings is in no named bucket, so any KPI built on the current columns either
ignores it or absorbs it into a denominator. That became Q1, and everything else
in the brief inherits its answer.

### Decided (shape only — no business rules were ruled)

- **The KPI derivation is deliberately NOT part of `figures.py`.** `figures.py`
  derives what the package *publishes*, and its fee self-check guards the
  deliverable. Nothing in the KPI work ships to the Claris reviewer, so keeping
  the two apart means a question still in flight can never destabilise a figure
  the reviewer is already holding. Same reasoning in reverse for the README
  entry: filed under "design work in progress", not in the deliverables list.
- **Two structural facts are asserted, not assumed.** The script raises unless
  legs tile the call exactly (leg 1 at `call_start`, last leg at `call_end`, all
  40,170) and no vessel is ever in two calls at once. Both are load-bearing for
  the brief — the first makes every time question reduce to a leg question, the
  second makes a vessel-level sequence well-defined — so a rebuild that broke
  either should fail loudly rather than quietly change what a KPI means.
- **The sequence question is left genuinely open.** *"The seq order of
  SWP-to-SWP KPI calcs"* has two readings — within a call (already built) and
  across calls per vessel (not built). The data supports the second well
  (30,069 calls have a predecessor, zero overlaps, median gap 105 days), but
  what it is *for* is William's to say, so the brief asks rather than assumes.
- **One technical trap flagged as a recommendation, not a question.** A
  vessel-level sequence must key on `dim_vessel.natural_key`, never on
  `vessel_key` — `OPEN_QUESTIONS.md` §10 records that `vessel_key` is row
  position in each rebuild, so a sequence keyed on it would silently renumber.

### Verified

- **MRTIS untouched** — commit, working tree and database mtime identical at
  close to open.
- **Deterministic** — two consecutive runs of `kpi/kpi_baseline.py` produce a
  byte-identical `KPI_BASELINE.md`.
- **Every quoted figure re-derives** — `--check-brief` passes on all eleven.
- **Cross-checked against the package's own published figures** where they
  overlap: 1,632 split calls (4.06%), 38,288 fee-bearing calls, 142 lay-up calls
  holding 23,390 hours / 975 vessel-days — all match `FIGURES.md` and
  `PORT_CALL_SPEC.md` §4 exactly, by a different code path.
- **Every relative link in the two new docs resolves** — 0 broken.
- **The review package did not move.** No file under `sample/`, `charts/`,
  `reports/`, `export/` or `docs/FIGURES.md` was touched.

### Open

Unchanged from session 6, plus the brief's own eight questions, none of which
block the handover:

- **Nobody has imported the sample into Claris yet** — still the one thing this
  repo cannot verify for itself.
- **The eight KPI decisions** await William. Q1 (what happens to the
  unattributed 20.7%) is the load-bearing one; Q3 would also close
  `OPEN_QUESTIONS.md` §14's open scope question as a side effect.
- **MRTIS §13**, **§11.3 `tpc = 0`** — ruled/deferred upstream, still unbuilt.

### Ruled after close (William, 2026-08-20)

**The reports are proof of concept.** Asked whether the sample reports should be
designed against a known downstream consumer, William: *"for the moment,
downstream is not known, so the reports are simply proof of concept."*

That settles the question raised at the end of this session — whether a report
is a working artifact the reviewer re-runs, or a presentation mockup of what a
finished FileMaker report should look like. Neither, for now: they demonstrate
that the data supports reporting at all. The consequences worth holding onto:

- **No downstream contract to satisfy**, so no report needs to anticipate a
  FileMaker layout, a print format or a house style that has not been specified.
- **The derivation discipline still applies in full.** Proof of concept
  describes the *audience*, not the rigour: a figure in a report still comes
  from `figures.py`, never hand-keyed, or the package loses the guarantee
  session 4 built.
- **Presentation polish is explicitly out of scope** until downstream is known.
  When it is wanted, the split discussed this session holds — spec and
  derivation here, formatting elsewhere, with a derived data file as the
  contract between them so no figure is ever retyped into a template.

**MRTIS stays parked**, confirmed by William the same day: the end goal is
handover and integration into FileMaker, and that work lives in this repo.

### Session 7 close (2026-08-20)

Three commits, all pushed to `origin/main` (`6fc0276..45daae8`), working tree
clean and level with origin.

- `b1991cd` — the design brief, `kpi/kpi_baseline.py` and its baseline.
- `1fde843` — this entry.
- `45daae8` — the proof-of-concept ruling on the reports.

**Everything in the repo still reproduces from its script.** A full re-run at
close produced no diff at all: `figures.py`, `kpi/kpi_baseline.py`,
`charts/build_charts.py`, `reports/build_reports.py` and
`export/build_review_package.py --sample` all reproduce their outputs exactly,
chart PNGs and the committed sample included. `figures.py` reports 0
fee-attribution mismatches across 40,245 chargeable legs, all three reports pass
their assertions, and `--check-brief` confirms the design brief's eleven quoted
figures still match MRTIS.

**MRTIS untouched, verified at close as well as at open.** Still
`2738601c9a87ff7be264f9c10cb1e1a618ef3436`, the same five untracked
`sample_port_calls*.csv` files it had on entry, and `mrtis.duckdb`'s mtime still
2026-08-19 22:59 — earlier than this session's first command.

**What changed in the package's character.** Nothing the reviewer holds moved.
What moved is the parked work: the KPI question now has measured ground under it
and a decision order, and the reports have a scope ruling that says what they
are for. Both were previously carried in conversation rather than in the repo.

### Closing addendum — the three in-repo disclosures, done before push

Asked whether to fix before pushing, the recommendation was: push the known-good
state first, because the MRTIS fixes force a rebuild that would disturb every
figure in the review package. But three of the ten findings are **disclosures
that belong to the reviewer's package, not to MRTIS**, and those were done first.

- **I-4** — `DATA_DICTIONARY.csv` now warns off `PORT_CALL::agency` explicitly
  ("NOT THE COLUMN FOR REVENUE-BY-AGENT REPORTING"), names
  `PORT_CALL_LEG::agency` as the one to use, and quantifies the $939,000 at
  stake. `docs/BUSINESS_RULES.md` §6 gained the same warning.
- **I-5** — §6 now states the magnitude alongside the rule: **3,233 chargeable
  legs (8.03%) carrying $29,495,250 — 10.82% of the billable total** — are legs
  where the agent changed mid-leg. About $1 in $9 of agency revenue is
  attributed to an agent where another agency was also involved. Also surfaced
  on `agent_changed_in_leg` in the data dictionary.
- **I-8** — §5 now publishes the split rate at all three denominators (4.06% of
  all calls / 7.55% of bulk calls / **31.33% of bulk discharge calls**) and says
  plainly that a rate quoted without its denominator is a different number here,
  not a small imprecision.

**All three figures are derived, not hand-keyed.** `figures.py` gained
`agency_grain`, `agent_changed` and `bulk_turnover` derivations, and
`docs/FIGURES.md` two new sections. The package's own discipline applied to its
own disclosures.

**Verified after the change:** `figures.py` still reports **0 attribution
mismatches across 40,245 chargeable legs**, and the only file to move under
`sample/` was `DATA_DICTIONARY.csv` — three field descriptions. **No sample data
row changed**, no chart moved, no report figure moved.

### Next session

**Focused on building the reports**, on the proof-of-concept footing ruled
above. It opens with the Q&A to articulate what William wants, and each answer
is a rule to be logged and cited like any other.

Two things still take precedence if they arrive first:

1. **The reviewer's questions**, if the handover has happened — specifically
   whether the FMPXMLRESULT import behaved as `IMPORT_GUIDE.md` describes.
2. **The KPI conversation**, whenever it is wanted, in the brief's order: Q1
   first, then Q2-Q4. Definitions only; they cost nothing to decide and unblock
   the rest.

Standing entry conditions unchanged: re-check MRTIS's commit before trusting any
figure here, and if it has moved, re-run `figures.py`, `kpi/kpi_baseline.py` and
both export modes before quoting anything.

---

## 2026-08-20 (session 6) — The reviewer readiness pass

**MRTIS commit unchanged at `2738601c9a87ff7be264f9c10cb1e1a618ef3436`** — the
same commit sessions 3, 4 and 5 built against, verified at open and again at
close. Read-only throughout. MRTIS's working tree ends the session as it
started: same commit, same five untracked `sample_port_calls*.csv` files
(timestamped 17:19–17:24 on 2026-08-19, before this repo existed), and
`mrtis.duckdb`'s mtime still 2026-08-19 22:59.

Session 5 closed the delivery question and left no build work queued — the next
move was a priority call, and William chose the readiness pass before the
handoff. Objective: read the reviewer-facing docs cold, as a Claris developer
with no MRTIS context would, and fix what assumes knowledge they will not have.

### What the cold read found

The package was correct and complete, and still had two holes that only show up
when you stop being the person who built it:

1. **Nothing told the reviewer how to import it.** `SAMPLE_README.md` promised
   they could "import real rows, wire up the relationships and run a report on
   day one" and then never said which of the two formats to use, in what order,
   or which fields join to which. The package's stated purpose is to be
   imported, and the one page a reviewer would open first was silent on the act
   itself.
2. **The rules doc assumed the shipping vocabulary.** `BUSINESS_RULES.md` is
   written for a FileMaker developer rather than a Python one, which was the
   right axis — but it still spends SWP, layberth, FGIS, TPC, AIS, DWT, dry
   bulk, Ro-Ro, Capesize, pilot sheet, Statement of Fact and topping off
   without defining any of them. A Claris developer has no reason to arrive
   knowing that vocabulary, and §4's evidence ladder is unreadable without it.

### What shipped

**`IMPORT_GUIDE.md`, written by the export script into both modes.** Not a
sample-only document: the full 644 MB export never had a guide of any kind, and
it needs one more, since it is handed over as a bare directory. Sections:
which format and why (`.xml` — FMPXMLRESULT carries field names *and* types in
its `<METADATA>`, so FileMaker creates the fields; CSV means mapping 115 fields
by hand), parent-first import order, the FileMaker steps, what to check as the
rows land, the relationship map, and a checksum table.

**The relationship map is asserted, not described.** A new
`check_relationships()` runs in **both** modes before anything is written and
raises rather than publishing a map that has drifted: all three primary keys
unique, no orphans in either direction, and — the non-obvious one a reviewer
would otherwise have to discover — an event is *either* fully placed (call and
leg) *or* fully unplaced (neither), never one without the other. That last
fact is what makes the `PORT_CALL → PORT_CALL_EVENT` shortcut relationship
safe to offer, and it had never been stated anywhere.

**The checksum table is the practical part.** Row counts, distinct-key count,
commercial/fee-bearing counts, both fee sums and the `call_start` range, all
derived from the rows actually written. The load-bearing line is that
`SUM(PORT_CALL_LEG::agency_fee)` must equal `SUM(PORT_CALL::agency_fee_total)`
— the same money counted from the legs and from the roll-up, so if they agree
after import the parent-child link survived the trip. A silently truncated
import otherwise looks exactly like real data.

Worth recording as an independent confirmation: the full-mode guide derives
$272,660,000, 40,245 chargeable legs and 40,028 commercial calls straight from
the frames being written — matching `figures.py` and `BUSINESS_RULES.md` §9
exactly, by a different code path.

**A glossary on `BUSINESS_RULES.md`**, 26 terms, each tied back to the section
that actually uses it — why AIS noise is why §3 has to collapse berth events,
why the IMO check digit is why §9.2 still bills a corrupted ID, why `tpc = 0`
matters only because a draft survey divides by it. Plus a short "where to
start" note up top: §2, §5, §9 are the model, §1 is the principle underneath.

### Decided

- **The glossary is unnumbered, deliberately.** It was drafted as "§11" and
  that was wrong: the doc already cites MRTIS's `OPEN_QUESTIONS.md` §11.2 and
  §11.3 as bare `§11.x`, so a §11 here would make those read as its
  subsections. It is now "## Glossary", and its two upstream references are
  written out in full. Caught by checking every `§` reference in the new text
  resolved to a real section of this doc — one did not.
- **The glossary says explicitly that it defines words, not rules**, and that
  the linked section is the authority wherever a term has a specific meaning
  here. CLAUDE.md's directive 1 makes MRTIS the oracle for every rule; a
  glossary sitting in the same file as the rules could quietly become a second
  source of them, so it disclaims that in its own opening.
- **Doc references are mode-aware.** The sample ships inside the repo, so it
  links `../docs/BUSINESS_RULES.md`. The full export may arrive as a bare
  directory with no repo around it, so there the guide names the file instead
  of linking to it, and tells the reviewer to check `MRTIS_COMMIT.txt` against
  the commit the docs record if the figures disagree.
- **The FileMaker steps are labelled as unverified, in a callout, in both
  modes.** They come from the file format and FileMaker's documented behaviour,
  not from an import this repo has watched run. Session 5 recorded that gap
  honestly in the log; it now says so on the page the reviewer is actually
  holding, and asks them to report back on exactly that. Turning the one
  unverifiable claim into an explicit question for the reviewer is the most
  useful thing this session did for the handoff.

### Verified

- **Both modes rebuild clean**, relationship assertions passing on the full
  40,170 / 41,804 / 290,305 as well as on the sample.
- **Determinism holds.** Two consecutive `--sample` builds byte-identical.
- **The committed data did not move.** Only four files differ in the working
  tree — the two docs, the export script, and the new guide. All six `.gz` data
  files are untouched, which is the ordering work from session 5 doing its job.
- **The full export's `DATA_DICTIONARY.csv` and `ROW_COUNT_RECONCILIATION.md`
  are byte-identical** to before this change. No figure moved anywhere.
- **Guardrails green.** `figures.py` reports 0 fee-attribution mismatches
  across 40,245 chargeable legs; charts reproduce; all three reports pass their
  assertions ($272,660,000 / $270,875,500 with 409 unattributed legs /
  $15,095,000).
- **Every relative link in the four touched docs resolves** — checked
  programmatically, 0 broken.

### Open

Unchanged, and none of it blocking the handoff:

- **Nobody has imported the sample into Claris yet.** Still the one thing this
  repo cannot verify for itself. The difference after this session is that the
  guide now tells the reviewer exactly what should happen and asks them to say
  if it does not — so the first round of feedback should settle it.
- **MRTIS §13** (General Cargo berths discharge-only, buoy sequencing) — ruled
  upstream, not built. Would move the split/leg baseline the fee figures sit on.
- **§11.3 `tpc = 0`** — deferred upstream; the fix belongs in `Ships_Register`.
- **The SWP-to-SWP KPI framework** — still parked, needs its own design session.

### Session 6 close (2026-08-20)

One commit, pushed to `origin/main` (`af0ff50..8e7c8d4`), working tree clean
and level with origin.

- `8e7c8d4` — `IMPORT_GUIDE.md` in both export modes, the
  `check_relationships()` assertions behind its relationship map, the glossary
  and reading order on `BUSINESS_RULES.md`, and the README refresh.

**The push was raised before it was made, and cleared.** It publishes
documentation only — no additional rows, no change to what `sample/` discloses
— so it sits inside the scope William already ruled on in session 5 rather
than reopening it. Recorded because the ruling said re-raise only if the scope
of what is published changes, and this is the first test of that line: it did
not change, and the push went ahead on his instruction.

**MRTIS untouched, verified at close as well as at open.** Still
`2738601c9a87ff7be264f9c10cb1e1a618ef3436`; working tree carries only the same
five `sample_port_calls*.csv` files it had on entry, timestamped 17:19–17:24 on
2026-08-19 — before this repo existed — and `mrtis.duckdb`'s mtime is still
2026-08-19 22:59, earlier than this session's first command. Every connection
was opened `read_only=True`.

**Everything in the repo still reproduces from its script.** Re-running the
full set at close produced no diff at all: `figures.py`, `charts/build_charts.py`,
`reports/build_reports.py` and `export/build_review_package.py --sample` all
reproduce their outputs exactly, chart PNGs included. `figures.py` still reports
0 fee-attribution mismatches across 40,245 chargeable legs, and all three
reports pass their assertions.

**What changed in the package's character.** Session 5 made a correct package
travel. This session made it *land*: the reviewer now opens a directory that
explains itself — how to import, what joins to what, how to prove the import
arrived whole, and what the words mean. The one claim the package cannot prove
about itself is now printed on the page rather than buried in a log, phrased as
a question to the reviewer. Nothing about the data changed; everything about
receiving it did.

### Closing addendum — the three in-repo disclosures, done before push

Asked whether to fix before pushing, the recommendation was: push the known-good
state first, because the MRTIS fixes force a rebuild that would disturb every
figure in the review package. But three of the ten findings are **disclosures
that belong to the reviewer's package, not to MRTIS**, and those were done first.

- **I-4** — `DATA_DICTIONARY.csv` now warns off `PORT_CALL::agency` explicitly
  ("NOT THE COLUMN FOR REVENUE-BY-AGENT REPORTING"), names
  `PORT_CALL_LEG::agency` as the one to use, and quantifies the $939,000 at
  stake. `docs/BUSINESS_RULES.md` §6 gained the same warning.
- **I-5** — §6 now states the magnitude alongside the rule: **3,233 chargeable
  legs (8.03%) carrying $29,495,250 — 10.82% of the billable total** — are legs
  where the agent changed mid-leg. About $1 in $9 of agency revenue is
  attributed to an agent where another agency was also involved. Also surfaced
  on `agent_changed_in_leg` in the data dictionary.
- **I-8** — §5 now publishes the split rate at all three denominators (4.06% of
  all calls / 7.55% of bulk calls / **31.33% of bulk discharge calls**) and says
  plainly that a rate quoted without its denominator is a different number here,
  not a small imprecision.

**All three figures are derived, not hand-keyed.** `figures.py` gained
`agency_grain`, `agent_changed` and `bulk_turnover` derivations, and
`docs/FIGURES.md` two new sections. The package's own discipline applied to its
own disclosures.

**Verified after the change:** `figures.py` still reports **0 attribution
mismatches across 40,245 chargeable legs**, and the only file to move under
`sample/` was `DATA_DICTIONARY.csv` — three field descriptions. **No sample data
row changed**, no chart moved, no report figure moved.

### Next session

The package is now as ready as it can get without a reviewer in the loop.

1. **Hand it over.** Nothing further is required first.
2. **Work the reviewer's questions** when they come — and specifically capture
   whether the FMPXMLRESULT import behaved as `IMPORT_GUIDE.md` describes, then
   correct the guide from what actually happened and drop the unverified
   callout.
3. **Or pick up the parked SWP-to-SWP KPI framework**, which still needs its
   own design session.

Standing entry conditions unchanged: re-check MRTIS's commit before trusting any
figure here, and if it has moved, re-run `figures.py` and both export modes
before quoting anything.

## 2026-08-20 (session 5) — The delivery question, closed

**MRTIS commit unchanged at `2738601c9a87ff7be264f9c10cb1e1a618ef3436`** — the
same commit sessions 3 and 4 built against, verified at open and again at
close. Read-only throughout: the database was opened `read_only=True`, and
MRTIS's working tree ends the session exactly as it started (same commit, same
five untracked `sample_port_calls*.csv` files, all timestamped 17:19–17:24 on
2026-08-19, i.e. before this repo existed — not ours).

Objective: close the delivery question, open since session 1 and named in
session 4 as the biggest thing between this package and its purpose. `package/`
was 644 MB and gitignored, so a Claris reviewer had no way to receive it.
Session 4 left a recommendation ready to execute; per CLAUDE.md's directive 4 it
was executed rather than re-litigated.

### What shipped

**`--sample` mode on `export/build_review_package.py`**, plus `--sample-start` /
`--sample-end` to override the window and `--no-compress` to build it plain.

The cut is **the most recent complete calendar year**, derived from the data at
run time rather than hard-coded — it rolls forward on its own as MRTIS's export
window advances. Today that is 2025: **5,483 calls, 5,679 legs, 35,703 events**
(13.6% / 13.6% / 12.3% of the full set).

Selection is on the **call**, never on the leg or the event. Every selected call
brings all of its legs and all of its events, including events dated past the
window when the call ran long (event timestamps reach 2026-05-22). Session 4's
constraint — never a truncated event stream — is the whole design: a split call
missing its second leg reads as a single call, and a leg missing its berth
events reads as a leg that never worked cargo. Shipping either would break the
assembly rules this package exists to demonstrate.

The build **asserts** that instead of assuming it. Per call it checks the
shipped leg count against `PORT_CALL.leg_count` and the shipped event count
against `PORT_CALL.event_count`, then checks that no leg or event points at a
call left behind, that no event points at a leg left behind, and that no
unplaced event slipped in. All five invariants were confirmed to hold on the
full dataset first, so a failure means the cut is wrong, not the data.

### Measured, then decided against the plan on one point

Session 4 said "measure before assuming the sample has to cover all three
tables" and rejected compression on the grounds that zipping solves transfer but
leaves "what does the reviewer actually open" unanswered. Both were right, and
the measurement changed the answer:

| | |
|---|---:|
| One year, all three tables, uncompressed | **83 MB** |
| ...of which `PORT_CALL_EVENT.xml` alone | 52 MB |
| Same content, gzipped per file | **4.2 MB** |

52 MB is past GitHub's per-file warning, and 83 MB would land in history again
on every re-export. But FMPXMLRESULT repeats a field tag around every single
value, so it compresses **33x on its own** and **20x across the package** —
the sample therefore ships gzipped per file. This does not contradict session 4's
reasoning — compression *instead of* a sample would have left the reviewer
question unanswered; compression *of* the sample is transport only. The sample
answers what to open; gzip answers how it fits in git. `SAMPLE_README.md`,
`DATA_DICTIONARY.csv`, `ROW_COUNT_RECONCILIATION.md` and `MRTIS_COMMIT.txt`
stay plain so they read on GitHub without downloading anything.

The alternative — narrowing to a quarter to fit uncompressed — was rejected: it
costs the full annual cycle the reporting demo depends on, to save 4 MB.

A small correction worth recording, because it is the project's own standard
biting: the sample guide's size sentence was first written with the figures
hand-keyed from `du` output (79 MB, 33x). Deriving them from the actual byte
counts gave 83 MB and 20x — `du` was reporting 4 KB disk blocks, and 33x is the
XML-only ratio, not the package's. The generated text now computes both from
the files it just wrote, so no window can produce a wrong claim about itself.

### Found and fixed: the export had no `ORDER BY`

Session 4's determinism work covered `figures.py` only. `build_review_package.py`
did `SELECT * FROM {table}` with no ordering — harmless while `package/` was
gitignored and regenerated, but a *committed* sample must be byte-stable or
every rebuild churns the whole file for no reason.

Every table now has an explicit **total** order, each verified unique first:
`port_call_id` on calls, `(port_call_id, leg_seq)` on legs, and
`port_call_id NULLS LAST, event_seq NULLS LAST, event_key` on events —
`event_key` is a unique BIGINT, so it totalises the order even across the
16,969 unplaced events where the first two columns are NULL.

This was not theoretical. Re-exporting showed `PORT_CALL` and `PORT_CALL_LEG`
hashing identically but **`PORT_CALL_EVENT` changing** — its old unordered
output was in storage order, not key order, and nothing guaranteed it would
come back the same way twice. Both modes are now byte-identical across
consecutive runs, and the event table additionally reads grouped by call and in
sequence, which is the order a reviewer wants anyway.

### Verified

- **Determinism:** two consecutive `--sample` builds byte-identical (gzip
  written with `mtime=0` and no stored filename); two consecutive full builds
  byte-identical.
- **Independently, not just via the script's own assertions:** the sample was
  decompressed and re-checked from scratch — 11 checks, all pass. Referential
  integrity in both directions; no unplaced events; every call has ≥1 leg; all
  `call_start` inside the window; each call's `agency_fee_total` equals the sum
  of its legs' fees; and counts *and* fee total re-queried straight from MRTIS
  for the same window match exactly (5,483 / 5,679 / 35,703, $36,544,500).
- **XML:** all three files parse; `FOUND` attribute equals the actual row count
  in each; XML row order matches CSV row order.
- **Full export unchanged where it matters:** `ROW_COUNT_RECONCILIATION.md` and
  `DATA_DICTIONARY.csv` byte-identical to before the ordering change. No figure
  moved.
- **Guardrails still green:** `figures.py` reports 0 fee-attribution mismatches
  across 40,245 chargeable legs; all three reports pass their assertions;
  re-running produced no diff in any derived doc.

### Decided

- **The sample's numbers are subtotals, and say so in three places.** Its
  reconciliation prints every sample total beside the full-dataset one; its
  README says not to quote a number off that directory; and it points at
  `docs/FIGURES.md` for the published figures. A reviewer reading
  $36,544,500 must not mistake it for the $272,660,000 headline.
- **`DATA_DICTIONARY.csv` keeps an identical schema and identical wording in
  both modes**, with `null_pct`/`example` computed over the rows actually
  shipped. Disclosed in the sample README, since a rarely-populated field can
  read 100% null in a one-year cut while being populated in the full set.
- **Unplaced events are excluded and disclosed.** 16,969 events belong to no
  call, so a whole-calls cut structurally cannot carry them; the README says a
  reviewer assessing completeness handling should ask for the full export.
- **A rate quoted in a field description must derive from the rows shipped.**
  Found while explaining §11.3 after the push: `PORT_CALL.tpc`'s data-dictionary
  entry warned that `0` "appears on ~10% of calls" — the full-dataset rate,
  hand-keyed. In the 2025 sample the real rate is **15.8%** (869 of 5,483), so
  the sample's own dictionary was describing a different population by about six
  points. The description is now built by a `DERIVED_DESC` callable that
  receives the post-cut frame, so the full export reads 10.1% and the sample
  reads 15.8%, each true of the directory it sits in. Its static `*_DESC` entry
  is `None` and the loader raises if a `None` has no `DERIVED_DESC` behind it —
  a description can never be both static and derived, and can never go missing.
  Only that one description changed in the full export; the reconciliation is
  byte-identical. Worth noting the same discipline was already in force
  elsewhere: `BUSINESS_RULES.md`'s §11.3 line (4,045 calls, 10.07%) reads from
  `figures.py`, so it was correct and needed no change.
- **The sample goes to the public repo — William's explicit ruling.** Raised
  before pushing, because it is a real step up in disclosure: the repo already
  published agency-level aggregates (Norton Lilly, $41,243,000 and so on), but
  `sample/` publishes 5,483 *individual* port calls, each naming the vessel,
  IMO, agency, berth and its own fee — commercially readable at the row level.
  Options put to him were public push, code-only with the sample transferred
  directly, flipping the repo private, or holding. He chose **push to the
  public repo**. Worth re-raising only if the scope of what is published
  changes again, not for a routine re-export of the same cut.

### Open

Unchanged from session 4, none of it blocking:

- **MRTIS §13** (General Cargo berths discharge-only, buoy sequencing) — ruled
  upstream but not built. It would move the split/leg baseline these fee figures
  sit on. Disclosed in `docs/BUSINESS_RULES.md` §10.
- **§11.3 `tpc = 0`** — deferred upstream; the fix belongs in `Ships_Register`.
- **The SWP-to-SWP KPI framework** — still parked, needs its own design session.

Newly open, and small:

- **Nobody has imported the sample into Claris yet.** The XML is well-formed
  FMPXMLRESULT and the CSV is clean, but "FileMaker parses it" is asserted from
  the format, not observed. That is a reviewer's step, not something this repo
  can verify for them — worth stating plainly rather than implying it was
  tested.

### Session 5 close (2026-08-20)

Three commits, all pushed to `origin/main`, working tree clean and level:

- `78d9e27` — the `--sample` mode, the explicit `ORDER BY`, and the sample itself.
- `fe73533` — the disclosure ruling on publishing row-level data.
- `edba7e4` — the derived `tpc = 0` rate (a follow-up, prompted by a question
  about §11.3 after the push, not by a planned task).

**MRTIS untouched, verified at close as well as at open.** Still
`2738601c9a87ff7be264f9c10cb1e1a618ef3436`; its working tree carries only the
same five `sample_port_calls*.csv` files it had on entry, timestamped 17:19–17:24
on 2026-08-19 — before this repo existed — and `mrtis.duckdb`'s mtime is
2026-08-19 22:59, earlier than this session's first command. Every connection
was opened `read_only=True`.

**Everything in the repo reproduces from its script.** Re-running the full set
at close produced no diff at all: `sample/` rebuilds byte-identically to what is
committed, and `figures.py`, `charts/build_charts.py` and
`reports/build_reports.py` all reproduce their outputs exactly — the chart PNGs
included. `figures.py` still reports 0 fee-attribution mismatches across 40,245
chargeable legs, and all three reports pass their assertions.

**What changed in the package's character.** For four sessions this was a
correct package that could not be delivered. It is now a correct package that
travels: a reviewer clones the repo and has 5,483 real port calls, whole, with a
guide that states what the cut is and what it is not. The full 644 MB export is
unchanged and still available on request.

### Closing addendum — the three in-repo disclosures, done before push

Asked whether to fix before pushing, the recommendation was: push the known-good
state first, because the MRTIS fixes force a rebuild that would disturb every
figure in the review package. But three of the ten findings are **disclosures
that belong to the reviewer's package, not to MRTIS**, and those were done first.

- **I-4** — `DATA_DICTIONARY.csv` now warns off `PORT_CALL::agency` explicitly
  ("NOT THE COLUMN FOR REVENUE-BY-AGENT REPORTING"), names
  `PORT_CALL_LEG::agency` as the one to use, and quantifies the $939,000 at
  stake. `docs/BUSINESS_RULES.md` §6 gained the same warning.
- **I-5** — §6 now states the magnitude alongside the rule: **3,233 chargeable
  legs (8.03%) carrying $29,495,250 — 10.82% of the billable total** — are legs
  where the agent changed mid-leg. About $1 in $9 of agency revenue is
  attributed to an agent where another agency was also involved. Also surfaced
  on `agent_changed_in_leg` in the data dictionary.
- **I-8** — §5 now publishes the split rate at all three denominators (4.06% of
  all calls / 7.55% of bulk calls / **31.33% of bulk discharge calls**) and says
  plainly that a rate quoted without its denominator is a different number here,
  not a small imprecision.

**All three figures are derived, not hand-keyed.** `figures.py` gained
`agency_grain`, `agent_changed` and `bulk_turnover` derivations, and
`docs/FIGURES.md` two new sections. The package's own discipline applied to its
own disclosures.

**Verified after the change:** `figures.py` still reports **0 attribution
mismatches across 40,245 chargeable legs**, and the only file to move under
`sample/` was `DATA_DICTIONARY.csv` — three field descriptions. **No sample data
row changed**, no chart moved, no report figure moved.

### Next session

No build work is required to send this — the next move is William's call, not a
technical one:

1. **Hand the sample to the Claris reviewer and work their questions.** The
   obvious next step, and the one everything so far was for. The first thing it
   would settle is the one thing this package still cannot self-verify: that
   FileMaker actually parses the FMPXMLRESULT. Well-formed is proven; imported is
   not.
2. **Pick up the parked SWP-to-SWP KPI framework**, which needs its own design
   session.

Whichever comes first, the standing entry conditions are unchanged: re-check
MRTIS's commit before trusting any figure here, and if it has moved, re-run
`figures.py` and both export modes before quoting anything.

Still open upstream and not blocking either path: **MRTIS §13** (ruled, unbuilt
— would move the split/leg baseline these fee figures sit on) and **§11.3
`tpc = 0`** (deferred by William to a later triage; the fix belongs in
`Ships_Register`, whose register file stores the literal zeros).

### How to reproduce this build

```
python3 -m venv .venv && .venv/bin/pip install duckdb pandas matplotlib
.venv/bin/python3 export/build_review_package.py           # full, 644 MB, gitignored
.venv/bin/python3 export/build_review_package.py --sample  # committed, 4.2 MB
.venv/bin/python3 figures.py
.venv/bin/python3 charts/build_charts.py
.venv/bin/python3 reports/build_reports.py
```

All of them open MRTIS's `mrtis.duckdb` `read_only=True` and write only inside
this repo.

## 2026-08-19 (session 4) — Clearing the stale figures: one derivation, and the audit backlog

**MRTIS commit unchanged at `2738601c9a87ff7be264f9c10cb1e1a618ef3436`** —
same commit session 3 exported against, so session 3's verified row counts and
fee totals still hold and `package/` did not need rebuilding. Read-only
against MRTIS throughout; the database was opened `read_only=True` and nothing
under `/Users/billy/Documents/MRTIS` was written.

Objective: finish the work session 3 deliberately stopped short of — the
stale charts and reports, the untouched `docs/BUSINESS_RULES.md`, and audit
#2's remaining A4–A14.

### The root cause, fixed properly

Sessions 1–3 hard-coded figures into three places at once: the rules doc, the
charts script, the reports script. When MRTIS rebuilt they all went stale
together, and three of them (A7, A8, A14) had never re-derived in the first
place. Editing the numbers again would have rebuilt the same trap.

**New: [`figures.py`](figures.py)** — one derivation, read live from MRTIS,
that every other deliverable now reads from. It writes `docs/FIGURES.md` and
`docs/figures.json`; `charts/build_charts.py` and `reports/build_reports.py`
import it, and the reports **assert** their totals against it rather than
printing whatever they computed.

Its most useful property: it re-implements William's §12 fee precedence
independently in SQL, then checks leg by leg that its answer equals the
`agency_fee` MRTIS actually stored. **0 mismatches across all 40,245
chargeable legs.** If MRTIS's `agency_fee_for()` ever moves without this
package catching up, the script raises instead of publishing a plausible
wrong number. That assertion is the thing A10 claimed a comment was doing and
wasn't.

### Re-derived — what actually moved

| Figure | Was published | Now derives |
|---|---:|---:|
| Billable (leg) basis | $272,167,500 | **$272,660,000** |
| Per-departure basis | $349,625,500 | **$349,527,500** |
| Over-bill of one against the other | "roughly 17%" | **$76,867,500 (28.2%)** |
| R5 | 3,112 legs / $15,560,000 | **3,019 legs / $15,095,000** |
| R2 | "0 legs, no matching traffic" | **2 legs, $21,000 → $2,000** |
| Six-rule net effect | −$26,701,000 (−8.9%) | **−$26,208,500 (−8.77%)** |
| Split-call rate | 4.1% | **4.06%** (1,632 calls) |
| Activity resolved | 83.3% | **82.79%** |
| Geofence artifacts | 5.3% | **5.23%** of all berth events (5.27% of placed) |

R5's 93-leg drop reconciles exactly against session 3's +$511,500
first-working-berth figure — the two were derived independently and agree.

### Audit backlog — A4 through A14 now closed

- **A4** — `§9.2` said the $10,500 tier was "canonical Bulk **or** register
  `ship_type_group` starting Bulk Carrier". In `agency_fee_for()` the register
  is consulted **only when the canonical type is absent**: a fallback, not an
  alternative. Rewritten as an explicit 5-step first-match-wins table with the
  3 live counterexamples (one Container, one Tanker, one Other, all correctly
  billing $3,500 where the old wording said $10,500). This was the finding
  most likely to be built wrong in FileMaker.
- **A7** — activity percentages re-derived, and the "never reached a berth"
  bucket (3.38%) now shown as its own row rather than omitted.
- **A8** — 18.8%, and stated as *of fee-bearing calls*, with 17.9% of all
  calls given alongside so the denominator can't be misread.
- **A9** — the three §12.4 mis-citations now point at §12.2 / §12.3.3.
- **A10** — the false comment is gone; the check it described now exists.
- **A11** — reports 1 and 2 no longer mix denominators. Both now carry the
  fee-bearing and all-rows counts as separate columns, and the averages say
  which they are over. (Gas: 941 calls, 726 fee-bearing — the two averages
  $2,700 and $3,500 now both divide out.)
- **A12** — report 2's shortfall is disclosed and reconciled: **409
  chargeable legs carry no agency at all**, $1,784,500, which is exactly the
  gap between the report's $270,875,500 and the package's $272,660,000.
- **A13** — `§10` now discloses the dredge/workboat removal (9 vessels,
  23,228 rows, 7.4% of the raw feed), the *Egret* exclusion (131 rows,
  $98,000 of fabricated fee), and a table of the still-open §11.x items.
- **A14** — both denominators quoted, so the 5.23%/5.27% ambiguity is stated
  rather than resolved silently in one direction.

### Rules doc brought current

`docs/BUSINESS_RULES.md` described the pre-rebuild rules throughout. Now
covers: lay-up calls flagged not deleted (`is_commercial_call` / `call_class`,
142 calls); layberth as non-commercial time (`berth_hours` no longer includes
it, 45,741.57 hrs moved to `layberth_hours` — flagged as *the* change most
likely to surprise anyone comparing an older extract); R5 off the first
**working** berth, with the 93-leg / +$511,500 correction explained; R2
extended to `General Cargo Ship (with Ro-Ro facility)`; and §11.1a's
unresolved-outranks-`No Cargo` fix, with the live check that **0 legs** now
report `No Cargo` while billing.

### Disclosed rather than discovered — the two per-departure roll-ups

`port_call_event.agency_fee` ($349,527,500) and
`SUM(port_call.agency_fee_departures_total)` ($346,692,500) differ by
$2,835,000 — 360 departure events that never landed in a call. This is
MRTIS §11.2, already ruled *leave as is*, not a new finding. Worth recording
that the gap re-derives $98,000 smaller than §11.2's $2,933,000, exactly the
fabricated *Egret* fee removed at ingest by §7.5 — an independent confirmation
that the Egret guard did what it claimed. Now disclosed in `§9.1` and in
report 1, because the two numbers give different over-billing ratios and a
reviewer picking either one silently gets a different answer.

### Verified

- `figures.py`: 0 fee-attribution mismatches / 40,245 chargeable legs.
- Reports 1, 2 and 3 assert their totals against `figures.py` and pass;
  report 2's $270,875,500 + $1,784,500 unattributed = $272,660,000 exactly.
- Every dollar figure and count in `BUSINESS_RULES.md` re-checked
  programmatically against `docs/figures.json` — all match.
- `package/` untouched and still consistent: its `ROW_COUNT_RECONCILIATION.md`
  totals equal `figures.py`'s, and its `DATA_DICTIONARY.csv` cross-references
  (sections 4, 5, 6, 9) all still resolve after the doc rewrite.
- The repo's `.venv` was missing on entry (gitignored) and was rebuilt per the
  documented setup.

### Open

- ~~`docs/PORT_CALL_SPEC.md` in MRTIS is itself stale.~~ **Withdrawn — checked,
  and it isn't.** This entry originally carried A7's finding forward without
  re-reading the current file. A7 was written during audit #2, *before* the
  rebuild; MRTIS updated the spec as part of that rebuild. Re-checked against
  this session's independent derivation and every figure agrees: §3's
  dictionary 35.9 / draft 46.1 / FGIS 0.8 / unresolved 13.8 / never-berthed
  3.4 and **82.8% resolved** against 35.86 / 46.14 / 0.79 / 13.82 / 3.38 and
  82.79%; §4's 4.1% split against 4.06%; §2's 5,102 collapsed berth events
  exactly; §1's 98.8% complete against 98.81%. The spec even states it is
  "post the 2026-08-19 non-commercial-time rebuild". **Nothing to fix
  upstream.** The lesson worth keeping: an audit finding names a moment, not a
  permanent state — re-verify before carrying one into a later session.
- **MRTIS §13** (General Cargo berths discharge-only, buoy sequencing) is
  ruled but not built. It would move the split/leg baseline these fee figures
  sit on. Disclosed in `§10`.
- **§11.3 `tpc = 0`** is deferred upstream; the fix belongs in
  `Ships_Register`, not here.
- The SWP-to-SWP KPI framework is still parked and needs its own design
  session.

### Session 4 close (2026-08-20)

Everything above is committed and pushed to `origin/main` (`e7e0898`, plus
`81ed1a8` withdrawing the spec-staleness note). Working tree clean, level
with origin. MRTIS untouched and still at `2738601c` — verified at close, not
just at open.

**The package's own figures needed no rebuild.** MRTIS hasn't moved since
session 3, so `package/` is still valid; its
`ROW_COUNT_RECONCILIATION.md` totals were re-checked against `figures.py`
this session and match exactly.

**Next session — the delivery question, open since session 1 and now the
biggest thing standing between this package and its purpose.** `package/` is
**644 MB** and gitignored. A Claris reviewer cannot import what they cannot
receive, and right now nothing in the repo gets it to them.

Recommendation, ready to execute rather than re-litigate:

1. **Add a `--sample` mode to `export/build_review_package.py`** producing a
   committable subset — whole port calls with all their legs and events
   intact (never a truncated event stream, which would break the assembly
   rules the package exists to demonstrate). One recent full year is the
   obvious cut. This is what lives in git and what a reviewer opens first.
2. **Keep the full 644 MB package as an on-request transfer**, built by the
   existing default mode. Nothing about it changes.
3. The bulk is `PORT_CALL_EVENT` (422 MB XML + 100 MB CSV). `PORT_CALL` and
   `PORT_CALL_LEG` together are ~108 MB and may be shippable whole — worth
   measuring before assuming the sample has to cover all three tables.

Why a sample rather than compression: a reviewer assessing *Claris
compatibility* needs to exercise import, relationships and a report against
real rows, not to hold all 290,305 events. Zipping solves transfer and leaves
the "what does the reviewer actually open" question unanswered.

Also still open, unchanged and not blocking: MRTIS §13 (ruled, unbuilt),
§11.3 `tpc = 0` (deferred to `Ships_Register`), and the SWP-to-SWP KPI
framework (parked, needs a design session).


## 2026-08-19 (session 3) — Re-export against the rebuilt MRTIS

**Re-exported against MRTIS commit `2738601c9a87ff7be264f9c10cb1e1a618ef3436`**
("End-session ritual: CHANGELOG entry, README structure refresh, MRTIS
parked"), up from `09e1cb63` — **four commits of MRTIS build work**, all of
it landing on figures this package publishes. Read-only against MRTIS
throughout; the database was opened `read_only=True` and nothing under
`/Users/billy/Documents/MRTIS` was written.

**Context: MRTIS is now parked.** William's direction closing that session —
*"focus only on Claris FM moving ahead, can park the other version"* — so
this repo is the active line of work from here, and MRTIS is a stable
upstream that is not expected to move again soon. That makes this re-export
a re-sync against a settled source rather than a moving one.

### What moved upstream, and why every figure here had to change

Four MRTIS commits (`e7ae299`, `22df777`, `578ed81`, `2738601`) implemented
the five rulings recorded at the end of session 2 below, plus eight further
rulings taken in the same conversation. The parts that reach this package:

| Change (MRTIS section) | Effect here |
|---|---|
| R5 prices off the leg's first **working** berth (§12.3.3.1) | +$511,500 over 93 legs — **not** the +$440,000/80 legs session 2 predicted; see below |
| Layberth out of `berth_stop_count`/`berth_hours`, into new `layberth_hours` (§8) | 45,742 hrs / 389 stops / 379 legs reallocated; **2 new columns** |
| Pure lay-up calls flagged, not deleted (§8/§14) | **2 new columns** (`is_commercial_call`, `call_class`); 142 calls out of counts |
| Unresolved outranks `No Cargo` for a leg's label (§11.1a) | 54 legs relabel; **0** legs now report `No Cargo` while billing |
| R2 extended to `General Cargo Ship (with Ro-Ro facility)` (§12.3.2) | −$19,000 over 2 legs |
| Fabricated `Egret` excluded at ingest (§7.5) | **131 fewer spine rows**; per-departure basis −$98,000 |

**Session 2's own R5 estimate was wrong, and MRTIS caught it.** The handoff
brief at the end of this log predicted "80 legs, +$440,000". That enumerated
only 5 of the 14 `ops = Layberth` zones by name and silently omitted the five
Violet Dock zones — despite the same write-up confirming all 14 carry
`facility_type = General Cargo`. Re-derived in MRTIS from the rebuilt
database: **107** chargeable Bulk legs have a layberth first stop, **93**
revert to the $10,500 base tier (**+$511,500**), and 14 correctly stay at
$5,000 against a genuine General Cargo working berth. Recorded here because
it is this repo's estimate that was wrong, not MRTIS's.

### Done

1. **Added the four new columns' `*_DESC` entries** — `is_commercial_call`,
   `call_class`, `layberth_hours` (on `PORT_CALL`) and `layberth_hours` (on
   `PORT_CALL_LEG`). The export hard-failing without them was the script
   behaving as designed (it refuses to ship an undocumented field), exactly
   as session 2 predicted; it was not a bug and cost about a minute.
2. **Rewrote the descriptions whose *meaning* changed** — more important than
   the additions, because these would otherwise have shipped saying the
   opposite of what the data now does: `berth_stop_count` and `berth_hours`
   (both now exclude layberth), `first_berth_zone`/`first_berth_facility`/
   `facility_type` (now the first **working** berth, and the field R5 prices
   off), and `activity` (an unresolved stop now outranks `No Cargo`).
3. **Fixed three audit findings that live in this script** (A5, A6), since
   they were about to ship wrong a second time:
   - `port_call_event.agency_fee` claimed "over-bills by roughly 17% (see
     BUSINESS_RULES.md §9.1)" — a figure its own citation never supported.
     Now states ~28% *and points at `ROW_COUNT_RECONCILIATION.md`*, which
     re-derives both bases on every export, rather than hard-coding a fourth
     number that will go stale again.
   - `vessel_key` pointed at a `BUSINESS_RULES.md` discussion that does not
     exist. Now carries the warning that actually matters to a FileMaker
     developer: **it is positional and changes on every MRTIS rebuild — do
     not key a file on it**; use `imo` or `port_call_id`/`leg_id`.
   - `tpc` likewise. Now states plainly that `0` is a literal placeholder for
     "not available" on ~10% of calls, not a measured value, and to filter
     `tpc > 0` before any draft-survey maths.
4. **Re-exported and verified.**

### Verified — re-derived from the database, not read out of the script's own output

| | Database | Exported CSV |
|---|---:|---:|
| `PORT_CALL` | 40,170 | 40,170 |
| `PORT_CALL_LEG` | 41,804 | 41,804 |
| `PORT_CALL_EVENT` | 290,305 | 290,305 |
| Billable (leg basis) | $272,660,000 | $272,660,000 |
| Per-departure (comparison) | $349,527,500 | $349,527,500 |
| Commercial calls | 40,028 | 40,028 |
| Lay-up calls | 142 | 142 |
| `layberth_hours` total | 45,741.57 | 45,741.57 |

All eight match exactly. Also confirmed: **115 fields** across the three
tables (was 111); all three XML files parse **well-formed** under expat
(including the 422 MB `PORT_CALL_EVENT.xml`), with `<ROW>` counts,
`<COL>`-per-row, `DATABASE@RECORDS` and `RESULTSET@FOUND` all mutually
consistent; booleans coerced to 1/0 with no `True`/`False` leaked; and **0**
legs report `activity = 'No Cargo'` while carrying a fee — the contradiction
audit #2 raised as A3 is gone from the exported data.

### Open — the next unit of work, deliberately not started

- **Charts and reports are now stale.** Both carry hard-coded figures from
  the old build: `reports/build_reports.py` reconciles against $272,167,500
  and "$15,560,000 / 3,112 legs" for R5, and `charts/build_charts.py`'s
  chart 4 hard-codes the R5 pair (32,676,000 → 15,560,000). Every one of
  those needs re-deriving, not just re-running. Chart 4 is also where audit
  finding A10 sits (a comment claiming a verification the script does not
  perform).
- **Audit #2's A4-A14** are otherwise still open (A5 and A6 are now closed
  by item 3 above; A3 is closed upstream by the §11.1a rebuild).
- `docs/BUSINESS_RULES.md` has not been touched this session and still
  describes the pre-rebuild rules throughout.
- The repo was **1 commit ahead of `origin/main`** on entry (`fdf56b3`,
  session 2's audit) — still unpushed.

## 2026-08-19 (session 1) — First build: business rules, export, charts, reports

**Built against MRTIS commit `09e1cb633ee9dc86a0393956eb118c9c8d5bafb8`**
(`git -C /Users/billy/Documents/MRTIS log -1` — "Close out session log:
mrtis-claris scoped and set up, repo confirmed non-sensitive"). Read-only
against MRTIS throughout; nothing in `/Users/billy/Documents/MRTIS` was
touched.

### What was done

Followed `CLAUDE.md` §3 in full, first session for this repo:

1. Confirmed and recorded the MRTIS commit above.
2. Read `MRTIS/docs/PORT_CALL_SPEC.md` in full and `MRTIS/docs/OPEN_QUESTIONS.md`
   in full (not just §12 — the whole document, since later sections
   reference and revise earlier ones and the fee-tier ruling in §12 only
   makes sense against §7/§8's billing-unit rulings).
3. Wrote [`docs/BUSINESS_RULES.md`](docs/BUSINESS_RULES.md) — port-call/leg/
   split assembly rules and the full agency fee schedule (base tiers + all
   six §12 rules), plain language, every rule cited back to its MRTIS section
   or ruling. Cross-checked every dollar figure quoted against the live
   database rather than trusting the doc's own numbers (see below).
4. Read `/Users/billy/Documents/Ships_Register/src/build_filemaker_package.py`
   as the proven precedent, then wrote
   [`export/build_review_package.py`](export/build_review_package.py) —
   reads MRTIS's `data/db/mrtis.duckdb` **read-only**, exports `port_call`,
   `port_call_leg`, `port_call_event` as CSV + FMPXMLRESULT XML, plus a
   `DATA_DICTIONARY.csv` (111 fields across the three tables) and a
   row-count/fee reconciliation. Column list and types are read live from the
   database's `information_schema` rather than hand-copied, so the export
   can't silently drift from `MRTIS/sql/schema_port_call.sql` — an
   undocumented column fails the build loudly instead of shipping unexplained.
5. Built four sample charts ([`charts/`](charts/)): fee revenue by vessel
   type, split-call rate, port calls by vessel type, and the §12 fee-tier
   rule-by-rule impact.
6. Built three sample canned reports ([`reports/`](reports/)): agency fee by
   vessel type, port calls/fee by agent (leg-grain agency, not raw per-event
   agent), and an R5-specific drill-down (dry bulk calling General Cargo
   berths, by facility).

### What was verified, not just asserted

Ran everything against the live `mrtis.duckdb` (read-only) rather than
trusting `OPEN_QUESTIONS.md`'s own stated figures, since that doc is a working
log and the database is the built artifact:

- Leg-basis billable total: **$272,167,500** over 40,245 legs — matches
  `OPEN_QUESTIONS.md` §12's "final verified figures" exactly, on both
  `SUM(port_call_leg.agency_fee)` and `SUM(port_call.agency_fee_total)`.
- Per-departure frozen basis: **$349,625,500** — matches, and confirmed
  genuinely frozen (unaffected by the §12 tiers, per the `apply_2026_tiers`
  flag in `build_db.py`).
- R5 (dry bulk @ General Cargo berth): **$15,560,000 / 3,112 legs** exactly —
  used as the reconciliation target for report 3 (`r5_general_cargo_bulk_impact`).

### Decisions made without stopping to ask

Per `CLAUDE.md` §2.4, these were technical calls within Phase 1's scope, not
business-rule questions — stated and proceeded on:

- **Full export, not a sample.** `export/build_review_package.py` exports all
  40,170 / 41,804 / 290,436 rows rather than a trimmed sample, matching
  CLAUDE.md's "real importable data" framing. Result is a ~638MB `package/`
  directory (`PORT_CALL_EVENT.xml` alone is ~440MB, FMPXMLRESULT is verbose).
  Kept out of git for now — see "Open" below.
- **DuckDB BOOLEAN → FileMaker NUMBER (1/0).** FileMaker has no native
  boolean type; this is the conventional mapping, same reasoning
  `Ships_Register`'s package uses implicitly by never emitting one.
- **Column order/type read live from `information_schema`, not hand-typed.**
  A stricter version of the `Ships_Register` pattern (which hand-lists
  `FIELD_SPEC`) — chosen because `schema_port_call.sql` has three tables and
  ~100 columns with rich inline comments already; re-deriving those by hand
  risked silent drift from the schema. The script hard-fails if a DB column
  has no matching description, so nothing ships undocumented.

### Open, for next session

- **MRTIS's own §13 (General Cargo discharge-only, buoy sequencing) is ruled
  but not yet built** as of this commit — explicitly phase 2 in MRTIS. It
  would move the split/leg baseline every fee figure in this package sits on.
  Watch `MRTIS/docs/OPEN_QUESTIONS.md` §13's "Still open" note and re-export
  when it lands, per the commit-tracking discipline in `CLAUDE.md` §4.
  Documented in `docs/BUSINESS_RULES.md` §10.
- **`package/` is generated, not committed.** Decide whether the reviewer
  gets the full package as a zip/transfer, or whether a lighter sample export
  mode should be added to `export/build_review_package.py` for anything that
  needs to live in git.
- Charts and reports are static PNG/CSV/MD snapshots of this build — no
  refresh automation. Fine for a one-time review package; would need
  re-running (not rebuilding from scratch) if MRTIS's commit moves.

### Also this session: repo pushed and made public

Committed and pushed all of the above to `origin/main`
(`b2fef89..f3d9a9d`). William then asked to make the repo public (it had
been scoped private in MRTIS's 2026-08-19 session log) and explicitly
acknowledged the risk; changed via `gh repo edit --visibility public
--accept-visibility-change-consequences`. Consistent with MRTIS's own prior
call (`docs/SESSION_LOG.md`, same date: "the fee figures are modeled/
estimated and not sensitive") — that call was about the MRTIS repo itself,
this is the same judgment extended to the derived package. Now public:
`github.com/theshipsagent/mrtis-claris`.

### Closing addendum — the three in-repo disclosures, done before push

Asked whether to fix before pushing, the recommendation was: push the known-good
state first, because the MRTIS fixes force a rebuild that would disturb every
figure in the review package. But three of the ten findings are **disclosures
that belong to the reviewer's package, not to MRTIS**, and those were done first.

- **I-4** — `DATA_DICTIONARY.csv` now warns off `PORT_CALL::agency` explicitly
  ("NOT THE COLUMN FOR REVENUE-BY-AGENT REPORTING"), names
  `PORT_CALL_LEG::agency` as the one to use, and quantifies the $939,000 at
  stake. `docs/BUSINESS_RULES.md` §6 gained the same warning.
- **I-5** — §6 now states the magnitude alongside the rule: **3,233 chargeable
  legs (8.03%) carrying $29,495,250 — 10.82% of the billable total** — are legs
  where the agent changed mid-leg. About $1 in $9 of agency revenue is
  attributed to an agent where another agency was also involved. Also surfaced
  on `agent_changed_in_leg` in the data dictionary.
- **I-8** — §5 now publishes the split rate at all three denominators (4.06% of
  all calls / 7.55% of bulk calls / **31.33% of bulk discharge calls**) and says
  plainly that a rate quoted without its denominator is a different number here,
  not a small imprecision.

**All three figures are derived, not hand-keyed.** `figures.py` gained
`agency_grain`, `agent_changed` and `bulk_turnover` derivations, and
`docs/FIGURES.md` two new sections. The package's own discipline applied to its
own disclosures.

**Verified after the change:** `figures.py` still reports **0 attribution
mismatches across 40,245 chargeable legs**, and the only file to move under
`sample/` was `DATA_DICTIONARY.csv` — three field descriptions. **No sample data
row changed**, no chart moved, no report figure moved.

### Next session: independent audit, not a build session

William asked for a fresh audit — no memory of this session, re-derive
everything from the live database rather than trusting what's written here,
report discrepancies rather than fixing them. Scope: does
`docs/BUSINESS_RULES.md` actually match MRTIS's sources, does
`export/build_review_package.py` genuinely read read-only and match the live
schema, do every chart/report figure reconcile independently. Modeled on
MRTIS's own audit precedent (`OPEN_QUESTIONS.md` §7, §11) — deliberately
changes nothing, leaves rulings to William. The prompt used to start that
session is not repeated here; see the next dated entry for its findings.

### How to reproduce this build

```
python3 -m venv .venv && .venv/bin/pip install duckdb pandas matplotlib
.venv/bin/python3 export/build_review_package.py
.venv/bin/python3 charts/build_charts.py
.venv/bin/python3 reports/build_reports.py
```

All three scripts open MRTIS's `mrtis.duckdb` `read_only=True` and write only
inside this repo.

---

## 2026-08-19 (session 2) — Independent audit. Nothing changed.

**Audited against MRTIS commit `09e1cb633ee9dc86a0393956eb118c9c8d5bafb8`** —
**unchanged** from session 1's recorded commit, so every session-1 figure was
still fair to re-test as-is. `data/db/mrtis.duckdb` md5
`cd91db791c85837712510b61b417456a`, mtime 2026-08-19 20:13:18, **byte-identical
before and after this audit**; no `.wal` or other file appeared beside it. Five
untracked `sample_port_calls*.csv` files sit in MRTIS's working tree; they
predate this session and were not touched.

Run in the spirit of MRTIS's own audits (`OPEN_QUESTIONS.md` §7, §11): read
cold, re-derive from the database rather than trust the write-up, **report and
do not fix**. Everything below that needs a decision is left for William. No
file in this repo was modified except this log entry; `git status` was clean
going in.

Method: a throwaway venv outside the repo, `duckdb.connect(..., read_only=True)`,
and — for the fee schedule — a **fresh re-implementation of the six rules from
the prose in `docs/BUSINESS_RULES.md` §9**, deliberately not importing or
reading `agency_fee_for()` first, so the check is against the written rule and
not against the code that wrote the number.

### What passed — re-derived exactly

- **Row counts.** `port_call` 40,170 · `port_call_leg` 41,804 ·
  `port_call_event` 290,436 (= `fact_zone_event`, so the spine rule holds).
- **The headline fee figures, all three.** `SUM(port_call_leg.agency_fee)` =
  **$272,167,500** over **40,245** chargeable legs;
  `SUM(port_call.agency_fee_total)` = the same to the cent;
  `SUM(port_call_event.agency_fee)` = `SUM(fact_zone_event.agency_fee)` =
  **$349,625,500**, confirming the per-departure basis is genuinely frozen.
- **The fee schedule itself.** Re-pricing all 41,804 legs from the written
  rules gave **0 mismatches** against the 40,245 stored fees. Re-pricing the
  same legs on the old two-tier schedule gave **$298,868,500**, so the movement
  is **−$26,701,000 (−8.934%)** — §9.4's number.
- **Rule by rule**, independently reproduced, exactly:

  | Rule | Legs | Old 2-tier | Built | Change |
  |---|---:|---:|---:|---:|
  | R1 Passenger/Cruise | 1,043 | $3,650,500 | $2,607,500 | −$1,043,000 |
  | R2 Ro-Ro / Vehicles | 0 | $0 | $0 | $0 |
  | R3 Container (FC) | 3,128 | $10,948,000 | $2,346,000 | −$8,602,000 |
  | R4 Refrigerated | 40 | $140,000 | $200,000 | +$60,000 |
  | R5 Bulk @ Gen. Cargo | 3,112 | $32,676,000 | **$15,560,000** | −$17,116,000 |
  | base tier | 32,922 | $251,454,000 | $251,454,000 | $0 |

- **Every unbilled leg is explained.** 1,559 legs carry no fee: 1,415 never
  reached a berth, 142 are pure lay-up (§8b), and **2** berthed and did
  non-layberth work but have no usable identity — exactly the two legs
  `OPEN_QUESTIONS.md` §11.4 already flags (`NONAME:RBNS ALAREEN-202012222142-L1`,
  `NONAME:US GOV VESSEL-202204180655-L1`, ≤$21,000).
- **The export is read-only and faithful.** `export/build_review_package.py`
  opens the DB `read_only=True`, issues only `SELECT`/`information_schema`
  reads, and writes solely inside this repo — confirmed by inspection and by
  the unchanged checksum above. Column **set, order and type match the live
  `information_schema`** for all 111 fields (28/36/47), across the CSV headers,
  the XML `<METADATA>` and `DATA_DICTIONARY.csv`. All three XML files parse
  **well-formed** (expat, including the 443 MB `PORT_CALL_EVENT.xml`);
  `<ROW>` counts, `<COL>`-per-row, `DATABASE@RECORDS` and `RESULTSET@FOUND` are
  all mutually consistent. No `True`/`False` leaked past the boolean→1/0
  coercion, no sub-second timestamps, no control characters. A **full
  value-by-value comparison of all 372,410 exported rows × 111 columns against
  the live tables came back identical**.
- **Charts and reports.** All four charts and all three reports re-derive
  exactly, including every one of report 3's 17 R5 facility rows, report 2's
  top-20 agencies and 37-agency count, and chart 4's four static rule pairs.
- **Supporting rates.** `complete` 98.81% (doc: 98.8%) · split calls
  1,632/40,170 = 4.06% (doc: 4.1%) · blank source agent 2.45% (doc: ~2.4%) ·
  unplaced events 17,100 = 5.89% (MRTIS spec: 5.9%).

### What did not pass

Ordered by how much a reviewer's conclusion would move.

**A1. `Gen` (general-cargo ships) sits inside `vessel_type = 'Bulk'`, and
therefore inside R5 — and this package never says so.** MRTIS's
`dictionaries/vessel_type.csv` maps `Gen` → `Bulk` (16,752 events). Re-derived
from the leg's own events: of R5's **3,112 legs / $15,560,000**, **1,509 legs
and $7,545,000 (48.5%) are vessels whose Zone Report Type is `Gen`**, not
`Bulk` (1,467 genuinely `Bulk`, 126 blank, 10 `Lift`). A further **1,045 legs /
$10,972,500** of `Gen` traffic bills at the $10,500 Bulk tier. So roughly
**$18.5M of the $272.2M billable total turns on that one dictionary row.**
`BUSINESS_RULES.md` §9.3 quotes William's *"any dry bulk vessel calling a
general cargo facility type"* and defines dry bulk as `vessel_type = 'Bulk'`
without disclosing that general-cargo ships are inside that set — so nearly
half of R5 is general-cargo ships calling general-cargo berths. MRTIS logs this
as still open (§7.4, *"it is stated nowhere and the report gives no way to see
it"*). **Needs a ruling from William, not a code fix.**

**A2. R5 is being priced off layberth berths.** 80 R5 legs / **$400,000** have a
first berth that is one of the 14 `ops = Layberth` zones that also carry
`facility_type = General Cargo` — Poland St (26), Perry Street (19), Buck Kreihs
(18, a repair yard), Alabo St (16), Esplanade Ave (1). This is faithful to
§12.3.3.1 as ruled ("first berth of the leg decides"), but it lands squarely on
`OPEN_QUESTIONS.md` §11.1's open finding that a leg's first berth can be a
layberth while the billed work happened at another berth. `BUSINESS_RULES.md`
§9.3 states the first-berth rule with no caveat, and `reports/` presents those
five repair/lay-up berths as General Cargo revenue drivers without comment.
**Ruling needed: should a layberth first berth be allowed to set R5's amount?**

**A3. §11.1's contradiction is live in the exported data and undisclosed.**
`BUSINESS_RULES.md` §5 states §8b flatly — "a leg only bills if it did real,
non-layberth cargo work somewhere". Re-derived: **54 legs report
`activity = 'No Cargo'` and carry a fee anyway, totalling $281,750.** (MRTIS
§11.1 quotes $413,000; that predates §12's re-tiering — the current figure is
$281,750, which should be corrected in MRTIS too.) Nothing in `docs/`,
`charts/` or `reports/` mentions it. A reviewer who filters
`activity = 'No Cargo'` in the exported data will find billed legs the rules
document says cannot exist.

**A4. `docs/BUSINESS_RULES.md` §9.2 misstates the base-tier precedence.** It
gives the $10,500 tier as "Bulk (canonical vessel type, **or** register
`ship_type_group` starting `Bulk Carrier`)". In `agency_fee_for()` the register
group is consulted **only when the canonical type is absent** — it is a
fallback, not an alternative. Live counterexamples: **3 chargeable legs**
(one each Container / Tanker / Other) have `ship_type_group LIKE 'Bulk
Carrier%'` and correctly bill $3,500, where the doc as written says $10,500.
Only $21,000 at stake here, but a FileMaker developer implementing §9.2
literally would build the wrong precedence into the tier calculation.

**A5. `package/DATA_DICTIONARY.csv` cites a percentage its own reference doesn't
support.** `port_call_event.agency_fee` is described as over-billing "by roughly
17% (see docs/BUSINESS_RULES.md section 9.1)". 17.0% is the over-bill against
the **superseded** $298,868,500 old-schedule leg basis. Against the
$272,167,500 that §9.1 actually publishes it is **28.5% ($77,458,000)**. The
cited section does not support the cited number.

**A6. Two dangling cross-references in the data dictionary — the reviewer's
main field-level document.**
- `vessel_key`, on all three tables: "see docs/BUSINESS_RULES.md and MRTIS
  OPEN_QUESTIONS.md #10". **`BUSINESS_RULES.md` contains no mention of
  `vessel_key`, positional keys, or §10.** This one matters for an import
  package: §10 says both `vessel_key` and `event_key` are `dataframe.index + 1`
  and are *not stable across rebuilds*, so a FileMaker file keyed on them
  breaks the next time MRTIS rebuilds.
- `tpc`: "Zero is sometimes a real value, sometimes a data gap -- see
  docs/BUSINESS_RULES.md". **`BUSINESS_RULES.md` says nothing about `tpc`.**
  Re-derived: `tpc = 0` on **4,045 calls (10.07%)**, matching §11.3.

**A7. §4's activity-resolution percentages don't re-derive.** The doc gives
dictionary 35.7% / draft 46.8% / FGIS 0.8% / unresolved 13.4%, "83.3%
resolved". Live: **35.99 / 46.14 / 0.79 / 13.69, 82.92% resolved** (plus 3.38%
that never reached a berth, a bucket §4 omits although MRTIS's spec states it).
These are `PORT_CALL_SPEC.md` §3's numbers copied across rather than
re-derived; the spec is itself stale relative to the post-§8/§12 rebuild. Small
movements (0.2–0.9pp), but the doc presents them as current.

**A8. §9.1's "19.0% of port calls were being charged 2–10 times" doesn't
re-derive, and drops a qualifier.** Live: **7,197 of 38,288 fee-bearing calls =
18.8%** (17.92% of all 40,170 calls; max 10 charges, so the "2–10" range holds).
MRTIS §7.1's 7,271/38,296 = 19.0% predates the §8 rebuild. MRTIS said "of
fee-bearing port calls"; `BUSINESS_RULES.md` says "of port calls", which reads
as all 40,170.

**A9. Mis-citation of §12.4, three places.** `charts/build_charts.py`'s chart-4
footer, and report 3's body text and docstring, all attribute the R5 /
rule-by-rule figures to `OPEN_QUESTIONS.md` **§12.4**. §12.4 is "Suggested build
order for the next session"; the figures live in §12.2 and the §12.3.3
resolution. The numbers are right — only the pointer is wrong.

**A10. A comment claims a check the script doesn't perform.**
`charts/build_charts.py:113-114` says the hard-coded §12 figures are "verified
against the live DB in the reconciliation query below". There is no
reconciliation query below; the function ends at `savefig`. (The four figures
themselves *do* verify — see the table above — so this is a false claim about
method, not a wrong number.)

**A11. Reports 1 and 2 mix denominators in adjacent columns.** In report 1 the
"Port calls" / "Legs" / "Billable fee" columns cover all calls, but "Avg
fee/call" is averaged over fee-bearing calls only. Gas: 941 calls,
$2,541,000, avg shown $3,500 — but $2,541,000 ÷ 941 = $2,700 (the average is
over 726 calls). "(unknown)": 199 calls, avg shown $5,263, ÷199 = $2,116 (over
80 calls). Report 2 does the same: Norton Lilly, 7,528 legs, $41,177,000, avg
shown $5,660, ÷7,528 = $5,470 (over 7,275 chargeable legs). No figure is wrong;
the three columns simply cannot be reconciled against each other and the report
doesn't say so.

**A12. Report 2 silently omits $1,779,000.** It filters
`agency is not null and agency != ''`, and **544 fee-bearing legs carry no
agency**. The CSV sums to **$270,388,500**, not the $272,167,500 published
everywhere else in the package. The report states no total, so nothing is
asserted wrongly — but a reviewer reconciling it against report 1 comes up
short by exactly that amount with no explanation.

**A13. Scope disclosures missing from §10 ("What's deliberately NOT in this
package").** It names §13 and §14 but not `OPEN_QUESTIONS.md` §11.1–§11.5 (the
open audit-#2 items, one of which — §11.1 — is A3 above) or §7.2–§7.5. It also
never records that the underlying data has **9 dredge/workboat vessels, 23,228
raw rows, 7.4% of the feed, removed at ingest** (§2). A reviewer reconciling
this export against a raw Zone Report extract will be told nothing about why the
row counts don't meet.

**A14. Minor: §3's "5.3% of raw berth events".** Re-derives to **5.23%** on all
berth events (5,102 / 97,584); it only rounds to 5.3% on the placed-events
denominator (5,102 / 96,845 = 5.27%). Same figure as MRTIS's spec — the
denominator, not the count, is what's ambiguous.

### Noted, no action implied

- **The canonical fee fallback is currently inert.** §9.3 describes
  `CANONICAL_FEE_FALLBACK` as covering vessels with no register row. Live: only
  **12 chargeable legs** have no register `ship_type` (matching §12.3.1's "12
  legs, $63,000"), and **none of them are Passenger / Container / Reefer**, so
  no leg in this build is actually priced by that path. The rule is stated
  correctly; it just never fires today.
- **FMPXMLRESULT conformance is unproven, not disproven.** The emitted files
  carry no `<PRODUCT>` element and use `RECORDID="1"` on every row. Both match
  `Ships_Register/src/build_filemaker_package.py`, the precedent CLAUDE.md §3.4
  names, so this package is no worse than the proven one — but **neither
  session has actually imported either package into FileMaker.** A ten-minute
  import smoke test would settle it; well-formed XML is not the same as
  accepted-by-FileMaker XML.

### Open, for a ruling or a follow-up build session

Nothing here was fixed, by design.

1. **A1 and A2 need William**, not a developer: does `Gen` belong in the dry-bulk
   tier and inside R5 (~$18.5M exposed), and may a layberth first berth set R5's
   amount ($400,000)? A1 is MRTIS's own §7.4 with the stakes now quantified.
2. **A3** is MRTIS §11.1, still unruled; its dollar figure needs restating as
   $281,750 post-§12 wherever $413,000 appears.
3. **A4–A14 are documentation and presentation defects in this repo** — no
   business ruling needed, they can be corrected in a build session. A4, A5 and
   A6 are the ones that would actively mislead a reviewer; A7, A8 and A14 are
   stale figures that should be re-derived from the database rather than copied
   from MRTIS's prose; A9–A13 are citations, comments and disclosures.
4. The recomputation queries used here were deliberately throwaway (run outside
   the repo). If these checks should run on every export, they want to live in
   the export script as guardrails, the way MRTIS does it — worth deciding
   before the next re-export.

### Ruled by William, same session (2026-08-19), on audit finding A1

**`Gen` = `Bulk`.** General-cargo ships do belong in the dry-bulk tier and
inside R5. This **confirms the build as it stands** — `dictionaries/vessel_type.csv`
already maps `Gen` → `Bulk` — so **no figure in this package moves**: R5 stays
3,112 legs / $15,560,000 (of which 1,509 legs / $7,545,000 are `Gen`), the
1,045 `Gen` legs at the $10,500 tier stay, and the billable total stays
$272,167,500. Nothing needs rebuilding or re-exporting.

What it changes is disclosure, not arithmetic: `docs/BUSINESS_RULES.md` §9
should state plainly that "dry bulk" (`vessel_type = 'Bulk'`) includes general
cargo ships, so a reviewer reading R5 as "bulk carriers at general cargo
terminals" isn't surprised when half the legs are general-cargo hulls.

**Carry back to MRTIS**: this is the ruling `OPEN_QUESTIONS.md` §7.4 has been
waiting for (*"Consistent with BUILD.md's General Cargo reasoning, but it is
stated nowhere"*). It cannot be recorded there from this repo — MRTIS is
read-only from here per `CLAUDE.md` §2.2 — so it needs writing into §7.4 in an
MRTIS session, with the R5 split above as the supporting evidence.

**A1 is closed. A2 (the layberth first berth) remains open** — see the
explanation requested in the same message, below.

### A2 explained, for William's ruling — R5 vs. the layberth berths

**The mechanism.** R5 is the only fee rule priced by the berth rather than the
vessel, and it keys off one field: `port_call_leg.facility_type`, which is the
facility type of the **leg's first berth stop** (§12.3.3.1, as ruled). Of the
29 zones the dictionary types `facility_type = General Cargo`, **14 are also
`ops = Layberth`** — "no cargo ever takes place" (§8): Buck Kreihs (a ship
repair yard), Poland St, Perry Street, Alabo St, Esplanade Ave and the rest.
They are General Cargo by *facility type* and lay-up wharves by *operation*.
So when a bulker lays up first and works cargo afterwards, R5 reads the lay-up
wharf and prices the whole leg at $5,000.

**What that produces.** 80 legs, **$400,000** — priced at $5,000 where the base
Bulk tier would have charged $10,500, so **$440,000 less than the vessel-priced
alternative**. Every one of the 80 has **2 or 3 berth stops** — never one — so
in every case real cargo work happened at a *different* berth than the one
setting the price. The split: Poland St 26, Perry Street 19, Buck Kreihs 18,
Alabo St 16, Esplanade Ave 1.

**Worked examples**, all three from the first week of the data:

- **Gh Power** (Bulk, leg `9233301-201901081714-L1`) — enters at 24 ft, sits at
  **Poland St** 9–9 Jan (24 ft → 24 ft, no draft change, no cargo), then loads
  at **Zen-Noh elevator** 15–17 Jan (24 ft → **40 ft**, a full grain load), and
  sails. Leg activity reads `Load` by dictionary — **from the elevator**. Fee
  reads $5,000 — **from Poland St**.
- **Belforest** (Bulk, leg `9698185-201901141342-L1`) — twelve days at **Buck
  Kreihs** (22 ft → 21 ft, a repair-yard stay), then **Zen-Noh**, 21 ft → 40 ft.
  Same shape: `Load` from the elevator, $5,000 from the repair yard.
- **Olympia Gr** (Bulk, leg `9817523-201901081643-L1`) — **Buck Kreihs** flat at
  39 ft, then discharges at **AST Meraux Buoys** (39 ft → 23 ft). `Discharge`
  from the buoys, $5,000 from the repair yard.

**Why it is a conflict and not just a quirk.** On these legs the two halves of
the row are read from two different stops: **`activity` comes from the real
working berth, `agency_fee` comes from the layberth.** That is exactly the
structural problem `OPEN_QUESTIONS.md` §11.1 raised (a leg reporting one stop's
attributes while billing for another's) — R5 is the first rule where it moves
money. Only 7 of the 80 are also §11.1's `No Cargo`-but-billed legs, so this is
a *separate* population, not a duplicate of A3.

It is also not what R5 was aimed at. §12.3.3.1's reasoning is about a dry bulk
vessel **working** a general cargo terminal instead of a bulk facility. A ship
repair yard is neither — it is a berth where, by the dictionary's own rule, no
cargo is ever worked.

**The decision, three ways:**

- **(a) Leave it.** R5 as ruled says "first berth", and this is first berth.
  Simple, already built, nothing moves. Cost: a full grain load out of Zen-Noh
  bills $5,000 because the ship was in the shipyard the week before.
- **(b) R5 should look at the first *working* berth** — skip layberth stops when
  deciding `facility_type`, the same way §8a already skips them when deciding
  where a leg splits. Consistent with a rule MRTIS has already adopted for the
  layberths; **+$440,000** (those 80 legs revert to $10,500 Bulk). Requires a
  rebuild of the leg layer and a re-export.
- **(c) R5 should exclude `ops = Layberth` zones from "General Cargo" entirely**,
  by narrowing the dictionary rather than the rule. Same $440,000 effect here,
  but it also changes what `facility_type` means everywhere else it is read.

**Recommendation: (b).** It applies a principle William has already ruled once —
a layberth is not a cargo job and should not drive cargo-job logic (§8a/§8b) —
to the one place that ruling was never extended. It is the smallest change that
removes the contradiction, and it leaves `facility_type` untouched for every
other consumer. **William's call, not this repo's** — and note it interacts with
§13.1, which will set `ops = Discharge` on the *other* 15 General Cargo zones,
so it is worth ruling before §13 is built rather than after.

### Ruled by William, same session (2026-08-19), on audit finding A2 — option (b), plus a general principle

**Ruling, verbatim in substance**: *"(b), this works, layberths don't need to be
considered in counts and fees, we just need to have it time-wise attached to
the leg and allocated as layberth when doing time calcs / KPI. In truth this
situation is an outlier, as no one wants their ship to break down, which is the
only reason they called that facility."*

So the rule is broader than R5. A layberth stop is **commercially invisible and
operationally visible**: it must not shape money or counts, but it is real
elapsed time and must stay attached to its leg, in its own bucket, so a time /
KPI calculation can see it and separate it.

**A2 is closed. This supersedes and generalises §8a/§8b**, which had already
taken layberths out of split detection and out of the fee test, but had left
them inside `facility_type` pricing, inside `berth_stop_count`, and inside
`berth_hours`.

#### Why the outlier reading is right, measured

The whole layberth footprint is **918 berth events across 421 legs and 420 port
calls** — 389 real (non-artifact) stops once geofence noise collapses. Median
stay **69.7 hours**, longest **1,700 hours** (71 days). Total **45,742 hours =
1,906 days** alongside a lay-up or repair wharf. That is **1.66% of all
`berth_hours` in the data** — which is exactly why it has never shown up in an
aggregate, and exactly why it is worth fixing rather than living with:

**On the 379 legs that touch one, layberth time is 71.7% of the `berth_hours`
those legs report** — 45,742 of 63,811 hours — and **389 of their 692 counted
berth stops are layberth stops.** So a "days alongside per call" or
"berth productivity" KPI on those legs today reads roughly three times the real
cargo time. Invisible in the total, dominant in the row. William's point stands
on the numbers.

#### Confirmed while scoping: every layberth zone is inside R5

Read from `dictionaries/zone_facility.csv`: **all 14** `ops = Layberth` zones
carry `facility_type = General Cargo` — Violet Dock 1-5 (→ LIT Violet), Buck
Kreihs, Andry St, Alabo St, Poland St, Mandeville St, Gov Nicholls St,
Esplanade Ave, Perry Street, Marlex. There is no layberth zone *outside* R5's
scope. That is the structural reason the conflict existed at all, not bad luck.

#### Scope of the change — all of it lands in MRTIS, none of it here

**This repo cannot implement any of it.** The fee and the leg columns are
computed in MRTIS's `build_port_calls.py` / `build_db.py`; `mrtis-claris` only
exports what MRTIS built, and MRTIS is read-only from here (`CLAUDE.md` §2.2).
This needs an MRTIS session — scratch-copy rebuild and full reverification per
their standing practice — and then a re-export here.

1. **R5 prices off the first *working* berth.** Skip layberth stops when
   resolving the leg's `facility_type`, the way §8a already skips them when
   resolving splits. **80 legs, +$440,000** ($400,000 → $840,000 as those legs
   revert to the $10,500 Bulk tier). Billable total $272,167,500 → **$272,607,500**.
2. **`berth_stop_count` excludes layberth stops**, on both leg and call. Removes
   **389 stops from 379 legs**.
3. **`berth_hours` excludes layberth time, and a new `layberth_hours` column
   carries it** on `port_call_leg` (and a call-level total). Moves **45,742
   hours** out of `berth_hours` into its own bucket — this is the "allocated as
   layberth when doing time calcs" half of the ruling, and it is a schema change
   (`sql/schema_port_call.sql`).
4. **No change needed to attachment.** Layberth events already stay on the spine
   and already belong to their leg — that half of the ruling is already true.

#### Three things the build session must decide, flagged not decided

- **Pure lay-up legs lose their last count.** 142 legs (142 calls) are nothing
  but layberth stops. They already bill $0 (§8b); under item 2 their
  `berth_stop_count` also goes to **0**, making them indistinguishable in the
  count columns from the 1,415 legs that never berthed at all. They need to stay
  tellable apart — the new `layberth_hours` being non-zero would do it, or an
  explicit flag. **Decide before building, not after.**
- **Does §14 count a pure lay-up as a port call?** William's ruling says
  layberths don't count. §14 (port-call counts per agent) is still open and
  would inherit this. 142 calls at stake. Not asked, not assumed.
- **Order this against §13.1.** §13.1 will set `ops = Discharge` on the **14
  remaining non-layberth General Cargo zones (14,109 berth events)**. Those are
  the berths R5's new "first *working* berth" lookup will land on more often
  once item 1 ships. The two changes touch the same code path and the same
  facility type — **rule the ordering, or build them together.**

#### One mechanical warning for the build session

`export/build_review_package.py` reads its column list live from
`information_schema` and **hard-fails on any column it has no description for**.
That is the script behaving as designed — but it means the new `layberth_hours`
column will break the export until a `*_DESC` entry is added here. Expected, not
a bug; noting it so it isn't diagnosed twice.

#### Still not fixed, by design

Nothing above was implemented. A1 and A2 are now both **ruled**; both need an
MRTIS build session to land, then a re-export and a documentation pass here.
A3–A14 remain as written.

### Knock-on: the layberth ruling also answers MRTIS §11.1 (audit finding A3), for $0

Checked while scoping the ruling. §11.1 asked which of two contradictory
statements is wrong when a leg mixes a layberth stop with an unresolved working
berth: the **label** (leg reports `activity = 'No Cargo'`) or the **fee** (it
bills anyway). Its option (a) was "an unresolved stop should outrank `No Cargo`".

William's principle — layberths don't count for money or counts, only for time —
picks option (a) by construction. If a layberth stop is not considered when
resolving the leg's activity, then a leg whose only other stop is unresolved has
**no** activity to report and correctly goes NULL/unresolved, instead of
borrowing "No Cargo" from a berth the ruling says to ignore.

Verified against the database: **all 54 of those legs have at least one real,
non-layberth working berth stop** — none is layberth-only. So they keep billing
exactly as they do now:

- Label: `No Cargo` → NULL / unresolved on **54 legs**.
- Fee: **$281,750, unchanged.** No dollar moves.

Cheapest item on the list — it removes a live contradiction from the exported
data at zero cost, and it falls out of a ruling already made rather than needing
a new one. **Flagged to William for confirmation** rather than assumed, since
§11.1 is MRTIS's question and MRTIS is read-only from here. If confirmed, it
carries back to `OPEN_QUESTIONS.md` §11.1 alongside the corrected figure
($281,750, not the pre-§12 $413,000).

### Ruled by William, same session (2026-08-19) — pure lay-ups: option (b), with a time carve-out

**Ruling**: *"(b), we can ignore them except for accounting for the time usage
on the seq order of SWP-to-SWP KPI calcs, which we have not discussed yet."*

So a pure lay-up call is **not a port call** — it does not count and it does not
bill — **but its time must survive** in the vessel's SWP-to-SWP sequence, so a
river-residency / turnaround KPI still sees the days the vessel was actually in
the river.

#### The 142 calls, measured

| | |
|---|---|
| Calls | **142** (all `call_status = 'complete'` — genuine SWP in and SWP out) |
| Legs | 142 (one leg each) |
| Events on the spine | 744 |
| Vessels | 111 (1.28 lay-up calls per vessel) |
| Agency fee | **$0** — already unbilled under §8b, so no revenue moves |
| Splits / FGIS certificates / tonnage | **0 / 0 / 0** — genuinely commercially empty |
| **SWP-to-SWP time** | **23,390 hours = 975 vessel-days** (median 4.7 days, longest 72) |

Headline counts after the ruling: port calls **40,170 → 40,028**, legs
**41,804 → 41,662**, split rate **4.06% → 4.08%**. No dollar figure in this
package changes.

#### Implementation constraint — flag, do not delete

The two halves of the ruling are only consistent if the rows **stay**. Deleting
a lay-up call would destroy the **975 vessel-days** the ruling explicitly says
to keep, and would break `PORT_CALL_SPEC.md` §0's spine rule ("nothing is
dropped"). So "ignore them" must be built as a **classification, not a
removal** — e.g. a call-level `is_commercial_call` / `call_class = 'layup'` flag
that every count and fee query filters on by default, while the row, its events,
its timestamps and its place in the vessel's SWP-to-SWP sequence all remain
intact.

This also supersedes the discriminator discussed under option (a): the lay-up
call no longer needs to be *distinguishable* from a never-berthed leg — it needs
to be **explicitly classified**, because the flag now drives whether the call
counts at all, not merely how it reads.

Consequence for §14 (per-agent port-call counts, still open): the answer is now
given — a pure lay-up does not count. 142 calls.

### Parked, named so it isn't lost: the SWP-to-SWP KPI framework

William, same message: *"the seq order of SWP-to-SWP KPI calcs, which we have
not discussed yet."* **Not yet specified, not yet scoped, no rulings taken.**

What is already in place for it: `port_call.call_start` / `call_end` /
`call_hours` (SWP crossing to SWP crossing), and the leg-level split of dwell
into `waiting_hours` / `inter_berth_idle_hours` / `outbound_idle_hours` /
`berth_hours` (`PORT_CALL_SPEC.md` §6). What it will additionally need, from the
rulings taken this session: the new `layberth_hours` bucket, and the lay-up
classification above so residency time can be attributed without the call
counting as commercial traffic.

**This is a design conversation with William, not a build task** — it should get
its own session and its own set of rulings before anything is written, in the
same way §7.1's billing-unit question was settled before the fee was rebuilt.
Flagged here so the next session picks it up rather than rediscovering it.

### Clarified by William, same session — build it general, not layberth-specific

Restated to confirm the reading, and it holds: **keep the layberth rows, exclude
them from vessel counts and from fees, but never lose the time.** William's test
for it: *"if the ship was at layberth 3 days, how do you explain the time gap?"*
— delete the row and there is an unexplained hole in the vessel's timeline
between two SWP crossings. (The data agrees with the instinct: median layberth
stop is **69.7 hours — 2.9 days**.)

**The addition worth capturing** — *"some of the outliers may be for other
oddities, but as long as time [is] accounted for, otherwise they need no
acknowledgement either by fee or count."*

That is a **general principle, not a layberth rule**. Build it as a
**non-commercial time** classification — time accounted for, excluded from counts
and fees — with layberth as its first member and room for the next oddity to
join it without reopening the logic. Building a layberth-specific carve-out
instead would mean retrofitting the same shape a second time the next time an
outlier surfaces.

This supersedes nothing above; it sets *how* the lay-up flag and the
`layberth_hours` bucket should be shaped when MRTIS builds them.

---

## Session 2 close — rulings taken, none implemented

Five rulings from William this session, all recorded, **none built** (the audit
changed nothing, and every one of them lands in MRTIS, which is read-only from
here):

| # | Ruling | Effect |
|---|---|---|
| A1 | `Gen` = `Bulk` — general cargo ships are in the dry-bulk tier and in R5 | Confirms the build; **$0 moves**; disclosure fix only |
| A2 | Option (b) — R5 prices off the first *working* berth | **80 legs, +$440,000**; total → $272,607,500 |
| A2b | Layberths out of `berth_stop_count` and `berth_hours`, into `layberth_hours` | 389 stops / 45,742 hrs reallocated on 379 legs |
| A3 | §11.1 — unresolved outranks `No Cargo` (confirmed by William, below) | 54 labels change, **$0 moves** |
| — | Pure lay-ups: option (b), flag not delete; §14 excludes them | 142 calls out of counts; **975 vessel-days preserved** |
| — | Shape: a general non-commercial-time classification, not a layberth case | Design constraint on the above |

**Next**: one MRTIS build session lands all of it (scratch-copy rebuild and full
reverification per MRTIS practice), then re-export here, re-run charts and
reports, and correct A4-A14. The SWP-to-SWP KPI framework is parked and needs
its own design session first. The commercial-side chart/report work discussed
this session can proceed on the current build without waiting — fee figures move
0.16%; only time/berth KPIs must wait.

### A3 confirmed by William (2026-08-19)

§11.1 resolves as option (a): an unresolved stop outranks `No Cargo` for the
leg's label. 54 legs move from `activity = 'No Cargo'` to NULL/unresolved;
**fee unchanged at $281,750**. All five rulings from this session are now final.

### Handoff brief — the MRTIS build session

**This session cannot do it.** `CLAUDE.md` §2.2 makes this repo read-only
against MRTIS, and the work requires editing `scripts/build_port_calls.py`,
`scripts/build_db.py`, `sql/schema_port_call.sql`, and MRTIS's own
`docs/OPEN_QUESTIONS.md` / `docs/SESSION_LOG.md`. It needs a session rooted in
`/Users/billy/Documents/MRTIS`, working under MRTIS's own discipline — note
MRTIS has **no `CLAUDE.md`**; its operating rules live in `docs/BUILD.md`,
`docs/SESSION_LOG.md` and `docs/OPEN_QUESTIONS.md`, and standing practice is a
**scratch-copy rebuild and full reverification before touching the real repo**.

**What to build** (all five ruled 2026-08-19, evidence and dollar figures above):

1. R5 prices off the leg's first **working** berth — skip layberth stops when
   resolving `facility_type`. `build_port_calls.py`.
2. Layberth stops leave `berth_stop_count` and `berth_hours`; new
   `layberth_hours` on `port_call_leg` + a call-level total.
   `build_port_calls.py` and `sql/schema_port_call.sql`.
3. Pure lay-up calls stop counting — as a **flag, not a delete**
   (`is_commercial_call` / `call_class`). Rows, events and timestamps stay.
4. Unresolved outranks `No Cargo` for the leg label (§11.1a).
5. Shape 1-4 as one **non-commercial time** classification, not layberth
   special-casing — other oddities will join it.

**Verification targets after the rebuild** (cross-check against known-good, the
method that caught the §12 bug):

| Figure | Before | Expected after |
|---|---|---|
| Billable total | $272,167,500 | **$272,607,500** (+$440,000, 80 legs) |
| Per-departure basis | $349,625,500 | **$349,625,500** — frozen, must not move |
| Port calls | 40,170 | **40,028** commercial (142 flagged, not deleted) |
| Legs | 41,804 | **41,662** commercial |
| `No Cargo` legs billing | 54 / $281,750 | **0 legs labelled so; $281,750 still billed** |
| Lay-up time preserved | — | **23,390 hrs / 975 vessel-days** still on the spine |
| Layberth reallocated | — | **45,742 hrs, 389 stops** off 379 legs into `layberth_hours` |

**MRTIS docs to update**: §7.4 (`Gen` = `Bulk`, ruled — currently "stated
nowhere"), §11.1 (resolved (a); correct $413,000 → **$281,750**), §12.3.3.1
(R5 amended to first *working* berth), §8 (extend to counts and hours), §14
(pure lay-ups excluded), §11.5 (the schema comment's "~12%" over-bill is
**17.0%**), plus `PORT_CALL_SPEC.md` §4 and §6.

**Also order against §13.1** — it sets `ops = Discharge` on the 14 remaining
non-layberth General Cargo zones (14,109 berth events), the same berths R5's new
lookup lands on. Build together or rule the order.

**Then come back here**: re-export (`export/build_review_package.py` will
hard-fail until `layberth_hours` and the new flag get `*_DESC` entries — expected,
not a bug), re-run charts and reports, and clear A4-A14.
