# Sample report: Port calls and fee revenue by agent

MRTIS commit `95ff34b` · leg-level agency (`port_call_leg.agency`) -- the agency that brought the vessel in owns the leg (docs/BUSINESS_RULES.md §6). 37 distinct agencies with billable legs; top 20 shown here, full list in the CSV.

**Total shown: $273,059,750**

> This is $1,809,750 short of the $274,869,500 billable total published elsewhere in this package. The difference is **415 chargeable legs that carry no agency at all** and so cannot appear in an agency breakdown. Nothing is lost — the fee is in the totals, just
> not attributable to an agent.

| Agency | Port calls | Legs | Chargeable legs | Billable fee | Avg fee / chargeable leg |
|---|---:|---:|---:|---:|---:|
| Norton Lilly | 7,355 | 7,552 | 7,315 | $41,510,250 | $5,675 |
| Southport | 4,307 | 4,358 | 4,270 | $40,734,000 | $9,540 |
| HOST | 3,708 | 3,928 | 3,790 | $33,107,000 | $8,735 |
| Blue Water | 2,458 | 2,636 | 2,601 | $27,153,500 | $10,440 |
| Gulf Inland | 1,806 | 1,976 | 1,912 | $15,798,500 | $8,263 |
| General Steamship | 1,656 | 1,821 | 1,718 | $13,320,500 | $7,753 |
| Tricon | 1,639 | 1,774 | 1,705 | $13,016,500 | $7,634 |
| Nova | 1,050 | 1,062 | 1,042 | $10,633,500 | $10,205 |
| General Maritime | 1,235 | 1,284 | 1,264 | $9,445,500 | $7,473 |
| Newship | 922 | 1,008 | 996 | $9,048,500 | $9,085 |
| Inchcape | 1,839 | 1,863 | 1,831 | $6,670,750 | $3,643 |
| Bertel | 1,768 | 1,768 | 1,738 | $6,083,000 | $3,500 |
| NordSud | 742 | 854 | 841 | $5,355,000 | $6,367 |
| Moran Shipping | 1,257 | 1,277 | 1,240 | $5,067,500 | $4,087 |
| Biehl | 1,088 | 1,107 | 1,065 | $4,916,750 | $4,617 |
| Celtic | 659 | 714 | 689 | $4,284,000 | $6,218 |
| GAC | 1,362 | 1,363 | 1,178 | $4,193,000 | $3,559 |
| Gulf Harbor | 794 | 802 | 780 | $3,464,000 | $4,441 |
| NolaPort | 951 | 951 | 950 | $2,375,000 | $2,500 |
| Fillette Green | 184 | 193 | 190 | $1,709,000 | $8,995 |
