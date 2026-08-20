# Sample report: R5 impact by facility -- dry bulk calling General Cargo berths

MRTIS commit `95ff34b` · Rule R5 (docs/BUSINESS_RULES.md §9.3): any dry-bulk vessel (`vessel_type = 'Bulk'`) whose leg's first **working** berth is a General Cargo facility type bills at a flat $5,000 (MRTIS OPEN_QUESTIONS.md §12.2 and the §12.3.3 resolution; the first-working-berth amendment is §12.3.3.1).

**Total: $15,225,000 across 3,045 legs**, reconciled against `figures.py`'s independent derivation of R5.

> Layberth stops are skipped when resolving which berth prices the leg. Every layberth zone carries `facility_type = General Cargo`, so pricing off the first berth of *any* kind handed the $5,000 tier to Bulk vessels that had merely lain at a layberth before working. Correcting that moved **93 legs** back to the $10,500 base tier (+$511,500) and is why this report's totals are lower than an
> extract taken before that amendment.

| Facility | Legs | Billable fee |
|---|---:|---:|
| Nashville Ave | 850 | $4,250,000 |
| AST Chalmette Slip | 846 | $4,230,000 |
| Avondale Global Gateway | 328 | $1,640,000 |
| 7th Street | 326 | $1,630,000 |
| Louisiana Ave | 244 | $1,220,000 |
| 1st Street | 154 | $770,000 |
| AST Globalplex | 143 | $715,000 |
| Harmony St | 79 | $395,000 |
| Baton Rouge General Cargo | 51 | $255,000 |
| Napoleon Ave | 17 | $85,000 |
| Henry Clay Ave | 7 | $35,000 |
