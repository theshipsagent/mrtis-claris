# Sample review package

Built read-only from MRTIS at commit `27d8a1913c6972dcc89289d3bab794e7a1a43854`. Rebuild with:

```
python3 export/build_review_package.py --sample
```

**Going straight to FileMaker? Read [`IMPORT_GUIDE.md`](IMPORT_GUIDE.md) instead** -- which files to import and in what order, how the three tables join, and a checksum table for confirming the import landed. This page is about what the cut *is*: what came, what deliberately did not, and which of its numbers are subtotals.

## Open it first

The six data files are gzipped. On macOS, double-click each in Finder, or
from a terminal in this directory:

```
gunzip -k *.gz
```

`-k` keeps the `.gz` alongside the expanded file so your working copy stays
clean; drop it if you would rather not keep both. Everything then imports
exactly as the full export does -- gzip is transport only, the CSV and XML
inside are untouched.

They are gzipped because this directory is committed to the repo:
**4.2 MB** compressed against 83 MB expanded, a 20x saving.
FMPXMLRESULT repeats a field tag around every single value, which compresses
away almost entirely -- that is what lets a full year of real rows travel
through git at all.

## What this is

A committable subset of the full export, sized so it travels through the
repo rather than by side channel. It exists so a Claris/FileMaker reviewer
can import real rows, wire up the relationships and run a report on day one
(see [`IMPORT_GUIDE.md`](IMPORT_GUIDE.md)), without waiting on a 644 MB transfer.

**Scope: calendar year 2025 (the most recent complete year in the data)** -- selected on `PORT_CALL.call_start`, and selected
on the **call**, never on the leg or the event.

## The one rule that matters

**Whole port calls only.** Every selected call brings all of its legs and all
of its events. Nothing is truncated. A partially-shipped call would show a
reviewer a broken version of the very assembly rules this package exists to
demonstrate -- a split call missing its second leg reads as a single call, and
a leg missing its berth events reads as a leg that never worked cargo.

The build asserts this rather than trusting it. For every call in the sample it
checks that the shipped leg count equals `PORT_CALL.leg_count` and the shipped
event count equals `PORT_CALL.event_count`, that no leg or event points at a
call left behind, and that no event points at a leg left behind. The export
fails rather than writing a sample that would import wrong.

A consequence worth stating: a call that starts inside the window and runs past
it keeps its later events, so event timestamps here run to 2026-05-22,
past the 2025-12-31 end of the window. That is correct, not a leak.
(Events span 2025-01-01 to 2026-05-22.)

## What is in it

| Table | Rows here | Rows in full export |
|---|---:|---:|
| PORT_CALL | 5,483 | 40,170 |
| PORT_CALL_LEG | 5,679 | 41,804 |
| PORT_CALL_EVENT | 35,703 | 290,305 |

Enough of each to exercise the interesting cases:

- 196 split calls (calls with more than one leg)
- 2 non-commercial (lay-up) calls, flagged not deleted
- 7 vessel types, 3,043 distinct vessels
- 5,591 of 5,679 legs carry an agency
- 83 legs with a flagged activity conflict

## What is deliberately not in it

- **Every other year.** The full export covers 2019-01-01 to 2026-07-31; this is one year of it.
- **Unplaced events.** The full export carries 16,969 events that
  belong to no port call at all (`unassigned_reason` = `before_first_entry` or
  `no_open_call`). They have no call, so a whole-calls cut cannot include them.
  A reviewer assessing completeness handling should ask for the full export.

## Numbers in here are subtotals

`ROW_COUNT_RECONCILIATION.md` shows the sample's fee totals **beside** the
full-dataset ones for exactly this reason. The package's published figures are
the full-dataset ones, derived in [`docs/FIGURES.md`](../docs/FIGURES.md); the
charts and reports in this repo are built from the full dataset, not from this
sample. Do not quote a number off this directory.

`DATA_DICTIONARY.csv` describes the same fields as the full export, with the
same wording. Its `null_pct` and `example` columns are computed over the rows
in *this* directory, so a rarely-populated field can read 100% null here while
being populated in the full export.

## The full export

Same script, no flag: `python3 export/build_review_package.py`. It writes
`package/` -- all 3 tables in full, ~644 MB across CSV and XML, gitignored and
shipped on request. Nothing about it changed to make this sample exist.

