#!/usr/bin/env python3
"""Single source of truth for every published figure in this package.

Why this exists
---------------
Sessions 1-3 hard-coded dollar figures and percentages into
`docs/BUSINESS_RULES.md`, `charts/build_charts.py` and
`reports/build_reports.py`. When MRTIS rebuilt (session 3), every one of them
went stale at once, and audit #2 found several that had *never* re-derived
(A7, A8, A14) plus a comment claiming a verification the script did not
perform (A10). Hard-coding is the defect; this module is the fix.

Everything below is derived live from MRTIS's DuckDB, read-only. Charts,
reports and the rules doc all read from here, so a figure can only ever be
wrong in one place, and re-running after an MRTIS rebuild re-derives all of
them together.

The fee attribution self-proves
-------------------------------
`fee_rules()` re-implements William's §12 schedule in SQL and then asserts,
per leg, that its answer equals the `agency_fee` MRTIS actually stored. If
the two ever disagree -- because MRTIS's `agency_fee_for()` changed and this
package hasn't caught up -- it raises rather than publishing a plausible
wrong number. That assertion is the thing A10 claimed and didn't do.

READ-ONLY against MRTIS, per CLAUDE.md prime directive #2.

Usage:
    python3 figures.py            # writes docs/FIGURES.md
    python3 figures.py --json     # dump the raw dict
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import duckdb

MRTIS_ROOT = Path("/Users/billy/Documents/MRTIS")
MRTIS_DB = MRTIS_ROOT / "data" / "db" / "mrtis.duckdb"
REPO = Path(__file__).resolve().parent

# William's §12 schedule, transcribed from MRTIS scripts/build_db.py's
# SHIP_TYPE_FEE_TIERS / CANONICAL_FEE_FALLBACK. Kept here only so the
# rule-by-rule breakdown can be *attributed*; the fee itself always comes from
# MRTIS, and fee_rules() asserts the two agree.
R1_SHIP_TYPES = ("Passenger/Cruise",)
R2_SHIP_TYPES = ("Ro-Ro Cargo Ship", "Vehicles Carrier",
                 "General Cargo Ship (with Ro-Ro facility)")
R3_SHIP_TYPES = ("Container Ship (Fully Cellular)",
                 "Container Ship (Fully Cellular/Ro-Ro Facility)")
R4_SHIP_TYPES = ("Refrigerated Cargo Ship",)
RULE_FEE = {"R1": 2500.0, "R2": 1000.0, "R3": 750.0, "R4": 5000.0, "R5": 5000.0}
RULE_LABEL = {
    "R1": "R1 Passenger/Cruise",
    "R2": "R2 Ro-Ro / Vehicles Carrier / Gen-Cargo w. Ro-Ro",
    "R3": "R3 Container (Fully Cellular)",
    "R4": "R4 Refrigerated Cargo Ship",
    "R5": "R5 Bulk @ General Cargo berth",
    "BASE": "Base tiers ($10,500 / $3,500)",
}
AGENCY_FEE_BULK = 10_500.0
AGENCY_FEE_OTHER = 3_500.0


def _sql_in(values) -> str:
    return ", ".join("'" + v.replace("'", "''") + "'" for v in values)


# Classifies every leg into the rule that priced it, and computes what the
# same leg would have billed under the pre-§12 two-tier schedule. The
# precedence here mirrors agency_fee_for() exactly: R5 first (§12.3.3.3),
# then the register's ship_type, then -- only when there is no register row
# at all -- the canonical fallback. Note the base-tier CASE consults
# ship_type_group ONLY when vessel_type is absent: it is a fallback, not an
# alternative (audit finding A4).
LEG_CLASSIFIED = f"""
with leg as (
    select l.leg_id, l.port_call_id, l.agency_fee, l.facility_type,
           l.first_berth_facility, l.agency, l.activity,
           pc.vessel_type as vt, pc.ship_type as st,
           pc.ship_type_group as stg, pc.imo
    from port_call_leg l
    join port_call pc using (port_call_id)
)
select *,
    case
        when vt = 'Bulk' and facility_type = 'General Cargo'          then 'R5'
        when coalesce(st,'') <> '' and st in ({_sql_in(R1_SHIP_TYPES)}) then 'R1'
        when coalesce(st,'') <> '' and st in ({_sql_in(R2_SHIP_TYPES)}) then 'R2'
        when coalesce(st,'') <> '' and st in ({_sql_in(R3_SHIP_TYPES)}) then 'R3'
        when coalesce(st,'') <> '' and st in ({_sql_in(R4_SHIP_TYPES)}) then 'R4'
        when coalesce(st,'') =  '' and vt = 'Passenger'                then 'R1'
        when coalesce(st,'') =  '' and vt = 'Container'                then 'R3'
        when coalesce(st,'') =  '' and vt = 'Reefer'                   then 'R4'
        else 'BASE'
    end as rule,
    case
        when vt = 'Bulk'            then {AGENCY_FEE_BULK}
        when coalesce(vt,'')  <> '' then {AGENCY_FEE_OTHER}
        when coalesce(stg,'') <> '' then
            case when stg like 'Bulk Carrier%' then {AGENCY_FEE_BULK}
                 else {AGENCY_FEE_OTHER} end
        when coalesce(imo,'') =  '' then null
        else {AGENCY_FEE_OTHER}
    end as old_two_tier_fee
from leg
"""


def mrtis_commit(short: bool = False) -> str:
    args = ["git", "-C", str(MRTIS_ROOT), "rev-parse"]
    if short:
        args.append("--short")
    args.append("HEAD")
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def fee_rules(con) -> dict:
    """Rule-by-rule fee movement, self-proved against MRTIS's stored fee.

    Assumes the `leg_classified` view is already registered (see derive()).
    """
    mismatches = con.execute(f"""
        select count(*) from leg_classified
        where agency_fee is not null
          and agency_fee is distinct from
              case rule {' '.join(f"when '{r}' then {f}" for r, f in RULE_FEE.items())}
                   else old_two_tier_fee end
    """).fetchone()[0]
    if mismatches:
        raise SystemExit(
            f"figures.py: {mismatches:,} legs where this package's rule attribution "
            f"disagrees with MRTIS's stored agency_fee. MRTIS's agency_fee_for() has "
            f"changed and this module must be re-synced before any figure it "
            f"produces can be published."
        )

    rows = con.execute("""
        select rule,
               count(*)                                   as legs,
               sum(old_two_tier_fee)                      as old_two_tier,
               sum(agency_fee)                            as bills_now,
               sum(agency_fee) - sum(old_two_tier_fee)    as change
        from leg_classified
        where agency_fee is not null
        group by 1 order by 1
    """).fetchdf()

    by_rule = {r["rule"]: {"label": RULE_LABEL[r["rule"]], "legs": int(r["legs"]),
                           "old_two_tier": float(r["old_two_tier"]),
                           "bills_now": float(r["bills_now"]),
                           "change": float(r["change"])}
               for _, r in rows.iterrows()}
    return {
        "by_rule": by_rule,
        "old_two_tier_total": float(rows["old_two_tier"].sum()),
        "bills_now_total": float(rows["bills_now"].sum()),
        "change_total": float(rows["change"].sum()),
        "attribution_mismatches": 0,
    }


def derive(con) -> dict:
    one = lambda s: con.execute(s).fetchone()
    f = {"mrtis_commit": mrtis_commit(), "mrtis_commit_short": mrtis_commit(short=True)}
    con.execute(f"create or replace temp view leg_classified as {LEG_CLASSIFIED}")

    # --- calls, legs, events -------------------------------------------------
    (calls, commercial, layup, complete, split, legs_total) = one("""
        select count(*),
               count(*) filter (where is_commercial_call),
               count(*) filter (where not is_commercial_call),
               count(*) filter (where is_complete),
               count(*) filter (where is_split),
               sum(leg_count)
        from port_call""")
    f["calls"] = {
        "total": calls, "commercial": commercial, "layup": layup,
        "complete": complete, "pct_complete": round(100 * complete / calls, 2),
        "split": split, "pct_split": round(100 * split / calls, 2),
    }
    legs, chargeable, leg_basis = one("""
        select count(*), count(*) filter (where agency_fee is not null), sum(agency_fee)
        from port_call_leg""")
    f["legs"] = {"total": legs, "chargeable": chargeable,
                 "not_chargeable": legs - chargeable}
    f["events"] = {"total": one("select count(*) from port_call_event")[0]}

    # --- the two fee bases (§9.1) -------------------------------------------
    dep_event, dep_rollup = one("""
        select (select sum(agency_fee) from port_call_event),
               (select sum(agency_fee_departures_total) from port_call)""")
    unassigned_fee, unassigned_n = one("""
        select sum(agency_fee), count(*) from port_call_event
        where agency_fee is not null and port_call_id is null""")
    f["fee_basis"] = {
        "leg_basis": float(leg_basis),
        "per_departure_event": float(dep_event),
        "per_departure_call_rollup": float(dep_rollup),
        # The two per-departure roll-ups differ by exactly the fee on departure
        # events that never landed in a call. MRTIS OPEN_QUESTIONS.md §11.2
        # ruled this "leave as is" -- understood, not hidden -- so this package
        # discloses it rather than silently publishing one of the two numbers.
        "per_departure_gap": float(dep_event) - float(dep_rollup),
        "unassigned_fee_events": unassigned_n,
        "unassigned_fee": float(unassigned_fee or 0.0),  # NULL once I-21 lands:
        # no fee-bearing event is left outside a call, so the sum has no rows.
        "over_bill_abs": float(dep_event) - float(leg_basis),
        "over_bill_pct": round(100 * (float(dep_event) - float(leg_basis)) / float(leg_basis), 1),
    }
    f["fee_basis"]["unassigned_reasons"] = {
        r["unassigned_reason"]: {"events": int(r["n"]), "fee": float(r["fee"])}
        for _, r in con.execute("""
            select unassigned_reason, count(*) n, sum(agency_fee) fee
            from port_call_event
            where agency_fee is not null and port_call_id is null
            group by 1 order by fee desc, unassigned_reason""").fetchdf().iterrows()
    }

    # --- A8: multi-charging under the per-departure basis --------------------
    fee_bearing, multi, max_charges = one("""
        with n as (select port_call_id, count(*) c from port_call_event
                   where agency_fee is not null and port_call_id is not null
                   group by 1)
        select count(*), count(*) filter (where c >= 2), max(c) from n""")
    f["multi_charge"] = {
        "fee_bearing_calls": fee_bearing, "multi_charged": multi,
        "max_charges": max_charges,
        "pct_of_fee_bearing": round(100 * multi / fee_bearing, 1),
        "pct_of_all_calls": round(100 * multi / calls, 1),
    }

    # --- A7: activity resolution --------------------------------------------
    am = con.execute("""
        select coalesce(activity_method, '(null)') m, count(*) n
        from port_call_leg group by 1 order by n desc, m""").fetchdf()
    f["activity_method"] = {r["m"]: {"legs": int(r["n"]),
                                     "pct": round(100 * int(r["n"]) / legs, 2)}
                            for _, r in am.iterrows()}
    resolved = sum(v["legs"] for k, v in f["activity_method"].items()
                   if k in ("dictionary", "draft_delta", "fgis"))
    f["activity_method_resolved_pct"] = round(100 * resolved / legs, 2)
    f["activity"] = {
        (r["a"] or "(unresolved)"): {"legs": int(r["n"]),
                                     "fee": (None if r["fee"] != r["fee"] else float(r["fee"]))}
        for _, r in con.execute("""
            select activity a, count(*) n, sum(agency_fee) fee
            from port_call_leg group by 1 order by n desc, a nulls last""").fetchdf().iterrows()
    }

    # --- A14: geofence artifact rate, both denominators ---------------------
    all_berth, artifacts, placed_berth, placed_artifacts = one("""
        select count(*) filter (where is_berth_stop or is_geofence_artifact),
               count(*) filter (where is_geofence_artifact),
               count(*) filter (where (is_berth_stop or is_geofence_artifact)
                                  and port_call_id is not null),
               count(*) filter (where is_geofence_artifact and port_call_id is not null)
        from port_call_event""")
    f["geofence"] = {
        "artifacts": artifacts, "all_berth_events": all_berth,
        "placed_berth_events": placed_berth,
        "pct_of_all": round(100 * artifacts / all_berth, 2),
        "pct_of_placed": round(100 * placed_artifacts / placed_berth, 2),
    }

    # --- layberth / non-commercial time (§8) --------------------------------
    lb_hours, lb_legs = one("""
        select round(sum(layberth_hours), 2), count(*) filter (where layberth_hours > 0)
        from port_call_leg""")
    f["layberth"] = {"hours": float(lb_hours), "legs_with_layberth": lb_legs}

    # --- A4: base-tier precedence counterexamples ---------------------------
    ce = con.execute("""
        select vt, count(*) legs, sum(agency_fee) fee from leg_classified
        where agency_fee is not null and stg like 'Bulk Carrier%'
          and coalesce(vt,'') <> '' and vt <> 'Bulk'
        group by 1 order by 2 desc, 1""").fetchdf()
    f["base_tier_counterexamples"] = {
        "legs": int(ce["legs"].sum()) if len(ce) else 0,
        "fee": float(ce["fee"].sum()) if len(ce) else 0.0,
        "by_vessel_type": {r["vt"]: int(r["legs"]) for _, r in ce.iterrows()},
    }

    # --- §9.3's canonical fallback: is it actually reachable? ---------------
    fb = con.execute("""
        select coalesce(vt, '(none)') vt, count(*) legs, sum(agency_fee) fee
        from leg_classified
        where agency_fee is not null and coalesce(st,'') = ''
        group by 1 order by 2 desc, 1""").fetchdf()
    f["canonical_fallback"] = {
        "legs_without_register_row": int(fb["legs"].sum()) if len(fb) else 0,
        "fee": float(fb["fee"].sum()) if len(fb) else 0.0,
        "by_vessel_type": {r["vt"]: int(r["legs"]) for _, r in fb.iterrows()},
        "reached_by_a_rule": int(fb[fb["vt"].isin(["Passenger", "Container", "Reefer"])]["legs"].sum()),
    }

    # --- tpc coverage (A6; MRTIS OPEN_QUESTIONS 11.3 / 15.7) ------------------
    # tpc = 0 used to stand for "not supplied" and was indistinguishable from a
    # measurement. MRTIS now stores NULL for it, so the figure this package
    # publishes changed shape: the count of zeros should be structurally 0, and
    # what matters is how many calls have no TPC at all. Both are derived so a
    # regression upstream would show as a non-zero `zeros`.
    tpc_zero = one("select count(*) from port_call where tpc = 0")[0]
    tpc_null = one("select count(*) from port_call where tpc is null")[0]
    tpc_real = one("select count(*) from port_call where tpc > 0")[0]
    f["tpc_zero"] = {"calls": tpc_zero, "pct": round(100 * tpc_zero / calls, 2)}
    f["tpc_coverage"] = {
        "not_supplied": tpc_null, "pct_not_supplied": round(100 * tpc_null / calls, 2),
        "real": tpc_real, "pct_real": round(100 * tpc_real / calls, 2),
    }

    # --- A12: fee-bearing legs with no agency -------------------------------
    no_agency_legs, no_agency_fee = one("""
        select count(*), sum(agency_fee) from port_call_leg
        where agency_fee is not null and coalesce(agency,'') = ''""")
    f["legs_without_agency"] = {
        "legs": no_agency_legs, "fee": float(no_agency_fee or 0.0),
        "reported_total": float(leg_basis) - float(no_agency_fee or 0.0),
    }

    # --- Agency attribution: the disclosures a reporting user needs ---------
    # Session 8 (report_concepts/ISSUES.md I-4, I-5). Agency exists at two
    # grains, and the leg grain is the ruled one (§6). The call-grain column is
    # the more obvious one to reach for, so the size of choosing wrong is
    # published rather than left to be discovered.
    ag_calls, ag_legs, ag_fee = one("""
        select (select count(*) from (select port_call_id from port_call_leg
                where coalesce(agency,'') <> '' group by 1
                having count(distinct agency) > 1)),
               (select count(*) from port_call_leg l join port_call c using (port_call_id)
                where coalesce(l.agency,'') <> '' and coalesce(c.agency,'') <> ''
                  and l.agency <> c.agency),
               (select sum(l.agency_fee) from port_call_leg l join port_call c using (port_call_id)
                where coalesce(l.agency,'') <> '' and coalesce(c.agency,'') <> ''
                  and l.agency <> c.agency)""")
    f["agency_grain"] = {
        "calls_with_multiple_agencies": ag_calls,
        "legs_disagreeing_with_call": ag_legs,
        "fee_at_risk": float(ag_fee or 0.0),
    }

    ch_legs, ch_fee = one("""
        select count(*), sum(agency_fee) from port_call_leg
        where agent_changed_in_leg and agency_fee is not null""")
    f["agent_changed"] = {
        "legs": ch_legs, "fee": float(ch_fee or 0.0),
        "pct_of_chargeable_legs": round(100 * ch_legs / chargeable, 2),
        "pct_of_fee": round(100 * float(ch_fee or 0.0) / float(leg_basis), 2),
    }

    # --- Turnover: the same truth at three denominators (I-8) ---------------
    bulk_calls, bulk_split, bulk_disch, bulk_disch_and_load = one("""
        select (select count(*) from port_call where vessel_type = 'Bulk'),
               (select count(*) from port_call where vessel_type = 'Bulk' and is_split),
               (select count(*) from (select l.port_call_id from port_call_leg l
                  join port_call c using (port_call_id) where c.vessel_type = 'Bulk'
                  group by 1 having count(*) filter (where l.activity = 'Discharge') > 0)),
               (select count(*) from (select l.port_call_id from port_call_leg l
                  join port_call c using (port_call_id) where c.vessel_type = 'Bulk'
                  group by 1 having count(*) filter (where l.activity = 'Discharge') > 0
                     and count(*) filter (where l.activity = 'Load') > 0))""")
    f["bulk_turnover"] = {
        "bulk_calls": bulk_calls,
        "bulk_split_calls": bulk_split,
        "bulk_discharge_calls": bulk_disch,
        "discharge_and_load_calls": bulk_disch_and_load,
        "pct_of_all_bulk_calls": round(100 * bulk_disch_and_load / bulk_calls, 2),
        "pct_of_bulk_discharge_calls": round(100 * bulk_disch_and_load / bulk_disch, 2),
    }

    f["fee_rules"] = fee_rules(con)
    return f


def _money(v) -> str:
    """Dollars with the minus sign outside the symbol: -$19,000, not $-19,000."""
    return f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}"


def write_markdown(f: dict, path: Path) -> None:
    fb, fr = f["fee_basis"], f["fee_rules"]
    L = [
        "# Derived figures", "",
        "Every number this package publishes, re-derived live from MRTIS's database.",
        "**Generated by `figures.py` — do not hand-edit.** `docs/BUSINESS_RULES.md`,",
        "`charts/` and `reports/` all read from this same derivation, so a figure",
        "cannot go stale in one place and stay current in another.", "",
        f"MRTIS commit: `{f['mrtis_commit']}`", "",
        "---", "", "## Volumes", "",
        "| | Count |", "|---|---:|",
        f"| Port calls | {f['calls']['total']:,} |",
        f"| — commercial | {f['calls']['commercial']:,} |",
        f"| — lay-up (flagged, excluded from commercial counts) | {f['calls']['layup']:,} |",
        f"| Complete calls (both ends seen) | {f['calls']['complete']:,} ({f['calls']['pct_complete']}%) |",
        f"| Split calls | {f['calls']['split']:,} ({f['calls']['pct_split']}%) |",
        f"| Legs | {f['legs']['total']:,} |",
        f"| — chargeable | {f['legs']['chargeable']:,} |",
        f"| Events | {f['events']['total']:,} |",
        "", "## The two fee bases", "",
        "| Basis | Total |", "|---|---:|",
        f"| **Per-leg (billable, the ruled figure)** | **{_money(fb['leg_basis'])}** |",
        f"| Per-departure, event level (frozen comparison) | {_money(fb['per_departure_event'])} |",
        f"| Per-departure, rolled up to `port_call` | {_money(fb['per_departure_call_rollup'])} |",
        f"| — gap between the two per-departure roll-ups | {_money(fb['per_departure_gap'])} |",
        "",
        f"The gap is exactly the fee on **{fb['unassigned_fee_events']} departure events that "
        f"never landed in a port call** — "
        + "; ".join(f"`{k}` {v['events']} events, {_money(v['fee'])}"
                    for k, v in fb["unassigned_reasons"].items())
        + ". The event-level figure includes them; the call roll-up structurally cannot.",
        "",
        f"Per-departure over-bills the billable basis by **{_money(fb['over_bill_abs'])} "
        f"({fb['over_bill_pct']}%)**.", "",
        f"Under per-departure counting, **{f['multi_charge']['multi_charged']:,} of "
        f"{f['multi_charge']['fee_bearing_calls']:,} fee-bearing calls "
        f"({f['multi_charge']['pct_of_fee_bearing']}%)** were charged 2–"
        f"{f['multi_charge']['max_charges']} times "
        f"({f['multi_charge']['pct_of_all_calls']}% of all {f['calls']['total']:,} calls).",
        "", "## Fee schedule: rule-by-rule", "",
        "| Rule | Chargeable legs | Old 2-tier | Bills now | Change |",
        "|---|---:|---:|---:|---:|",
    ]
    for key in ("R1", "R2", "R3", "R4", "R5", "BASE"):
        r = fr["by_rule"].get(key)
        if not r:
            continue
        L.append(f"| {r['label']} | {r['legs']:,} | {_money(r['old_two_tier'])} | "
                 f"{_money(r['bills_now'])} | {_money(r['change'])} |")
    pct = 100 * fr["change_total"] / fr["old_two_tier_total"]
    L += [
        f"| **Total** | **{f['legs']['chargeable']:,}** | **{_money(fr['old_two_tier_total'])}** | "
        f"**{_money(fr['bills_now_total'])}** | **{_money(fr['change_total'])} ({pct:.2f}%)** |",
        "",
        f"Attribution self-check: **{fr['attribution_mismatches']} legs** where this "
        f"package's rule attribution disagrees with the fee MRTIS actually stored.",
        "", "## Activity resolution", "",
        "| Method | Legs | % of all legs |", "|---|---:|---:|",
    ]
    for m, v in f["activity_method"].items():
        L.append(f"| {m} | {v['legs']:,} | {v['pct']}% |")
    L += [
        f"", f"Resolved by real evidence: **{f['activity_method_resolved_pct']}%** of "
        f"{f['legs']['total']:,} legs.", "",
        "| `activity` | Legs | Fee |", "|---|---:|---:|",
    ]
    for a, v in f["activity"].items():
        L.append(f"| {a} | {v['legs']:,} | {'—' if v['fee'] is None else _money(v['fee'])} |")
    g = f["geofence"]
    L += [
        "", "## Other published figures", "",
        "| Figure | Value |", "|---|---:|",
        f"| Geofence artifacts, % of all berth events | {g['pct_of_all']}% ({g['artifacts']:,} / {g['all_berth_events']:,}) |",
        f"| Geofence artifacts, % of *placed* berth events | {g['pct_of_placed']}% |",
        f"| Layberth hours (now separate from `berth_hours`) | {f['layberth']['hours']:,.2f} |",
        f"| Legs carrying layberth time | {f['layberth']['legs_with_layberth']:,} |",
        f"| `tpc` supplied and usable | {f['tpc_coverage']['real']:,} calls ({f['tpc_coverage']['pct_real']}%) |",
        f"| `tpc` not supplied (NULL — never 0) | {f['tpc_coverage']['not_supplied']:,} calls ({f['tpc_coverage']['pct_not_supplied']}%) |",
        f"| `tpc = 0` placeholders remaining | {f['tpc_zero']['calls']:,} — MRTIS §15.7 replaced them with NULL |",
        f"| Chargeable legs with no agency (omitted from the by-agent report) | {f['legs_without_agency']['legs']:,} ({_money(f['legs_without_agency']['fee'])}) |",
        f"| Base-tier precedence counterexamples (A4) | {f['base_tier_counterexamples']['legs']} legs ({_money(f['base_tier_counterexamples']['fee'])}) |",
        f"| Chargeable legs with no register row | {f['canonical_fallback']['legs_without_register_row']} ({_money(f['canonical_fallback']['fee'])}) |",
        f"| — of those, reached by the canonical fallback | {f['canonical_fallback']['reached_by_a_rule']} |",
        "",
        "## Agency attribution — disclosures for anyone reporting by agent", "",
        "Agency exists at two grains and §6 rules that the **leg** grain is the "
        "correct one. These figures are published so the cost of reaching for the "
        "other column, or of reading a by-agent report as a clean division of the "
        "book, is a known quantity rather than a discovery.", "",
        "| Figure | Value |", "|---|---:|",
        f"| Port calls whose legs carry more than one agency | {f['agency_grain']['calls_with_multiple_agencies']:,} |",
        f"| Legs whose agency differs from their call-level `port_call.agency` | {f['agency_grain']['legs_disagreeing_with_call']:,} |",
        f"| — fee mis-attributed if `port_call.agency` is used instead | {_money(f['agency_grain']['fee_at_risk'])} |",
        f"| Chargeable legs where the agent changed mid-leg | {f['agent_changed']['legs']:,} ({f['agent_changed']['pct_of_chargeable_legs']}%) |",
        f"| — fee on those legs | {_money(f['agent_changed']['fee'])} ({f['agent_changed']['pct_of_fee']}% of the billable total) |",
        "",
        "## Bulk turnover — one behaviour, three denominators", "",
        "Discharge-then-load within a single port call. The rate depends entirely "
        "on what it is divided by, so all three denominators are published together "
        "and no figure travels without one.", "",
        "| Denominator | Rate |", "|---|---:|",
        f"| Of **all** bulk port calls ({f['bulk_turnover']['bulk_calls']:,}) | {f['bulk_turnover']['pct_of_all_bulk_calls']}% |",
        f"| Of bulk calls that **discharge** ({f['bulk_turnover']['bulk_discharge_calls']:,}) | **{f['bulk_turnover']['pct_of_bulk_discharge_calls']}%** |",
        "",
        f"{f['bulk_turnover']['discharge_and_load_calls']:,} bulk calls both discharge "
        "and load. The second rate is the one that matches trade experience "
        "(William, 2026-08-20: 24-35%); the first is the same fact and looks like a "
        "different one.",
        "",
    ]
    path.write_text("\n".join(L) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="dump the derived dict as JSON")
    ap.add_argument("--db", default=str(MRTIS_DB))
    args = ap.parse_args()

    con = duckdb.connect(args.db, read_only=True)
    try:
        f = derive(con)
    finally:
        con.close()

    if args.json:
        print(json.dumps(f, indent=2))
        return
    out = REPO / "docs" / "FIGURES.md"
    write_markdown(f, out)
    (REPO / "docs" / "figures.json").write_text(json.dumps(f, indent=2) + "\n")
    print(f"-> {out}")
    print(f"-> {REPO / 'docs' / 'figures.json'}")
    print(f"   billable {_money(f['fee_basis']['leg_basis'])} · "
          f"{f['legs']['chargeable']:,} chargeable legs · "
          f"{f['fee_rules']['attribution_mismatches']} attribution mismatches")


if __name__ == "__main__":
    main()
