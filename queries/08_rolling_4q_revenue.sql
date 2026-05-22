-- Question: What does trailing-12-month (4-quarter rolling) revenue look like?
-- Why: Smooths QoQ noise and shows the underlying growth trajectory without seasonality jumps.
-- Output verified: 24 rows. Findings:
-- 1) Compute & Networking Rolling_4Q is monotonically increasing across all 8 quarters.
--    Even FY26Q1 (where raw QoQ slowed to +9.9% and H20 write-down hit margins) doesn't dip.
--    This is the smoothing payoff: trend is up-and-right regardless of single-quarter noise.
-- 2) Graphics Rolling_4Q grew ~46% across FY26 (15,408 -> 22,459). Quietly healthy, not flat.
-- 3) All Other shows 0.0 because revenue = 0 by design (Decision 2). To see the corporate
--    cost trailing-4Q, swap Revenue_USDmm for OperatingIncome_USDmm. Skipped here as a 
--    variant for Week 3.
-- 4) Rolling_4Q at end-of-fiscal-year ties to annual segment revenue - quiet cross-check.

SELECT
    dp.PeriodKey,
    ds.SegmentName,
    fs.Revenue_USDmm AS QuarterlyRevenue,
    SUM(fs.Revenue_USDmm) OVER (
        PARTITION BY ds.SegmentKey
        ORDER BY dp.SortOrder
        ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ) AS Rolling_4Q_Revenue,
    ROUND(
        SUM(fs.Revenue_USDmm) OVER (
            PARTITION BY ds.SegmentKey
            ORDER BY dp.SortOrder
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) / 4.0,
        0
    ) AS Avg_Quarterly_Revenue_4Q
FROM FactSegment fs
JOIN DimPeriod dp ON fs.PeriodKey = dp.PeriodKey
JOIN DimSegment ds ON fs.SegmentKey = ds.SegmentKey
WHERE dp.Granularity = 'Quarter'
ORDER BY ds.SegmentKey, dp.SortOrder;