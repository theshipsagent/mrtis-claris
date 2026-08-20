#!/usr/bin/env python3
"""Every port call in calendar 2025, one row each, with a flag column marking
the vessels under discussion -- the no-berth calls, split by what the evidence
says they were actually doing.

Built at William's request, 2026-08-20: "export table of all rows all ships for
2025, and let me look, add a column to flag the shps in question."

The flag is deliberately categorical rather than a yes/no, because the no-berth
population is not one thing (report_concepts/ISSUES.md I-12, I-13, I-15):

  berthed                    normal call, reached a berth
  NOBERTH_LNG_FEED_GAP       LNG hull, no berth -- the Venture Global blind
                             window before the geofence appeared (I-12)
  NOBERTH_LIGHTERED_DOWN     no berth, draft fell >1ft -- gave cargo at anchor
  NOBERTH_LOADED_UP          no berth, draft rose >1ft -- took cargo at anchor
  NOBERTH_NO_CARGO_EVIDENCE  no berth, draft flat -- genuinely worked nothing
  NOBERTH_NO_DRAFT_DATA      no berth, drafts missing -- cannot say
  NOT_AN_OCEAN_VESSEL        no IMO and no type from either source -- a tug,
                             workboat or government craft, which MRTIS
                             deliberately never bills. Broken out separately
                             because one such craft (Gol Warrior, 7ft draft,
                             25 crossings) would otherwise dominate the
                             no-cargo-evidence category and make it look like
                             a finding.

Every supporting column the flag is derived from is in the table, so the
classification can be checked rather than trusted.

Read-only against MRTIS.  Usage: python3 report_concepts/build_2025_review_table.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb

MRTIS_DB = "/Users/billy/Documents/MRTIS/data/db/mrtis.duckdb"
OUT = Path(__file__).resolve().parent
YEAR_FROM, YEAR_TO = "2025-01-01", "2026-01-01"

SQL = f"""
select
    c.port_call_id,
    c.call_start, c.call_end, round(c.call_hours, 1) as call_hours,
    c.call_status, c.is_complete, c.is_split, c.leg_count,

    c.vessel_name, c.imo,
    c.vessel_type            as feed_vessel_type,
    v.ship_type              as register_ship_type,
    v.ship_type_group        as register_ship_type_group,
    c.dwt,
    case when c.dwt is null then null
         when c.dwt <  20000 then '1. under 20k'
         when c.dwt <  40000 then '2. 20-40k Handy'
         when c.dwt <  60000 then '3. 40-60k MR'
         when c.dwt <  85000 then '4. 60-85k LR1/Pmax'
         when c.dwt < 125000 then '5. 85-125k LR2/Afra'
         else                     '6. 125k+ Suez/VLCC' end as size_band,
    c.tpc,

    c.berth_stop_count, c.anchorage_stop_count, c.event_count,
    c.entry_draft_ft, c.exit_draft_ft,
    (c.exit_draft_ft - c.entry_draft_ft) as draft_change_ft,

    l.first_berth_facility, l.facility_type, l.activity, l.activity_method,
    l.cargo_group, l.cargo_subgroup, l.cargo, l.destination, l.estimated_tons,

    c.agency, c.agency_fee_total,

    -- ---- the flag -------------------------------------------------------
    case
      when c.berth_stop_count > 0 then 'berthed'
      when coalesce(c.imo,'') = '' and coalesce(c.vessel_type,'') = ''
           and coalesce(v.ship_type,'') = '' then 'NOT_AN_OCEAN_VESSEL'
      when coalesce(v.ship_type,'') like '%LNG%' or c.vessel_type = 'Gas'
           then 'NOBERTH_LNG_FEED_GAP'
      when c.entry_draft_ft is null or c.exit_draft_ft is null
           then 'NOBERTH_NO_DRAFT_DATA'
      when c.exit_draft_ft < c.entry_draft_ft - 1 then 'NOBERTH_LIGHTERED_DOWN'
      when c.exit_draft_ft > c.entry_draft_ft + 1 then 'NOBERTH_LOADED_UP'
      else 'NOBERTH_NO_CARGO_EVIDENCE'
    end as review_flag,

    -- plain-language why, so the flag is not a black box
    case
      when c.berth_stop_count > 0 then ''
      when coalesce(c.imo,'') = '' and coalesce(c.vessel_type,'') = ''
           and coalesce(v.ship_type,'') = ''
           then 'No IMO and no type anywhere -- tug/workboat/government craft, never billed by design'
      when coalesce(v.ship_type,'') like '%LNG%' or c.vessel_type = 'Gas'
           then 'LNG/gas hull, no berth recorded -- Venture Global geofence absent until 2026-02-04 (ISSUES I-12)'
      when c.entry_draft_ft is null or c.exit_draft_ft is null
           then 'No berth and no draft pair -- cannot tell whether cargo moved'
      when c.exit_draft_ft < c.entry_draft_ft - 1
           then 'No berth, left ' || cast(c.entry_draft_ft - c.exit_draft_ft as varchar) || 'ft lighter -- gave cargo at anchor (ISSUES I-15)'
      when c.exit_draft_ft > c.entry_draft_ft + 1
           then 'No berth, left ' || cast(c.exit_draft_ft - c.entry_draft_ft as varchar) || 'ft deeper -- took cargo at anchor (ISSUES I-15)'
      else 'No berth and draft unchanged -- no evidence cargo moved'
    end as review_note

from port_call c
left join dim_vessel v on v.vessel_key = c.vessel_key
left join port_call_leg l
       on l.port_call_id = c.port_call_id and l.leg_seq = 1
where c.call_start >= timestamp '{YEAR_FROM}'
  and c.call_start <  timestamp '{YEAR_TO}'
order by c.call_start, c.port_call_id
"""


def main() -> None:
    con = duckdb.connect(MRTIS_DB, read_only=True)
    commit = subprocess.run(
        ["git", "-C", "/Users/billy/Documents/MRTIS", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True).stdout.strip()

    df = con.execute(SQL).df()
    path = OUT / "port_calls_2025_review.csv"
    df.to_csv(path, index=False)

    print(f"MRTIS commit {commit} · calendar year 2025")
    print(f"-> {path}  ({len(df):,} calls, {len(df.columns)} columns)")
    print()
    print("review_flag breakdown:")
    vc = df["review_flag"].value_counts()
    for k, n in vc.items():
        fee = df.loc[df.review_flag == k, "agency_fee_total"].fillna(0).sum()
        print(f"  {k:28s} {n:6,}  fee ${fee:>14,.0f}")
    nb = df[df.review_flag != "berthed"]
    print()
    print(f"  flagged (no berth) total     : {len(nb):,} of {len(df):,} calls "
          f"({len(nb)/len(df)*100:.1f}%)")
    print(f"  fee they carry today         : ${nb['agency_fee_total'].fillna(0).sum():,.0f}")
    con.close()


if __name__ == "__main__":
    main()
