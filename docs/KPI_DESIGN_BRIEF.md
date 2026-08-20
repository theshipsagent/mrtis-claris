# SWP-to-SWP KPI framework — design brief

**Status: no rulings taken, nothing built.** This is the preparation for a
design conversation with William, not a specification and not a proposal to
implement. It exists because the KPI framework has been parked since session 2
with one line of scope — *"the seq order of SWP-to-SWP KPI calcs, which we have
not discussed yet"* — and the next session on it should start from measured
ground rather than from a blank page.

**What it does.** States what MRTIS already stores that a time/KPI layer could
be built on, reports what that material actually looks like when measured, and
sets out the decisions that have to be made before any KPI is defined —
each one with options, measured impact, and a recommendation where the choice
is technical rather than commercial.

**What it does not do.** It defines no KPI, sets no target, and invents no rule.
CLAUDE.md's directive 1 makes MRTIS the oracle for every business rule in this
package; a KPI definition is a business rule, and William rules on it. Where
this brief recommends, it recommends on *shape* — how a decision should be
implemented once made — per directive 4.

**Where the numbers come from.** Every figure below is derived live from MRTIS,
read-only, by [`kpi/kpi_baseline.py`](../kpi/kpi_baseline.py) and published in
[`KPI_BASELINE.md`](KPI_BASELINE.md). Re-run `kpi/kpi_baseline.py --check-brief`
to assert this document has not gone stale against a rebuilt MRTIS. Built
against MRTIS commit `0c4ed0c241fb037b5e45b62fb6a865907c1cf4f2`.

**Where it would be built.** Not here. The time buckets are MRTIS's columns, and
this repo is read-only against MRTIS (CLAUDE.md directive 2) — and MRTIS is
parked at William's direction. §7 sets out the split between what gets ruled,
what gets built upstream, and what this package can demonstrate without
touching MRTIS at all.

---

## 1. Where the ask came from

Two things from William, both recorded in `SESSION_LOG.md` (session 2,
2026-08-19), and they pull in the same direction:

> *"the seq order of SWP-to-SWP KPI calcs, which we have not discussed yet."*

and, deciding how lay-up calls should be handled:

> *"if the ship was at layberth 3 days, how do you explain the time gap?"*
>
> *"some of the outliers may be for other oddities, but as long as time [is]
> accounted for, otherwise they need no acknowledgement either by fee or
> count."*

The second is already built upstream, as the **non-commercial time**
classification (`PORT_CALL_SPEC.md` §4, `OPEN_QUESTIONS.md` §8): layberth and
lay-up time is excluded from counts and fees but never deleted, because deleting
it would leave an unexplained hole in the vessel's timeline between two SWP
crossings.

That ruling is the KPI framework's founding principle, arrived at before the
framework itself: **every hour between the two SWP crossings must be accounted
for somewhere, even when it earns nothing and counts as nothing.** The rest of
this brief is mostly about how far the current build is from satisfying it.

The earlier ruling that shaped the buckets is `PORT_CALL_SPEC.md` §6, from
`logic.md`: *"waiting can only be waiting for the berth, as the anchorage stop
happens after it departs."*

---

## 2. What already exists to build on

### On `port_call` — the SWP-to-SWP clock

| Column | Meaning |
|---|---|
| `call_start` / `call_end` | The two SWP crossings — `Enter` at the pilot station, matching `Exit` |
| `call_hours` | Elapsed between them |
| `call_status` / `is_complete` | `complete` only when both crossings are present |
| `is_commercial_call` / `call_class` | The non-commercial classification; `layup` calls are flagged, never deleted |
| `berth_stop_count`, `layberth_hours`, `anchorage_stop_count`, `leg_count`, `is_split` | Call-level shape |

### On `port_call_leg` — the five time buckets (`PORT_CALL_SPEC.md` §6)

| Bucket | Meaning | Hours held |
|---|---|---:|
| `waiting_hours` | Anchorage dwell **before** the leg's first berth arrival — the only figure that means "waiting for a berth" | 2,470,459 |
| `inter_berth_idle_hours` | Dwell between first berth arrival and last sailing | 308,627 |
| `outbound_idle_hours` | Dwell after the last sailing — leaving, not waiting | 195,837 |
| `berth_hours` | Alongside a **working** berth | 2,716,075 |
| `layberth_hours` | Alongside a non-commercial (layberth) stop | 45,742 |

Plus `leg_start` / `leg_end` / `leg_hours`, `berth_arrive_time` /
`berth_depart_time`, `activity`, `agency` (the leg's operating agency, per §5),
`first_berth_facility` and `facility_type`.

### Two structural facts, asserted rather than assumed

Both are checked by `kpi/kpi_baseline.py` on every run, so a rebuild that broke
either would fail loudly rather than quietly changing what a KPI means:

1. **Legs tile the call exactly.** Leg 1 starts at `call_start` and the last leg
   ends at `call_end`, on all 40,170 calls. So the SWP-to-SWP clock is fully
   partitioned by legs, and every time question reduces to a question about leg
   buckets.
2. **A vessel is never in two calls at once.** Zero overlapping calls per
   vessel, so a vessel-level sequence is well-defined the moment someone decides
   what it should measure.

---

## 3. The finding that shapes everything: the clock does not close

The five buckets do not add up to the elapsed time they partition.

| | Hours |
|---|---:|
| Elapsed leg time (`leg_hours`) | 7,232,805 |
| Sum of the five stored buckets | 5,736,739 |
| **Unattributed remainder** | **1,496,066 — 20.7%** |

Median unattributed time per leg is 23.1 hours. This is not a bug: dwell is
recorded only where the feed records a *stop*, and the Zone Report's
transit and SWP-crossing rows carry no dwell at all. A vessel underway between
two recorded stops — steaming up-river to its berth, shifting, or heading back
down to the pilot station — is in no bucket.

Where the remainder sits:

| | Elapsed | Classified | Unclassified |
|---|---:|---:|---:|
| Leg start → first berth arrival | 3,016,809 | 2,442,932 as `waiting_hours` | **573,877** |
| Last sailing → leg end | 681,742 | 134,276 as `outbound_idle_hours` | **547,466** |

and legs that never reached a berth at all (1,418 of them) are **67.9%**
unattributed, because for a vessel that entered, anchored and left, only the
anchorage dwell has anywhere to go.

The buckets reconcile to the underlying events where they should: recorded
berth dwell of 2,761,816 hours is `berth_hours` + `layberth_hours`
(2,716,075 + 45,742) to within a rounding hour. Recorded anchorage dwell
exceeds the three idle buckets by about 0.2%, an artefact of the overlap
attribution rule; not material to any decision here, and not chased further
this session.

**Why this is decision #1.** William's ruling says time must be accounted for.
Today, one hour in five between the SWP crossings is in no named bucket, so any
KPI built on the current columns either silently ignores it or silently absorbs
it into a denominator. Every other decision in §4 inherits whatever is decided
here.

---

## 4. The decisions to be made

Eight of them. Q1 first — the rest read differently depending on its answer.

### Q1. What happens to the unattributed 20.7%?

**Options.**

| | |
|---|---|
| **(a) A named residual bucket** — `underway_hours` = elapsed − the five buckets | The clock closes by construction and can be asserted as a guardrail. One new column; no new evidence needed |
| **(b) Split the residual by position** — approach transit / inter-berth transit / departure transit | More informative (573,877 h approaching vs 547,466 h departing are genuinely different things), more code, same evidence |
| **(c) Leave it implicit** | No work; every KPI silently carries a 20.7% hole, and the founding principle is not met |

**Recommendation: (a) now, (b) only if a KPI actually asks for it.** A residual
bucket is the cheapest thing that makes the accounting *provable* — it converts
"time is accounted for" from a claim into a hard guardrail of the kind
`PORT_CALL_SPEC.md` §8 already runs (elapsed must equal the sum of buckets, or
the build aborts). (b) is a refinement of a residual that (a) has already made
visible, and buys nothing until a KPI needs approach and departure told apart.
(c) is the option that fails William's own test.

**For William:** this is a shape recommendation and needs only a yes. The
commercial question underneath it is Q4.

### Q2. What is a KPI measured on — the call, the leg, or the berth stop?

The three answer different questions, and a split call is where they diverge:
1,632 calls (4.06%) have two legs with two different agencies and two different
cargo jobs.

- **Per call** — "how long was the ship in the river." The natural home for
  SWP-to-SWP residency.
- **Per leg** — "how long did that cargo job take." The natural home for
  waiting and berth productivity, and the unit the agency fee already bills on
  (`OPEN_QUESTIONS.md` §7.1), so it is the unit that reconciles to money.
- **Per berth stop** — "how did that facility perform." Not currently a table;
  would have to be assembled from events.

**Recommendation: leg as the default unit, call for residency only.** It matches
the billing unit, it is where the time buckets already live, and it keeps
split calls attributable to the agency that actually worked them. Note the
consequence, which is William's to accept: on a split call, leg 1 owns the
whole approach from the SWP crossing and the last leg owns the whole departure
— by construction, since legs tile the call.

**For William:** confirm that a split call should read as two jobs in KPI
reporting the same way it reads as two bills.

### Q3. Which population does a KPI run over?

| Population | Count | Note |
|---|---:|---|
| All port calls | 40,170 | Includes truncated and non-commercial |
| Commercial only | 40,028 | Excludes 142 lay-up calls |
| Complete only | 39,691 | Excludes 479 calls missing an SWP crossing |
| **Commercial AND complete** | **39,549** | The only population where SWP-to-SWP duration means what it says |
| Fee-bearing only | 38,288 calls / 40,245 legs | The §14 scope question, still open upstream |

The 479 open-ended calls carry 220,485 hours of *truncated* duration — a real
number that means nothing, because one end of the clock is missing.

**Recommendation: commercial AND complete as the default for every duration
KPI, stated on the face of every report, with the excluded counts shown rather
than dropped.** This is the same discipline `PORT_CALL_SPEC.md` §1 already
applies: incomplete calls are kept and flagged *so they can be excluded
deliberately instead of quietly distorting*.

**For William:** the open half is `OPEN_QUESTIONS.md` §14's unresolved scope
question — should KPI reporting cover every commercial call, or only the ones
that bill? The two differ by roughly 9% of calls (no usable IMO and no vessel
type — the tug/workboat exclusion). Ruling it here would also close §14.

### Q4. Does non-commercial time appear in a *time* KPI?

The existing ruling settles counts and fees but stops just short of KPIs, and
it stops in a suggestive place — William, `OPEN_QUESTIONS.md` §8: *"we just
need to have it time-wise attached to the leg and allocated as layberth when
doing time calcs / KPI."*

Read plainly, that says: **shown, in its own bucket, never folded into
`berth_hours`.** The build already does exactly that for layberth stops. What
is genuinely undecided is the *call-level* case — the 142 pure lay-up calls
holding 23,390 hours, 975 vessel-days (`PORT_CALL_SPEC.md` §4). They are excluded from every count and
every fee, and the ruling explicitly preserves their time so a river-residency
KPI can still see it.

**Recommendation: two families, named differently and never mixed.**
*Traffic and productivity* KPIs run on commercial calls only, with layberth
hours excluded from every denominator. *Residency* KPIs — "vessel-days in the
river" — include lay-up calls and layberth hours, and say so on the face of the
report. A single "days in river" figure that quietly includes or quietly
excludes 975 vessel-days is wrong either way; the fix is two named figures, not
a choice between them.

**For William:** confirm the reading, and confirm that a lay-up call *appears*
in residency reporting despite counting as zero port calls.

### Q5. What does "seq order" mean?

The original scope line is the one thing in this brief that cannot be resolved
by measurement — it has two readings and they need different work:

1. **Within a call** — the order of events and stops between the crossings.
   Already built (`event_seq`, `berth_stop_seq`, `leg_seq`); nothing to design.
2. **Across calls, per vessel** — the vessel's sequence of river visits, and
   what happens between them. Not built.

Reading 2 is well-supported by the data: 30,069 calls have an earlier call by
the same vessel in-window, no vessel's calls overlap, median gap from one SWP
exit to the next SWP entry is 2,526 hours (~105 days). But 2,956 vessels are
seen exactly once, so any repeat-visit KPI covers a subset and must publish
that coverage.

**One technical trap, worth flagging before anything is built.** A vessel-level
sequence must be keyed on the vessel's *stable* identity —
`dim_vessel.natural_key` (IMO, or `NONAME:` + name) — **not** on `vessel_key`.
`OPEN_QUESTIONS.md` §10 records that `vessel_key` is assigned by row position
in each rebuild, so a sequence keyed on it would silently renumber whenever
MRTIS rebuilds. This is a recommendation, not a question.

**For William:** which question is the sequence meant to answer — river
turnaround, repeat business per agency, berth cycle time, or something else?
The measurement is easy; knowing what it is *for* determines its shape.

### Q6. Where do the window edges get handled?

The export window opens and closes mid-traffic: 6,448 events sit before the
vessel's first `Enter` and 10,521 have no open call, 558 calls start in the
first month of the window and 518 in the last. A vessel already in the river on
day one has no recorded entry.

**Recommendation: exclude by rule and publish the coverage, not by silently
trimming dates.** `call_status` already identifies the affected calls, so the
exclusion costs nothing and can be stated as a line on each report.

### Q7. What is the rule for degenerate rows?

Small, but a duration KPI divides by these: 135 legs with `leg_hours <= 0`,
8 legs with negative `berth_hours`, 3 complete calls shorter than an hour.

**Recommendation: a hard guardrail plus an explicit exclusion, counted.** These
are the rows most likely to be a real assembly bug; a guardrail that names them
turns each into a fixable defect instead of an outlier that quietly widens a
distribution.

### Q8. What denominators exist for rate KPIs?

Only 10,545 of 41,662 commercial legs (25.3%) carry a tonnage, all of it FGIS
grain estimates; `actual_tons` is empty everywhere.

**Recommendation: build the time KPIs fleet-wide and label any tons-per-hour
KPI as grain-only.** A "tons per berth hour" figure computed over the legs that
happen to have tonnage would describe grain and be read as the river.

---

## 5. A candidate KPI list, to react to

Draft only — offered so the conversation has something concrete to cut, not as
a proposal. Each depends on the decisions above.

| KPI | Unit | Population | Depends on |
|---|---|---|---|
| SWP-to-SWP hours (median, p90) | Call | Commercial + complete | Q3 |
| Approach: SWP entry → first berth arrival | Leg 1 | Commercial + complete | Q1, Q2 |
| Waiting for berth | Leg | Legs that reached a berth | Q1 |
| Hours alongside working | Leg | Legs that worked a berth | Q4 |
| Departure: last sailing → SWP exit | Last leg | Commercial + complete | Q1, Q2 |
| Underway / unattributed share | Leg | All | **Q1** |
| River residency incl. non-commercial time | Call | All calls, lay-ups included | Q4 |
| Turnaround by agency | Leg | Commercial + complete | Q2, Q3 |
| Turnaround by facility | Berth stop | Legs that worked a berth | Q2 |
| Gap between visits, per vessel | Vessel | Vessels with ≥2 calls | Q5 |
| Tons per berth hour | Leg | Grain legs only (25.3%) | Q8 |

For orientation, measured on today's build: median SWP-to-SWP is 131.5 hours
across the 39,549 commercial complete calls, ranging from 182.8 (Bulk) to 26.3
(Passenger); median approach is 34.9 hours and median departure 10.0 hours on
single-leg calls.

---

## 6. What each ruling unblocks

| Ruling | Where it lands | Cost |
|---|---|---|
| Q1 residual bucket | MRTIS `build_port_calls.py` + `schema_port_call.sql`, one derived column and one guardrail | Small |
| Q2 unit | Definition only — no schema change | None |
| Q3 population | Definition + a filter every report states | None |
| Q4 non-commercial time in KPIs | Definition; closes the last open corner of the §8 ruling | None |
| Q5 sequence | New derivation keyed on `natural_key`; possibly a `vessel_call_seq` column | Medium |
| Q6 window edges | Filter, already supported by `call_status` | None |
| Q7 degenerate rows | Guardrail in MRTIS | Small |
| Q8 denominators | Labelling discipline | None |

Most of the value is in definitions, not code — which is why this is a
conversation and not a build task.

---

## 7. Where the work would happen

**MRTIS is parked** (its session log, 2026-08-19: *"focus only on Claris FM
moving ahead, can park the other version"*), and this repo is read-only against
it. That splits cleanly:

1. **Rule here, with William.** All eight decisions above are definitions; none
   of them requires MRTIS to be running.
2. **Build upstream when MRTIS is unparked.** Q1, Q5 and Q7 touch
   `build_port_calls.py` and the port-call schema. They should join the existing
   MRTIS backlog (§13, §11.3, §10's stable-key work), not be retrofitted here.
3. **Demonstrate here, read-only, without waiting.** Everything except Q1's
   residual column can be computed in a query against the existing columns —
   `kpi/kpi_baseline.py` already computes the residual on the fly rather than
   requiring the column to exist. So a sample KPI report for the Claris
   reviewer, in the shape of the existing `reports/`, is buildable now and does
   not depend on MRTIS being unparked.

**Recommended order:** rule Q1–Q4 (they are the load-bearing four and cost
nothing to decide), build a prototype KPI report here against the current
columns to make the definitions concrete, then hand Q1/Q5/Q7 to MRTIS's backlog
for the session that unparks it.

---

## 8. What this brief is not

It takes no rulings and changes no data. Nothing in it is published to the
Claris reviewer: the review package's figures come from `figures.py` and
`FIGURES.md`, deliberately kept separate, so a KPI question still in flight can
never destabilise a figure the reviewer is already holding.

The numbers here describe what MRTIS stores today at commit `0c4ed0cce0b2f562fed7988c330202a9e2ad10d8`. If
MRTIS rebuilds, re-run `kpi/kpi_baseline.py` — and
`kpi/kpi_baseline.py --check-brief` will say whether this document went stale
with it.

---

## Q9 — Does the clock start at the SWP crossing, or at the anchorage?

**Added 2026-08-20**, after William's `SWP Anch` ruling and the measurement
behind it (`report_concepts/ISSUES.md` I-16).

This brief frames the question as **SWP-to-SWP**. That framing has a hard edge
which the other eight questions cannot reach around: a clock starting at the SWP
crossing **structurally cannot see pre-arrival waiting**.

| | Hours | |
|---|---:|---|
| `waiting_hours` counted on legs | 2,470,459 | inside the call |
| Waiting at `SWP Anch` | **294,293** | **before the call — invisible to a SWP-to-SWP clock** |
| | | **11% of the two combined** |

**William has already ruled this for operations** — *"before they tender NOR and
commence the port call, so we can ignore"* — and that ruling is right for fees,
counts and every existing figure. **It does not automatically settle the KPI
question**, because a KPI about *how long a ship waits for this port* may
legitimately want to start earlier than a KPI about *how long the agency worked
the call*. The two can have different clocks and both be correct.

**Options**

1. **Start at the SWP crossing.** Consistent with the operations ruling and with
   every figure already published. Excludes 294,293 hours by design.
2. **Start at first contact with `SWP Anch`.** Captures the full wait a
   principal experiences. Requires a second clock, since these events sit in no
   call.
3. **Report both**, as a call clock and a port clock.

**One caveat if 2 or 3 is chosen:** 2019 alone holds **111,645** of those hours
at a 35.6-hour median, against ~25,000 and 20–27 hours in recent years. Bringing
pre-arrival waiting inside the boundary would let 2019 dominate any year-on-year
comparison, so this interacts with the 2019 data-quality caveat already recorded
in `report_concepts/ISSUES.md` I-9.

**Recommendation:** option 3 — the operations clock stays exactly as ruled, and a
separate port-experience clock is defined alongside it, so neither question
distorts the other. **No ruling taken here.**
