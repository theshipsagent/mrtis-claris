# CLAUDE.md — Operating Manual for This Project

Read this in full at the start of every session, before doing anything else.

## 1. Mission

Turn MRTIS's validated port-call/agency-fee logic into a package a
Claris/FileMaker reviewer can evaluate for compatibility — real importable
data, a plain-language rules spec, sample charts, sample reports. Phase 1
only: proof and evidence, not a native FileMaker build.

## 2. Prime directives

1. **MRTIS is the oracle.** Every business rule in this package must be read
   directly from `/Users/billy/Documents/MRTIS` — its `docs/OPEN_QUESTIONS.md`
   (the rulings, cited by section number), `docs/PORT_CALL_SPEC.md` (the
   assembly rules), and `scripts/build_db.py` / `scripts/build_port_calls.py`
   (the actual implementation, in particular `agency_fee_for()`). Never guess
   or re-derive a rule from first principles — MRTIS has already done that
   work, session by session, with William's explicit rulings. Quote it, cite
   it, don't reinvent it.
2. **Read-only against MRTIS.** Never write to
   `/Users/billy/Documents/MRTIS/data/db/mrtis.duckdb` or any file under
   `/Users/billy/Documents/MRTIS`. Query the database read-only; export from
   it; never mutate it. Same discipline for `/Users/billy/Documents/File Maker/`
   and `/Users/billy/Documents/File Maker Analysis /` — read for context, do
   not edit either.
3. **This is Phase 1: export and evidence, not a rebuild.** Do not write
   native FileMaker scripts, layouts, or relationships. The deliverable is
   data + documentation + visuals a reviewer can look at — the actual
   FileMaker build is a later, explicitly-greenlit phase, consistent with how
   both existing FileMaker projects are scoped.
4. **William is the shipping/business SME, not the technical architect for
   this clone.** He has explicitly delegated the technical approach — when a
   real fork appears, state the options, make a clear recommendation, and
   proceed on the recommendation rather than opening a long clarifying
   round. Stop and ask only when a business-rule fact (not a technical
   choice) is genuinely unknown and MRTIS's docs don't answer it.
   > **Suspended twice on 2026-08-20, and restored both times.** The second was
   > the batch build of the three findings William ruled from his read-through of
   > the raw event rows — I-21, I-22, I-24.1 — which closed
   > `OPEN_QUESTIONS.md` §11.2. MRTIS ends at `95ff34b`. Four findings
   > there remain unruled
   > (I-20, I-23, I-17, I-18b) and each needs a fresh suspension recorded here
   > before any of them is built.
   >
   > **Suspended first on 2026-08-20, and restored the same day.** William
   > directed that the reporting exercise's findings be fixed in MRTIS
   > (*"lets fix the 6 findings"*), so this directive was lifted for that work
   > and that work only, under MRTIS's own standing practice: scratch-copy
   > rebuild and full reverification before the real repo was touched. The work
   > is complete — MRTIS `2738601` → `0c4ed0c`, seven findings closed — and the
   > directive is back in force. See `SESSION_LOG.md` session 9. Anything
   > further in MRTIS needs a fresh, explicit suspension recorded here first.

5. **Leave a trail.** Every session gets a dated entry in `SESSION_LOG.md` —
   create the file on the first session if it doesn't exist yet, matching
   MRTIS's own log style (what was done, what was decided, what's open, what
   next). Record the exact MRTIS git commit (`git -C /Users/billy/Documents/MRTIS rev-parse HEAD`)
   the export was built against, every time it's rebuilt.

## 3. First session's job

1. Confirm the MRTIS commit this package is being built against
   (`git -C /Users/billy/Documents/MRTIS log -1`), and record it.
2. Read `MRTIS/docs/PORT_CALL_SPEC.md` and `MRTIS/docs/OPEN_QUESTIONS.md` §12
   (the agency fee schedule, built and verified 2026-08-19) in full.
3. Write `docs/BUSINESS_RULES.md` here — the port-call assembly rules (what a
   port call and a leg are, how splits work, how activity resolves) and the
   agency fee schedule (all six §12 rules plus the base tiers), in plain
   language for a FileMaker developer with no Python context. Cite the MRTIS
   section/ruling each rule comes from.
4. Adapt the pattern in `Ships_Register/src/build_filemaker_package.py`
   (read it first — it's the proven precedent) into an export script here
   that reads MRTIS's `data/db/mrtis.duckdb` **read-only** and produces a
   FileMaker-importable package (XML/CSV, with a `DATA_DICTIONARY.csv`
   describing every field) of `port_call`, `port_call_leg`, and
   `port_call_event`.
5. Build a small set of sample charts (fee totals by tier, split-call rate,
   calls by vessel type — whatever tells the clearest story) as a shareable
   artifact.
6. Produce 2-3 sample canned reports (e.g. "agency fee by vessel type",
   "port calls by agent") as a concrete demonstration of the reporting
   capability William asked for.
7. Write the `SESSION_LOG.md` entry and update `README.md`'s deliverables
   checklist.

## 4. Session start ritual

1. Read this file in full.
2. Read `README.md`.
3. Read the last 1-2 entries of `SESSION_LOG.md` if it exists.
4. Confirm the MRTIS commit hasn't moved since the last export
   (`git -C /Users/billy/Documents/MRTIS log -1` vs. what's recorded in the
   last session log entry) — if it has, note what changed before trusting
   any previously-exported figures.
5. State the objective for this session, then proceed.
