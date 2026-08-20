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
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import figures  # noqa: E402  -- repo-root module, the single source of figures

MRTIS_DB = "/Users/billy/Documents/MRTIS/data/db/mrtis.duckdb"
OUT = Path(__file__).resolve().parent


def commit() -> str:
    return subprocess.run(
        ["git", "-C", "/Users/billy/Documents/MRTIS", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def report_1_agency_fee_by_vessel_type(con, c: str, f: dict):
    """Report 1: Agency fee by vessel type. The headline P&L-style report --
    what MRTIS bills, broken down by the vessel-type tiers of section 9 of
    docs/BUSINESS_RULES.md.

    The billable total is asserted against figures.py's derivation rather than
    a hard-coded constant (which is how it went stale after MRTIS's rebuild).

    Audit finding A11: the old version put "Port calls" (all calls) next to
    "Avg fee/call" (averaged over fee-bearing calls only), so the columns
    could not be reconciled against each other -- Gas showed $2,541,000 over
    941 calls with an average of $3,500, which divides out to $2,700. Both
    denominators are now columns in their own right, and the average is
    stated explicitly as being over fee-bearing calls.
    """
    df = con.execute("""
        select coalesce(vessel_type, '(unknown)') as vessel_type,
               count(*) as port_calls,
               count(*) filter (where agency_fee_total is not null
                                  and agency_fee_total > 0) as fee_bearing_calls,
               sum(leg_count) as legs,
               sum(agency_fee_total) as agency_fee_billable,
               sum(agency_fee_departures_total) as agency_fee_departures_comparison,
               round(sum(agency_fee_total)
                     / nullif(count(*) filter (where agency_fee_total is not null
                                                 and agency_fee_total > 0), 0), 0)
                   as avg_fee_per_fee_bearing_call,
               round(sum(agency_fee_total) / nullif(count(*), 0), 0)
                   as avg_fee_per_call_all
        from port_call
        group by 1
        order by agency_fee_billable desc nulls last
    """).fetchdf()
    df.to_csv(OUT / "agency_fee_by_vessel_type.csv", index=False)

    total = df["agency_fee_billable"].sum()
    expected = f["fee_basis"]["leg_basis"]
    if round(total, 2) != round(expected, 2):
        raise SystemExit(f"Report 1: billable total ${total:,.0f} does not match "
                         f"figures.py's ${expected:,.0f}")

    lines = [
        "# Sample report: Agency fee by vessel type", "",
        f"MRTIS commit `{c}` · billable basis = one fee per leg with a berth stop "
        "(docs/BUSINESS_RULES.md §9).", "",
        f"**Total billable agency fee: ${total:,.0f}**", "",
        "Two averages are given because two denominators are in play. Most vessel",
        "types include calls that never berthed and so never billed; averaging over",
        "all calls and averaging over fee-bearing calls give materially different",
        "answers, and only the second is the average fee of an actual job.", "",
        "| Vessel type | Port calls | Fee-bearing calls | Legs | Billable fee | "
        "Per-departure (comparison) | Avg fee / fee-bearing call | Avg fee / call |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    money = lambda v: "—" if v != v else f"${v:,.0f}"
    for _, r in df.iterrows():
        lines.append(
            f"| {r.vessel_type} | {r.port_calls:,.0f} | {r.fee_bearing_calls:,.0f} | "
            f"{r.legs:,.0f} | {money(r.agency_fee_billable)} | "
            f"{money(r.agency_fee_departures_comparison)} | "
            f"{money(r.avg_fee_per_fee_bearing_call)} | {money(r.avg_fee_per_call_all)} |"
        )
    lines += [
        "",
        "The per-departure column sums `port_call.agency_fee_departures_total` — the",
        f"**call-level** roll-up, ${f['fee_basis']['per_departure_call_rollup']:,.0f}. "
        f"The event-level frozen basis is ${f['fee_basis']['per_departure_event']:,.0f}, "
        f"${f['fee_basis']['per_departure_gap']:,.0f} higher: the difference is the fee on",
        f"{f['fee_basis']['unassigned_fee_events']} departure events that never landed in a "
        "call, which a call-level column structurally cannot hold",
        "(MRTIS OPEN_QUESTIONS.md §11.2, ruled: leave as is).",
    ]
    (OUT / "agency_fee_by_vessel_type.md").write_text("\n".join(lines) + "\n")
    print(f"Report 1 -> agency_fee_by_vessel_type.csv / .md  (total ${total:,.0f})")


def report_2_port_calls_by_agent(con, c: str, f: dict):
    """Report 2: Port calls and fee revenue by agent, at the leg grain
    (port_call_leg.agency -- the leg-owning agency, per docs/BUSINESS_RULES.md
    §6, not the raw per-event agent). Demonstrates agent-performance reporting.

    Audit findings A11 and A12, both fixed here:
      A11 -- "Legs" counted all legs while "Avg fee/leg" averaged over
             chargeable legs only, so the columns did not divide out. Both
             counts are now columns.
      A12 -- the agency filter silently dropped fee-bearing legs that carry no
             agency, so the CSV summed short of the total published everywhere
             else in the package with nothing to explain the difference. The
             shortfall is now stated, and reconciled against figures.py.
    """
    df = con.execute("""
        select agency,
               count(distinct port_call_id) as port_calls,
               count(*) as legs,
               count(*) filter (where agency_fee is not null) as chargeable_legs,
               sum(agency_fee) as billable_fee,
               round(sum(agency_fee)
                     / nullif(count(*) filter (where agency_fee is not null), 0), 0)
                   as avg_fee_per_chargeable_leg
        from port_call_leg
        where agency is not null and agency != ''
        group by 1
        order by billable_fee desc nulls last
    """).fetchdf()
    df.to_csv(OUT / "port_calls_by_agent.csv", index=False)

    reported = df["billable_fee"].sum()
    na = f["legs_without_agency"]
    if round(reported, 2) != round(na["reported_total"], 2):
        raise SystemExit(f"Report 2: ${reported:,.0f} does not match figures.py's "
                         f"expected ${na['reported_total']:,.0f}")

    top = df.head(20)
    lines = [
        "# Sample report: Port calls and fee revenue by agent", "",
        f"MRTIS commit `{c}` · leg-level agency (`port_call_leg.agency`) -- the agency "
        "that brought the vessel in owns the leg (docs/BUSINESS_RULES.md §6). "
        f"{len(df)} distinct agencies with billable legs; top 20 shown here, full list in the CSV.", "",
        f"**Total shown: ${reported:,.0f}**", "",
        f"> This is ${na['fee']:,.0f} short of the ${f['fee_basis']['leg_basis']:,.0f} "
        f"billable total published elsewhere in this package. The difference is "
        f"**{na['legs']:,} chargeable legs that carry no agency at all** and so cannot "
        "appear in an agency breakdown. Nothing is lost — the fee is in the totals, just",
        "> not attributable to an agent.", "",
        "| Agency | Port calls | Legs | Chargeable legs | Billable fee | Avg fee / chargeable leg |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    money = lambda v: "—" if v != v else f"${v:,.0f}"
    for _, r in top.iterrows():
        lines.append(
            f"| {r.agency} | {r.port_calls:,.0f} | {r.legs:,.0f} | "
            f"{r.chargeable_legs:,.0f} | {money(r.billable_fee)} | "
            f"{money(r.avg_fee_per_chargeable_leg)} |"
        )
    (OUT / "port_calls_by_agent.md").write_text("\n".join(lines) + "\n")
    print(f"Report 2 -> port_calls_by_agent.csv / .md  ({len(df)} agencies, "
          f"${reported:,.0f}, {na['legs']} unattributed legs)")


def report_3_r5_general_cargo_bulk_impact(con, c: str, f: dict):
    """Report 3: R5 impact by facility -- which General Cargo berths drive
    the $5,000 dry-bulk-at-general-cargo rule (docs/BUSINESS_RULES.md §9.3).

    The R5 total is reconciled against figures.py rather than the hard-coded
    "$15,560,000 / 3,112 legs" this used to assert -- a figure that went stale
    the moment MRTIS re-priced R5 off the first *working* berth. The rule and
    its figures are MRTIS OPEN_QUESTIONS.md §12.2 and the §12.3.3 resolution;
    §12.4 (cited here previously -- audit finding A9) is the build-order note
    and carries none of these numbers.
    """
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
    r5 = f["fee_rules"]["by_rule"]["R5"]
    if int(total_legs) != r5["legs"] or round(total_fee, 2) != round(r5["bills_now"], 2):
        raise SystemExit(
            f"Report 3: R5 here is ${total_fee:,.0f} / {total_legs:,} legs but "
            f"figures.py derives ${r5['bills_now']:,.0f} / {r5['legs']:,} legs")

    lines = [
        "# Sample report: R5 impact by facility -- dry bulk calling General Cargo berths", "",
        f"MRTIS commit `{c}` · Rule R5 (docs/BUSINESS_RULES.md §9.3): any dry-bulk vessel "
        "(`vessel_type = 'Bulk'`) whose leg's first **working** berth is a General Cargo "
        "facility type bills at a flat $5,000 "
        "(MRTIS OPEN_QUESTIONS.md §12.2 and the §12.3.3 resolution; the first-working-berth "
        "amendment is §12.3.3.1).", "",
        f"**Total: ${total_fee:,.0f} across {total_legs:,} legs**, reconciled against "
        "`figures.py`'s independent derivation of R5.", "",
        "> Layberth stops are skipped when resolving which berth prices the leg. Every "
        "layberth zone carries `facility_type = General Cargo`, so pricing off the first "
        "berth of *any* kind handed the $5,000 tier to Bulk vessels that had merely lain "
        "at a layberth before working. Correcting that moved **93 legs** back to the "
        "$10,500 base tier (+$511,500) and is why this report's totals are lower than an",
        "> extract taken before that amendment.", "",
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
    f = figures.derive(con)
    report_1_agency_fee_by_vessel_type(con, c, f)
    report_2_port_calls_by_agent(con, c, f)
    report_3_r5_general_cargo_bulk_impact(con, c, f)
    con.close()


if __name__ == "__main__":
    main()
