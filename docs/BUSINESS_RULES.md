# Business rules — port calls, legs, and the agency fee

Plain-language write-up of the rules that produce the `port_call`,
`port_call_leg`, and `port_call_event` tables you're being asked to evaluate.
No Python — this describes *what* the rules are and *why*, for a FileMaker
developer assessing whether Claris can model the same logic.

Every rule below is cited back to its source in MRTIS
(`/Users/billy/Documents/MRTIS`) — a section of `docs/PORT_CALL_SPEC.md`, a
ruling in `docs/OPEN_QUESTIONS.md`, or the implementation in
`scripts/build_db.py` / `scripts/build_port_calls.py`. This document doesn't
invent anything; it translates. Built against MRTIS commit
`61c899b241fb037b5e45b62fb6a865907c1cf4f2` — see `SESSION_LOG.md` for how to
tell if that's moved since.

**Where the numbers come from.** Every count, percentage and dollar figure in
this document is re-derived live from MRTIS's database by
[`figures.py`](../figures.py) and published in
[`docs/FIGURES.md`](FIGURES.md); the charts and reports read from the same
derivation. Nothing here is hand-keyed. If MRTIS rebuilds, re-run `figures.py`
and every figure in the package moves together — that is deliberate, because
in earlier sessions hard-coded figures went stale in one place while staying
current in another.

**Where to start.** If you read three sections, read **§2** (what a port call
is), **§5** (legs, and why one call can bill twice) and **§9** (the fee
schedule). Those three are the model: everything else either feeds them or
qualifies them. §1 is the design principle underneath all of it and is worth
two minutes before the rest.

**Shipping terms** — SWP, layberth, FGIS, TPC, dry bulk and the rest — are
defined in the **glossary** at the end. It defines vocabulary only; the rules
are in the numbered sections above it.

---

## 1. The spine: nothing is dropped, nothing is guessed

Every raw event from the Zone Report feed gets exactly one row in
`port_call_event`, forever — including events the assembly logic couldn't
place into any call. Source values live in their own `src_*` columns and are
never overwritten; whatever the build derives from them lands in a column
alongside, so any row can be read two ways at once: what the source said, and
what MRTIS made of it.

Anything that can't be derived from actual evidence is left NULL, with a
reason code explaining why. This is a hard design rule, not a data-quality
compromise. (MRTIS `PORT_CALL_SPEC.md` §0.)

**For FileMaker:** this argues for a table structure that keeps raw imported
fields untouched and computes/derives into separate fields, rather than
overwriting on import — mirrors what a FileMaker "staging table + calculated
fields" pattern would do.

---

## 2. What a port call is

A **port call** runs from a vessel's `Enter` at the pilot station (Southwest
Pass crossing) to the matching `Exit`. Everything between — anchoring,
docking, shifting berths — belongs to that one call.

> "a vessel must enter swp and exit swp to become a total voyage even if we
> paper split the two operations in the middle" — William, quoted in
> `logic.md` (MRTIS `PORT_CALL_SPEC.md` §1)

Real data doesn't always close cleanly, so three edge cases are handled
explicitly rather than silently dropped:

| Situation | Outcome |
|---|---|
| Events before a vessel's first `Enter` | Left unassigned, reason `before_first_entry` |
| A second `Enter` while a call is still open | The open call is closed as `open_end`; a new call starts |
| An `Exit` with no open call | Unassigned, reason `no_open_call` |
| A call that never sees an `Exit` | Kept, `call_status = 'open_end'` |

`call_status` is `'complete'` only when both ends are present — currently
**98.81%** of calls (39,691 of 40,170). The rest are real gaps in the source
feed, kept and flagged so duration analytics can exclude them deliberately.

### Not every call is commercial

Some calls are a vessel going nowhere: a lay-up, a repair-yard stay, a spell
at a layberth with no cargo work at either end. William ruled (2026-08-19,
`OPEN_QUESTIONS.md` §8/§14) that these are **flagged, not deleted** — the
rows, their events and their timestamps all stay on the record, so the
vessel-days they represent are still countable, but they drop out of
commercial counts and revenue.

| Column | Meaning |
|---|---|
| `is_commercial_call` | True for a normal working call; false for a pure lay-up |
| `call_class` | `commercial` or `layup` — the reason, in words |

Currently **142 of 40,170** calls are `layup`, leaving **40,028** commercial.

**For FileMaker:** report on `is_commercial_call = 1` by default. Deleting
these rows instead of flagging them would silently destroy the lay-up
time — which is exactly the figure a berth-utilisation question needs.

---

## 3. Berth stops: the visit, not the geofence hit

A **berth stop** is one visit to one facility, not one row in the raw feed.
Two rulings from William (2026-08-19) shape this, both because the source
data is AIS/geofence-derived rather than a hand-kept berth log.

**The facility is the unit, not the individual zone.** Two berths of the same
elevator (e.g. "Zen-Noh Upper" and "Zen-Noh Lower") are one facility — a
vessel that shifts between them has shifted, not called twice. This mapping
lives in the zone/facility dictionary. (`PORT_CALL_SPEC.md` §2, "focus on the
facility canonical as will avoid this confusion.")

**Only the first docking and the last sailing count.** AIS/geofence noise
produces false re-arrivals — overlapping geofences, movement within a berth —
that look like a vessel docked, sailed, and redocked within minutes, which is
physically implausible for an ocean vessel. So a visit is defined as a run of
consecutive berth events at the same facility (or within a configurable bounce
window, default 2 hours) of the previous one. The **first arrival** is the
real docking; the **last departure** is the real sailing; everything in
between is kept on the record (nothing is dropped from the spine) but flagged
`is_geofence_artifact` and excluded from being read as an operation.
Currently **5,102 berth events** collapse this way — **5.23%** of all 97,528
berth events, or **5.27%** of the 96,845 that were placed into a call. (Both
denominators are quoted because the two round differently: the second is
where a "5.3%" figure comes from.)

An anchorage or pilot-station event between two berth events always ends the
visit — going to anchor and coming back is a genuine second call at that
facility, not noise.

**For FileMaker:** this is a "collapse consecutive same-facility rows into one
visit, keep the originals" pattern — doable with a sort + break-key script
step over a sorted found set, or a summary/self-join approach.

---

## 4. What the vessel did — `activity` (Load / Discharge / No Cargo)

Resolved by a strict evidence order, strongest first — a lower-ranked source
is never consulted once a higher one has answered:

1. **The zone dictionary, where a facility can only physically do one thing.**
   A grain elevator can only load; a "Layberth" zone (14 zones, e.g. Buck
   Kreihs, Violet Dock) never does cargo work at all → `No Cargo`. This
   outranks everything else, including draft, because the physical capability
   of a berth is a hard fact and the draft signal on these records is noisy
   AIS variance. (`PORT_CALL_SPEC.md` §3 rung 1 — William: *"as per dictionary,
   a vessel at a grain elevator can only load and only load cargo group
   grain."*)
2. **FGIS.** A USDA grain certificate issued against the visit → `Load`,
   cargo group `Grain`.
3. **Draft delta — a tie-breaker, not a decider, and only where the
   dictionary doesn't already know.** Deeper on sailing than on arrival →
   `Load`; lighter → `Discharge`. Measured first-docking to last-sailing
   across the whole visit (never across a berth shift within one facility).
4. **Nothing.** `activity` stays NULL if none of the above can speak — never
   guessed.

**An unresolved stop outranks `No Cargo`.** Ruled by William 2026-08-19
(`OPEN_QUESTIONS.md` §11.1, option (a)) and built. Previously a leg that mixed
a layberth stop with a working berth whose activity couldn't be resolved
reported `No Cargo` — while billing a full agency fee, because the fee test
and the label test used different predicates. 54 legs said "no cargo" and
charged for cargo work. Now the resolution order is: a real (non-`No Cargo`)
activity first; failing that, if any stop is unresolved the leg reports
**NULL**; only a leg with nothing *but* layberth stops reports `No Cargo`
itself. The same fix made `cargo_group` and `first_berth_zone` read from the
first **working** stop rather than whichever stop was literally first.

Live check: **0 legs** now report `activity = 'No Cargo'` while carrying a fee.

| Method | Legs | Share |
|---|---:|---:|
| Draft delta | 19,290 | 46.14% |
| Zone dictionary | 14,990 | 35.86% |
| FGIS | 331 | 0.79% |
| **Resolved** | **34,611** | **82.79%** |
| Unresolved (reached a berth, no evidence spoke) | 5,778 | 13.82% |
| Never reached a berth at all | 1,415 | 3.38% |
| **All legs** | **41,804** | **100%** |

That last row is a separate bucket from "unresolved" and is reported
separately: a leg that never berthed has nothing to resolve, rather than
evidence that failed.

When the dictionary and the draft disagree, it's flagged
(`activity_conflict`) rather than silently overridden — usually AIS noise,
occasionally a dictionary row that needs correcting.

---

## 5. Legs, and the split call

A **leg** is a run of consecutive berth stops that share one activity, plus
the anchorage/pilot-station time leading up to them. A new leg starts *only*
when the activity actually changes — Discharge → Load, or Load → Discharge.

- Two `Load` stops back to back (topping off at a second elevator) is **one
  leg** — same cargo job.
- A stop whose activity is unresolved **joins the leg already in progress**.
  An unknown can never manufacture a split.

**Real-world confirmation:** MV *Ultra Leopard* discharged iron ore at Nucor
Steel, then — without leaving the river — idled 11 days at two anchorages,
then loaded soybeans at ADM Reserve under a *different master*. Two
Statement-of-Fact-confirmed legs, one continuous river presence.
(`PORT_CALL_SPEC.md` §4; `OPEN_QUESTIONS.md` §4.)

Only vessel types that genuinely work this way can split: dry-bulk carriers,
plus vessels with no recorded type (an unknown type must not be assumed
ineligible). Tankers, gas carriers, cruise ships, container ships and reefers
are excluded by design — William: *"reduced as the tankers, gas, other,
cruise, container and reefer can be ignored."* **1,632 calls (4.06%) are
split calls.**

**Read that 4.06% with its denominator attached.** A split call *is* a
discharge-then-load turnover, and the rate it appears to run at changes by more
than four times depending on what it is divided by — all three of these describe
the same 1,628 bulk calls:

| Denominator | Rate |
|---|---:|
| All 40,170 port calls | 4.06% |
| All 21,565 **bulk** calls | 7.55% |
| The 5,197 bulk calls that **discharge** | **31.33%** |

The last is the operationally meaningful one, and it is the one that matches
trade experience — William, 2026-08-20: *"from experience 24-35% bulk ships turn
over in the river from discharge to load."* A rate quoted without its denominator
is not a small imprecision here; it is a different number. (Derived in
`docs/FIGURES.md`; see `report_concepts/ISSUES.md` I-8.)

### `No Cargo` (layberth) is special — two separate rulings

William, 2026-08-19 (`OPEN_QUESTIONS.md` §8), ruled on this in two distinct
parts:

- **§8a — a layberth stop can never open a leg boundary.** It's not a cargo
  job, so it can't be the discharge-then-load pivot the split rule depends on.
  It joins whatever leg is already in progress, exactly like an unresolved
  stop. (This is *why* Discharge → No Cargo → Load still correctly splits on
  the Discharge/Load boundary, as if the layberth stop weren't there.)
- **§8b — a pure layberth call never bills.** A leg only bills if it did real,
  non-layberth cargo work *somewhere*. A leg made entirely of layberth stops —
  a lay-up, a repair-yard visit — accrues **no fee**, exactly like a call that
  never berthed at all. A leg that mixes one layberth stop with genuine other
  berth work still bills; only the layberth stop itself is fee-exempt.

---

## 6. Agency

Two non-destructive transformations sit on top of the raw `Agent` field:

1. **`agency`** — the raw agent name run through a spelling/roll-up
   dictionary (misspellings, agencies since renamed or sold).
2. **`agency_leg`** — **the agency that brought the vessel in owns the whole
   leg**, applied to every event in that leg. This is the column analytics
   and reporting should use, and it does two things:
   - **Fills blanks.** ~2.4% of source rows carry no agent; once the call is
     assembled, the rest of the leg makes the answer obvious.
   - **Undoes a known pilot-sheet artefact.** Pilot sheets sometimes record
     the *outbound* agent (the one taking the ship back out for its next
     voyage) on the sailing event of a call another agency actually worked.
     Reverting the sailing to the inbound agency corrects this — and because
     it's applied per leg, a genuine split call still correctly keeps two
     different agencies, one per leg. (`PORT_CALL_SPEC.md` §5.)

### Two things to know before reporting revenue by agent

**1. Use the leg grain. `port_call.agency` is not it.** Agency exists on the
port call *and* on the leg, and the call-level column is the more obvious one to
reach for. It is a single pick for a call that may have been worked by two
agencies: **91 port calls carry more than one agency across their legs**, and the
**91 legs** that disagree with their own call-level value hold **$939,000** of
fee. Report off `port_call.agency` and that $939,000 is credited to the wrong
agent — not lost from the total, just attributed to whoever won the pick. Use
`port_call_leg.agency`, or `port_call_event.agency_leg` at event grain.

**2. A by-agent report is not a clean division of the book.** The agency on a leg
is the **inbound** agency, and it keeps the whole fee even where the agent changed
during the leg. That is the ruled behaviour, not a defect — but its scale is
material and belongs stated rather than discovered:

| | Chargeable legs | Fee |
|---|---:|---:|
| Agent stable through the leg | 37,012 | $243,164,750 |
| **Agent changed mid-leg** (`agent_changed_in_leg`) | **3,233 (8.03%)** | **$29,495,250 (10.82%)** |

So roughly **one dollar in nine** of agency revenue is attributed to an agent
where at least one other agency was also involved in that leg. The commercial
reason is ordinary: on a chartered voyage the owner's agent handles the inbound
and the charterer's agent takes over for the outbound load (William, 2026-08-20),
which is why the effect is a dry-bulk one — it is essentially absent from
container and cruise traffic, where one operator handles the whole call.

Both figures are derived in `docs/FIGURES.md`, never hand-keyed. See
`report_concepts/ISSUES.md` I-4 and I-5.

---

## 7. Time

- **`waiting_hours`** — anchorage dwell **before** the leg's first berth
  arrival only. This is the *only* figure that means "waiting for a berth."
- **`inter_berth_idle_hours`** — dwell between first berth arrival and last
  sailing (e.g. a shift to anchorage mid-leg).
- **`outbound_idle_hours`** — dwell after the last sailing. The vessel is
  leaving, not waiting on a dock — reported separately so it's never
  miscounted as waiting.
- **`berth_hours`** — hours alongside a **working** berth. Layberth time is
  **not** in this figure (see below).
- **`layberth_hours`** — hours alongside a layberth, held separately.

Dwell is attributed by **overlap** with these time windows, not by which side
of the berth arrival an anchorage event happened to start on — pilot sheets
routinely leave an anchorage record open for hours or days after a vessel is
already alongside working, and counting that as "waiting" would double-count
cargo time. (`PORT_CALL_SPEC.md` §6 — William: *"waiting can only be waiting
for the berth, as the anchorage stop happens after it departs."*)

### Layberth time is non-commercial time, and is held apart

Ruled by William 2026-08-19 (`OPEN_QUESTIONS.md` §8) and built: a layberth is
not a working berth, so its hours and its stops no longer inflate the figures
that describe cargo work. **`berth_stop_count` and `berth_hours` now count
working berths only**; layberth time moved into its own `layberth_hours`
column on both `port_call_leg` and `port_call`.

Currently **45,741.57 hours across 377 legs** sit in `layberth_hours`. Before
this ruling that time was inside `berth_hours`, where it read as cargo
operations.

**This is the change most likely to surprise anyone comparing against an
older extract**: `berth_hours` is a smaller number than it used to be, and
that is correct, not data loss — the hours are in the column next to it.
The design intent is a general **non-commercial time** classification, not a
layberth special case; other non-working states are expected to join it.

---

## 8. Cargo

Populated only where an actual external source can say — never inferred:

| Column | Source |
|---|---|
| `cargo`, `destination`, `estimated_tons` | FGIS grain certificates, aggregated per leg |
| `cargo_group` | FGIS (`Grain`), else the zone dictionary's typical cargo group |
| `dwt`, `tpc`, `ship_type`, `ship_type_group` | the ships register, matched by canonical IMO |

`estimated_tons` is a **leg total** aggregated across every FGIS certificate
tied to that leg (one sailing can carry several) — never sum it again across
the leg's individual event rows, it'll double-count.

`estimated_tons` vs. `actual_tons`: FGIS metric tons is explicitly an
*estimate* per William's original mapping, not a certified actual weight.
`actual_tons` is reserved for a genuinely certified figure and is NULL
everywhere today — no source for it exists yet. This is deliberate: an empty
column that *looks* like real data is worse than no column.

---

## 9. The agency fee schedule

This is the number a FileMaker reviewer will care about most, so it's laid
out in full, base tiers plus the six rules layered on top.

### 9.1 Two bases exist, and they answer different questions

MRTIS keeps **two** fee totals, deliberately, rather than replacing one with
the other:

| Basis | What it charges | Column | Current total |
|---|---|---|---|
| **Per-departure** (frozen, historical) | Every single sailing from a berth | `port_call_event.agency_fee` | $349,527,500 |
| **Per-leg** (the ruled, billable figure) | One charge per leg that reached a berth | `port_call_leg.agency_fee`, summed to `port_call.agency_fee_total` | $272,660,000 |

**Why two exist:** William's ruling (`OPEN_QUESTIONS.md` §7.1, 2026-08-19,
verbatim: *"agency fee is per port call, not per berth except when split
discharge then load"*) established that the real billing unit is the
**leg**, not the berth departure. Under the old per-departure counting,
**7,197 of 38,288 fee-bearing calls — 18.8%** — were charged 2 to 10 times
because a single call can touch several berths (a tanker might call 4–6
berths in one visit and still only bill once). *That percentage is of
fee-bearing calls; against all 40,170 calls it is 17.9%.* The per-departure
basis is kept **frozen** as a historical comparison point, unaffected by the
newer fee-tier rules below (`OPEN_QUESTIONS.md` §12.3.4) — so the two numbers
stay comparable across time, but they are answering "what if every departure
billed" vs. "what actually bills."

Per-departure over-bills the billable basis by **$76,867,500 (28.2%)**.

**A caution before you reconcile the per-departure figure.** There are two
roll-ups of it and they do not agree:

| Source | Total |
|---|---:|
| `port_call_event.agency_fee` (event level) | $349,527,500 |
| `SUM(port_call.agency_fee_departures_total)` (call level) | $346,692,500 |
| **Gap** | **$2,835,000** |

The gap is exactly the fee carried by **360 departure events that never landed
in a port call** — 240 `before_first_entry` ($1,925,000) and 120
`no_open_call` ($910,000). A call-level column can only hold call-level fees,
so the shortfall is structural rather than an error. William ruled it **leave
as is** (`OPEN_QUESTIONS.md` §11.2): the gap is heavily front-loaded into
2019, an edge effect of where the source feed starts, not an ongoing leak. It
is disclosed here rather than left for a reviewer to trip over, because the
two numbers give different over-billing ratios depending which one you pick.

**For a FileMaker rebuild: `port_call_leg.agency_fee`, rolled up to
`port_call.agency_fee_total`, is the number to report as revenue. The
per-departure figure is a QA/comparison artifact, not a billing figure.**

### 9.2 Base tiers (pre-2026-08-19, still the fallback)

These are tested **in order, first match wins.** The order matters more than
the amounts — see the warning below.

| # | Test | Fee |
|---|---|---|
| 1 | Canonical `vessel_type` = `Bulk` | $10,500 |
| 2 | Canonical `vessel_type` is anything else non-empty | $3,500 |
| 3 | *Only if canonical `vessel_type` is absent* — register `ship_type_group` starts `Bulk Carrier` | $10,500 |
| 4 | *Only if canonical `vessel_type` is absent* — any other non-empty `ship_type_group` | $3,500 |
| 5 | No usable IMO *and* no type from any source (a tug, workboat, or government craft — not an agented ocean vessel) | No fee (NULL) |

> **The register is a fallback, not an alternative.** `ship_type_group` is
> consulted **only when the canonical vessel type is missing entirely**. A
> vessel that has a canonical type never has its register group looked at,
> even if that group says `Bulk Carrier`.
>
> This is not hypothetical: **3 chargeable legs today** — one Container, one
> Tanker, one Other — carry `ship_type_group LIKE 'Bulk Carrier%'` and
> correctly bill **$3,500**, because their canonical type already answered at
> test 2. Implementing this as "canonical Bulk *or* register Bulk Carrier"
> bills them $10,500 and is wrong. Only $21,000 is at stake in today's data,
> but the precedence is what gets built into the calculation and it would be
> wrong for every future vessel too.

Step 3 exists to recover real Capesize and Kamsarmax bulkers whose Zone
Report `Type` was never recorded — the register knows them even when the feed
doesn't.

A vessel whose IMO merely fails its check digit still bills at the lower tier
— a corrupted ID number is a typo on a real ship, not the absence of one.

### 9.3 The six §12 rules (William's revised schedule, ruled and built 2026-08-19)

William's instruction, verbatim (`OPEN_QUESTIONS.md` §12):

> *"minor change to the fee rules, if vessel type is; Passenger/Cruise use fee
> $2500; if Ro-Ro Cargo Ship or Vehicles Carrier use fee $1000; if vessel type
> is Container Ship (Fully Cellular) or Container Ship (Fully
> Cellular/Ro-Ro Facility) use fee $750; if vessel type is Refrigerated Cargo
> Ship use fee $5000; last, any dry bulk vessel calling a general cargo
> facility type, use fee $5000"*

| # | Condition | Fee |
|---|---|---|
| R1 | Vessel type = `Passenger/Cruise` | $2,500 |
| R2 | Vessel type = `Ro-Ro Cargo Ship`, `Vehicles Carrier`, or `General Cargo Ship (with Ro-Ro facility)` | $1,000 |
| R3 | Vessel type = `Container Ship (Fully Cellular)` or `Container Ship (Fully Cellular/Ro-Ro Facility)` | $750 |
| R4 | Vessel type = `Refrigerated Cargo Ship` | $5,000 |
| R5 | Any **dry bulk** vessel calling a **General Cargo** facility type (at the leg's first *working* berth) | $5,000 |

**R2 covers a third type not in William's original wording.** Neither
`Ro-Ro Cargo Ship` nor `Vehicles Carrier` appears anywhere in MRTIS's traffic.
`General Cargo Ship (with Ro-Ro facility)` does, and is the nearest thing to
what R2 describes. Ruled by William 2026-08-19 (`OPEN_QUESTIONS.md` §12.3.2):
*"a roro is a port call"* — so it is covered by R2 rather than left at the
base tier. **2 chargeable legs**, $21,000 → $2,000.

**Where "vessel type" comes from (R1–R4):** these are values from the *ships
register's* raw `ship_type` field, not MRTIS's own 7-value canonical
vocabulary (Bulk/Container/Gas/Other/Passenger/Reefer/Tanker) — the register
is more specific, and two of the named types (`Ro-Ro Cargo Ship`, `Vehicles
Carrier`) have no canonical equivalent at all. Ruled 2026-08-19
(`OPEN_QUESTIONS.md` §12.3.1): the register's `ship_type` is checked
**first**; the canonical type is only a fallback for the small number of
vessels (63 fleet-wide) with no register match at all, and even then only for
the three rules that have a canonical equivalent (Passenger, Container,
Reefer — Ro-Ro/Vehicles Carrier stay unreachable without a register row, by
design).

**"Dry bulk" for R5** means MRTIS's own canonical `vessel_type = 'Bulk'` —
the same field the $10,500 base tier already uses, not a register-only
definition. (`OPEN_QUESTIONS.md` §12.3.3, resolved.)

**Which berth decides R5, on a leg touching more than one facility:** the
leg's first **working** berth stop — layberth stops are skipped when
resolving `facility_type`. The leg (not the berth, not the call) stays the
billing unit regardless of how many berths it touches — a tanker calling 4–6
berths in one visit still bills once. R5 only changes the *amount*, using the
leg's first working berth; it does not introduce any new per-berth billing.
(`OPEN_QUESTIONS.md` §12.3.3.1, ruled and built 2026-08-19.)

> **This was amended after the first build of the schedule.** R5 originally
> priced off the leg's first berth of *any* kind. Because every layberth zone
> carries `facility_type = General Cargo`, a Bulk vessel that happened to lie
> at a layberth before working was being handed the $5,000 General Cargo tier
> on the strength of a berth where no cargo moved. Pricing off the first
> working berth instead moved **93 legs** back to the $10,500 base tier,
> **+$511,500**. 14 Bulk legs still start at a genuine General Cargo working
> berth and correctly stay at $5,000.
>
> `first_berth_zone`, `first_berth_facility` and `facility_type` on
> `port_call_leg` all now describe the first **working** berth. If you are
> comparing against an older extract, these columns can name a different
> berth than they used to.

**Precedence:** R5 outranks R1–R4 if a vessel could ever satisfy both — though
today that's structurally impossible, since a Bulk vessel is never also
Passenger/Container/Reefer. Stated explicitly rather than left to that
coincidence. (`OPEN_QUESTIONS.md` §12.3.3.3.)

**Does this apply to the frozen per-departure basis too?** No — ruled
2026-08-19 (`OPEN_QUESTIONS.md` §12.3.4): the per-departure basis stays on
the old two-tier schedule ($10,500/$3,500) so it remains a fixed historical
benchmark. Only the leg-level fee (§9.1 above) uses the six new rules.

### 9.4 Net effect of the six rules

Measured against the full rebuilt dataset (40,245 chargeable legs), re-derived
by `figures.py` — see [`docs/FIGURES.md`](FIGURES.md):

| Rule | Chargeable legs | Would have billed (old 2-tier) | Bills now | Change |
|---|---:|---:|---:|---:|
| R1 Passenger/Cruise | 1,043 | $3,650,500 | $2,607,500 | −$1,043,000 |
| R2 Ro-Ro / Vehicles Carrier / Gen-Cargo w. Ro-Ro | 2 | $21,000 | $2,000 | −$19,000 |
| R3 Container (Fully Cellular) | 3,128 | $10,948,000 | $2,346,000 | −$8,602,000 |
| R4 Refrigerated Cargo Ship | 40 | $140,000 | $200,000 | **+$60,000** (the only rule that raises a fee) |
| R5 Bulk @ General Cargo berth | 3,019 | $31,699,500 | $15,095,000 | −$16,604,500 |
| Base tiers, untouched by §12 | 33,013 | $252,409,500 | $252,409,500 | $0 |
| **Total** | **40,245** | **$298,868,500** | **$272,660,000** | **−$26,208,500 (−8.77%)** |

**How this table is proved.** `figures.py` re-implements the §12 precedence
independently and then asserts, leg by leg, that its answer equals the fee
MRTIS actually stored. It currently reports **0 mismatches across all 40,245
chargeable legs** — so the rule attribution above is not an estimate, it
reproduces the built figure exactly. If MRTIS's `agency_fee_for()` ever
changes without this package catching up, the script fails rather than
publishing a plausible wrong number.

This is a *fee re-tiering*, not a rules change to what counts as a leg or a
split — the leg-count and split-call logic in §5 above is unaffected by §9.

---

## 10. What's deliberately NOT in this package

- **§13 of `OPEN_QUESTIONS.md`** (General Cargo berths as discharge-only, and
  buoy-sequencing rules for activity resolution) is **ruled but not yet
  built** in MRTIS as of this commit — explicitly phase 2, pending more data.
  It would move the split/leg baseline that today's fee figures sit on top
  of. Not reflected in this export; watch for it in a future MRTIS commit.
- **Per-agent port-call counts** (`OPEN_QUESTIONS.md` §14) — raised, not yet
  scoped or built.
- `Shipper`, `Consignee`, `Receiver`, `Last Port`, `Next Port`, `Origin` — no
  source is wired into MRTIS yet. Deliberately absent rather than populated
  with guesses.

### Rows removed upstream — why this won't reconcile to a raw extract

If you compare this export against a raw Zone Report extract, the counts will
not meet, by design:

- **9 dredge/workboat vessels are filtered out at ingest** — 23,228 rows,
  **7.4% of the raw feed**. William's ruling (`OPEN_QUESTIONS.md` §2): remove
  them at the front end rather than flagging them, *"removes those records and
  focuses the table"*. Matching is by IMO wherever the dictionary supplies
  one, never by name alone — "Texas Star" is both a dredge and, separately, a
  real tanker, and a name-based filter deleted the tanker too.
- **131 rows for a vessel named *Egret* are excluded** (`OPEN_QUESTIONS.md`
  §7.5). An IMO-repair rule had merged two genuinely different ships that
  shared a name; the merge is now refused. This also removes $98,000 of
  fabricated fee from the per-departure basis.

### Still-open MRTIS questions that touch this data

These are logged upstream and unresolved as of this commit. None invalidates
a figure here, but a reviewer should know they exist:

| Section | Status |
|---|---|
| §11.2 — the two per-departure roll-ups don't reconcile ($2,835,000) | **Ruled: leave as is.** Disclosed in §9.1 above |
| §11.3 — `tpc = 0` is a placeholder on 4,045 calls (10.07%), not a measured value | **Deferred.** Filter `tpc > 0` before any draft-survey maths |
| §11.4 — 2 legs berthed and did non-layberth work but carry no fee | **Ruled: no**, they do not bill |
| §11.5 | Documentation corrections, no ruling needed |
| §7.2–§7.4 | Dredge/vessel-identity edge cases, all ruled and built |
| §13 | Ruled, **not built** — see the first bullet above |

If the MRTIS commit this package was built against changes before those
land, re-export rather than assuming these figures still hold — see
`SESSION_LOG.md`.

---

## Glossary

Everything above is written for a FileMaker developer rather than a Python
one, but it still assumes the shipping vocabulary the source data is built
out of. This section supplies it.

**This section defines words, not rules.** Nothing here overrides or adds to
anything above. Where a term carries a *specific* meaning in this data rather
than its ordinary industry one, the section that gives it that meaning is
linked, and that section — not this one — is the authority.

| Term | What it means here |
|---|---|
| **AIS** | Automatic Identification System — the transponder every commercial vessel broadcasts position and identity from. The source feed's positions and drafts are derived from it, which is why §3 has to collapse geofence noise and why §4 treats draft as a tie-breaker rather than a decider. |
| **Agency / agent** | The shore-side firm that handles a vessel's business while it is in port — pilots, berths, customs, crew. The party the agency fee in §9 is charged by, and the subject of the reporting in `reports/`. |
| **Anchorage** | A designated area where a vessel anchors and waits, typically for a berth. Time here is `waiting_hours` only when it precedes the leg's first berth arrival (§7). |
| **Berth** | One place a vessel can lie alongside. Several berths can belong to one **facility** — §3 treats the facility as the unit, so shifting between two berths of the same elevator is not a second call. |
| **Capesize / Kamsarmax** | Size classes of dry-bulk carrier (Capesize is too large for the Suez or Panama canals; Kamsarmax is sized for the port of Kamsar). They appear in §9.2 only as examples of real bulkers the Zone Report sometimes fails to type, which the ships register can still identify. |
| **Draft** | How deep the hull sits below the waterline, in feet here. A vessel that loads gets deeper and one that discharges gets lighter, which is the signal §4 uses as its third-ranked evidence. |
| **Draft survey** | Working out cargo weight from the change in draft. It needs **TPC**, which is why the `tpc = 0` placeholder matters (MRTIS `OPEN_QUESTIONS.md` §11.3, listed in §10): a survey run against a zero silently produces nonsense. |
| **Dry bulk** | Unpackaged bulk cargo — grain, ore, coal — and the vessels built to carry it. The category R5 prices off (§9.3), defined there as MRTIS's canonical `vessel_type = 'Bulk'`. |
| **DWT (deadweight tonnage)** | The total weight a vessel can carry — cargo, fuel, stores, crew. From the ships register, not the feed. |
| **Facility** | One commercial operation on the river (a grain elevator, a refinery dock, a container terminal), which may run several berths. The unit a berth stop is counted against (§3). |
| **FGIS** | The USDA's Federal Grain Inspection Service, which issues official certificates against grain loadings. Those certificates are the only cargo evidence in this data that comes from outside the vessel-movement feed, which is why §4 ranks them second and §8 sources `cargo` and `estimated_tons` from them. (MRTIS `docs/BUILD.md`.) |
| **Geofence** | A virtual boundary drawn around a zone. A vessel crossing one generates an event — and overlapping or badly-drawn boundaries generate false ones, which is what `is_geofence_artifact` flags (§3). |
| **IMO number** | A permanent 7-digit identifier issued by the International Maritime Organization. It stays with the hull for life, through renaming, reflagging and resale — which is why it is the stable vessel key here and `vessel_key` is not. The last digit is a check digit, so a corrupted number can be detected; §9.2 rules that a failed check digit still bills, because it is a typo on a real ship. |
| **Layberth** | A berth where a vessel lies *without working cargo* — laid up, waiting on repair, or simply parked. MRTIS's zone dictionary marks these `ops = Layberth` ("no cargo ever takes place"). Non-commercial throughout: it never resolves an activity to anything but `No Cargo` (§4), never opens a leg boundary (§5), never bills (§5), and its hours are held apart from `berth_hours` (§7). |
| **Leg** | This project's billing unit. Defined in §5 — a run of berth stops sharing one activity, plus the waiting time leading up to them. |
| **Pilot sheet** | The river pilot's record of a movement. A source of agent and timing data, and the origin of the outbound-agent artefact §6 corrects and the open anchorage records §7 works around. |
| **Pilot station** | Where a river pilot boards or leaves a vessel. At **SWP** it is the point a port call opens and closes (§2). |
| **Port call** | The whole visit, SWP entry to SWP exit. Defined in §2. |
| **Ro-Ro** | Roll-on/roll-off — cargo driven on and off on its own wheels rather than lifted. Its own fee tier under R2 (§9.3). |
| **Ships register** | A reference dataset of vessel particulars (`ship_type`, `ship_type_group`, `dwt`, `tpc`), matched to the feed by IMO. Distinct from the Zone Report and more finely typed than it — §9.3 turns on exactly that distinction. |
| **Split call** | One port call that did two different cargo jobs — classically discharge, then load, without leaving the river. Two legs, so two fees. Defined in §5; it is the case the whole leg model exists for. |
| **Statement of Fact (SOF)** | The signed, chronological record of what happened during a port call, kept by the agent and master. Not a source in this pipeline, but the ground truth §5's *Ultra Leopard* case was confirmed against. |
| **SWP (Southwest Pass)** | The main deep-draft entrance from the Gulf into the Mississippi. Crossing it inbound opens a port call and crossing it outbound closes one (§2), which is what "SWP-to-SWP" means wherever it appears. |
| **Topping off** | Finishing a load at a second berth after part-loading at a first. §5's reason two consecutive `Load` stops are one leg and not two. |
| **TPC** | Tonnes per centimetre immersion — how many tonnes it takes to change a vessel's draft by one centimetre. The conversion factor in a draft survey. Read the caution on `tpc = 0` in §10 before using it. |
| **Zone Report** | The raw source feed this whole package derives from: a vessel-movement export recording each vessel's crossings into and out of named river zones, with the agent, draft and action of the moment. Everything in §1's "spine" is one row of it. |
