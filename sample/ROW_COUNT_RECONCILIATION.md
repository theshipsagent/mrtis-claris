# Row-count reconciliation -- SAMPLE

Built read-only from `/Users/billy/Documents/MRTIS/data/db/mrtis.duckdb` at MRTIS commit `95ff34b274a52e77bfb99feca8d8169c0304571f`.

**Scope: calendar year 2025 (the most recent complete year in the data).** Whole port calls only -- every leg and every event of each selected call is present, and nothing else is. See `SAMPLE_README.md` for what that includes and excludes.

Cross-check the full-dataset column against `docs/PORT_CALL_QUALITY.md` in MRTIS if it moves unexpectedly between exports.

| Table | Rows in sample | Rows in full dataset | Share |
|---|---:|---:|---:|
| **PORT_CALL** | **5,471** | 40,355 | 13.6% |
| **PORT_CALL_LEG** | **5,667** | 42,005 | 13.5% |
| **PORT_CALL_EVENT** | **35,709** | 290,294 | 12.3% |

## Agency fee totals

The sample column is a subtotal of this window and **is not the package's headline figure**. The published totals are the full-dataset ones, derived in `docs/FIGURES.md`.

| Basis | Sample | Full dataset |
|---|---:|---:|
| Per-leg (billable), summed from PORT_CALL_LEG | $36,610,500 | $274,869,500 |
| Per-leg (billable), summed from PORT_CALL.agency_fee_total | $36,610,500 | $274,869,500 |
| Per-departure (frozen, comparison-only), summed from PORT_CALL_EVENT | $45,808,000 | $349,527,500 |
