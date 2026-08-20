# Sample report: R5 impact by facility -- dry bulk calling General Cargo berths

MRTIS commit `09e1cb6` · Rule R5 (docs/BUSINESS_RULES.md §9.3): any dry-bulk vessel (`vessel_type = 'Bulk'`) whose leg's first berth is a General Cargo facility type bills at a flat $5,000, decided by the leg's first berth (MRTIS OPEN_QUESTIONS.md §12.3.3, ruled).

**Total: $15,560,000 across 3,112 legs** (reconciles exactly to the built-and-verified $15,560,000 / 3,112 legs in MRTIS OPEN_QUESTIONS.md §12.4).

| Facility | Legs | Billable fee |
|---|---:|---:|
| Nashville Ave | 842 | $4,210,000 |
| AST Chalmette Slip | 832 | $4,160,000 |
| Avondale Global Gateway | 327 | $1,635,000 |
| 7th Street | 323 | $1,615,000 |
| Louisiana Ave | 236 | $1,180,000 |
| 1st Street | 153 | $765,000 |
| AST Globalplex | 140 | $700,000 |
| Harmony St | 78 | $390,000 |
| Baton Rouge General Cargo | 51 | $255,000 |
| LIT Violet | 27 | $135,000 |
| Poland St | 26 | $130,000 |
| Perry Street | 19 | $95,000 |
| Buck Kreihs | 18 | $90,000 |
| Napoleon Ave | 17 | $85,000 |
| Alabo St | 16 | $80,000 |
| Henry Clay Ave | 6 | $30,000 |
| Esplanade Ave | 1 | $5,000 |
