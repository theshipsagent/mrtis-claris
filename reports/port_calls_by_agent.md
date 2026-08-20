# Sample report: Port calls and fee revenue by agent

MRTIS commit `61c899b` · leg-level agency (`port_call_leg.agency`) -- the agency that brought the vessel in owns the leg (docs/BUSINESS_RULES.md §6). 37 distinct agencies with billable legs; top 20 shown here, full list in the CSV.

**Total shown: $270,875,500**

> This is $1,784,500 short of the $272,660,000 billable total published elsewhere in this package. The difference is **409 chargeable legs that carry no agency at all** and so cannot appear in an agency breakdown. Nothing is lost — the fee is in the totals, just
> not attributable to an agent.

| Agency | Port calls | Legs | Chargeable legs | Billable fee | Avg fee / chargeable leg |
|---|---:|---:|---:|---:|---:|
| Norton Lilly | 7,334 | 7,528 | 7,275 | $41,243,000 | $5,669 |
| Southport | 4,282 | 4,333 | 4,237 | $40,415,500 | $9,539 |
| HOST | 3,693 | 3,911 | 3,764 | $32,873,000 | $8,734 |
| Blue Water | 2,444 | 2,620 | 2,574 | $26,870,000 | $10,439 |
| Gulf Inland | 1,802 | 1,972 | 1,899 | $15,701,000 | $8,268 |
| General Steamship | 1,647 | 1,811 | 1,705 | $13,214,500 | $7,750 |
| Tricon | 1,629 | 1,761 | 1,687 | $12,863,500 | $7,625 |
| Nova | 1,042 | 1,054 | 1,032 | $10,528,500 | $10,202 |
| General Maritime | 1,227 | 1,276 | 1,254 | $9,361,500 | $7,465 |
| Newship | 918 | 1,004 | 988 | $8,981,000 | $9,090 |
| Inchcape | 1,829 | 1,853 | 1,819 | $6,621,750 | $3,640 |
| Bertel | 1,765 | 1,765 | 1,731 | $6,058,500 | $3,500 |
| NordSud | 738 | 849 | 835 | $5,317,000 | $6,368 |
| Moran Shipping | 1,247 | 1,267 | 1,227 | $5,022,000 | $4,093 |
| Biehl | 1,082 | 1,099 | 1,055 | $4,842,250 | $4,590 |
| Celtic | 655 | 709 | 683 | $4,240,500 | $6,209 |
| GAC | 1,362 | 1,363 | 1,173 | $4,175,500 | $3,560 |
| Gulf Harbor | 787 | 795 | 770 | $3,413,500 | $4,433 |
| NolaPort | 954 | 954 | 950 | $2,375,000 | $2,500 |
| K&C | 190 | 198 | 185 | $1,688,500 | $9,127 |
