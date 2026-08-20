# Report concepts — an exercise, not a deliverable

**Status:** in progress · **Opened:** 2026-08-20 (session 8) · **Window:** 2023-08-01 → 2026-07-31

## What this folder is

Concept/sample reports built to **test what can actually be pulled** out of the
validated MRTIS port-call data, and to surface the mistakes, gaps and changes
that testing exposes. The reports are the means; [`ISSUES.md`](ISSUES.md) — the
running defect log — is as much the point as the reports themselves. When the
set is complete, that log is carried into a separate build-fix session.

## What this folder is *not*

- **Not part of the Claris review package.** The deliverable reports live in
  [`../reports/`](../reports/) and are listed in the README's deliverables
  checklist. Nothing here is. A concept report must never be mistaken for one
  the reviewer has been handed.
- **Not a change to anything.** Nothing here writes to MRTIS's database, and
  nothing here alters the existing export, sample, charts or reports. The
  exercise is read-and-observe; fixes happen later, deliberately, in their own
  session.
- **Not the full history.** Ruled by William 2026-08-20: three years is enough
  for this exercise.

## The window

Trailing 36 months anchored on the **data's** last date (`max(call_end)` =
2026-07-31), not on wall-clock today: **2023-08-01 → 2026-07-31**.

Anchoring to today would make every figure drift on re-run and break the
byte-identical reproducibility the rest of this repo holds to. The anchor is
stated in every report header so a reader always knows which 36 months they
are looking at.

Scale of the window: **16,256 port calls · 16,886 legs · 16,179 chargeable ·
$110,318,250 billable fee** — 40.5% of the all-time $272,660,000.

## Discipline that still applies in full

Proof of concept describes the *audience*, not the rigour (William,
2026-08-20). Every figure here is derived by script from MRTIS, never
hand-keyed, and every report states the MRTIS commit it was built against.
