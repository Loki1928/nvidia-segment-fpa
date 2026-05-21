"""
load_data.py — Pass 2: Load dimensions, facts, and run reconciliation checks.

Reads source data from nvidia_annual_data.xlsx and populates the full NVIDIA
segment FP&A database (nvidia_fpa.db). After loading, runs four reconciliation
queries directly in SQL to confirm the load did not silently break any of the
ties we established in Excel.

Pass 3 will refactor this into clean load() + validate() functions with a
--validate-only flag.

Usage:
    python load_data.py

Requires: pandas, openpyxl
"""

import sqlite3
from pathlib import Path

import pandas as pd

# --- Configuration -----------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / "nvidia_fpa.db"
EXCEL_PATH = SCRIPT_DIR.parent / "Raw data" / "nvidia_annual_data.xlsx"


# --- Dimension data ----------------------------------------------------------
# Hand-coded: these are fixed business identifiers, not data that changes.

DIM_PERIOD = [
    # (PeriodKey, FiscalYear, FiscalQuarter, Granularity, PeriodEndDate, SortOrder)
    ("FY24",   "FY24", None, "Annual",  "2024-01-28",  1),
    ("FY25Q1", "FY25", "Q1", "Quarter", "2024-04-28",  2),
    ("FY25Q2", "FY25", "Q2", "Quarter", "2024-07-28",  3),
    ("FY25Q3", "FY25", "Q3", "Quarter", "2024-10-27",  4),
    ("FY25Q4", "FY25", "Q4", "Quarter", "2025-01-26",  5),
    ("FY25",   "FY25", None, "Annual",  "2025-01-26",  6),
    ("FY26Q1", "FY26", "Q1", "Quarter", "2025-04-27",  7),
    ("FY26Q2", "FY26", "Q2", "Quarter", "2025-07-27",  8),
    ("FY26Q3", "FY26", "Q3", "Quarter", "2025-10-26",  9),
    ("FY26Q4", "FY26", "Q4", "Quarter", "2026-01-25", 10),
    ("FY26",   "FY26", None, "Annual",  "2026-01-25", 11),
]

DIM_SEGMENT = [
    ("CN",  "Compute & Networking"),
    ("GFX", "Graphics"),
    ("OTH", "All Other"),
]

DIM_END_MARKET = [
    # (EndMarketKey, EndMarketName, IsSubline, ParentEndMarket)
    ("DC",      "Data Center",   0, None),
    ("DC_COMP", "DC-Compute",    1, "DC"),
    ("DC_NET",  "DC-Networking", 1, "DC"),
    ("GAMING",  "Gaming",        0, None),
    ("PROVIZ",  "Pro Viz",       0, None),
    ("AUTO",    "Automotive",    0, None),
    ("OEM",     "OEM and Other", 0, None),
]

DIM_GEOGRAPHY = [
    ("US",    "United States"),
    ("SG",    "Singapore"),
    ("TW",    "Taiwan"),
    ("CN_HK", "China (incl HK)"),
    ("OTH",   "Other"),
]

DIM_BASIS = [
    ("BILL_TO", "Bill-to location",     None),
    ("CUST_HQ", "Customer HQ location", "FY26Q3"),
]

DIM_SCENARIO = [
    ("ACT",  "Actual"),
    ("BASE", "Base case"),
    ("BULL", "Bull case"),
    ("BEAR", "Bear case"),
]


# --- Text-to-key mappings ----------------------------------------------------

SEGMENT_KEY = {name: key for key, name in DIM_SEGMENT}
ENDMARKET_KEY = {name: key for key, name, _, _ in DIM_END_MARKET}
GEOGRAPHY_KEY = {name: key for key, name in DIM_GEOGRAPHY}


def basis_for_quarter(period_key: str) -> str:
    """Return BasisKey for a quarterly geography row, driven by period.

    NVIDIA switched from bill-to location to customer-HQ location starting
    Q3 FY26. The Q3 10-Q recast FY25Q3 to the new basis as a comparison.
    Q1 and Q2 of both fiscal years remain on the old bill-to basis.
    """
    quarter = period_key[-2:]
    return "BILL_TO" if quarter in ("Q1", "Q2") else "CUST_HQ"


# --- Dimension load ----------------------------------------------------------

def load_dimensions(conn: sqlite3.Connection) -> None:
    """Clear and reload all six dimension tables."""
    cur = conn.cursor()

    cur.execute("DELETE FROM DimBasis")
    cur.executemany(
        "INSERT INTO DimBasis (BasisKey, BasisName, EffectiveFrom) VALUES (?, ?, ?)",
        DIM_BASIS,
    )

    cur.execute("DELETE FROM DimEndMarket")
    cur.executemany(
        "INSERT INTO DimEndMarket (EndMarketKey, EndMarketName, IsSubline, ParentEndMarket) "
        "VALUES (?, ?, ?, ?)",
        DIM_END_MARKET,
    )

    cur.execute("DELETE FROM DimGeography")
    cur.executemany(
        "INSERT INTO DimGeography (GeographyKey, GeographyName) VALUES (?, ?)",
        DIM_GEOGRAPHY,
    )

    cur.execute("DELETE FROM DimPeriod")
    cur.executemany(
        "INSERT INTO DimPeriod (PeriodKey, FiscalYear, FiscalQuarter, Granularity, "
        "PeriodEndDate, SortOrder) VALUES (?, ?, ?, ?, ?, ?)",
        DIM_PERIOD,
    )

    cur.execute("DELETE FROM DimScenario")
    cur.executemany(
        "INSERT INTO DimScenario (ScenarioKey, ScenarioName) VALUES (?, ?)",
        DIM_SCENARIO,
    )

    cur.execute("DELETE FROM DimSegment")
    cur.executemany(
        "INSERT INTO DimSegment (SegmentKey, SegmentName) VALUES (?, ?)",
        DIM_SEGMENT,
    )

    conn.commit()


# --- Fact load ---------------------------------------------------------------

def load_segment_facts(conn: sqlite3.Connection) -> int:
    """Load FactSegment from both quarterly and annual Excel tabs."""
    qtrly = pd.read_excel(EXCEL_PATH, sheet_name="segment_quarterly")
    annual = pd.read_excel(EXCEL_PATH, sheet_name="segment_annual")

    rows = []
    for _, r in qtrly.iterrows():
        rows.append((
            r["Period"],
            SEGMENT_KEY[r["Segment"]],
            "ACT",
            float(r["Revenue"]),
            float(r["OtherSegmentItems"]),
            float(r["OperatingIncome"]),
        ))
    for _, r in annual.iterrows():
        rows.append((
            r["FiscalYear"],
            SEGMENT_KEY[r["Segment"]],
            "ACT",
            float(r["Revenue"]),
            float(r["OtherSegmentItems"]),
            float(r["OperatingIncome"]),
        ))

    cur = conn.cursor()
    cur.execute("DELETE FROM FactSegment")
    cur.executemany(
        "INSERT INTO FactSegment (PeriodKey, SegmentKey, ScenarioKey, Revenue_USDmm, "
        "OtherSegmentItems_USDmm, OperatingIncome_USDmm) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def load_endmarket_facts(conn: sqlite3.Connection) -> int:
    """Load FactEndMarket from both quarterly and annual Excel tabs."""
    qtrly = pd.read_excel(EXCEL_PATH, sheet_name="endmarket_quarterly")
    annual = pd.read_excel(EXCEL_PATH, sheet_name="endmarket_annual")

    rows = []
    for _, r in qtrly.iterrows():
        rows.append((
            r["Period"],
            ENDMARKET_KEY[r["EndMarket"]],
            "ACT",
            float(r["Revenue"]),
        ))
    for _, r in annual.iterrows():
        rows.append((
            r["FiscalYear"],
            ENDMARKET_KEY[r["EndMarket"]],
            "ACT",
            float(r["Revenue"]),
        ))

    cur = conn.cursor()
    cur.execute("DELETE FROM FactEndMarket")
    cur.executemany(
        "INSERT INTO FactEndMarket (PeriodKey, EndMarketKey, ScenarioKey, Revenue_USDmm) "
        "VALUES (?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def load_geography_facts(conn: sqlite3.Connection) -> int:
    """Load FactGeography from quarterly (mixed basis) and annual (CUST_HQ only) tabs."""
    qtrly = pd.read_excel(EXCEL_PATH, sheet_name="geography_quarterly")
    annual = pd.read_excel(EXCEL_PATH, sheet_name="geography_annual")

    rows = []
    for _, r in qtrly.iterrows():
        rows.append((
            r["Period"],
            GEOGRAPHY_KEY[r["Geography"]],
            basis_for_quarter(r["Period"]),
            "ACT",
            float(r["Revenue"]),
        ))
    for _, r in annual.iterrows():
        rows.append((
            r["FiscalYear"],
            GEOGRAPHY_KEY[r["Geography"]],
            "CUST_HQ",
            "ACT",
            float(r["Revenue"]),
        ))

    cur = conn.cursor()
    cur.execute("DELETE FROM FactGeography")
    cur.executemany(
        "INSERT INTO FactGeography (PeriodKey, GeographyKey, BasisKey, ScenarioKey, "
        "Revenue_USDmm) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    return len(rows)


def load_facts(conn: sqlite3.Connection) -> None:
    """Load all three fact tables and print row counts vs expected."""
    expectations = [
        ("FactSegment",    load_segment_facts(conn),    30),
        ("FactEndMarket",  load_endmarket_facts(conn),  77),
        ("FactGeography",  load_geography_facts(conn),  40),
    ]
    conn.commit()

    print("Fact row counts (actual vs expected):")
    all_ok = True
    for name, actual, expected in expectations:
        flag = "OK " if actual == expected else "FAIL"
        if actual != expected:
            all_ok = False
        print(f"  [{flag}] {name:15s} actual={actual:3d}  expected={expected:3d}")
    print()
    if not all_ok:
        raise RuntimeError("One or more fact tables did not load to expected count.")


# --- Reconciliation checks ---------------------------------------------------

def check_segment_opinc_rollup(conn: sqlite3.Connection) -> bool:
    """Check 1: Quarterly segment OpInc must sum to published annual OpInc."""
    cur = conn.cursor()
    cur.execute("""
        SELECT dp.FiscalYear, SUM(fs.OperatingIncome_USDmm) AS QtrlySum
        FROM FactSegment fs
        JOIN DimPeriod dp ON fs.PeriodKey = dp.PeriodKey
        WHERE dp.Granularity = 'Quarter'
        GROUP BY dp.FiscalYear
        ORDER BY dp.FiscalYear
    """)
    expected = {"FY25": 81_453.0, "FY26": 130_387.0}
    rows = cur.fetchall()
    ok = True
    print("Check 1 - Quarterly segment OpInc rollup vs published consolidated:")
    for fy, qtrly_sum in rows:
        expected_val = expected.get(fy)
        diff = qtrly_sum - expected_val if expected_val is not None else None
        status = "PASS" if expected_val is not None and abs(diff) < 0.5 else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  [{status}] {fy}  quarterly_sum={qtrly_sum:>10,.0f}  expected={expected_val:>10,.0f}  diff={diff:>+6,.0f}")
    print()
    return ok


def check_endmarket_vs_segment_revenue(conn: sqlite3.Connection) -> bool:
    """Check 2: End-market revenue (excluding sub-lines) = segment revenue per period."""
    cur = conn.cursor()
    cur.execute("""
        WITH em_total AS (
            SELECT fem.PeriodKey, SUM(fem.Revenue_USDmm) AS EMRev
            FROM FactEndMarket fem
            JOIN DimEndMarket dem ON fem.EndMarketKey = dem.EndMarketKey
            WHERE dem.IsSubline = 0
            GROUP BY fem.PeriodKey
        ),
        seg_total AS (
            SELECT PeriodKey, SUM(Revenue_USDmm) AS SegRev
            FROM FactSegment
            GROUP BY PeriodKey
        )
        SELECT e.PeriodKey, e.EMRev, s.SegRev, (e.EMRev - s.SegRev) AS Diff
        FROM em_total e
        JOIN seg_total s ON e.PeriodKey = s.PeriodKey
        ORDER BY e.PeriodKey
    """)
    rows = cur.fetchall()
    print("Check 2 - End-market revenue (top-level lines only) = segment revenue per period:")
    ok = True
    for period, em_rev, seg_rev, diff in rows:
        status = "PASS" if abs(diff) < 0.5 else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  [{status}] {period:8s}  endmkt={em_rev:>10,.0f}  segment={seg_rev:>10,.0f}  diff={diff:>+6,.0f}")
    print()
    return ok


def check_sublines_vs_parent(conn: sqlite3.Connection) -> bool:
    """Check 3: DC_COMP + DC_NET must equal DC parent line per period."""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            PeriodKey,
            SUM(CASE WHEN EndMarketKey = 'DC' THEN Revenue_USDmm ELSE 0 END) AS DC_Parent,
            SUM(CASE WHEN EndMarketKey IN ('DC_COMP', 'DC_NET') THEN Revenue_USDmm ELSE 0 END) AS DC_Children,
            SUM(CASE WHEN EndMarketKey = 'DC' THEN Revenue_USDmm ELSE 0 END)
              - SUM(CASE WHEN EndMarketKey IN ('DC_COMP', 'DC_NET') THEN Revenue_USDmm ELSE 0 END) AS Diff
        FROM FactEndMarket
        GROUP BY PeriodKey
        ORDER BY PeriodKey
    """)
    rows = cur.fetchall()
    print("Check 3 - DC sub-lines sum to parent DC line per period:")
    ok = True
    for period, parent, children, diff in rows:
        status = "PASS" if abs(diff) < 0.5 else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  [{status}] {period:8s}  DC_parent={parent:>10,.0f}  DC_comp+net={children:>10,.0f}  diff={diff:>+6,.0f}")
    print()
    return ok


def check_geography_vs_segment_revenue(conn: sqlite3.Connection) -> bool:
    """Check 4: Geography revenue per period = segment revenue per period.

    Only runs for periods where geography data exists. Q4 quarters
    intentionally absent — documented as Decision 8.
    """
    cur = conn.cursor()
    cur.execute("""
        WITH geo_total AS (
            SELECT PeriodKey, SUM(Revenue_USDmm) AS GeoRev
            FROM FactGeography
            GROUP BY PeriodKey
        ),
        seg_total AS (
            SELECT PeriodKey, SUM(Revenue_USDmm) AS SegRev
            FROM FactSegment
            GROUP BY PeriodKey
        )
        SELECT g.PeriodKey, g.GeoRev, s.SegRev, (g.GeoRev - s.SegRev) AS Diff
        FROM geo_total g
        JOIN seg_total s ON g.PeriodKey = s.PeriodKey
        ORDER BY g.PeriodKey
    """)
    rows = cur.fetchall()
    print("Check 4 - Geography revenue = segment revenue per period (Q4 absent by design):")
    ok = True
    for period, geo_rev, seg_rev, diff in rows:
        status = "PASS" if abs(diff) < 0.5 else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  [{status}] {period:8s}  geo={geo_rev:>10,.0f}  segment={seg_rev:>10,.0f}  diff={diff:>+6,.0f}")
    print()
    return ok


def validate(conn: sqlite3.Connection) -> None:
    """Run all four reconciliation checks. Raise if any fail."""
    results = [
        check_segment_opinc_rollup(conn),
        check_endmarket_vs_segment_revenue(conn),
        check_sublines_vs_parent(conn),
        check_geography_vs_segment_revenue(conn),
    ]
    if not all(results):
        raise RuntimeError("One or more reconciliation checks failed.")
    print("All reconciliation checks passed.")


def show_dimension_counts(conn: sqlite3.Connection) -> None:
    """Print row counts for every dimension table to confirm the load."""
    cur = conn.cursor()
    dims = [
        ("DimPeriod",     11),
        ("DimSegment",     3),
        ("DimEndMarket",   7),
        ("DimGeography",   5),
        ("DimBasis",       2),
        ("DimScenario",    4),
    ]
    print("Dimension row counts (actual vs expected):")
    all_ok = True
    for name, expected in dims:
        cur.execute(f"SELECT COUNT(*) FROM {name}")
        (actual,) = cur.fetchone()
        flag = "OK " if actual == expected else "FAIL"
        if actual != expected:
            all_ok = False
        print(f"  [{flag}] {name:15s} actual={actual:3d}  expected={expected:3d}")
    print()
    if not all_ok:
        raise RuntimeError("One or more dimension tables did not load to expected count.")


# --- Entry point -------------------------------------------------------------

def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Cannot find {DB_PATH}.")
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find {EXCEL_PATH}. Expected at ..\\Raw data\\nvidia_annual_data.xlsx"
        )

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        # Clear fact tables first so dimension reloads don't trip FK constraints
        for tbl in ("FactSegment", "FactEndMarket", "FactGeography"):
            conn.execute(f"DELETE FROM {tbl}")
        load_dimensions(conn)
        show_dimension_counts(conn)
        load_facts(conn)
        validate(conn)

    print(f"Pass 2 complete. Database: {DB_PATH}")


if __name__ == "__main__":
    main()