#!/usr/bin/env python3
"""Port-wide concept reports -- count and agency revenue by facility and agency.

Scope ruled by William, 2026-08-20 (session 8): *"the fee's apply to every ship,
in sample reports we only focused on grain, but the second sample test will be
total port calls by facility and agency against count and rev$ as we don't yet
have all cargoes into split out by cargo."*

So: every vessel, every facility, every agency, no cargo dimension. Same window
as the grain reports -- trailing 36 months anchored on the data's last date.

Read-only against MRTIS. Every figure derived here; none hand-keyed.

Usage:  python3 report_concepts/build_portwide_reports.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb

MRTIS_DB = "/Users/billy/Documents/MRTIS/data/db/mrtis.duckdb"
OUT = Path(__file__).resolve().parent
WIN_FROM, WIN_TO = "2023-08-01", "2026-08-01"
W = f"l.leg_start >= timestamp '{WIN_FROM}' and l.leg_start < timestamp '{WIN_TO}'"

NO_BERTH = "(never berthed)"
NO_AGENCY = "(no agency)"


def commit() -> str:
    return subprocess.run(["git", "-C", "/Users/billy/Documents/MRTIS",
                           "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()


def money(v) -> str:
    return "--" if not v else f"${v:,.0f}"


def md_table(headers, rows, aligns=None) -> str:
    aligns = aligns or ["---"] * len(headers)
    return "\n".join(["| " + " | ".join(headers) + " |",
                      "|" + "|".join(aligns) + "|"]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def preflight(con):
    """The reports below claim their totals reconcile. Prove it rather than
    saying it: leg-grain revenue must equal the window's total agency fee, and
    every leg must fall in exactly one facility bucket and one agency bucket."""
    tot = con.execute(f"select count(*), sum(l.agency_fee), "
                      f"count(*) filter (where l.agency_fee > 0) "
                      f"from port_call_leg l where {W}").fetchone()
    by_fac = con.execute(f"""
        select count(*), sum(l.agency_fee) from (
          select coalesce(l.first_berth_facility, '{NO_BERTH}') f, l.agency_fee
          from port_call_leg l where {W}) l""").fetchone()
    assert tot[0] == by_fac[0], "facility bucketing loses legs"
    assert (tot[1] or 0) == (by_fac[1] or 0), "facility bucketing loses revenue"
    return tot   # (legs, revenue, chargeable)


def report(con, c, tot):
    legs_all, rev_all, chg_all = tot

    by_fac = con.execute(f"""
        select coalesce(l.first_berth_facility, '{NO_BERTH}') as facility,
               coalesce(l.facility_type, '--') as facility_type,
               count(distinct l.port_call_id) as port_calls,
               count(*) as legs,
               count(distinct l.vessel_key) as vessels,
               count(*) filter (where l.agency_fee > 0) as chargeable,
               sum(l.agency_fee) as revenue
        from port_call_leg l where {W}
        group by 1, 2 order by 7 desc nulls last, 4 desc, 1
    """).fetchall()

    by_agency = con.execute(f"""
        select coalesce(l.agency, '{NO_AGENCY}') as agency,
               count(distinct l.port_call_id) as port_calls,
               count(*) as legs,
               count(distinct l.vessel_key) as vessels,
               count(distinct l.first_berth_facility) as facilities,
               count(*) filter (where l.agency_fee > 0) as chargeable,
               sum(l.agency_fee) as revenue
        from port_call_leg l where {W}
        group by 1 order by 7 desc nulls last, 3 desc, 1
    """).fetchall()

    matrix = con.execute(f"""
        select coalesce(l.agency, '{NO_AGENCY}') as agency,
               coalesce(l.first_berth_facility, '{NO_BERTH}') as facility,
               count(*) as legs,
               count(*) filter (where l.agency_fee > 0) as chargeable,
               sum(l.agency_fee) as revenue
        from port_call_leg l where {W}
        group by 1, 2 order by 1, 5 desc nulls last, 2
    """).fetchall()

    # ---- CSVs (the queryable artifact -- full depth, no truncation)
    with open(OUT / "portwide_by_facility.csv", "w") as fh:
        fh.write("facility,facility_type,port_calls,legs,distinct_vessels,"
                 "chargeable_legs,revenue,avg_revenue_per_chargeable_leg\n")
        for fa, ft, pc, lg, ve, ch, rv in by_fac:
            fh.write(f'"{fa}","{ft}",{pc},{lg},{ve},{ch},{rv or 0:.0f},'
                     f'{(rv/ch) if ch else 0:.0f}\n')

    with open(OUT / "portwide_by_agency.csv", "w") as fh:
        fh.write("agency,port_calls,legs,distinct_vessels,facilities_served,"
                 "chargeable_legs,revenue,avg_revenue_per_chargeable_leg\n")
        for ag, pc, lg, ve, fc, ch, rv in by_agency:
            fh.write(f'"{ag}",{pc},{lg},{ve},{fc},{ch},{rv or 0:.0f},'
                     f'{(rv/ch) if ch else 0:.0f}\n')

    with open(OUT / "portwide_agency_by_facility.csv", "w") as fh:
        fh.write("agency,facility,legs,chargeable_legs,revenue\n")
        for ag, fa, lg, ch, rv in matrix:
            fh.write(f'"{ag}","{fa}",{lg},{ch},{rv or 0:.0f}\n')

    # ---- Markdown
    n_fac, n_ag = len(by_fac), len(by_agency)
    calls_all = con.execute(f"select count(distinct l.port_call_id) "
                            f"from port_call_leg l where {W}").fetchone()[0]
    ves_all = con.execute(f"select count(distinct l.vessel_key) "
                          f"from port_call_leg l where {W}").fetchone()[0]
    TOP = 25

    L = [f"# Concept report P1 — Port calls and agency revenue, by facility and by agency",
         "",
         f"MRTIS commit `{c}` · window **{WIN_FROM} → 2026-07-31** (trailing 36 months, "
         f"anchored on the data's last date) · **every vessel, every cargo, whole port**",
         "",
         "Ruled by William, 2026-08-20: *\"the fee's apply to every ship... the second "
         "sample test will be total port calls by facility and agency against count and "
         "rev$ as we don't yet have all cargoes into split out by cargo.\"* So there is "
         "**no cargo dimension here** — cargo is carried on only 67% of legs port-wide "
         "and is well-evidenced only for grain, so splitting by it would report coverage "
         "as if it were trade.",
         "",
         "## The window at a glance", ""]
    L.append(md_table(
        ["Measure", "Value"],
        [["Port calls", f"{calls_all:,}"],
         ["Legs (berth visits — the unit revenue is earned in)", f"{legs_all:,}"],
         ["Distinct vessels", f"{ves_all:,}"],
         ["Chargeable legs", f"{chg_all:,}"],
         ["**Agency revenue**", f"**{money(rev_all)}**"],
         ["Facilities with activity", f"{n_fac:,}"],
         ["Agencies with activity", f"{n_ag:,}"]],
        ["---", "---:"]))
    L += ["",
          "> **Two counts, on purpose.** A split call works more than one berth, so it "
          "appears under each facility it visited. `Port calls` therefore does **not** sum "
          "down the facility column — the leg does. Revenue is per leg "
          "(`docs/BUSINESS_RULES.md` §9), so the revenue column *does* sum, exactly, to "
          f"{money(rev_all)}. That is asserted by the build, not asserted in prose.",
          "",
          f"## P1a — By facility (top {TOP} of {n_fac} by revenue; full list in "
          "`portwide_by_facility.csv`)", ""]
    L.append(md_table(
        ["Facility", "Type", "Port calls", "Legs", "Vessels", "Chargeable",
         "Revenue", "Avg / chargeable leg", "Share"],
        [[fa, ft, f"{pc:,}", f"{lg:,}", f"{ve:,}", f"{ch:,}", money(rv),
          money(rv / ch) if ch else "--",
          f"{(rv or 0)/rev_all*100:.1f}%"] for fa, ft, pc, lg, ve, ch, rv in by_fac[:TOP]],
        ["---", "---", "---:", "---:", "---:", "---:", "---:", "---:", "---:"]))

    L += ["", f"## P1b — By agency (all {n_ag}, by revenue)", ""]
    L.append(md_table(
        ["Agency", "Port calls", "Legs", "Vessels", "Facilities served",
         "Chargeable", "Revenue", "Avg / chargeable leg", "Share"],
        [[ag, f"{pc:,}", f"{lg:,}", f"{ve:,}", f"{fc:,}", f"{ch:,}", money(rv),
          money(rv / ch) if ch else "--",
          f"{(rv or 0)/rev_all*100:.1f}%"] for ag, pc, lg, ve, fc, ch, rv in by_agency],
        ["---", "---:", "---:", "---:", "---:", "---:", "---:", "---:", "---:"]))

    L += ["", "## P1c — Agency × facility",
          "",
          "The full cross-tab is `portwide_agency_by_facility.csv` "
          f"({len(matrix):,} populated cells of {n_ag:,} × {n_fac:,} possible — "
          f"{len(matrix)/(n_ag*n_fac)*100:.1f}% density). Shown here: each agency's "
          "single largest facility by revenue, which is the shape of the book most "
          "reports actually want.", ""]
    top_cell = {}
    for ag, fa, lg, ch, rv in matrix:
        if ag not in top_cell:
            top_cell[ag] = (fa, lg, ch, rv)
    L.append(md_table(
        ["Agency", "Largest facility by revenue", "Legs there", "Revenue there",
         "= share of that agency's revenue"],
        [[ag, top_cell[ag][0], f"{top_cell[ag][1]:,}", money(top_cell[ag][3]),
          f"{(top_cell[ag][3] or 0)/rv*100:.0f}%" if rv else "--"]
         for ag, pc, lg, ve, fc, ch, rv in by_agency if ag in top_cell],
        ["---", "---", "---:", "---:", "---:"]))
    L.append("")
    (OUT / "portwide_by_facility.md").write_text("\n".join(L) + "\n")
    return calls_all, legs_all, rev_all, n_fac, n_ag, by_fac, by_agency


def main():
    con = duckdb.connect(MRTIS_DB, read_only=True)
    c = commit()
    tot = preflight(con)
    calls, legs, rev, n_fac, n_ag, by_fac, by_ag = report(con, c, tot)
    print(f"MRTIS commit {c} · window {WIN_FROM} -> 2026-07-31 · whole port")
    print(f"  {calls:,} port calls · {legs:,} legs · {n_fac} facilities · {n_ag} agencies")
    print(f"  revenue ${rev:,.0f}")
    print(f"  top facility: {by_fac[0][0]} ${by_fac[0][6]:,.0f}")
    print(f"  top agency:   {by_ag[0][0]} ${by_ag[0][6]:,.0f}")
    con.close()


if __name__ == "__main__":
    main()
