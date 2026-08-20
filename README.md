# MRTIS → Claris/FileMaker Review Package

**Status:** Phase 1 — Export & Review Package · **Mode:** Build deliverables for review; do not touch any live platform
**Owner:** William · **Started:** 2026-08-19

---

## What this is

MRTIS (`/Users/billy/Documents/MRTIS`) is a Python/DuckDB pipeline that assembles
river port-call and agency-fee data from raw Zone Report events, and has been
the place where the *correct* business rules — the port-call/leg assembly
logic, the agency fee schedule — were worked out and validated, ruling by
ruling, session by session.

This repo turns that validated logic into something a Claris/FileMaker
reviewer can actually evaluate: real data they can import and browse, the
business rules written up in plain language (not Python), and sample
charts/reports demonstrating what it produces. It is **not** a native
FileMaker rebuild — no FileMaker scripts or layouts get written here. It
stops at "here is proof this works, packaged for review."

## Relationship to other projects

- **`MRTIS`** (sibling repo) — the source of truth. Everything in this repo is
  read *from* MRTIS, never written *to* it. If MRTIS's rules change, this
  package needs re-syncing — the export step should record the exact MRTIS
  commit it was built against.
- **`/Users/billy/Documents/File Maker/`** — the internal "Vessel Operating
  Platform — Evaluation & Redesign" project. Currently Phase 1 (teardown of
  the current platform), info-only, no build yet. This package is meant to
  feed its `02_DESIGN_NEW/` forward-looking design work as evidence of what a
  correct port-call/fee model looks like — not to jump ahead of its own
  governance.
- **`/Users/billy/Documents/File Maker Analysis /`** — the independent audit
  of Blue Water Shipping's live FileMaker Agency Platform. This package's
  plain-language business-rules spec may also be useful evidence there.

## Deliverables

Built in session 1, re-exported in session 3, re-derived end-to-end in
session 4 (all 2026-08-19), made deliverable in session 5 and made
reviewer-ready in session 6 (both 2026-08-20) — see `SESSION_LOG.md` for the
full write-up and the MRTIS commit this was built against.

> **Every published figure is derived, not hand-keyed.**
> [`figures.py`](figures.py) re-derives every count, percentage and dollar
> figure live from MRTIS and writes [`docs/FIGURES.md`](docs/FIGURES.md); the
> rules doc, charts and reports all read from that one derivation. It also
> re-implements the §12 fee schedule independently and asserts, leg by leg,
> that it reproduces the fee MRTIS actually stored — currently **0 mismatches
> across 40,245 chargeable legs**. Re-run it after any MRTIS rebuild and the
> whole package moves together.

1. ✅ A FileMaker-importable export of the validated port-call/fee data —
   [`export/build_review_package.py`](export/build_review_package.py)
   (following the pattern proven in
   `Ships_Register/src/build_filemaker_package.py`), producing CSV +
   FMPXMLRESULT XML + `DATA_DICTIONARY.csv` for `port_call`,
   `port_call_leg`, `port_call_event`. Two modes — see **How a reviewer
   receives this** below.
2. ✅ [`docs/BUSINESS_RULES.md`](docs/BUSINESS_RULES.md) — the port-call
   assembly and fee-tier rules, written for a FileMaker developer, not a
   Python one, every rule cited to its MRTIS source. Current as of the
   post-rebuild rules (first-working-berth R5, layberth as non-commercial
   time, lay-up flagging, unresolved-outranks-`No Cargo`). Closes with a
   glossary of the shipping vocabulary the rules are written in — SWP,
   layberth, FGIS, TPC, dry bulk — since a Claris developer has no reason to
   arrive knowing it.
3. ✅ Sample charts demonstrating the data — [`charts/`](charts/) (fee by
   vessel type, split-call rate, calls by vessel type, §12 fee-tier impact).
4. ✅ Sample canned reports demonstrating reporting capability —
   [`reports/`](reports/) (agency fee by vessel type, port calls by agent,
   R5 general-cargo-bulk drill-down).
5. ✅ [`figures.py`](figures.py) → [`docs/FIGURES.md`](docs/FIGURES.md) — the
   single derivation every other deliverable reads from, with the fee-rule
   attribution self-check described above.

## How a reviewer receives this

The full export is 644 MB, which is why it stayed undeliverable through three
sessions. It now ships two ways, from the one script:

| | [`sample/`](sample/) — committed | `package/` — on request |
|---|---|---|
| Build | `python3 export/build_review_package.py --sample` | `python3 export/build_review_package.py` |
| Scope | calendar year 2025 — 5,483 calls, 5,679 legs, 35,703 events | everything — 40,170 / 41,804 / 290,305 |
| Size | 4.2 MB gzipped (83 MB expanded) | 644 MB, gitignored |
| For | opening on day one: import, relationships, a report | completeness, edge cases, the unplaced-event stream |

Both modes now write an **`IMPORT_GUIDE.md`** alongside the data: which of the
two formats to import and in what order, the three-table relationship map
(with the key uniqueness and no-orphan claims *asserted* by the build, not
just described), what to check as the rows land, and a checksum table for
confirming the import arrived whole. It is explicit that the FileMaker steps
come from the file format and FileMaker's documentation rather than from an
import this repo has watched run — that remains the one thing this package
cannot verify for itself, and the guide asks the reviewer to report back on
exactly it.

**The sample is whole port calls only** — every selected call brings all of its
legs and all of its events, and the build *asserts* that per call rather than
assuming it. A truncated event stream would show a reviewer a broken version of
the very assembly rules this package exists to demonstrate.
[`sample/SAMPLE_README.md`](sample/SAMPLE_README.md) states exactly what the cut
includes, what it deliberately excludes, and which of its numbers are subtotals
rather than the published figures — read it to know what you are holding, and
[`sample/IMPORT_GUIDE.md`](sample/IMPORT_GUIDE.md) to get it into FileMaker.

Both modes emit rows in an explicit, total key order, so a rebuild against an
unchanged MRTIS is byte-identical and the committed sample never churns.

## How to work in this project

Read `CLAUDE.md` in full at the start of every session before doing anything else.
