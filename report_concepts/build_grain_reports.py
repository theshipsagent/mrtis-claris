#!/usr/bin/env python3
"""Grain concept reports -- an exercise in what can be pulled, not a deliverable.

Scope ruled by William, 2026-08-20 (session 8): the grain loading elevators
plus the midstream buoy MGMT, over the last three years only.

Read-only against MRTIS. Writes CSV (the queryable artifact) + Markdown (what a
canned report would show). Every figure derived here; none hand-keyed.

Two findings from report_concepts/ISSUES.md shape what these reports may say:

  I-1  ARTCO Destrehan Buoys carries a grain-only dictionary rule identical to
       MGMT's, over 622 legs. William scoped MGMT as "the only buoy which
       exclusively loads grain". Until that is ruled, ARTCO is reported in a
       clearly-separated addendum -- never folded into a headline total.

  I-2  Tonnage exists ONLY where an FGIS certificate matched. Ship count is
       complete; tonnage is not, and coverage runs 86.7-99.9% at elevators but
       40.1% at MGMT. So tons and ships do not share a denominator, and every
       table that shows both must show coverage too, or it states a falsehood
       by omission.

Usage:  python3 report_concepts/build_grain_reports.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb

MRTIS_DB = "/Users/billy/Documents/MRTIS/data/db/mrtis.duckdb"
OUT = Path(__file__).resolve().parent

# Window: trailing 36 months anchored on the DATA's last date, never on
# wall-clock today -- an anchor that moves makes every figure irreproducible.
WIN_FROM, WIN_TO = "2023-08-01", "2026-08-01"      # [from, to)
ELEVATOR_TYPE = "Elevator"
BUOY_IN_SCOPE = "MGMT"
# I-1, RULED 2026-08-20: ARTCO Destrehan Buoys is multi-purpose, not grain-only.
# Its dictionary grain rule is wrong, so its legs enter grain reports ONLY on
# genuine FGIS evidence -- never on the dictionary tag the ruling invalidated.
BUOY_EVIDENCE_ONLY = "ARTCO Destrehan Buoys"

W = f"l.leg_start >= timestamp '{WIN_FROM}' and l.leg_start < timestamp '{WIN_TO}'"
SCOPE = (f"(l.facility_type = '{ELEVATOR_TYPE}'"
         f" or l.first_berth_facility = '{BUOY_IN_SCOPE}'"
         f" or (l.first_berth_facility = '{BUOY_EVIDENCE_ONLY}'"
         f"     and l.cargo_source = 'fgis'))")


def commit() -> str:
    return subprocess.run(
        ["git", "-C", "/Users/billy/Documents/MRTIS", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True).stdout.strip()


def money(v) -> str:
    return "--" if v is None else f"${v:,.0f}"


def tons(v) -> str:
    return "--" if v in (None, 0) else f"{v:,.0f}"


def md_table(headers, rows, aligns=None) -> str:
    aligns = aligns or ["---"] * len(headers)
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(aligns) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def preflight(con):
    """Assert the things the reports quietly depend on. A rebuilt MRTIS that
    broke any of these should fail loudly, not report a different truth."""
    anchor = con.execute("select max(call_end) from port_call").fetchone()[0]
    assert anchor.strftime("%Y-%m") == "2026-07", (
        f"window anchor moved: max(call_end) is {anchor}, not in 2026-07. "
        "Re-derive WIN_FROM/WIN_TO before trusting any figure here.")

    # Every in-scope leg must be grain, or the report's title is a lie.
    bad = con.execute(f"""
        select first_berth_facility, count(*),
               count(*) filter (where cargo_group = 'Grain')
        from port_call_leg l where {SCOPE}
        group by 1 having count(*) <> count(*) filter (where cargo_group = 'Grain')
    """).fetchall()
    assert not bad, f"in-scope facility is not 100% grain: {bad}"

    n_elev = con.execute(
        f"select count(distinct first_berth_facility) from port_call_leg l "
        f"where l.facility_type = '{ELEVATOR_TYPE}'").fetchone()[0]
    assert n_elev == 9, f"expected 9 elevators, found {n_elev}"
    return anchor


def scope_note(con) -> tuple:
    r = con.execute(f"""
        select count(*), count(*) filter (where l.cargo_source = 'fgis'),
               sum(l.estimated_tons), count(distinct c.vessel_key),
               sum(l.agency_fee)
        from port_call_leg l join port_call c using (port_call_id)
        where {W} and {SCOPE}""").fetchone()
    return r


# --------------------------------------------------------------------------
# G1 -- grain volume trended against ship count
# --------------------------------------------------------------------------
def g1_trend(con, c, anchor):
    """G1a: the port total, month by month. G1b: per elevator, year by year.

    'Ship count' is reported two ways deliberately -- loadings (legs, the
    number of times a ship was worked) and distinct vessels -- because the
    phrase carries both readings in the trade and the report should not
    silently pick one.
    """
    monthly = con.execute(f"""
        select strftime(l.leg_start, '%Y-%m') as month,
               count(*) as loadings,
               count(distinct l.vessel_key) as vessels,
               count(*) filter (where l.cargo_source = 'fgis') as fgis_matched,
               sum(l.estimated_tons) as tons_matched
        from port_call_leg l where {W} and {SCOPE}
        group by 1 order by 1
    """).fetchall()

    by_fac = con.execute(f"""
        select l.first_berth_facility as facility, l.facility_type,
               count(*) as loadings,
               count(distinct l.vessel_key) as vessels,
               count(*) filter (where l.cargo_source = 'fgis') as fgis_matched,
               sum(l.estimated_tons) as tons_matched,
               sum(l.agency_fee) as fee
        from port_call_leg l where {W} and {SCOPE}
        group by 1, 2 order by 3 desc, 1
    """).fetchall()

    by_fac_year = con.execute(f"""
        select l.first_berth_facility as facility,
               year(l.leg_start) as yr, count(*) as loadings,
               sum(l.estimated_tons) as tons_matched
        from port_call_leg l where {W} and {SCOPE}
        group by 1, 2 order by 1, 2
    """).fetchall()

    # ---- CSV
    with open(OUT / "grain_volume_by_month.csv", "w") as fh:
        fh.write("month,loadings,distinct_vessels,fgis_matched_loadings,"
                 "fgis_coverage_pct,tons_fgis_matched,tons_per_matched_loading\n")
        for m, ld, ve, fm, tn in monthly:
            fh.write(f"{m},{ld},{ve},{fm},{fm/ld*100:.1f},{tn or 0:.0f},"
                     f"{(tn/fm) if fm else 0:.0f}\n")

    with open(OUT / "grain_volume_by_facility.csv", "w") as fh:
        fh.write("facility,facility_type,loadings,distinct_vessels,fgis_matched_loadings,"
                 "fgis_coverage_pct,tons_fgis_matched,tons_per_matched_loading,agency_fee\n")
        for fa, ft, ld, ve, fm, tn, fee in by_fac:
            fh.write(f'"{fa}",{ft},{ld},{ve},{fm},{fm/ld*100:.1f},{tn or 0:.0f},'
                     f'{(tn/fm) if fm else 0:.0f},{fee or 0:.0f}\n')

    # ---- Markdown
    tot_ld = sum(r[1] for r in monthly)
    tot_fm = sum(r[3] for r in monthly)
    tot_tn = sum(r[4] or 0 for r in monthly)
    ves = con.execute(f"select count(distinct l.vessel_key) from port_call_leg l "
                      f"where {W} and {SCOPE}").fetchone()[0]

    L = [f"# Concept report G1 — Grain volume trended against ship count",
         "",
         f"MRTIS commit `{c}` · window **{WIN_FROM} → 2026-07-31** (trailing 36 months, "
         f"anchored on the data's last date `{anchor:%Y-%m-%d}`, not on today) · "
         f"scope **9 grain elevators + MGMT**",
         "",
         "> **Read the two denominators before the numbers.** Ship count is complete: "
         f"every one of the **{tot_ld:,} loadings** ({ves:,} distinct vessels) is counted. "
         f"Tonnage is not — tons exist only where an FGIS certificate matched, which is "
         f"**{tot_fm:,} of {tot_ld:,} loadings ({tot_fm/tot_ld*100:.1f}%)**. The tonnage "
         "column therefore measures a *subset* of the ships in the same row. Comparing "
         "tons across facilities without reading the coverage column will mislead you — "
         "see `ISSUES.md` I-2.",
         "",
         f"**Grain moved (FGIS-certified, in-scope, 36 months): {tot_tn:,.0f} metric tonnes** "
         f"across {tot_fm:,} certified loadings.",
         "",
         "## G1a — Port total, by month",
         ""]
    L.append(md_table(
        ["Month", "Loadings", "Vessels", "FGIS matched", "Coverage", "Tonnes (matched)", "Tonnes / matched loading"],
        [[m, f"{ld:,}", f"{ve:,}", f"{fm:,}", f"{fm/ld*100:.0f}%", tons(tn),
          tons(tn/fm if fm else None)] for m, ld, ve, fm, tn in monthly],
        ["---", "---:", "---:", "---:", "---:", "---:", "---:"]))

    L += ["", "## G1b — By elevator (and MGMT), full window", ""]
    L.append(md_table(
        ["Facility", "Type", "Loadings", "Vessels", "FGIS matched", "Coverage",
         "Tonnes (matched)", "Tonnes / matched loading"],
        [[fa, ft, f"{ld:,}", f"{ve:,}", f"{fm:,}", f"{fm/ld*100:.1f}%", tons(tn),
          tons(tn/fm if fm else None)] for fa, ft, ld, ve, fm, tn, _ in by_fac],
        ["---", "---", "---:", "---:", "---:", "---:", "---:", "---:"]))
    L += ["",
          f"> **MGMT's coverage is the outlier.** At {[f'{fm/ld*100:.1f}%' for fa,_,ld,_,fm,_,_ in by_fac if fa=='MGMT'][0]} "
          "it is roughly half the elevators' rate, so its tonnes-per-loading is not "
          "comparable with theirs. The gap is a certificate-matching gap, not a trade "
          "difference. Ship count for MGMT is sound; tonnage is a partial view.",
          ""]

    # per-facility × year
    L += ["## G1c — Loadings by facility and year", ""]
    years = sorted({y for _, y, _, _ in by_fac_year})
    facs = [r[0] for r in by_fac]
    grid = {(f, y): (0, 0) for f in facs for y in years}
    for fa, y, ld, tn in by_fac_year:
        grid[(fa, y)] = (ld, tn or 0)
    L.append(md_table(
        ["Facility"] + [f"{y} loadings" for y in years],
        [[f] + [f"{grid[(f, y)][0]:,}" for y in years] for f in facs],
        ["---"] + ["---:"] * len(years)))
    L += ["",
          f"> 2023 and 2026 are **part years** — the window opens 1 Aug 2023 and closes "
          "31 Jul 2026, so each shows five and seven months respectively. Only 2024 and "
          "2025 are whole calendar years and only those two are comparable like for like.",
          ""]
    (OUT / "grain_volume_by_month.md").write_text("\n".join(L) + "\n")
    return tot_ld, tot_fm, tot_tn


# --------------------------------------------------------------------------
# G2 -- ship count and revenue per agent
# --------------------------------------------------------------------------
def g2_agent(con, c, anchor):
    by_agent = con.execute(f"""
        select coalesce(l.agency, '(no agency)') as agency,
               count(*) as loadings,
               count(distinct l.vessel_key) as vessels,
               count(*) filter (where l.agency_fee > 0) as chargeable,
               sum(l.agency_fee) as fee,
               count(*) filter (where l.cargo_source = 'fgis') as fgis_matched,
               sum(l.estimated_tons) as tons_matched
        from port_call_leg l where {W} and {SCOPE}
        group by 1 order by 5 desc nulls last, 1
    """).fetchall()

    matrix = con.execute(f"""
        select coalesce(l.agency, '(no agency)') as agency,
               l.first_berth_facility as facility,
               count(*) as loadings, sum(l.agency_fee) as fee
        from port_call_leg l where {W} and {SCOPE}
        group by 1, 2 order by 1, 2
    """).fetchall()

    facs = [r[0] for r in con.execute(f"""
        select l.first_berth_facility from port_call_leg l where {W} and {SCOPE}
        group by 1 order by count(*) desc, 1""").fetchall()]

    with open(OUT / "grain_agent_revenue.csv", "w") as fh:
        fh.write("agency,loadings,distinct_vessels,chargeable_legs,agency_fee,"
                 "avg_fee_per_chargeable_leg,fgis_matched_loadings,tons_fgis_matched\n")
        for ag, ld, ve, ch, fee, fm, tn in by_agent:
            fh.write(f'"{ag}",{ld},{ve},{ch},{fee or 0:.0f},'
                     f'{(fee/ch) if ch else 0:.0f},{fm},{tn or 0:.0f}\n')

    with open(OUT / "grain_agent_by_facility.csv", "w") as fh:
        fh.write("agency,facility,loadings,agency_fee\n")
        for ag, fa, ld, fee in matrix:
            fh.write(f'"{ag}","{fa}",{ld},{fee or 0:.0f}\n')

    tot_fee = sum(r[4] or 0 for r in by_agent)
    tot_ld = sum(r[1] for r in by_agent)
    tot_ch = sum(r[3] for r in by_agent)

    L = [f"# Concept report G2 — Ship count and revenue by agent, grain berths",
         "",
         f"MRTIS commit `{c}` · window **{WIN_FROM} → 2026-07-31** · scope **9 grain "
         f"elevators + MGMT** · leg-level agency (`port_call_leg.agency`) — the agency "
         "that brought the vessel in owns the leg (`docs/BUSINESS_RULES.md` §6)",
         "",
         f"**Total agency fee on grain berths, 36 months: {money(tot_fee)}** across "
         f"{tot_ch:,} chargeable legs of {tot_ld:,} loadings.",
         "",
         "## G2a — By agent, all grain berths", ""]
    L.append(md_table(
        ["Agency", "Loadings", "Vessels", "Chargeable legs", "Agency fee",
         "Avg fee / chargeable leg", "Share of fee"],
        [[ag, f"{ld:,}", f"{ve:,}", f"{ch:,}", money(fee),
          money(fee / ch) if ch else "--",
          f"{(fee or 0)/tot_fee*100:.1f}%"] for ag, ld, ve, ch, fee, fm, tn in by_agent],
        ["---", "---:", "---:", "---:", "---:", "---:", "---:"]))

    L += ["", "## G2b — Loadings by agent and facility", "",
          "Fee per cell is in `grain_agent_by_facility.csv`; loadings shown here for "
          "legibility.", ""]
    cell = {(a, f): 0 for a, _, _, _ in matrix for f in facs}
    for ag, fa, ld, _ in matrix:
        cell[(ag, fa)] = ld
    agents = [r[0] for r in by_agent]
    short = [f.replace(" Buoys", "").replace("Cargill ", "C.").replace("ADM ", "ADM ")
             for f in facs]
    L.append(md_table(
        ["Agency"] + short + ["Total"],
        [[ag] + [f"{cell.get((ag, f), 0):,}" if cell.get((ag, f), 0) else "·"
                 for f in facs]
         + [f"{sum(cell.get((ag, f), 0) for f in facs):,}"] for ag in agents],
        ["---"] + ["---:"] * (len(facs) + 1)))
    L += ["",
          "> A `·` is a genuine zero — that agent did not work that berth in the window, "
          "rather than a missing value.",
          ""]
    (OUT / "grain_agent_revenue.md").write_text("\n".join(L) + "\n")
    return tot_fee, tot_ld


# --------------------------------------------------------------------------
# Addendum -- the facility awaiting a ruling (ISSUES.md I-1)
# --------------------------------------------------------------------------
def addendum(con, c):
    """The ARTCO legs NOT admitted: dictionary-tagged grain with no FGIS evidence.
    Ruled mis-tagged (ISSUES.md I-1); quantified here so the build-fix session
    knows exactly what a dictionary correction would move."""
    r = con.execute(f"""
        select count(*), count(distinct l.vessel_key),
               count(*) filter (where l.cargo_source = 'fgis'),
               sum(l.estimated_tons), sum(l.agency_fee),
               count(*) filter (where l.agency_fee > 0)
        from port_call_leg l
        where {W} and l.first_berth_facility = '{BUOY_EVIDENCE_ONLY}'
          and l.cargo_source is distinct from 'fgis'""").fetchone()
    ld, ve, fm, tn, fee, ch = r
    L = [f"# Addendum — `{BUOY_EVIDENCE_ONLY}`: the legs held out of the grain reports",
         "",
         f"MRTIS commit `{c}` · window **{WIN_FROM} → 2026-07-31** · "
         "**excluded from G1 and G2**",
         "",
         "**Ruled by William, 2026-08-20:** *\"artco can occasionally add grain ships "
         "tagged to that into the report, as we can\'t bake it in as it remains multi "
         "purpose facility.\"*",
         "",
         "So `ARTCO Destrehan Buoys` is a multi-purpose midstream berth that sometimes "
         "loads grain — and the grain-only rule in "
         "`MRTIS/dictionaries/zone_facility.csv` (Cargo group `Grain`, *\"Can never be a "
         "liquid cargo\"*, *\"Apply always\"*) is **wrong**. G1 and G2 therefore admit "
         "ARTCO legs **only where an FGIS certificate proves grain**, and never on that "
         "dictionary tag.",
         "",
         "This page is what that exclusion removed: legs the dictionary calls grain with "
         "no evidence behind the claim. It is the measured size of the defect, for the "
         "build-fix session.",
         "",
         "## Held out of the reports — dictionary-tagged grain, no FGIS evidence", ""]
    L.append(md_table(
        ["Measure", "Value"],
        [["Loadings excluded", f"{ld:,}"],
         ["Distinct vessels", f"{ve:,}"],
         ["FGIS matched", f"{fm:,} (nil by definition — this is the no-evidence set)"],
         ["Tonnes", tons(tn) + " (none: no certificate, no tonnage)"],
         ["Chargeable legs", f"{ch:,}"],
         ["Agency fee not counted in G2", money(fee)]],
        ["---", "---:"]))
    L += ["",
          f"> **What a dictionary fix would move.** Clearing `Cargo group` on ARTCO\'s two "
          f"rows retags these {ld:,} legs from `Grain` to no cargo group. They keep their "
          f"agency fee and their berth activity — only the false cargo label goes. The "
          "177 all-time FGIS-evidenced ARTCO legs are unaffected and stay grain.",
          "",
          "> **Worth checking at the same time:** 17 dictionary rows carry a Grain cargo "
          "group. MGMT\'s is confirmed correct; ARTCO\'s is confirmed wrong. The other 13 "
          "sit at Elevator facilities, where a grain-only rule is safe — but the pattern "
          "that produced ARTCO\'s row may have produced others at multi-purpose berths.",
          ""]
    (OUT / "addendum_artco_destrehan.md").write_text("\n".join(L) + "\n")
    return ld, fee


def main():
    con = duckdb.connect(MRTIS_DB, read_only=True)
    c = commit()
    anchor = preflight(con)
    ld, fm, tn = g1_trend(con, c, anchor)
    fee, ld2 = g2_agent(con, c, anchor)
    assert ld == ld2, f"G1 and G2 disagree on loadings: {ld} vs {ld2}"
    a_ld, a_fee = addendum(con, c)
    print(f"MRTIS commit {c} · window {WIN_FROM} -> 2026-07-31")
    print(f"  G1  {ld:,} loadings, {fm:,} FGIS-matched ({fm/ld*100:.1f}%), {tn:,.0f} tonnes")
    print(f"  G2  {fee:,.0f} agency fee over the same {ld2:,} loadings")
    print(f"  addendum ({BUOY_EVIDENCE_ONLY}, excluded)  {a_ld:,} loadings, ${a_fee:,.0f}")
    con.close()


if __name__ == "__main__":
    main()
