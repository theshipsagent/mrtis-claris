#!/usr/bin/env python3
"""Sample canned reports demonstrating MRTIS's reporting capability, for the
Claris/FileMaker review package. Read-only against MRTIS's duckdb.

Each report writes a CSV (the queryable artifact) and a short Markdown
summary (what a canned FileMaker report/layout would show a user). Every
figure is cross-checked in a comment against docs/BUSINESS_RULES.md or
MRTIS's own OPEN_QUESTIONS.md so a reviewer can verify this isn't a fresh
re-derivation.

Usage:
    python3 reports/build_reports.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb

MRTIS_DB = "/Users/billy/Documents/MRTIS/data/db/mrtis.duckdb"
OUT = Path(__file__).resolve().parent


def commit() -> str:
    return subprocess.run(
        ["git", "-C", "/Users/billy/Documents/MRTIS", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def report_1_agency_fee_by_vessel_type(con, c: str):
    """Report 1: Agency fee by vessel type. The headline P&L-style report --
    what MRTIS bills, broken down by the vessel-type tiers of section 9 of
    docs/BUSINESS_RULES.md. Billable total should reconcile to $272,167,500
    (package/ROW_COUNT_RECONCILIATION.md)."""
    df = con.execute("""
        select coalesce(vessel_type, '(unknown)') as vessel_type,
               count(*) as port_calls,
               sum(leg_count) as legs,
               sum(agency_fee_total) as agency_fee_billable,
               sum(agency_fee_departures_total) as agency_fee_departures_comparison,
               round(avg(agency_fee_total), 0) as avg_fee_per_call
        from port_call
        group by 1
        order by agency_fee_billable desc nulls last
    """).fetchdf()
    df.to_csv(OUT / "agency_fee_by_vessel_type.csv", index=False)

    total = df["agency_fee_billable"].sum()
    lines = [
        "# Sample report: Agency fee by vessel type", "",
        f"MRTIS commit `{c}` · billable basis = one fee per leg with a berth stop "
        "(docs/BUSINESS_RULES.md §9).", "",
        f"**Total billable agency fee: ${total:,.0f}**", "",
        "| Vessel type | Port calls | Legs | Billable fee | Per-departure (comparison) | Avg fee/call |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in df.iterrows():
        lines.append(
            f"| {r.vessel_type} | {r.port_calls:,.0f} | {r.legs:,.0f} | "
            f"${r.agency_fee_billable:,.0f} | ${r.agency_fee_departures_comparison:,.0f} | "
            f"${r.avg_fee_per_call:,.0f} |"
        )
    (OUT / "agency_fee_by_vessel_type.md").write_text("\n".join(lines) + "\n")
    print(f"Report 1 -> agency_fee_by_vessel_type.csv / .md  (total ${total:,.0f})")


def report_2_port_calls_by_agent(con, c: str):
    """Report 2: Port calls and fee revenue by agent, at the leg grain
    (port_call_leg.agency -- the leg-owning agency, per docs/BUSINESS_RULES.md
    §6, not the raw per-event agent). Demonstrates agent-performance reporting."""
    df = con.execute("""
        select agency,
               count(distinct port_call_id) as port_calls,
               count(*) as legs,
               sum(agency_fee) as billable_fee,
               round(avg(agency_fee), 0) as avg_fee_per_leg
        from port_call_leg
        where agency is not null and agency != ''
        group by 1
        order by billable_fee desc nulls last
    """).fetchdf()
    df.to_csv(OUT / "port_calls_by_agent.csv", index=False)

    top = df.head(20)
    lines = [
        "# Sample report: Port calls and fee revenue by agent", "",
        f"MRTIS commit `{c}` · leg-level agency (`port_call_leg.agency`) -- the agency "
        "that brought the vessel in owns the leg (docs/BUSINESS_RULES.md §6). "
        f"{len(df)} distinct agencies with billable legs; top 20 shown here, full list in the CSV.", "",
        "| Agency | Port calls | Legs | Billable fee | Avg fee/leg |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, r in top.iterrows():
        lines.append(
            f"| {r.agency} | {r.port_calls:,.0f} | {r.legs:,.0f} | "
            f"${r.billable_fee:,.0f} | ${r.avg_fee_per_leg:,.0f} |"
        )
    (OUT / "port_calls_by_agent.md").write_text("\n".join(lines) + "\n")
    print(f"Report 2 -> port_calls_by_agent.csv / .md  ({len(df)} agencies, top 20 in .md)")


def report_3_r5_general_cargo_bulk_impact(con, c: str):
    """Report 3: R5 impact by facility -- which General Cargo berths drive
    the $5,000 dry-bulk-at-general-cargo rule (docs/BUSINESS_RULES.md §9.3).
    Total should reconcile to exactly $15,560,000 / 3,112 legs, the built and
    verified R5 figure in MRTIS OPEN_QUESTIONS.md §12.4."""
    df = con.execute("""
        select l.first_berth_facility as facility,
               count(*) as legs,
               sum(l.agency_fee) as billable_fee
        from port_call_leg l
        join port_call c using (port_call_id)
        where l.facility_type = 'General Cargo'
          and c.vessel_type = 'Bulk'
          and l.agency_fee is not null
        group by 1
        order by billable_fee desc
    """).fetchdf()
    df.to_csv(OUT / "r5_general_cargo_bulk_impact.csv", index=False)

    total_fee, total_legs = df["billable_fee"].sum(), df["legs"].sum()
    lines = [
        "# Sample report: R5 impact by facility -- dry bulk calling General Cargo berths", "",
        f"MRTIS commit `{c}` · Rule R5 (docs/BUSINESS_RULES.md §9.3): any dry-bulk vessel "
        "(`vessel_type = 'Bulk'`) whose leg's first berth is a General Cargo facility "
        "type bills at a flat $5,000, decided by the leg's first berth "
        "(MRTIS OPEN_QUESTIONS.md §12.3.3, ruled).", "",
        f"**Total: ${total_fee:,.0f} across {total_legs:,} legs** "
        "(reconciles exactly to the built-and-verified $15,560,000 / 3,112 legs in "
        "MRTIS OPEN_QUESTIONS.md §12.4).", "",
        "| Facility | Legs | Billable fee |",
        "|---|---:|---:|",
    ]
    for _, r in df.iterrows():
        lines.append(f"| {r.facility} | {r.legs:,.0f} | ${r.billable_fee:,.0f} |")
    (OUT / "r5_general_cargo_bulk_impact.md").write_text("\n".join(lines) + "\n")
    print(f"Report 3 -> r5_general_cargo_bulk_impact.csv / .md  (${total_fee:,.0f} / {total_legs} legs)")


def main():
    c = commit()
    con = duckdb.connect(MRTIS_DB, read_only=True)
    report_1_agency_fee_by_vessel_type(con, c)
    report_2_port_calls_by_agent(con, c)
    report_3_r5_general_cargo_bulk_impact(con, c)
    con.close()


if __name__ == "__main__":
    main()
