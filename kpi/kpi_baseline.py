#!/usr/bin/env python3
"""Baseline measurements for the SWP-to-SWP KPI design conversation.

Why this exists
---------------
`docs/KPI_DESIGN_BRIEF.md` asks William to rule on how time between SWP
crossings should be measured. Those rulings turn on numbers -- how much of
the clock is already attributed, how much is not, how many rows would fall
foul of each candidate filter -- and a design brief carrying hand-keyed
numbers is exactly the defect session 4 removed from this package
(`figures.py`'s docstring). So the brief quotes; this module derives.

This is deliberately NOT part of `figures.py`. `figures.py` derives the
figures the package *publishes* to its reviewer, and its fee self-check
guards the deliverable. Nothing here is published to the Claris reviewer:
it is raw material for a design conversation that has taken no rulings yet.
Keeping the two apart means a KPI question in flight can never destabilise a
figure the reviewer is already holding.

Nothing here proposes a rule. Where a measurement implies a choice, the
choice is written up as an open question in the brief, for William.

READ-ONLY against MRTIS, per CLAUDE.md prime directive #2.

Usage:
    python3 kpi/kpi_baseline.py                # writes docs/KPI_BASELINE.md
    python3 kpi/kpi_baseline.py --json         # dump the raw dict
    python3 kpi/kpi_baseline.py --check-brief  # assert the brief's figures still hold
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import duckdb

MRTIS_ROOT = Path("/Users/billy/Documents/MRTIS")
MRTIS_DB = MRTIS_ROOT / "data" / "db" / "mrtis.duckdb"
REPO = Path(__file__).resolve().parent.parent
BASELINE_MD = REPO / "docs" / "KPI_BASELINE.md"
BASELINE_JSON = REPO / "docs" / "kpi_baseline.json"
BRIEF_MD = REPO / "docs" / "KPI_DESIGN_BRIEF.md"

# The five time buckets MRTIS stores on a leg today (PORT_CALL_SPEC.md §6).
BUCKETS = ("waiting_hours", "inter_berth_idle_hours", "outbound_idle_hours",
           "berth_hours", "layberth_hours")
BUCKET_SUM = " + ".join(f"COALESCE({b}, 0)" for b in BUCKETS)


def mrtis_commit() -> str:
    return subprocess.run(
        ["git", "-C", str(MRTIS_ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True).stdout.strip()


def derive(db: str) -> dict:
    con = duckdb.connect(db, read_only=True)

    def one(sql: str) -> dict:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row))

    def rows(sql: str) -> list[dict]:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    f: dict = {"mrtis_commit": mrtis_commit()}

    # --- population -------------------------------------------------------
    f["population"] = one("""
        SELECT COUNT(*)                                                    AS calls,
               SUM(is_commercial_call)::INT                                AS commercial,
               SUM(NOT is_commercial_call)::INT                            AS layup,
               SUM(call_status = 'complete')::INT                          AS complete,
               SUM(call_status = 'open_end')::INT                          AS open_end,
               SUM(is_commercial_call AND call_status = 'complete')::INT    AS commercial_complete,
               SUM(is_split)::INT                                          AS split,
               COUNT(DISTINCT vessel_key)                                  AS vessels,
               MIN(call_start)                                             AS window_start,
               MAX(call_end)                                               AS window_end
        FROM port_call""")
    f["population"]["legs"] = one("SELECT COUNT(*) AS n FROM port_call_leg")["n"]

    # --- does the clock close? -------------------------------------------
    # Legs tile the call exactly: leg 1 starts at call_start, the last leg
    # ends at call_end (asserted below). So call-level time accounting is
    # entirely a question about the leg buckets.
    f["tiling"] = one("""
        SELECT SUM(l.leg_seq = 1 AND l.leg_start = c.call_start)::INT              AS leg1_at_call_start,
               SUM(l.leg_seq = 1)::INT                                             AS leg1_count,
               SUM(l.leg_seq = l.leg_count AND l.leg_end = c.call_end)::INT        AS lastleg_at_call_end,
               SUM(l.leg_seq = l.leg_count)::INT                                   AS lastleg_count
        FROM port_call_leg l JOIN port_call c USING (port_call_id)""")

    f["accounting"] = one(f"""
        SELECT ROUND(SUM(leg_hours), 0)                                    AS leg_hours,
               ROUND(SUM({BUCKET_SUM}), 0)                                 AS bucketed_hours,
               ROUND(SUM(leg_hours - ({BUCKET_SUM})), 0)                   AS unattributed_hours,
               ROUND(100 * SUM(leg_hours - ({BUCKET_SUM})) / SUM(leg_hours), 1) AS unattributed_pct,
               ROUND(QUANTILE_CONT(leg_hours - ({BUCKET_SUM}), 0.5), 1)    AS p50_unattributed,
               SUM((leg_hours - ({BUCKET_SUM})) < -0.01)::INT              AS legs_over_attributed
        FROM port_call_leg WHERE leg_hours IS NOT NULL""")

    f["buckets"] = one(f"""
        SELECT {', '.join(f'ROUND(SUM(COALESCE({b},0)), 0) AS {b}' for b in BUCKETS)}
        FROM port_call_leg""")

    f["by_shape"] = rows(f"""
        SELECT CASE WHEN berth_stop_count = 0 AND COALESCE(layberth_hours,0) = 0 THEN 'never reached a berth'
                    WHEN berth_stop_count = 0                                    THEN 'layberth stops only'
                    ELSE 'worked a berth' END                                AS shape,
               COUNT(*)                                                      AS legs,
               ROUND(SUM(leg_hours), 0)                                      AS leg_hours,
               ROUND(SUM(leg_hours - ({BUCKET_SUM})), 0)                     AS unattributed_hours,
               ROUND(100 * SUM(leg_hours - ({BUCKET_SUM})) / SUM(leg_hours), 1) AS unattributed_pct
        FROM port_call_leg GROUP BY 1 ORDER BY legs DESC""")

    # Where the unattributed time sits, on legs that actually worked a berth.
    f["stretches"] = one("""
        SELECT COUNT(*)                                                                          AS legs,
               ROUND(SUM(DATE_DIFF('minute', leg_start, berth_arrive_time) / 60.0), 0)           AS approach_hours,
               ROUND(SUM(COALESCE(waiting_hours, 0)), 0)                                         AS approach_waiting,
               ROUND(SUM(DATE_DIFF('minute', berth_depart_time, leg_end) / 60.0), 0)             AS departure_hours,
               ROUND(SUM(COALESCE(outbound_idle_hours, 0)), 0)                                   AS departure_idle
        FROM port_call_leg
        WHERE berth_arrive_time IS NOT NULL AND berth_depart_time IS NOT NULL""")
    s = f["stretches"]
    s["approach_unclassified"] = round(s["approach_hours"] - s["approach_waiting"])
    s["departure_unclassified"] = round(s["departure_hours"] - s["departure_idle"])

    # Dwell exists only where the feed records a stop; the rest is underway.
    f["dwell_sources"] = rows("""
        SELECT CASE WHEN is_berth_stop THEN 'berth stop'
                    WHEN is_anchorage  THEN 'anchorage'
                    ELSE 'transit / SWP crossing' END        AS event_class,
               COUNT(*)                                      AS events,
               ROUND(SUM(COALESCE(dwell_hours, 0)), 0)       AS dwell_hours
        FROM port_call_event WHERE port_call_id IS NOT NULL
        GROUP BY 1 ORDER BY dwell_hours DESC""")

    # --- candidate headline KPIs, measured as they would be today ---------
    f["headline"] = one("""
        SELECT COUNT(*)                                                                     AS calls,
               ROUND(QUANTILE_CONT(call_hours, 0.5), 1)                                     AS p50_call_hours,
               ROUND(QUANTILE_CONT(call_hours, 0.9), 1)                                     AS p90_call_hours
        FROM port_call WHERE is_commercial_call AND call_status = 'complete'""")
    f["approach_depart"] = one("""
        SELECT ROUND(QUANTILE_CONT(DATE_DIFF('minute', c.call_start, l.berth_arrive_time) / 60.0, 0.5), 1) AS p50_swp_to_first_berth,
               ROUND(QUANTILE_CONT(DATE_DIFF('minute', l.berth_depart_time, c.call_end) / 60.0, 0.5), 1)  AS p50_last_sailing_to_swp
        FROM port_call c JOIN port_call_leg l USING (port_call_id)
        WHERE c.is_commercial_call AND c.call_status = 'complete' AND NOT c.is_split
          AND l.berth_arrive_time IS NOT NULL AND l.berth_depart_time IS NOT NULL""")
    f["by_type"] = rows("""
        SELECT vessel_type, COUNT(*) AS calls,
               ROUND(QUANTILE_CONT(call_hours, 0.5), 1) AS p50_hours,
               ROUND(QUANTILE_CONT(call_hours, 0.9), 1) AS p90_hours
        FROM port_call WHERE is_commercial_call AND call_status = 'complete'
        GROUP BY 1 ORDER BY calls DESC LIMIT 6""")

    # --- the sequence dimension ------------------------------------------
    f["sequence"] = one("""
        WITH c AS (SELECT vessel_key, call_start,
                          LAG(call_end) OVER (PARTITION BY vessel_key ORDER BY call_start) AS prev_end
                   FROM port_call)
        SELECT COUNT(*) FILTER (WHERE prev_end IS NOT NULL)                                       AS calls_with_predecessor,
               ROUND(QUANTILE_CONT(DATE_DIFF('minute', prev_end, call_start) / 60.0, 0.5), 1)     AS p50_gap_hours,
               ROUND(QUANTILE_CONT(DATE_DIFF('minute', prev_end, call_start) / 60.0, 0.9), 1)     AS p90_gap_hours,
               SUM(DATE_DIFF('minute', prev_end, call_start) < 0)::INT                            AS overlapping_calls
        FROM c WHERE prev_end IS NOT NULL""")
    f["sequence"]["single_call_vessels"] = one("""
        SELECT COUNT(*) AS n FROM (SELECT vessel_key FROM port_call
        GROUP BY 1 HAVING COUNT(*) = 1)""")["n"]
    f["sequence"]["vessels"] = f["population"]["vessels"]

    # --- traps a KPI framework has to rule on ----------------------------
    f["traps"] = one("""
        SELECT (SELECT COUNT(*) FROM port_call_leg WHERE leg_hours <= 0)                       AS nonpositive_leg_hours,
               (SELECT COUNT(*) FROM port_call_leg WHERE berth_hours < 0)                      AS negative_berth_hours,
               (SELECT COUNT(*) FROM port_call WHERE call_status = 'complete' AND call_hours < 1) AS calls_under_one_hour,
               (SELECT ROUND(SUM(call_hours), 0) FROM port_call WHERE call_status = 'open_end') AS open_end_hours,
               (SELECT COUNT(*) FROM port_call WHERE call_start < TIMESTAMP '2019-02-01')      AS calls_in_first_month,
               (SELECT COUNT(*) FROM port_call WHERE call_start > TIMESTAMP '2026-07-01')      AS calls_in_last_month,
               (SELECT COUNT(*) FROM port_call_leg WHERE berth_arrive_time IS NULL)            AS legs_no_berth_arrival,
               (SELECT COUNT(*) FROM port_call_leg WHERE activity IS NULL)                     AS legs_unresolved_activity,
               (SELECT COUNT(*) FROM port_call_leg WHERE COALESCE(layberth_hours,0) > 0 AND berth_stop_count > 0) AS legs_mixed_layberth""")
    f["unplaced"] = rows("""
        SELECT unassigned_reason, COUNT(*) AS events FROM port_call_event
        WHERE port_call_id IS NULL GROUP BY 1 ORDER BY events DESC""")

    # --- denominators for any rate KPI -----------------------------------
    f["denominators"] = one("""
        SELECT COUNT(*)                                    AS commercial_legs,
               SUM(l.estimated_tons IS NOT NULL)::INT      AS legs_with_estimated_tons,
               SUM(l.actual_tons IS NOT NULL)::INT         AS legs_with_actual_tons,
               ROUND(100.0 * SUM(l.estimated_tons IS NOT NULL) / COUNT(*), 1) AS pct_with_tons
        FROM port_call_leg l JOIN port_call c USING (port_call_id)
        WHERE c.is_commercial_call""")
    f["denominators"]["berth_facilities"] = one("""
        SELECT COUNT(DISTINCT facility) AS n FROM port_call_event WHERE is_berth_stop""")["n"]

    # --- guardrails on this module's own reading --------------------------
    t = f["tiling"]
    assert t["leg1_at_call_start"] == t["leg1_count"], "leg 1 does not start at call_start"
    assert t["lastleg_at_call_end"] == t["lastleg_count"], "last leg does not end at call_end"
    assert f["accounting"]["unattributed_hours"] > 0, "expected an unattributed remainder"
    assert f["sequence"]["overlapping_calls"] == 0, "per-vessel calls overlap in time"

    con.close()
    return f


def render(f: dict) -> str:
    p, a, b, s, tr, d, q = (f["population"], f["accounting"], f["buckets"],
                            f["stretches"], f["traps"], f["denominators"], f["sequence"])
    L = [
        "# KPI baseline — measurements behind the design brief",
        "",
        "Raw material for [`KPI_DESIGN_BRIEF.md`](KPI_DESIGN_BRIEF.md).",
        "**Generated by `kpi/kpi_baseline.py` — do not hand-edit.**",
        "",
        "Nothing here is a rule, a target or a published figure. These are",
        "measurements of what MRTIS stores today, taken so the design questions",
        "in the brief can be argued from numbers rather than from impressions.",
        "The package's *published* figures live in [`FIGURES.md`](FIGURES.md),",
        "derived separately by `figures.py`.",
        "",
        f"MRTIS commit: `{f['mrtis_commit']}`",
        "",
        "---",
        "",
        "## 1. Population",
        "",
        "| | Count |",
        "|---|---:|",
        f"| Port calls | {p['calls']:,} |",
        f"| — commercial | {p['commercial']:,} |",
        f"| — lay-up (flagged, non-commercial) | {p['layup']:,} |",
        f"| — complete (both SWP crossings seen) | {p['complete']:,} |",
        f"| — open-ended (one crossing missing) | {p['open_end']:,} |",
        f"| — **commercial AND complete** (the safe duration population) | **{p['commercial_complete']:,}** |",
        f"| Split calls | {p['split']:,} |",
        f"| Legs | {p['legs']:,} |",
        f"| Distinct vessels | {p['vessels']:,} |",
        "",
        f"Window: `{p['window_start']}` → `{p['window_end']}`.",
        "",
        "## 2. The clock does not close",
        "",
        "Legs tile the call exactly — leg 1 starts at `call_start` and the last leg",
        f"ends at `call_end`, verified on all {p['calls']:,} calls — so call-level time",
        "accounting is entirely a question about the five leg buckets.",
        "",
        "| | Hours |",
        "|---|---:|",
        f"| Elapsed leg time (`leg_hours`) | {a['leg_hours']:,.0f} |",
        f"| Sum of the five stored buckets | {a['bucketed_hours']:,.0f} |",
        f"| **Unattributed remainder** | **{a['unattributed_hours']:,.0f}** |",
        f"| Remainder as a share of elapsed time | **{a['unattributed_pct']}%** |",
        f"| Median remainder per leg | {a['p50_unattributed']} |",
        f"| Legs where the buckets exceed elapsed time | {a['legs_over_attributed']:,} |",
        "",
        "### The five buckets, as stored",
        "",
        "| Bucket | Hours |",
        "|---|---:|",
    ]
    for k in BUCKETS:
        L.append(f"| `{k}` | {b[k]:,.0f} |")
    L += [
        "",
        "### Why: dwell exists only where the feed records a stop",
        "",
        "| Event class | Events | Dwell hours |",
        "|---|---:|---:|",
    ]
    for r in f["dwell_sources"]:
        L.append(f"| {r['event_class']} | {r['events']:,} | {r['dwell_hours']:,.0f} |")
    L += [
        "",
        "A vessel underway between two recorded stops is in no bucket at all.",
        "",
        "### Where the remainder sits, by leg shape",
        "",
        "| Leg shape | Legs | Elapsed hours | Unattributed | Share |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in f["by_shape"]:
        L.append(f"| {r['shape']} | {r['legs']:,} | {r['leg_hours']:,.0f} | "
                 f"{r['unattributed_hours']:,.0f} | {r['unattributed_pct']}% |")
    L += [
        "",
        "### The two open stretches, on legs that worked a berth",
        "",
        f"Measured across {s['legs']:,} legs with both a recorded berth arrival and departure.",
        "",
        "| Stretch | Elapsed | Classified | Unclassified |",
        "|---|---:|---:|---:|",
        f"| Leg start → first berth arrival | {s['approach_hours']:,.0f} | "
        f"{s['approach_waiting']:,.0f} (`waiting_hours`) | **{s['approach_unclassified']:,.0f}** |",
        f"| Last sailing → leg end | {s['departure_hours']:,.0f} | "
        f"{s['departure_idle']:,.0f} (`outbound_idle_hours`) | **{s['departure_unclassified']:,.0f}** |",
        "",
        "## 3. Candidate headline KPIs, measured as they stand today",
        "",
        f"On the {f['headline']['calls']:,} commercial, complete calls:",
        "",
        "| | Median | p90 |",
        "|---|---:|---:|",
        f"| SWP-to-SWP hours | {f['headline']['p50_call_hours']} | {f['headline']['p90_call_hours']} |",
        "",
        "| | Median |",
        "|---|---:|",
        f"| SWP entry → first berth arrival (single-leg calls) | {f['approach_depart']['p50_swp_to_first_berth']} |",
        f"| Last sailing → SWP exit (single-leg calls) | {f['approach_depart']['p50_last_sailing_to_swp']} |",
        "",
        "| Vessel type | Calls | Median hours | p90 hours |",
        "|---|---:|---:|---:|",
    ]
    for r in f["by_type"]:
        L.append(f"| {r['vessel_type'] or '(none recorded)'} | {r['calls']:,} | "
                 f"{r['p50_hours']} | {r['p90_hours']} |")
    L += [
        "",
        "## 4. The sequence dimension",
        "",
        "| | |",
        "|---|---:|",
        f"| Distinct vessels | {q['vessels']:,} |",
        f"| Calls with an earlier call by the same vessel in-window | {q['calls_with_predecessor']:,} |",
        f"| Vessels seen exactly once | {q['single_call_vessels']:,} |",
        f"| Median gap, previous SWP exit → next SWP entry (hours) | {q['p50_gap_hours']:,.1f} |",
        f"| p90 gap (hours) | {q['p90_gap_hours']:,.1f} |",
        f"| Overlapping calls for one vessel | {q['overlapping_calls']} |",
        "",
        "## 5. Traps a KPI framework has to rule on",
        "",
        "| | Count |",
        "|---|---:|",
        f"| Legs with `leg_hours <= 0` | {tr['nonpositive_leg_hours']:,} |",
        f"| Legs with negative `berth_hours` | {tr['negative_berth_hours']:,} |",
        f"| Complete calls shorter than one hour | {tr['calls_under_one_hour']:,} |",
        f"| Hours sitting on open-ended (truncated) calls | {tr['open_end_hours']:,.0f} |",
        f"| Calls starting in the first month of the window | {tr['calls_in_first_month']:,} |",
        f"| Calls starting in the last month of the window | {tr['calls_in_last_month']:,} |",
        f"| Legs with no recorded berth arrival | {tr['legs_no_berth_arrival']:,} |",
        f"| Legs whose activity never resolved | {tr['legs_unresolved_activity']:,} |",
        f"| Legs mixing layberth and working stops | {tr['legs_mixed_layberth']:,} |",
        "",
        "| Events outside any call | Count |",
        "|---|---:|",
    ]
    for r in f["unplaced"]:
        L.append(f"| `{r['unassigned_reason']}` | {r['events']:,} |")
    L += [
        "",
        "## 6. Denominators available for rate KPIs",
        "",
        "| | |",
        "|---|---:|",
        f"| Commercial legs | {d['commercial_legs']:,} |",
        f"| — with an estimated tonnage (FGIS grain match) | {d['legs_with_estimated_tons']:,} ({d['pct_with_tons']}%) |",
        f"| — with an actual tonnage | {d['legs_with_actual_tons']:,} |",
        f"| Distinct berth facilities | {d['berth_facilities']:,} |",
        "",
    ]
    return "\n".join(L) + "\n"


def check_brief(f: dict) -> int:
    """Assert the figures the brief quotes still match what MRTIS says."""
    if not BRIEF_MD.exists():
        print(f"no brief at {BRIEF_MD} — nothing to check")
        return 0
    text = BRIEF_MD.read_text()
    a, p, s, tr, q, d = (f["accounting"], f["population"], f["stretches"],
                         f["traps"], f["sequence"], f["denominators"])
    expect = {
        "unattributed hours": f"{a['unattributed_hours']:,.0f}",
        "unattributed share": f"{a['unattributed_pct']}%",
        "elapsed leg hours": f"{a['leg_hours']:,.0f}",
        "commercial+complete calls": f"{p['commercial_complete']:,}",
        "open-ended calls": f"{p['open_end']:,}",
        "lay-up calls": f"{p['layup']:,}",
        "approach unclassified": f"{s['approach_unclassified']:,}",
        "departure unclassified": f"{s['departure_unclassified']:,}",
        "non-positive leg hours": f"{tr['nonpositive_leg_hours']:,}",
        "vessels seen once": f"{q['single_call_vessels']:,}",
        "legs with tonnage": f"{d['legs_with_estimated_tons']:,}",
    }
    missing = [f"{k} ({v})" for k, v in expect.items()
               if not re.search(rf"(?<![\d,]){re.escape(v)}(?![\d])", text)]
    if missing:
        print("BRIEF IS STALE — these derived figures no longer appear in it:")
        for m in missing:
            print(f"  - {m}")
        return 1
    print(f"brief checked: {len(expect)} derived figures still match MRTIS "
          f"at {f['mrtis_commit'][:7]}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="dump the derived dict as JSON")
    ap.add_argument("--check-brief", action="store_true",
                    help="assert the design brief's figures still match MRTIS")
    ap.add_argument("--db", default=str(MRTIS_DB))
    args = ap.parse_args()

    f = derive(args.db)

    if args.check_brief:
        sys.exit(check_brief(f))

    if args.json:
        print(json.dumps(f, indent=2, default=str))
        return

    BASELINE_MD.write_text(render(f))
    BASELINE_JSON.write_text(json.dumps(f, indent=2, default=str) + "\n")
    print(f"-> {BASELINE_MD}")
    print(f"-> {BASELINE_JSON}")
    print(f"   {f['accounting']['unattributed_hours']:,.0f} h "
          f"({f['accounting']['unattributed_pct']}%) of leg time sits in no bucket")


if __name__ == "__main__":
    main()
