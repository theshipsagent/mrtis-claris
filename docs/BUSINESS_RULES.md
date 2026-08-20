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
`09e1cb633ee9dc86a0393956eb118c9c8d5bafb8` — see `SESSION_LOG.md` for how to
tell if that's moved since.

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
**98.8%** of calls. The rest are real gaps in the source feed, kept and
flagged so duration analytics can exclude them deliberately.

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
Currently **5.3%** of raw berth events collapse this way.

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

Currently 83.3% of legs resolve (35.7% by dictionary, 46.8% by draft, 0.8% by
FGIS); 13.4% stay unresolved. When the dictionary and the draft disagree, it's
flagged (`activity_conflict`) rather than silently overridden — usually AIS
noise, occasionally a dictionary row that needs correcting.

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
cruise, container and reefer can be ignored."* **4.1% of calls are split
calls.**

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

---

## 7. Time

- **`waiting_hours`** — anchorage dwell **before** the leg's first berth
  arrival only. This is the *only* figure that means "waiting for a berth."
- **`inter_berth_idle_hours`** — dwell between first berth arrival and last
  sailing (e.g. a shift to anchorage mid-leg).
- **`outbound_idle_hours`** — dwell after the last sailing. The vessel is
  leaving, not waiting on a dock — reported separately so it's never
  miscounted as waiting.
- **`berth_hours`** — hours alongside.

Dwell is attributed by **overlap** with these time windows, not by which side
of the berth arrival an anchorage event happened to start on — pilot sheets
routinely leave an anchorage record open for hours or days after a vessel is
already alongside working, and counting that as "waiting" would double-count
cargo time. (`PORT_CALL_SPEC.md` §6 — William: *"waiting can only be waiting
for the berth, as the anchorage stop happens after it departs."*)

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
| **Per-departure** (frozen, historical) | Every single sailing from a berth | `port_call_event.agency_fee` | $349,625,500 |
| **Per-leg** (the ruled, billable figure) | One charge per leg that reached a berth | `port_call_leg.agency_fee`, summed to `port_call.agency_fee_total` | $272,167,500 |

**Why two exist:** William's ruling (`OPEN_QUESTIONS.md` §7.1, 2026-08-19,
verbatim: *"agency fee is per port call, not per berth except when split
discharge then load"*) established that the real billing unit is the
**leg**, not the berth departure. Under the old per-departure counting, 19.0%
of port calls were being charged 2–10 times because a single call can touch
several berths (a tanker might call 4–6 berths in one visit and still only
bill once). The per-departure basis is kept **frozen** as a historical
comparison point, unaffected by the newer fee-tier rules below
(`OPEN_QUESTIONS.md` §12.3.4) — so the two numbers stay comparable across
time, but they are answering "what if every departure billed" vs. "what
actually bills."

**For a FileMaker rebuild: `port_call_leg.agency_fee`, rolled up to
`port_call.agency_fee_total`, is the number to report as revenue. The
per-departure figure is a QA/comparison artifact, not a billing figure.**

### 9.2 Base tiers (pre-2026-08-19, still the fallback)

| Vessel type | Fee |
|---|---|
| Bulk (canonical vessel type, or register `ship_type_group` starting `Bulk Carrier`) | $10,500 |
| Everything else with a known type | $3,500 |
| No usable IMO *and* no type from any source (a tug, workboat, or government craft — not an agented ocean vessel) | No fee (NULL) |

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
| R2 | Vessel type = `Ro-Ro Cargo Ship` or `Vehicles Carrier` | $1,000 |
| R3 | Vessel type = `Container Ship (Fully Cellular)` or `Container Ship (Fully Cellular/Ro-Ro Facility)` | $750 |
| R4 | Vessel type = `Refrigerated Cargo Ship` | $5,000 |
| R5 | Any **dry bulk** vessel calling a **General Cargo** facility type (at the leg's *first* berth) | $5,000 |

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
leg's **first** berth stop. The leg (not the berth, not the call) stays the
billing unit regardless of how many berths it touches — a tanker calling 4–6
berths in one visit still bills once. R5 only changes the *amount*, using the
leg's first berth; it does not introduce any new per-berth billing.
(`OPEN_QUESTIONS.md` §12.3.3.1, resolved.)

**Precedence:** R5 outranks R1–R4 if a vessel could ever satisfy both — though
today that's structurally impossible, since a Bulk vessel is never also
Passenger/Container/Reefer. Stated explicitly rather than left to that
coincidence. (`OPEN_QUESTIONS.md` §12.3.3.3.)

**Does this apply to the frozen per-departure basis too?** No — ruled
2026-08-19 (`OPEN_QUESTIONS.md` §12.3.4): the per-departure basis stays on
the old two-tier schedule ($10,500/$3,500) so it remains a fixed historical
benchmark. Only the leg-level fee (§9.1 above) uses the six new rules.

### 9.4 Net effect of the six rules

Measured against the full rebuilt dataset (40,245 chargeable legs):

| Rule | Chargeable legs | Would have billed (old 2-tier) | Bills now | Change |
|---|---|---|---|---|
| R1 Passenger/Cruise | 1,043 | $3,650,500 | $2,607,500 | −$1,043,000 |
| R2 Ro-Ro / Vehicles Carrier | 0 | $0 | $0 | $0 (no matching traffic in this data) |
| R3 Container (Fully Cellular) | 3,128 | $10,948,000 | $2,346,000 | −$8,602,000 |
| R4 Refrigerated Cargo Ship | 40 | $140,000 | $200,000 | **+$60,000** (the only rule that raises a fee) |
| R5 Bulk @ General Cargo berth | 3,112 | $32,676,000 | $15,560,000 | −$17,116,000 |
| **Total** | | **$298,868,500** | **$272,167,500** | **−$26,701,000 (−8.9%)** |

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

If the MRTIS commit this package was built against changes before those
land, re-export rather than assuming these figures still hold — see
`SESSION_LOG.md`.
