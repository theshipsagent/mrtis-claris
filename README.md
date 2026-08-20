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

Built in session 1 (2026-08-19) — see `SESSION_LOG.md` for the full write-up
and the MRTIS commit this was built against.

1. ✅ A FileMaker-importable export of the validated port-call/fee data —
   [`export/build_review_package.py`](export/build_review_package.py)
   (following the pattern proven in
   `Ships_Register/src/build_filemaker_package.py`), producing CSV +
   FMPXMLRESULT XML + `DATA_DICTIONARY.csv` for `port_call`,
   `port_call_leg`, `port_call_event` in `package/` (not committed — see
   `SESSION_LOG.md`'s "Open" section).
2. ✅ [`docs/BUSINESS_RULES.md`](docs/BUSINESS_RULES.md) — the port-call
   assembly and fee-tier rules, written for a FileMaker developer, not a
   Python one, every rule cited to its MRTIS source.
3. ✅ Sample charts demonstrating the data — [`charts/`](charts/) (fee by
   vessel type, split-call rate, calls by vessel type, §12 fee-tier impact).
4. ✅ Sample canned reports demonstrating reporting capability —
   [`reports/`](reports/) (agency fee by vessel type, port calls by agent,
   R5 general-cargo-bulk drill-down).

## How to work in this project

Read `CLAUDE.md` in full at the start of every session before doing anything else.
