# Importing this export into Claris / FileMaker

Built read-only from MRTIS at commit `699a9fcdf3f1e6a9b94e29603080ee88b1c756dd`. Every number on this page is derived from the rows in this directory, so it describes the sample you are holding and not some other build.

## Which files to import

Each table ships in two formats, same rows in both:

- **`*.xml.gz` -- FMPXMLRESULT.** FileMaker's own XML grammar. Its `<METADATA>` block names every field and its type, so FileMaker can create the fields for you. **Prefer these.**
- **`*.csv.gz` -- plain CSV.** The same rows with a header row. Use these only if XML import is unavailable to you: you map every field by hand, and everything arrives as text until you set the field types yourself.

Expand them first (`gunzip -k *.gz` in this directory) -- gzip is transport only, and FileMaker reads the expanded file.

## Import parent tables first

1. `PORT_CALL`
2. `PORT_CALL_LEG`
3. `PORT_CALL_EVENT`

Nothing enforces this at import time -- each file is independent. It matters because it lets you build the relationship graph as you go, without a key pointing at a table that does not exist yet.

## The steps

1. Create a new empty file, or open a scratch one.
2. **File -> Import Records -> XML Data Source...**
3. Choose the file option and select `PORT_CALL.xml`. Leave the XSLT stylesheet option **off** -- FMPXMLRESULT is FileMaker's native grammar and needs no transform.
4. In the import dialog, set the target to **New Table**. The fields and their types come from the XML's `<METADATA>` block.
5. Repeat for the other two tables, in the order above.

Importing the CSVs instead: tick **"Don't import first record (contains field names)"** -- row 1 is the header.

> **This section is written from the file format and FileMaker's documented behaviour, not from an import we have watched run.** Nobody on this side has put these files through Claris. The XML is well-formed FMPXMLRESULT and every file parses, but *well-formed* and *imports cleanly* are different claims and only one of them is proven here. If steps 2-4 do not behave as described, that is the single most useful thing you can send back.

## What to check as it lands

- **Timestamps.** 2 fields on `PORT_CALL`, 4 on `PORT_CALL_LEG` and 1 on `PORT_CALL_EVENT` are declared `TIMESTAMP`. Values are written `yyyy-MM-dd HH:mm:ss`, and the XML's `<DATABASE>` element declares `DATEFORMAT="yyyy-MM-dd"` / `TIMEFORMAT="HH:mm:ss"` to match. Confirm they arrive as timestamps and not as text -- this is the likeliest thing to go wrong and the easiest to miss.
- **The `is_*` flags are numbers, not booleans.** `1` / `0`, typed `NUMBER`.
- **Empty means empty.** MRTIS leaves a value NULL wherever no evidence supports it, rather than guessing -- see [`docs/BUSINESS_RULES.md`](../docs/BUSINESS_RULES.md) section 1. Those arrive as empty fields. Do not auto-enter `0` into them: a blank `activity` means "nothing could say", which is not the same as `No Cargo`.
- **Do not key anything on `vessel_key`.** It is assigned by row position at MRTIS build time and changes on every rebuild. `port_call_id`, `leg_id` and `imo` are content-derived and stable. (Also flagged in `DATA_DICTIONARY.csv`.)

## How the three tables relate

| Parent | Field | Child | Field | Cardinality |
|---|---|---|---|---|
| `PORT_CALL` | `port_call_id` | `PORT_CALL_LEG` | `port_call_id` | 1 : 1-2 |
| `PORT_CALL_LEG` | `leg_id` | `PORT_CALL_EVENT` | `leg_id` | 1 : many |
| `PORT_CALL` | `port_call_id` | `PORT_CALL_EVENT` | `port_call_id` | 1 : many (shortcut) |

The third relationship is a convenience -- it lets a call-level layout reach its whole event stream without going through legs. It is redundant, not contradictory: an event's `port_call_id` always agrees with its leg's.

Facts this build **asserts** before writing the files, so the map above cannot quietly go stale:

- `PORT_CALL.port_call_id` (5,483 rows), `PORT_CALL_LEG.leg_id` (5,679) and `PORT_CALL_EVENT.event_key` (35,703) are each unique. They are the primary keys.
- No orphans in either direction: every leg resolves to a call, and every placed event resolves to both a call and a leg.
- An event is **either** fully placed (it has a call *and* a leg) **or** fully unplaced (it has neither). There is no third state, so `leg_id` being empty always means `port_call_id` is empty too.
- `leg_id` is `port_call_id` + `-L` + `leg_seq` (e.g. `1012919-202501270659-L1`), so the child key is derivable from the parent key and the sequence number.

This export carries **no unplaced events** -- it is whole port calls only, so every event here joins. (The full export carries events belonging to no call at all; see `SAMPLE_README.md`.)

## Check the import landed

Run these against the imported tables before you trust anything you build on them. They take two minutes and they catch a silently truncated import, which otherwise looks exactly like real data.

| Check | Expected |
|---|---:|
| Records in `PORT_CALL` | 5,483 |
| Records in `PORT_CALL_LEG` | 5,679 |
| Records in `PORT_CALL_EVENT` | 35,703 |
| Distinct `PORT_CALL::port_call_id` | 5,483 (equal to its record count -- the key is unique) |
| Calls with `is_commercial_call = 1` | 5,481 |
| Calls carrying a fee (`agency_fee_total` not empty) | 5,125 |
| Chargeable legs (`agency_fee` not empty) | 5,321 |
| Sum of `PORT_CALL_LEG::agency_fee` | $36,544,500 |
| Sum of `PORT_CALL::agency_fee_total` | $36,544,500 |
| Earliest `PORT_CALL::call_start` | 2025-01-01 01:06 |
| Latest `PORT_CALL::call_start` | 2025-12-31 23:53 |

**The two fee sums must match each other.** They are the same money counted two ways -- once from the legs, once from the roll-up already stored on the call. If they agree after import, the parent-child link survived the trip, which is the thing most worth knowing on day one.

That figure is the **billable** basis. `PORT_CALL_EVENT::agency_fee` is a different, deliberately frozen per-departure basis that sums to something larger and is not what bills -- [`docs/BUSINESS_RULES.md`](../docs/BUSINESS_RULES.md) section 9.1 explains why both exist. Do not report it as revenue.

> Every figure on this page is a subtotal of this sample, not the package's published figure. See `SAMPLE_README.md`.

