"""
rebuild_excel_from_db.py — Reconstruct nvidia_annual_data.xlsx from nvidia_fpa.db.

Use this when the source Excel has been lost but nvidia_fpa.db is intact.
The rebuilt file matches the exact 6-sheet structure load_data.py expects,
so re-running load_data.py against it will reproduce the same 30/77/40 row
counts and pass all 22 reconciliation checks.

Sheets produced (column order matters):
    segment_quarterly    — Period, Segment, Revenue, OtherSegmentItems, OperatingIncome
    segment_annual       — FiscalYear, Segment, Revenue, OtherSegmentItems, OperatingIncome
    endmarket_quarterly  — Period, EndMarket, Revenue
    endmarket_annual     — FiscalYear, EndMarket, Revenue
    geography_quarterly  — Period, Geography, Revenue
    geography_annual     — FiscalYear, Geography, Revenue

Note: Geography sheets do NOT carry a Basis column. load_data.py derives basis
from period for the quarterly sheet (basis_for_quarter), and hard-codes
'CUST_HQ' for the annual sheet (Decision 1 / Decision 8).

Usage:
    python rebuild_excel_from_db.py

Requires: pandas, openpyxl
"""

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "nvidia_fpa.db"
EXCEL_OUT = Path(__file__).resolve().parent / "nvidia_annual_data.xlsx"


def fetch_segment(conn, granularity, period_col):
    """Fetch segment data, joining dimension names. period_col is 'Period' or 'FiscalYear'."""
    sql = f"""
        SELECT
            fs.PeriodKey  AS {period_col},
            ds.SegmentName AS Segment,
            fs.Revenue_USDmm           AS Revenue,
            fs.OtherSegmentItems_USDmm AS OtherSegmentItems,
            fs.OperatingIncome_USDmm   AS OperatingIncome
        FROM FactSegment fs
        JOIN DimSegment ds ON fs.SegmentKey = ds.SegmentKey
        JOIN DimPeriod  dp ON fs.PeriodKey  = dp.PeriodKey
        WHERE dp.Granularity = ?
        ORDER BY dp.SortOrder, ds.SegmentKey
    """
    return pd.read_sql_query(sql, conn, params=(granularity,))


def fetch_endmarket(conn, granularity, period_col):
    sql = f"""
        SELECT
            fem.PeriodKey       AS {period_col},
            dem.EndMarketName   AS EndMarket,
            fem.Revenue_USDmm   AS Revenue
        FROM FactEndMarket fem
        JOIN DimEndMarket dem ON fem.EndMarketKey = dem.EndMarketKey
        JOIN DimPeriod    dp  ON fem.PeriodKey    = dp.PeriodKey
        WHERE dp.Granularity = ?
        ORDER BY dp.SortOrder, dem.IsSubline, dem.EndMarketKey
    """
    return pd.read_sql_query(sql, conn, params=(granularity,))


def fetch_geography(conn, granularity, period_col):
    sql = f"""
        SELECT
            fg.PeriodKey       AS {period_col},
            dg.GeographyName   AS Geography,
            fg.Revenue_USDmm   AS Revenue
        FROM FactGeography fg
        JOIN DimGeography dg ON fg.GeographyKey = dg.GeographyKey
        JOIN DimPeriod    dp ON fg.PeriodKey    = dp.PeriodKey
        WHERE dp.Granularity = ?
        ORDER BY dp.SortOrder, dg.GeographyKey
    """
    return pd.read_sql_query(sql, conn, params=(granularity,))


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Cannot find {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        sheets = {
            "segment_quarterly":   fetch_segment(conn,   "Quarter", "Period"),
            "segment_annual":      fetch_segment(conn,   "Annual",  "FiscalYear"),
            "endmarket_quarterly": fetch_endmarket(conn, "Quarter", "Period"),
            "endmarket_annual":    fetch_endmarket(conn, "Annual",  "FiscalYear"),
            "geography_quarterly": fetch_geography(conn, "Quarter", "Period"),
            "geography_annual":    fetch_geography(conn, "Annual",  "FiscalYear"),
        }

    with pd.ExcelWriter(EXCEL_OUT, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Wrote {EXCEL_OUT}")
    print("Sheet row counts:")
    for sheet_name, df in sheets.items():
        print(f"  {sheet_name:22s} {len(df):3d} rows")

    print()
    expected_totals = {
        "segment":   (len(sheets["segment_quarterly"])   + len(sheets["segment_annual"]),   30),
        "endmarket": (len(sheets["endmarket_quarterly"]) + len(sheets["endmarket_annual"]), 77),
        "geography": (len(sheets["geography_quarterly"]) + len(sheets["geography_annual"]), 40),
    }
    print("Totals (qtrly + annual) vs load_data.py expectations:")
    for name, (actual, expected) in expected_totals.items():
        flag = "OK " if actual == expected else "FAIL"
        print(f"  [{flag}] {name:10s} actual={actual:3d}  expected={expected:3d}")


if __name__ == "__main__":
    main()
