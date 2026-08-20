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

## Deliverables (not yet built — see `CLAUDE.md` for the first session's job)

1. A FileMaker-importable export of the validated port-call/fee data
   (following the pattern already proven in `Ships_Register/src/build_filemaker_package.py`).
2. `docs/BUSINESS_RULES.md` — the port-call assembly and fee-tier rules,
   written for a FileMaker developer, not a Python one.
3. Sample charts/dashboard demonstrating the data.
4. A small set of sample canned reports, demonstrating reporting capability.

## How to work in this project

Read `CLAUDE.md` in full at the start of every session before doing anything else.
