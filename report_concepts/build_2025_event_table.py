#!/usr/bin/env python3
"""Every event row in calendar 2025 -- the raw spine, sorted by vessel then time.

William, 2026-08-20: "i mean everysingle record/row for 2025, so i can sort be
ship and date, then i can figure it out."

So this is `port_call_event` unaggregated: one row per Zone Report event, in
vessel-then-time order, which is the sort in which a port call reads itself.
Source values are kept alongside the canonical ones (src_zone, src_action,
src_agent, src_imo, src_mile) so nothing is hidden behind a lookup.

**Unplaced events are included.** Events that never landed in a port call carry
port_call_id blank and an unassigned_reason -- they are the likeliest place an
unexplained gap shows itself, so excluding them would hide the answer.

Two review columns are carried down from the call the event belongs to, so a
suspect call can be spotted while scrolling the raw rows:
  call_review_flag  -- same categories as port_calls_2025_review.csv
  call_review_note  -- the plain-language reason

Read-only against MRTIS. Usage: python3 report_concepts/build_2025_event_table.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb

MRTIS_DB = "/Users/billy/Documents/MRTIS/data/db/mrtis.duckdb"
OUT = Path(__file__).resolve().parent
YEAR_FROM, YEAR_TO = "2025-01-01", "2026-01-01"

# -- WHOLE CALLS THAT OVERLAP 2025, never calendar-clipped.
# -- William, 2026-08-20: "take care on year end and year start, u took calendar
# -- year, but the voyage may of ended or began in previous or subsequent year."
# -- A calendar filter on call_start dropped 105 calls that opened in 2024 and
# -- worked through 2025, and a calendar filter on event_time truncated 828 event
# -- rows mid-sequence. Both are fatal to reading a call by sorting on vessel and
# -- date. So: any call whose span touches 2025 is included IN FULL, with every
# -- one of its events whatever year they fall in.


FLAG = """
      case
        when c.port_call_id is null then 'EVENT_NOT_IN_ANY_CALL'
        when c.berth_stop_count > 0 then 'berthed'
        when coalesce(c.imo,'') = '' and coalesce(c.vessel_type,'') = ''
             and coalesce(dv.ship_type,'') = '' then 'NOT_AN_OCEAN_VESSEL'
        when coalesce(dv.ship_type,'') like '%LNG%' or c.vessel_type = 'Gas'
             then 'NOBERTH_LNG_FEED_GAP'
        when c.entry_draft_ft is null or c.exit_draft_ft is null
             then 'NOBERTH_NO_DRAFT_DATA'
        when c.exit_draft_ft < c.entry_draft_ft - 1 then 'NOBERTH_LIGHTERED_DOWN'
        when c.exit_draft_ft > c.entry_draft_ft + 1 then 'NOBERTH_LOADED_UP'
        else 'NOBERTH_NO_CARGO_EVIDENCE'
      end
"""

SQL = f"""
select
    -- sort keys first, so the file opens in the order it should be read
    e.vessel_name, e.imo, e.event_time,

    e.action, e.src_action,
    e.src_zone, e.berth, e.facility, e.facility_type,
    e.mile, e.src_mile, e.draft_ft,

    e.port_call_id, e.leg_id, e.leg_seq, e.event_seq, e.unassigned_reason,

    e.vessel_type as feed_vessel_type, dv.ship_type as register_ship_type,
    dv.ship_type_group as register_ship_type_group, e.dwt, e.tpc,

    e.is_berth_stop, e.berth_stop_seq, e.is_anchorage, e.is_waiting_time,
    e.is_geofence_artifact, e.dwell_hours, e.hours_since_prev,

    e.activity, e.activity_method,
    e.cargo_group, e.cargo_subgroup, e.cargo, e.destination, e.estimated_tons,

    e.src_agent, e.agency, e.agency_leg, e.agency_normalized,
    e.agency_fee as event_fee_departures_basis,

    e.call_status, e.is_split_call,

    {FLAG} as call_review_flag,

    case
      when c.port_call_id is null
           then 'Event never landed in a port call: ' || coalesce(e.unassigned_reason,'(no reason recorded)')
      when c.berth_stop_count > 0 then ''
      when coalesce(c.imo,'') = '' and coalesce(c.vessel_type,'') = ''
           and coalesce(dv.ship_type,'') = ''
           then 'No IMO and no type anywhere -- tug/workboat/government craft, never billed by design'
      when coalesce(dv.ship_type,'') like '%LNG%' or c.vessel_type = 'Gas'
           then 'LNG/gas hull, no berth recorded -- Venture Global geofence absent until 2026-02-04'
      when c.entry_draft_ft is null or c.exit_draft_ft is null
           then 'No berth and no draft pair -- cannot tell whether cargo moved'
      when c.exit_draft_ft < c.entry_draft_ft - 1
           then 'No berth, left ' || cast(c.entry_draft_ft - c.exit_draft_ft as varchar) || 'ft lighter -- gave cargo at anchor'
      when c.exit_draft_ft > c.entry_draft_ft + 1
           then 'No berth, left ' || cast(c.exit_draft_ft - c.entry_draft_ft as varchar) || 'ft deeper -- took cargo at anchor'
      else 'No berth and draft unchanged -- no evidence cargo moved'
    end as call_review_note,

    e.event_key, e.src_imo, e.src_vessel_type

from port_call_event e
left join port_call c  on c.port_call_id = e.port_call_id
left join dim_vessel dv on dv.vessel_key = e.vessel_key
where (
    -- every event of any call that overlaps 2025, whatever year it falls in
    e.port_call_id in (
        select port_call_id from port_call c
        where c.call_start < timestamp '2026-01-01'
    and (c.call_end is null or c.call_end >= timestamp '2025-01-01')
    )
    -- plus unplaced events that fall in 2025, which belong to no call at all
    or (e.port_call_id is null
        and e.event_time >= timestamp '{YEAR_FROM}'
        and e.event_time <  timestamp '{YEAR_TO}')
  )
order by e.vessel_name, e.imo, e.event_time, e.event_key
"""


def main() -> None:
    con = duckdb.connect(MRTIS_DB, read_only=True)
    commit = subprocess.run(
        ["git", "-C", "/Users/billy/Documents/MRTIS", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True).stdout.strip()

    df = con.execute(SQL).df()

    # Assert no call is truncated: every call in the file must carry its full
    # event_seq run, 1..n. A gap means the selection clipped a sequence, which
    # is exactly the defect this whole-call selection exists to prevent.
    chk = con.execute("""
        with sel as (
          select port_call_id from port_call c
          where c.call_start < timestamp '2026-01-01'
            and (c.call_end is null or c.call_end >= timestamp '2025-01-01')
        ),
        f as (
          select e.port_call_id, e.event_seq
          from port_call_event e join sel using (port_call_id)
        )
        select count(*) from (
          select port_call_id from f
          group by 1
          having count(*) <> max(event_seq) or min(event_seq) <> 1
        )
    """).fetchone()[0]
    assert chk == 0, f"{chk} calls have a truncated event sequence in this export"

    path = OUT / "port_call_events_2025_all_rows.csv"
    df.to_csv(path, index=False)

    print(f"MRTIS commit {commit} · whole calls overlapping 2025 · every event row")
    print(f"-> {path}")
    print(f"   {len(df):,} rows x {len(df.columns)} columns, "
          f"sorted by vessel_name, imo, event_time")
    print()
    placed = df.port_call_id.notna().sum()
    print(f"  events placed in a port call : {placed:,}")
    print(f"  events NOT in any call       : {len(df)-placed:,}")
    if len(df) - placed:
        for k, n in df.loc[df.port_call_id.isna(), "unassigned_reason"].value_counts().items():
            print(f"    - {k}: {n:,}")
    print()
    print("  call_review_flag on these rows:")
    for k, n in df.call_review_flag.value_counts().items():
        print(f"    {k:26s} {n:7,} rows")
    print()
    print(f"  distinct vessels: {df.vessel_name.nunique():,}")
    con.close()


if __name__ == "__main__":
    main()
