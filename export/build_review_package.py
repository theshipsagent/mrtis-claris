#!/usr/bin/env python3
"""Build a Claris/FileMaker-ready review package from MRTIS's port-call layer.

Adapted from the proven pattern in
/Users/billy/Documents/Ships_Register/src/build_filemaker_package.py -- same
shape (FIELD_SPEC declares column order/type/description, CSV + FMPXMLRESULT
XML per table, an asserted DATA_DICTIONARY.csv, a row-count reconciliation),
applied to MRTIS's `port_call`, `port_call_leg`, and `port_call_event` tables
instead of the ships register.

READ-ONLY against MRTIS. Opens data/db/mrtis.duckdb with read_only=True and
never writes to it, per CLAUDE.md's prime directive #2. Also records the exact
MRTIS git commit this export was built against, since that commit is what
docs/BUSINESS_RULES.md's rule citations and dollar figures are pinned to.

Two modes:

  * default -- the FULL export (every row of all three tables). ~644 MB, so it
    is gitignored and shipped on request, not through the repo.
  * --sample -- a committable subset: WHOLE port calls only, with every one of
    their legs and events intact. Never a truncated event stream; a partial
    call would break the very assembly rules this package exists to
    demonstrate. This is what a reviewer opens first.

Usage:
    python3 export/build_review_package.py
    python3 export/build_review_package.py --sample
    python3 export/build_review_package.py --sample --sample-start 2025-07-01 --sample-end 2026-01-01
    python3 export/build_review_package.py --mrtis-db /path/to/mrtis.duckdb --out package/
"""

from __future__ import annotations

import argparse
import csv
import gzip
import shutil
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

import duckdb
import pandas as pd

MRTIS_ROOT = Path("/Users/billy/Documents/MRTIS")
DEFAULT_DB = MRTIS_ROOT / "data" / "db" / "mrtis.duckdb"

# DuckDB type -> FileMaker FMPXMLRESULT field type.
# FileMaker has no native boolean; DuckDB BOOLEAN columns are exported as
# NUMBER (1/0), the conventional FileMaker representation.
DUCKDB_TO_FM_TYPE = {
    "VARCHAR": "TEXT",
    "BIGINT": "NUMBER",
    "INTEGER": "NUMBER",
    "DOUBLE": "NUMBER",
    "BOOLEAN": "NUMBER",
    "TIMESTAMP": "TIMESTAMP",
}

# ---------------------------------------------------------------------------
# Field descriptions, one dict per table. Column order and DuckDB type are
# read live from the database at run time (so this script never drifts from
# the schema silently) -- these dicts supply only the human-readable
# description for DATA_DICTIONARY.csv. Wording follows
# MRTIS/sql/schema_port_call.sql's column comments and docs/PORT_CALL_SPEC.md.
# A column present in the DB but missing here fails loudly at run time rather
# than shipping an undocumented field.
# ---------------------------------------------------------------------------

PORT_CALL_DESC = {
    "port_call_id": "Primary key: '<imo|NONAME:name>-<YYYYMMDDHHMM of first event>'.",
    "vessel_key": "Internal MRTIS join key. WARNING -- NOT a stable identity: it is assigned by row position at build time, so it changes on every MRTIS rebuild. Do NOT key a FileMaker file on it; use imo, or port_call_id/leg_id, which are content-derived and stable. (MRTIS OPEN_QUESTIONS.md section 10 tracks making these stable; approved, not yet built.)",
    "imo": "Canonical 7-digit IMO number.",
    "vessel_name": "Vessel's current/canonical name.",
    "call_name": "Name actually carried on this call's source events (may differ from vessel_name if renamed since).",
    "vessel_type": "Canonical vessel type (Bulk/Container/Gas/Other/Passenger/Reefer/Tanker), from the Zone Report's own Type field.",
    "ship_type": "Ships register's raw, fine-grained type (e.g. 'Container Ship (Fully Cellular)'). Drives the R1-R4 fee tiers.",
    "ship_type_group": "Ships register's size-bucketed group within a type family (e.g. 'Bulk Carrier-Handymax').",
    "dwt": "Deadweight tonnage, from the ships register.",
    "tpc": "Tonnes per centimetre immersion, from the ships register. CAUTION: 0 appears on ~10% of calls and is stored as a literal zero, not a blank -- it is a placeholder for 'not available' in the upstream register, not a measured value. Filter tpc > 0 before any draft-survey calculation. (MRTIS OPEN_QUESTIONS.md section 11.3; the fix belongs upstream in Ships_Register and is deferred.)",
    "call_start": "Timestamp of the call's first event (the SWP entry, when the call is complete).",
    "call_end": "Timestamp of the call's last event (the SWP exit, when complete).",
    "call_hours": "call_end minus call_start, in hours.",
    "call_status": "'complete' (both SWP ends present) / 'open_start' / 'open_end' / 'fragment'. Only 'complete' calls have reliable duration figures.",
    "is_complete": "1 if call_status = 'complete', else 0.",
    "leg_count": "Number of legs in this call. 1 = single call, 2+ = split call.",
    "is_split": "1 if leg_count > 1.",
    "is_commercial_call": "FILTER ON THIS BY DEFAULT for any count or fee report. 0 marks a non-commercial call -- every berth visit was layberth (lay-up/repair), so it does not count as a port call and accrues no fee. The row, its events and its timestamps are all kept so the elapsed time is never lost. A call that never reached a berth at all is a different category and stays 1. See docs/BUSINESS_RULES.md section 5.",
    "call_class": "Names why: 'commercial' or 'layup'. Today layup is the only non-commercial class; it is built as a general classification so other non-commercial cases can join it later.",
    "berth_stop_count": "Count of real, non-artifact, NON-LAYBERTH berth stops across the whole call -- i.e. actual cargo work. A pure lay-up call reads 0 here, same as a call that never berthed; tell those apart by layberth_hours > 0, not by this column.",
    "layberth_hours": "Hours alongside a layberth (lay-up/repair wharf) across the whole call -- real elapsed time, excluded from berth_hours and from every count and fee. Summed from this call's legs.",
    "anchorage_stop_count": "Count of anchorage stops across the whole call.",
    "event_count": "Total raw events (port_call_event rows) belonging to this call.",
    "entry_draft_ft": "Draft in feet at the SWP entry crossing. NULL if no Enter event was recorded.",
    "exit_draft_ft": "Draft in feet at the SWP exit crossing. NULL if no Exit event was recorded.",
    "agency": "Canonical agency for the call -- the inbound agency (the one that brought the vessel in).",
    "agency_fee_total": "BILLABLE FIGURE. Sum of this call's legs' agency_fee (one fee per leg that reached a berth). See docs/BUSINESS_RULES.md section 9.",
    "agency_fee_departures_total": "Comparison-only figure: what this call would total under the old per-departure-charges-every-sailing basis. Not the billing figure.",
    "fgis_record_count": "Count of FGIS grain certificates tied to this call.",
    "estimated_tons": "FGIS certified metric tons, summed across the call's legs. An ESTIMATE per William's original mapping, not a certified actual weight.",
    "actual_tons": "Reserved for a genuinely certified/actual tonnage. NULL everywhere today -- no source wired in yet.",
}

PORT_CALL_LEG_DESC = {
    "leg_id": "Primary key: '<port_call_id>-L<n>'.",
    "port_call_id": "Foreign key to port_call.",
    "leg_seq": "1-based sequence of this leg within its call.",
    "leg_count": "Legs in the parent call (denormalized for convenience -- same as port_call.leg_count).",
    "vessel_key": "Internal MRTIS join key -- NOT a stable identity; see the PORT_CALL.vessel_key note. Do not key a FileMaker file on it.",
    "leg_start": "Timestamp of the leg's first event.",
    "leg_end": "Timestamp of the leg's last event.",
    "leg_hours": "leg_end minus leg_start, in hours.",
    "activity": "'Load' / 'Discharge' / 'No Cargo' / blank (unresolved -- never guessed). Real activity wins first; below that an UNRESOLVED stop outranks 'No Cargo', so a layberth stop elsewhere in the leg cannot overwrite an honest 'we don't know'. Only a leg of nothing but layberth stops reports 'No Cargo'. See docs/BUSINESS_RULES.md section 4.",
    "activity_method": "How activity was decided: 'dictionary' / 'fgis' / 'draft_delta' / 'unresolved', tried in that priority order.",
    "activity_conflict": "1 if the dictionary/FGIS evidence and the draft delta disagreed. Flagged, never silently overridden.",
    "activity_conflict_reason": "'draft' or 'fgis' -- which two sources disagreed.",
    "draft_delta_ft": "Sailing draft minus arrival draft at the leg's berth work, in feet.",
    "berth_stop_count": "Real, non-artifact, NON-LAYBERTH berth stops in this leg -- i.e. actual cargo work. A pure lay-up leg reads 0; distinguish it from a leg that never berthed by layberth_hours > 0.",
    "geofence_artifact_events": "Berth events in this leg that are neither the first docking nor the last sailing of their visit -- AIS/geofence noise, not operations.",
    "first_berth_zone": "Raw source zone name of the leg's first WORKING berth stop. Layberth stops are skipped when resolving this, so a vessel that lays up before working cargo reports the berth where the work actually happened.",
    "first_berth_facility": "Canonical facility name of the leg's first WORKING (non-layberth) berth stop.",
    "facility_type": "Facility type of the leg's first WORKING (non-layberth) berth stop (Elevator / Tank Storage / General Cargo / etc). Decides fee rule R5 -- so a bulk carrier that lays up at a repair yard before loading at an elevator is priced from the elevator, not the repair yard. Falls back to the literal first stop only when every stop in the leg is layberth.",
    "berth_arrive_time": "Arrival timestamp at the leg's first berth.",
    "berth_depart_time": "Sailing timestamp from the leg's last berth.",
    "waiting_hours": "Anchorage dwell BEFORE the leg's first berth arrival only -- the only figure that means 'waiting for a berth'.",
    "inter_berth_idle_hours": "Dwell between the leg's berth arrival and its last sailing.",
    "outbound_idle_hours": "Dwell after the leg's last sailing -- the vessel departing, not waiting on a dock.",
    "berth_hours": "Hours alongside doing real, non-layberth cargo work. Layberth dwell is reported separately in layberth_hours, so a 'days alongside' or berth-productivity figure is never inflated by a repair-yard stay.",
    "layberth_hours": "Hours alongside a layberth (lay-up/repair wharf) on this leg -- real elapsed time, but not cargo work, so it is held here rather than folded into berth_hours. 0 for a leg with no layberth stop.",
    "agency": "Canonical agency for this leg (the inbound agency of this leg specifically).",
    "agency_source": "Where the leg's agency was determined from: 'inbound' / 'leg' / 'call' / 'none'.",
    "agent_changed_in_leg": "1 if the source data showed more than one distinct agency inside this leg.",
    "cargo_group": "From FGIS ('Grain'), else the zone dictionary's typical cargo group for the first berth.",
    "cargo": "FGIS grain/grain class, where certified.",
    "cargo_source": "'fgis' / 'dictionary' / blank.",
    "destination": "FGIS-declared destination (export legs only).",
    "estimated_tons": "FGIS certified metric tons for this leg. An ESTIMATE, not certified actual weight -- do not sum across the leg's individual event rows.",
    "actual_tons": "Reserved for certified/actual tonnage. NULL everywhere today.",
    "fgis_record_count": "Count of FGIS certificates tied to this leg.",
    "agency_fee": "BILLABLE FIGURE. One fee per leg that reached a berth, priced per docs/BUSINESS_RULES.md section 9's tier rules. NULL if the leg never berthed, or the vessel has no usable identity/type (a tug or government craft).",
    "agency_fee_departures": "Comparison-only: what this leg would total charging every berth departure (the old, frozen basis). Not the billing figure.",
}

PORT_CALL_EVENT_DESC = {
    "event_key": "Primary key, 1:1 with MRTIS's fact_zone_event -- every raw source event has exactly one row here, always, including events that couldn't be placed in a call.",
    "port_call_id": "Foreign key to port_call. NULL when the event could not be placed (see unassigned_reason).",
    "leg_id": "Foreign key to port_call_leg. NULL when unplaced.",
    "leg_seq": "Sequence of the leg this event belongs to, within its call.",
    "event_seq": "1-based position of this event within its call, in time order.",
    "unassigned_reason": "Why this event has no call: 'before_first_entry' (export window opens mid-voyage) or 'no_open_call' (no Enter was ever recorded). Blank when the event is placed.",
    "vessel_key": "Internal MRTIS join key -- NOT a stable identity; see the PORT_CALL.vessel_key note. Do not key a FileMaker file on it.",
    "src_imo": "IMO exactly as exported in the source Zone Report row.",
    "imo": "Canonical 7-digit IMO.",
    "vessel_name": "Vessel name carried on this specific event.",
    "src_vessel_type": "Type exactly as exported (often blank).",
    "vessel_type": "Canonical vessel type, back-filled from the vessel where the source row itself was blank.",
    "ship_type": "Ships register's raw, fine-grained type.",
    "ship_type_group": "Ships register's size-bucketed group.",
    "dwt": "Deadweight tonnage, from the ships register.",
    "tpc": "Tonnes per centimetre immersion, from the ships register.",
    "src_action": "Action exactly as exported: Arrive / Depart / Enter / Exit.",
    "action": "Canonical action label: Arrived/Sailed at a berth, Anchor/Weigh Anchor at anchorage, Enter/Exit at the pilot station.",
    "event_time": "Timestamp of the event, unchanged from source (military time).",
    "src_zone": "Zone exactly as exported.",
    "berth": "The zone, relabelled (e.g. 'SWP Cross' becomes In/Out by direction).",
    "facility": "Canonical facility name (e.g. multiple 'Shell Norco' berth zones collapse to one facility).",
    "facility_type": "Facility type: Elevator / Tank Storage / General Cargo / Anchorage / Pilot Station / etc.",
    "src_mile": "Mile marker exactly as parsed off the source row.",
    "mile": "Canonical mile for the zone.",
    "draft_ft": "Draft in feet, from the source 'Draft FT' field.",
    "src_agent": "Agent exactly as exported (blank stays blank here).",
    "agency": "Canonical agency of the raw agent, per the agent dictionary. Row-level, NOT the leg-owning agency -- see agency_leg.",
    "agency_leg": "THE COLUMN TO USE FOR REPORTING. The leg's inbound agency, applied to every event of that leg -- fills source blanks and corrects a known pilot-sheet artefact. See docs/BUSINESS_RULES.md section 6.",
    "agency_normalized": "1 where agency_leg differs from this row's own raw agency.",
    "berth_stop_seq": "Which berth stop of the call this event belongs to.",
    "is_berth_stop": "1 if this event is a berth arrival/departure.",
    "is_geofence_artifact": "1 for a berth event that is neither the first docking nor the last sailing of its visit -- AIS/geofence noise, kept on the spine but not read as a real operation.",
    "is_anchorage": "1 if this event is an anchorage event.",
    "is_waiting_time": "1 on an anchorage event that sits before the leg's first berth arrival -- i.e. counts as waiting for that berth.",
    "dwell_hours": "On an Arrive/Anchor row: hours until the matching Depart.",
    "hours_since_prev": "Gap in hours from the previous event of the call.",
    "activity": "Carried down from the leg: 'Load' / 'Discharge' / 'No Cargo' / blank.",
    "activity_method": "Carried down from the leg: how activity was decided.",
    "cargo_group": "Carried down from the leg.",
    "cargo": "Carried down from the leg.",
    "destination": "Carried down from the leg.",
    "estimated_tons": "Carried down from the leg -- a LEG TOTAL. Do not sum across a leg's individual event rows.",
    "actual_tons": "Carried down from the leg. NULL everywhere today.",
    "call_status": "Carried down from the call: 'complete' / 'open_start' / 'open_end' / 'fragment'.",
    "is_split_call": "1 if the parent call has more than one leg.",
    "agency_fee": "COMPARISON-ONLY. The old per-departure fee for this specific sailing, unchanged. NOT the billable figure -- that lives on port_call_leg.agency_fee. Summing this column instead of the billable one over-states the total by about 28% on the current build -- see package/ROW_COUNT_RECONCILIATION.md, which re-derives both bases on every export rather than quoting a figure here that goes stale.",
}

TABLES = [
    ("port_call", "PORT_CALL", PORT_CALL_DESC),
    ("port_call_leg", "PORT_CALL_LEG", PORT_CALL_LEG_DESC),
    ("port_call_event", "PORT_CALL_EVENT", PORT_CALL_EVENT_DESC),
]

# Explicit, total row order per table. DuckDB does not promise a stable order
# for an unordered SELECT, and the sample is COMMITTED -- without this, a
# rebuild against an unchanged MRTIS could reshuffle every row and churn the
# whole file for no reason. Each ordering is verified unique: port_call_id is
# the port_call PK, (port_call_id, leg_seq) is unique on legs, and event_key is
# a unique BIGINT that totalises the event order even where port_call_id and
# event_seq are NULL (the unplaced events). Ordering events by call and then by
# sequence also happens to be the order a reviewer wants to read them in.
ORDER_BY = {
    "port_call": "port_call_id",
    "port_call_leg": "port_call_id, leg_seq",
    "port_call_event": "port_call_id NULLS LAST, event_seq NULLS LAST, event_key",
}


def mrtis_commit() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(MRTIS_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"Could not determine MRTIS git commit: {exc}")


def load_table(con: duckdb.DuckDBPyConnection, table: str, desc: dict) -> tuple[pd.DataFrame, list[tuple]]:
    """Read a table's live schema and data, and build its FIELD_SPEC.

    Column order and DuckDB type come straight from the database, so this
    export can never silently drift from schema_port_call.sql. A column with
    no entry in `desc` fails loudly -- an undocumented field should never
    ship in the reviewer's data dictionary.
    """
    cols = con.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = ? ORDER BY ordinal_position", [table]
    ).fetchall()
    missing = [c for c, _ in cols if c not in desc]
    if missing:
        raise SystemExit(f"{table}: no description for column(s) {missing} -- update *_DESC in this script.")
    spec = []
    for col, dtype in cols:
        fm_type = DUCKDB_TO_FM_TYPE.get(dtype)
        if fm_type is None:
            raise SystemExit(f"{table}.{col}: unmapped DuckDB type '{dtype}' -- add it to DUCKDB_TO_FM_TYPE.")
        spec.append((col, fm_type, desc[col]))
    df = con.execute(f"SELECT * FROM {table} ORDER BY {ORDER_BY[table]}").fetchdf()
    return df, spec


def coerce_booleans(df: pd.DataFrame, spec: list[tuple]) -> pd.DataFrame:
    """DuckDB BOOLEAN -> FileMaker NUMBER (1/0), per DUCKDB_TO_FM_TYPE's note."""
    for col, _, _ in spec:
        if df[col].dtype == bool or str(df[col].dtype) == "boolean":
            df[col] = df[col].map({True: 1, False: 0, pd.NA: None})
    return df


def write_csv(df: pd.DataFrame, fields: list[str], path: Path) -> None:
    df[fields].to_csv(path, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")


def write_fmpxmlresult(df: pd.DataFrame, spec: list[tuple], table_name: str, path: Path) -> None:
    fields = [f for f, _, _ in spec]
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        '<FMPXMLRESULT xmlns="http://www.filemaker.com/fmpxmlresult">',
        "<ERRORCODE>0</ERRORCODE>",
        f'<DATABASE DATEFORMAT="yyyy-MM-dd" LAYOUT="{escape(table_name)}" NAME="{escape(table_name)}" '
        f'RECORDS="{len(df)}" TIMEFORMAT="HH:mm:ss" />',
        "<METADATA>",
    ]
    for name, ftype, _ in spec:
        lines.append(f'<FIELD EMPTYOK="YES" MAXREPEAT="1" NAME="{escape(name)}" TYPE="{ftype}"/>')
    lines.append("</METADATA>")
    lines.append(f'<RESULTSET FOUND="{len(df)}">')
    for row in df[fields].itertuples(index=False):
        lines.append('<ROW MODID="1" RECORDID="1">')
        for val in row:
            if val is None or pd.isna(val):
                lines.append("<COL><DATA></DATA></COL>")
            elif hasattr(val, "isoformat"):
                lines.append(f"<COL><DATA>{escape(val.isoformat(sep=' '))}</DATA></COL>")
            else:
                lines.append(f"<COL><DATA>{escape(str(val))}</DATA></COL>")
        lines.append("</ROW>")
    lines.append("</RESULTSET>")
    lines.append("</FMPXMLRESULT>")
    path.write_text("\n".join(lines), encoding="utf-8")


def gzip_in_place(path: Path) -> Path:
    """Replace `path` with `path.gz`, deterministically.

    mtime=0 and no stored filename, so identical input always produces
    identical bytes -- a rebuild against an unchanged MRTIS leaves the
    committed sample untouched rather than churning it. FMPXMLRESULT repeats
    a field tag around every value, so it compresses ~33x on its own and ~20x
    across the package -- which is what lets a full year of real rows live in
    the repo at all. The sample guide derives both figures from the files it
    just wrote rather than quoting these.
    """
    out = path.with_suffix(path.suffix + ".gz")
    with path.open("rb") as src, out.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as dst:
            shutil.copyfileobj(src, dst)
    path.unlink()
    return out


def resolve_sample_window(calls: pd.DataFrame, start: str | None, end: str | None):
    """Decide the sample's window: the most recent COMPLETE calendar year in
    the data, unless both --sample-start and --sample-end are given.

    Derived from the data, never hard-coded, so the sample rolls forward on
    its own as MRTIS's export window advances. Returns a half-open interval
    [lo, hi) on call_start, plus a one-line description for the docs.
    """
    if start or end:
        if not (start and end):
            raise SystemExit("--sample-start and --sample-end must be given together.")
        lo, hi = pd.Timestamp(start), pd.Timestamp(end)
        if lo >= hi:
            raise SystemExit(f"--sample-start {lo.date()} is not before --sample-end {hi.date()}.")
        return lo, hi, f"explicit window {lo.date()} <= call_start < {hi.date()}"

    first, last = calls["call_start"].min(), calls["call_start"].max()
    # A year is complete only if the data actually runs to its 31 December.
    year = last.year if (last.month, last.day) == (12, 31) else last.year - 1
    lo, hi = pd.Timestamp(year=year, month=1, day=1), pd.Timestamp(year=year + 1, month=1, day=1)
    if first > lo:
        raise SystemExit(
            f"Data starts {first.date()}, so calendar year {year} is not fully covered. "
            "Pass --sample-start/--sample-end explicitly."
        )
    return lo, hi, f"calendar year {year} (the most recent complete year in the data)"


def filter_to_sample(frames: dict, lo, hi) -> dict:
    """Cut the frames down to WHOLE port calls whose call_start falls in
    [lo, hi) -- every leg and every event of each selected call comes with it.

    Selection is on the CALL, never on the leg or event. A call that starts in
    the window and runs past it keeps all of its events, including the ones
    dated outside the window: a truncated event stream would break the
    assembly rules this package exists to demonstrate.

    Every invariant below is asserted rather than assumed. All five hold on
    the full dataset, so a failure here means the cut is wrong, not the data.
    """
    calls = frames["PORT_CALL"]
    kept = calls[(calls["call_start"] >= lo) & (calls["call_start"] < hi)].copy()
    if kept.empty:
        raise SystemExit(f"No port calls with {lo.date()} <= call_start < {hi.date()}.")
    ids = set(kept["port_call_id"])

    legs = frames["PORT_CALL_LEG"]
    legs = legs[legs["port_call_id"].isin(ids)].copy()
    events = frames["PORT_CALL_EVENT"]
    events = events[events["port_call_id"].isin(ids)].copy()

    # 1. every sampled call brought its legs, and exactly leg_count of them
    got = legs.groupby("port_call_id").size()
    want = kept.set_index("port_call_id")["leg_count"]
    bad = want[want != got.reindex(want.index).fillna(0).astype(int)]
    if len(bad):
        raise SystemExit(f"Sample integrity: {len(bad)} call(s) have the wrong leg count, e.g. {bad.index[0]}.")

    # 2. every sampled call brought its events, and exactly event_count of them
    got = events.groupby("port_call_id").size()
    want = kept.set_index("port_call_id")["event_count"]
    bad = want[want != got.reindex(want.index).fillna(0).astype(int)]
    if len(bad):
        raise SystemExit(f"Sample integrity: {len(bad)} call(s) have the wrong event count, e.g. {bad.index[0]}.")

    # 3. no leg or event points at a call that did not come along
    if not set(legs["port_call_id"]) <= ids:
        raise SystemExit("Sample integrity: a leg references a port call outside the sample.")
    if not set(events["port_call_id"].dropna()) <= ids:
        raise SystemExit("Sample integrity: an event references a port call outside the sample.")

    # 4. every event's leg came along too
    orphans = set(events["leg_id"].dropna()) - set(legs["leg_id"])
    if orphans:
        raise SystemExit(f"Sample integrity: {len(orphans)} event(s) reference a leg outside the sample.")

    # 5. unplaced events (port_call_id NULL) belong to no call, so none can be here
    if events["port_call_id"].isna().any():
        raise SystemExit("Sample integrity: an unplaced event was selected; the sample is whole calls only.")

    return {"PORT_CALL": kept, "PORT_CALL_LEG": legs, "PORT_CALL_EVENT": events}


def write_sample_readme(out: Path, frames: dict, full: dict, window, commit: str,
                        compress: bool, expanded_bytes: int) -> None:
    """The one page a reviewer reads before importing the sample.

    Its whole job is to make the cut impossible to misread: what came, what
    deliberately did not, and which numbers here are subtotals rather than the
    package's published figures.
    """
    lo, hi, window_desc = window
    gz_bytes = sum(f.stat().st_size for f in out.glob("*.gz"))
    calls, legs, events = frames["PORT_CALL"], frames["PORT_CALL_LEG"], frames["PORT_CALL_EVENT"]
    ev_lo, ev_hi = events["event_time"].min(), events["event_time"].max()

    lines = [
        "# Sample review package", "",
        f"Built read-only from MRTIS at commit `{commit}`. Rebuild with:", "",
        "```",
        "python3 export/build_review_package.py --sample",
        "```", "",
    ]
    if compress:
        lines += [
            "## Open it first", "",
            "The six data files are gzipped. On macOS, double-click each in Finder, or",
            "from a terminal in this directory:", "",
            "```",
            "gunzip -k *.gz",
            "```", "",
            "`-k` keeps the `.gz` alongside the expanded file so your working copy stays",
            "clean; drop it if you would rather not keep both. Everything then imports",
            "exactly as the full export does -- gzip is transport only, the CSV and XML",
            "inside are untouched.", "",
            "They are gzipped because this directory is committed to the repo:",
            f"**{gz_bytes / 1e6:.1f} MB** compressed against {expanded_bytes / 1e6:.0f} MB expanded, "
            f"a {expanded_bytes / gz_bytes:.0f}x saving.",
            "FMPXMLRESULT repeats a field tag around every single value, which compresses",
            "away almost entirely -- that is what lets a full year of real rows travel",
            "through git at all.", "",
        ]
    lines += [
        "## What this is", "",
        "A committable subset of the full export, sized so it travels through the",
        "repo rather than by side channel. It exists so a Claris/FileMaker reviewer",
        "can import real rows, wire up the relationships and run a report on day one,",
        "without waiting on a 644 MB transfer.", "",
        f"**Scope: {window_desc}** -- selected on `PORT_CALL.call_start`, and selected",
        "on the **call**, never on the leg or the event.", "",
        "## The one rule that matters", "",
        "**Whole port calls only.** Every selected call brings all of its legs and all",
        "of its events. Nothing is truncated. A partially-shipped call would show a",
        "reviewer a broken version of the very assembly rules this package exists to",
        "demonstrate -- a split call missing its second leg reads as a single call, and",
        "a leg missing its berth events reads as a leg that never worked cargo.", "",
        "The build asserts this rather than trusting it. For every call in the sample it",
        "checks that the shipped leg count equals `PORT_CALL.leg_count` and the shipped",
        "event count equals `PORT_CALL.event_count`, that no leg or event points at a",
        "call left behind, and that no event points at a leg left behind. The export",
        "fails rather than writing a sample that would import wrong.", "",
        "A consequence worth stating: a call that starts inside the window and runs past",
        f"it keeps its later events, so event timestamps here run to {ev_hi:%Y-%m-%d},",
        f"past the {(hi - pd.Timedelta(days=1)):%Y-%m-%d} end of the window. That is correct, not a leak.",
        f"(Events span {ev_lo:%Y-%m-%d} to {ev_hi:%Y-%m-%d}.)", "",
        "## What is in it", "",
        "| Table | Rows here | Rows in full export |",
        "|---|---:|---:|",
        f"| PORT_CALL | {len(calls):,} | {full['counts']['PORT_CALL']:,} |",
        f"| PORT_CALL_LEG | {len(legs):,} | {full['counts']['PORT_CALL_LEG']:,} |",
        f"| PORT_CALL_EVENT | {len(events):,} | {full['counts']['PORT_CALL_EVENT']:,} |",
        "",
        "Enough of each to exercise the interesting cases:", "",
        f"- {int(calls['is_split'].sum()):,} split calls (calls with more than one leg)",
        f"- {int((~calls['is_commercial_call'].astype(bool)).sum()):,} non-commercial (lay-up) calls, flagged not deleted",
        f"- {calls['vessel_type'].nunique()} vessel types, {calls['imo'].nunique():,} distinct vessels",
        f"- {int(legs['agency'].notna().sum()):,} of {len(legs):,} legs carry an agency",
        f"- {int(legs['activity_conflict'].fillna(0).astype(int).sum()):,} legs with a flagged activity conflict",
        "",
        "## What is deliberately not in it", "",
        f"- **Every other year.** The full export covers {full['first_call']:%Y-%m-%d} to "
        f"{full['last_call']:%Y-%m-%d}; this is one year of it.",
        f"- **Unplaced events.** The full export carries {full['unplaced_events']:,} events that",
        "  belong to no port call at all (`unassigned_reason` = `before_first_entry` or",
        "  `no_open_call`). They have no call, so a whole-calls cut cannot include them.",
        "  A reviewer assessing completeness handling should ask for the full export.",
        "",
        "## Numbers in here are subtotals", "",
        "`ROW_COUNT_RECONCILIATION.md` shows the sample's fee totals **beside** the",
        "full-dataset ones for exactly this reason. The package's published figures are",
        "the full-dataset ones, derived in [`docs/FIGURES.md`](../docs/FIGURES.md); the",
        "charts and reports in this repo are built from the full dataset, not from this",
        "sample. Do not quote a number off this directory.", "",
        "`DATA_DICTIONARY.csv` describes the same fields as the full export, with the",
        "same wording. Its `null_pct` and `example` columns are computed over the rows",
        "in *this* directory, so a rarely-populated field can read 100% null here while",
        "being populated in the full export.", "",
        "## The full export", "",
        "Same script, no flag: `python3 export/build_review_package.py`. It writes",
        "`package/` -- all 3 tables in full, ~644 MB across CSV and XML, gitignored and",
        "shipped on request. Nothing about it changed to make this sample exist.", "",
    ]
    (out / "SAMPLE_README.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mrtis-db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--out", type=Path, default=None,
                    help="Output directory. Defaults to package/ (full) or sample/ (--sample).")
    ap.add_argument("--sample", action="store_true",
                    help="Build the committable subset: whole port calls only, all their legs and events.")
    ap.add_argument("--sample-start", default=None, help="Inclusive lower bound on call_start (with --sample-end).")
    ap.add_argument("--sample-end", default=None, help="Exclusive upper bound on call_start (with --sample-start).")
    ap.add_argument("--no-compress", action="store_true",
                    help="With --sample, leave the CSV/XML uncompressed instead of writing .gz.")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    if args.out is None:
        args.out = repo / ("sample" if args.sample else "package")
    if not args.sample and (args.sample_start or args.sample_end):
        raise SystemExit("--sample-start/--sample-end only apply with --sample.")
    if not args.sample and args.no_compress:
        raise SystemExit("--no-compress only applies with --sample; the full export is never compressed.")
    # The sample is committed, so it ships gzipped (~4 MB instead of ~83 MB).
    # The full export is not committed and stays plain -- it is handed over
    # directly, and a 644 MB gzip step would only slow the handover down.
    compress = args.sample and not args.no_compress

    commit = mrtis_commit()
    print(f"MRTIS commit: {commit}")

    con = duckdb.connect(str(args.mrtis_db), read_only=True)
    frames, specs = {}, {}
    for db_table, out_name, desc in TABLES:
        df, spec = load_table(con, db_table, desc)
        df = coerce_booleans(df, spec)
        frames[out_name] = df
        specs[out_name] = spec
    con.close()

    # Full-dataset totals, captured BEFORE any cut: the sample's own docs quote
    # these alongside its own so nobody reads a sample subtotal as the headline.
    full = {
        "counts": {name: len(df) for name, df in frames.items()},
        "fee_leg": frames["PORT_CALL_LEG"]["agency_fee"].sum(),
        "fee_call": frames["PORT_CALL"]["agency_fee_total"].sum(),
        "fee_dep": frames["PORT_CALL_EVENT"]["agency_fee"].sum(),
        "unplaced_events": int(frames["PORT_CALL_EVENT"]["port_call_id"].isna().sum()),
        "first_call": frames["PORT_CALL"]["call_start"].min(),
        "last_call": frames["PORT_CALL"]["call_start"].max(),
    }

    window = None
    if args.sample:
        lo, hi, window_desc = resolve_sample_window(frames["PORT_CALL"], args.sample_start, args.sample_end)
        frames = filter_to_sample(frames, lo, hi)
        window = (lo, hi, window_desc)
        print(f"Sample window: {window_desc}")
        print(f"  {len(frames['PORT_CALL']):,} of {full['counts']['PORT_CALL']:,} port calls, "
              f"whole, with all their legs and events -- integrity checks passed")

    args.out.mkdir(parents=True, exist_ok=True)
    expanded_bytes = 0  # pre-gzip total, so the sample guide can derive its own size claim

    for db_table, out_name, _ in TABLES:
        df, spec = frames[out_name], specs[out_name]
        fields = [f for f, _, _ in spec]
        written = [args.out / f"{out_name}.csv", args.out / f"{out_name}.xml"]
        write_csv(df, fields, written[0])
        write_fmpxmlresult(df, spec, out_name, written[1])
        if compress:
            expanded_bytes += sum(f.stat().st_size for f in written)
            written = [gzip_in_place(f) for f in written]
        else:
            # drop a .gz left behind by an earlier compressed build
            for f in written:
                f.with_suffix(f.suffix + ".gz").unlink(missing_ok=True)
        print(f"{out_name}: {len(df):,} rows x {len(fields)} fields -> "
              + ", ".join(f.name for f in written)
              + (f" ({sum(f.stat().st_size for f in written) / 1e6:.1f} MB gzipped)" if compress else ""))

    # --- data dictionary, one row per field across all three tables ---
    dict_rows = []
    for db_table, out_name, _ in TABLES:
        df, spec = frames[out_name], specs[out_name]
        for name, ftype, desc in spec:
            s = df[name].dropna()
            example = s.iloc[0] if len(s) else None
            dict_rows.append({
                "table": out_name,
                "field": name,
                "filemaker_type": ftype,
                "description": desc,
                "null_pct": round(100 * df[name].isna().mean(), 1),
                "example": example,
            })
    pd.DataFrame(dict_rows).to_csv(args.out / "DATA_DICTIONARY.csv", index=False)
    print(f"Data dictionary -> {args.out}/DATA_DICTIONARY.csv ({len(dict_rows)} fields across {len(TABLES)} tables)")

    # --- row-count reconciliation against the MRTIS build report ---
    # In sample mode every row is carried alongside its full-dataset counterpart,
    # so a sample subtotal can never be mistaken for the headline figure.
    fee_leg_total = frames["PORT_CALL_LEG"]["agency_fee"].sum()
    fee_call_total = frames["PORT_CALL"]["agency_fee_total"].sum()
    fee_dep_total = frames["PORT_CALL_EVENT"]["agency_fee"].sum()

    def pct(part, whole):
        return f"{100 * part / whole:.1f}%" if whole else "n/a"

    if args.sample:
        lo, hi, window_desc = window
        recon_lines = [
            "# Row-count reconciliation -- SAMPLE", "",
            f"Built read-only from `{args.mrtis_db}` at MRTIS commit `{commit}`.", "",
            f"**Scope: {window_desc}.** Whole port calls only -- every leg and every "
            "event of each selected call is present, and nothing else is. See "
            "`SAMPLE_README.md` for what that includes and excludes.", "",
            "Cross-check the full-dataset column against `docs/PORT_CALL_QUALITY.md` "
            "in MRTIS if it moves unexpectedly between exports.", "",
            "| Table | Rows in sample | Rows in full dataset | Share |",
            "|---|---:|---:|---:|",
        ]
        for _, out_name, _ in TABLES:
            n, t = len(frames[out_name]), full["counts"][out_name]
            recon_lines.append(f"| **{out_name}** | **{n:,}** | {t:,} | {pct(n, t)} |")
        recon_lines += [
            "",
            "## Agency fee totals",
            "",
            "The sample column is a subtotal of this window and **is not the "
            "package's headline figure**. The published totals are the full-dataset "
            "ones, derived in `docs/FIGURES.md`.",
            "",
            "| Basis | Sample | Full dataset |", "|---|---:|---:|",
            f"| Per-leg (billable), summed from PORT_CALL_LEG | ${fee_leg_total:,.0f} | ${full['fee_leg']:,.0f} |",
            f"| Per-leg (billable), summed from PORT_CALL.agency_fee_total | ${fee_call_total:,.0f} | ${full['fee_call']:,.0f} |",
            f"| Per-departure (frozen, comparison-only), summed from PORT_CALL_EVENT | ${fee_dep_total:,.0f} | ${full['fee_dep']:,.0f} |",
        ]
    else:
        recon_lines = [
            "# Row-count reconciliation", "",
            f"Built read-only from `{args.mrtis_db}` at MRTIS commit `{commit}`.", "",
            "Cross-check against `docs/PORT_CALL_QUALITY.md` in MRTIS if these move "
            "unexpectedly between exports.", "",
            "| Table | Rows |", "|---|---|",
        ]
        for _, out_name, _ in TABLES:
            recon_lines.append(f"| **{out_name}** | **{len(frames[out_name]):,}** |")
        recon_lines += [
            "", "## Agency fee totals (sanity check against docs/BUSINESS_RULES.md section 9)", "",
            "| Basis | Total |", "|---|---|",
            f"| Per-leg (billable), summed from PORT_CALL_LEG | ${fee_leg_total:,.0f} |",
            f"| Per-leg (billable), summed from PORT_CALL.agency_fee_total | ${fee_call_total:,.0f} |",
            f"| Per-departure (frozen, comparison-only), summed from PORT_CALL_EVENT | ${fee_dep_total:,.0f} |",
        ]
    (args.out / "ROW_COUNT_RECONCILIATION.md").write_text("\n".join(recon_lines) + "\n")
    print(f"Reconciliation -> {args.out}/ROW_COUNT_RECONCILIATION.md")

    if args.sample:
        write_sample_readme(args.out, frames, full, window, commit, compress, expanded_bytes)
        print(f"Sample guide -> {args.out}/SAMPLE_README.md")

    (args.out / "MRTIS_COMMIT.txt").write_text(commit + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
