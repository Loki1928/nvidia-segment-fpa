# Analytical SQL Queries

Eight analytical SQL queries answering business questions against the NVIDIA segment FP&A database. Each file has a header comment explaining what the query asks, what output to expect, and the verified findings from running it.

All queries use the star schema defined in [`../decisions.md`](../decisions.md) and assume the database has been built using [`../Database/load_data.py`](../Database/load_data.py).

## Queries

| # | File | What it answers | Key SQL pattern |
|---|------|-----------------|-----------------|
| 1 | `01_yoy_annual_growth.sql` | How much did NVIDIA's total revenue grow each year? | `LAG()` with `ORDER BY` |
| 2 | `02_qoq_and_yoy_quarterly.sql` | How fast is each segment growing quarter-over-quarter and year-over-year? | `LAG()` with `PARTITION BY` and offset 1 + offset 4 |
| 3 | `03_dc_subline_growth.sql` | How fast are Data Center sub-lines (Compute vs Networking) growing? | `LAG()` with `WHERE IsSubline = 1` filter |
| 4 | `04_segment_mix_shift.sql` | How has the revenue mix between segments shifted over time? | `SUM() OVER (PARTITION BY)` for share-of-total |
| 5 | `05_china_revenue_trend.sql` | How is China revenue trending, and what does it say about export controls? | Conditional aggregation (`SUM(CASE WHEN...)`) + `LAG()` |
| 6 | `06_operating_margin_trend.sql` | How is each segment's operating margin trending? | `LAG()` over a derived margin calculation |
| 7 | `07_corporate_cost_trajectory.sql` | How fast is corporate unallocated cost (All Other) growing? | `LAG()` + `SUM() OVER (PARTITION BY)` in the same query |
| 8 | `08_rolling_4q_revenue.sql` | What does the trailing-4-quarter revenue trajectory look like? | `ROWS BETWEEN 3 PRECEDING AND CURRENT ROW` |

## How to run

Open `Database/nvidia_fpa.db` in [DB Browser for SQLite](https://sqlitebrowser.org/), go to the Execute SQL tab, paste any query file's contents, and run.

Each query is self-contained — no setup beyond having the database loaded. Output verifications and headline findings are in the header comment of each file.

## SQL window functions covered

This folder demonstrates the four most common analytical window-function patterns:

- **Period-over-period comparison** — `LAG(value, n) OVER (PARTITION BY ... ORDER BY ...)` for YoY/QoQ growth (queries 1, 2, 3, 6, 7)
- **Share-of-total** — `SUM(value) OVER (PARTITION BY group)` for mix analysis (queries 4, 7)
- **Conditional aggregation** — `SUM(CASE WHEN ... THEN value ELSE 0 END)` to pivot rows into columns (query 5)
- **Rolling windows** — `ROWS BETWEEN n PRECEDING AND CURRENT ROW` for trailing-period smoothing (query 8)