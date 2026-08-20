# Addendum — `ARTCO Destrehan Buoys`: the legs held out of the grain reports

MRTIS commit `2738601` · window **2023-08-01 → 2026-07-31** · **excluded from G1 and G2**

**Ruled by William, 2026-08-20:** *"artco can occasionally add grain ships tagged to that into the report, as we can't bake it in as it remains multi purpose facility."*

So `ARTCO Destrehan Buoys` is a multi-purpose midstream berth that sometimes loads grain — and the grain-only rule in `MRTIS/dictionaries/zone_facility.csv` (Cargo group `Grain`, *"Can never be a liquid cargo"*, *"Apply always"*) is **wrong**. G1 and G2 therefore admit ARTCO legs **only where an FGIS certificate proves grain**, and never on that dictionary tag.

This page is what that exclusion removed: legs the dictionary calls grain with no evidence behind the claim. It is the measured size of the defect, for the build-fix session.

## Held out of the reports — dictionary-tagged grain, no FGIS evidence

| Measure | Value |
|---|---:|
| Loadings excluded | 176 |
| Distinct vessels | 169 |
| FGIS matched | 0 (nil by definition — this is the no-evidence set) |
| Tonnes | -- (none: no certificate, no tonnage) |
| Chargeable legs | 176 |
| Agency fee not counted in G2 | $1,841,000 |

> **What a dictionary fix would move.** Clearing `Cargo group` on ARTCO's two rows retags these 176 legs from `Grain` to no cargo group. They keep their agency fee and their berth activity — only the false cargo label goes. The 177 all-time FGIS-evidenced ARTCO legs are unaffected and stay grain.

> **Worth checking at the same time:** 17 dictionary rows carry a Grain cargo group. MGMT's is confirmed correct; ARTCO's is confirmed wrong. The other 13 sit at Elevator facilities, where a grain-only rule is safe — but the pattern that produced ARTCO's row may have produced others at multi-purpose berths.

