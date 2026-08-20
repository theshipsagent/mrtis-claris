# Addendum — `ARTCO Destrehan Buoys`: a defect found, ruled, and fixed

MRTIS commit `699a9fc` · window **2023-08-01 → 2026-07-31** · these legs are **excluded from G1 and G2**

**This page records a closed loop.** The grain reports found a defect, William ruled on it, and MRTIS has since been corrected — so this addendum is now a record of what was wrong rather than a warning about what still is.

## What was found

`ARTCO Destrehan Buoys` carried a grain-only rule in `MRTIS/dictionaries/zone_facility.csv` identical to MGMT's — Mid-Stream, ops `Load`, Cargo group `Grain`, rule *"Can never be a liquid cargo"*, note *"Apply always"*. Every one of its 622 legs was tagged grain, but only 177 (28.5%) carried an FGIS certificate. The other 445 were grain solely because the dictionary said so.

## What was ruled

**William, 2026-08-20:** *"artco can occasionally add grain ships tagged to that into the report, as we can't bake it in as it remains multi purpose facility."* The rule over-claimed: the berth does load grain, but not only grain.

## What was fixed

`Cargo group` cleared on both dictionary rows (MRTIS `OPEN_QUESTIONS.md` §15.1). `ops = Load` and the rule text were left alone — the ruling was about cargo, not direction. **445 legs moved from `Grain` to no cargo group; the 177 FGIS-evidenced legs kept their grain tag and their tonnage.** Verified leg by leg against a pre-change copy of the database: nothing else in MRTIS moved at all — 0 legs changed fee, activity, agency, hours or facility, and the billable total stayed at $272,660,000.

## The legs this excludes from G1 and G2, in the reporting window

G1 and G2 admit ARTCO legs **only on FGIS evidence**, which was the right policy before the fix and remains the right policy after it. These are the legs that policy leaves out:

| Measure | Value |
|---|---:|
| Loadings excluded | 176 |
| Distinct vessels | 169 |
| Tonnes | none — no certificate, so no tonnage exists for them |
| Chargeable legs | 176 |
| Agency fee not counted in G2 | $1,841,000 |

> **Their fee and berth activity were never in question** — only the cargo label was, and it is now correct. They appear in full in the port-wide report `portwide_by_facility.md`, which counts every leg regardless of cargo.

> **Worth checking in a later session:** 15 dictionary rows still carry a Grain cargo group (down from 17). MGMT's is confirmed correct by William; the remaining 13 sit at Elevator facilities, where a grain-only rule is safe. But the pattern that produced ARTCO's row is worth looking for at other multi-purpose berths.

