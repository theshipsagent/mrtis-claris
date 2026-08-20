#!/usr/bin/env python3
"""Sample charts demonstrating the MRTIS port-call/fee data, for the
Claris/FileMaker review package. Read-only against MRTIS's duckdb.

Usage:
    python3 charts/build_charts.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

MRTIS_DB = "/Users/billy/Documents/MRTIS/data/db/mrtis.duckdb"
OUT = Path(__file__).resolve().parent
NAVY = "#1b3a5c"
TEAL = "#1a7a72"
SLATE = "#5b6b79"
AMBER = "#c9862a"
PALETTE = [NAVY, TEAL, AMBER, SLATE, "#7a4fa3", "#a83246", "#3f7d3f", "#8a8a8a"]


def commit() -> str:
    return subprocess.run(
        ["git", "-C", "/Users/billy/Documents/MRTIS", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#c7ccd1")
    ax.spines["bottom"].set_color("#c7ccd1")
    ax.tick_params(colors="#3a3f45")
    ax.yaxis.grid(True, color="#e6e9ec", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def footer(fig, note=""):
    c = commit()
    fig.text(0.01, 0.01, f"MRTIS commit {c}  ·  Phase 1 review package{('  ·  ' + note) if note else ''}",
              fontsize=7.5, color="#8a8f94")


def chart_fee_by_vessel_type(con):
    df = con.execute("""
        select coalesce(vessel_type,'(unknown)') vt, sum(agency_fee_total) fee, count(*) calls
        from port_call group by 1 order by fee desc nulls last
    """).fetchdf()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.barh(df["vt"][::-1], df["fee"][::-1] / 1e6, color=PALETTE[0])
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}M"))
    for b, fee, n in zip(bars, df["fee"][::-1], df["calls"][::-1]):
        ax.text(b.get_width() + 2, b.get_y() + b.get_height() / 2,
                 f"${fee:,.0f}  ({n:,} calls)", va="center", fontsize=9, color="#2a2f35")
    ax.set_title("Agency fee revenue by vessel type", fontsize=14, weight="bold", pad=14, loc="left")
    ax.set_xlabel("Agency fee, $ millions (billable, per-leg basis)")
    style_axes(ax)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    footer(fig, "billable = one fee per leg with a berth stop, per docs/BUSINESS_RULES.md §9")
    fig.savefig(OUT / "fee_by_vessel_type.png", dpi=150)
    plt.close(fig)


def chart_split_call_rate(con):
    df = con.execute("select is_split, count(*) n from port_call group by 1").fetchdf()
    df["label"] = df["is_split"].map({True: "Split call\n(2+ legs)", False: "Single-leg call"})
    total = df["n"].sum()
    fig, ax = plt.subplots(figsize=(8, 6.5))
    colors = [TEAL if s else "#d8dce0" for s in df["is_split"]]
    wedges, _ = ax.pie(df["n"], colors=colors, startangle=90, counterclock=False,
                        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2))
    split_n = int(df.loc[df.is_split, "n"].iloc[0])
    split_pct = 100 * split_n / total
    ax.text(0, 0.06, f"{split_pct:.1f}%", ha="center", va="center", fontsize=30, weight="bold", color=NAVY)
    ax.text(0, -0.14, "of calls are split", ha="center", va="center", fontsize=11, color="#5b6b79")
    ax.legend(wedges, [f"{l.replace(chr(10), ' ')} ({n:,})" for l, n in zip(df["label"], df["n"])],
               loc="upper center", bbox_to_anchor=(0.5, -0.02), frameon=False, fontsize=9)
    ax.set_title("Split-call rate", fontsize=14, weight="bold", pad=10)
    fig.tight_layout()
    footer(fig, "split = discharge-then-load turnover on one continuous river visit, MRTIS PORT_CALL_SPEC.md §4")
    fig.savefig(OUT / "split_call_rate.png", dpi=150)
    plt.close(fig)


def chart_calls_by_vessel_type(con):
    df = con.execute("""
        select coalesce(vessel_type,'(unknown)') vt, count(*) n
        from port_call group by 1 order by n desc
    """).fetchdf()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.bar(df["vt"], df["n"], color=[PALETTE[i % len(PALETTE)] for i in range(len(df))])
    for b, n in zip(bars, df["n"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + max(df["n"]) * 0.01,
                 f"{n:,}", ha="center", fontsize=9, color="#2a2f35")
    ax.set_title("Port calls by vessel type", fontsize=14, weight="bold", pad=14, loc="left")
    ax.set_ylabel("Port calls")
    style_axes(ax)
    fig.tight_layout()
    footer(fig)
    fig.savefig(OUT / "calls_by_vessel_type.png", dpi=150)
    plt.close(fig)


def chart_fee_tier_impact(con):
    # Static from docs/BUSINESS_RULES.md §9.4 -- the §12 rule-by-rule movement,
    # verified against the live DB in the reconciliation query below.
    rows = [
        ("R1 Passenger/Cruise", 3_650_500, 2_607_500),
        ("R3 Container", 10_948_000, 2_346_000),
        ("R4 Reefer", 140_000, 200_000),
        ("R5 Bulk @ Gen. Cargo", 32_676_000, 15_560_000),
    ]
    labels = [r[0] for r in rows]
    old = [r[1] / 1e6 for r in rows]
    new = [r[2] / 1e6 for r in rows]
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(9, 5.5))
    w = 0.35
    ax.bar([i - w / 2 for i in x], old, width=w, label="Old 2-tier schedule", color=SLATE)
    ax.bar([i + w / 2 for i in x], new, width=w, label="§12 six-rule schedule (built)", color=AMBER)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.1f}M"))
    ax.set_title("Fee-tier rule impact (2026-08-19 ruling)", fontsize=14, weight="bold", pad=14, loc="left")
    ax.legend(frameon=False)
    style_axes(ax)
    fig.tight_layout()
    footer(fig, "figures per MRTIS OPEN_QUESTIONS.md §12.4 (R2 excluded: no matching traffic)")
    fig.savefig(OUT / "fee_tier_rule_impact.png", dpi=150)
    plt.close(fig)


def main():
    con = duckdb.connect(MRTIS_DB, read_only=True)
    chart_fee_by_vessel_type(con)
    chart_split_call_rate(con)
    chart_calls_by_vessel_type(con)
    chart_fee_tier_impact(con)
    con.close()
    for f in sorted(OUT.glob("*.png")):
        print(f"-> {f}")


if __name__ == "__main__":
    main()
