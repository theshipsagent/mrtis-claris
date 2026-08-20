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

Usage:
    python3 export/build_review_package.py
    python3 export/build_review_package.py --mrtis-db /path/to/mrtis.duckdb --out package/
"""

from __future__ import annotations

import argparse
import csv
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
    df = con.execute(f"SELECT * FROM {table}").fetchdf()
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mrtis-db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "package")
    args = ap.parse_args()

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

    args.out.mkdir(parents=True, exist_ok=True)

    for db_table, out_name, _ in TABLES:
        df, spec = frames[out_name], specs[out_name]
        fields = [f for f, _, _ in spec]
        write_csv(df, fields, args.out / f"{out_name}.csv")
        write_fmpxmlresult(df, spec, out_name, args.out / f"{out_name}.xml")
        print(f"{out_name}: {len(df):,} rows x {len(fields)} fields -> {args.out}/{out_name}.csv, {out_name}.xml")

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
    recon_lines = [
        "# Row-count reconciliation", "",
        f"Built read-only from `{args.mrtis_db}` at MRTIS commit `{commit}`.", "",
        "Cross-check against `docs/PORT_CALL_QUALITY.md` in MRTIS if these move "
        "unexpectedly between exports.", "",
        "| Table | Rows |", "|---|---|",
    ]
    for _, out_name, _ in TABLES:
        recon_lines.append(f"| **{out_name}** | **{len(frames[out_name]):,}** |")
    fee_leg_total = frames["PORT_CALL_LEG"]["agency_fee"].sum()
    fee_call_total = frames["PORT_CALL"]["agency_fee_total"].sum()
    fee_dep_total = frames["PORT_CALL_EVENT"]["agency_fee"].sum()
    recon_lines += [
        "", "## Agency fee totals (sanity check against docs/BUSINESS_RULES.md section 9)", "",
        "| Basis | Total |", "|---|---|",
        f"| Per-leg (billable), summed from PORT_CALL_LEG | ${fee_leg_total:,.0f} |",
        f"| Per-leg (billable), summed from PORT_CALL.agency_fee_total | ${fee_call_total:,.0f} |",
        f"| Per-departure (frozen, comparison-only), summed from PORT_CALL_EVENT | ${fee_dep_total:,.0f} |",
    ]
    (args.out / "ROW_COUNT_RECONCILIATION.md").write_text("\n".join(recon_lines) + "\n")
    print(f"Reconciliation -> {args.out}/ROW_COUNT_RECONCILIATION.md")

    (args.out / "MRTIS_COMMIT.txt").write_text(commit + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
