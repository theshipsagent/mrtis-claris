# mrtis-claris session log

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

### How to reproduce this build

```
python3 -m venv .venv && .venv/bin/pip install duckdb pandas matplotlib
.venv/bin/python3 export/build_review_package.py
.venv/bin/python3 charts/build_charts.py
.venv/bin/python3 reports/build_reports.py
```

All three scripts open MRTIS's `mrtis.duckdb` `read_only=True` and write only
inside this repo.
