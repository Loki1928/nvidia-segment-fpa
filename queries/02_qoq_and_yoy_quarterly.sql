-- Question: How fast is each segment growing quarter-over-quarter and year-over-year?
-- Expected output: 24 rows (8 quarters x 3 segments).
-- QoQ_Pct NULL for FY25Q1 in each segment (no prior quarter within partition).
-- YoY_Pct NULL for all FY25 quarters (no FY24 quarterly data).
-- Output verified: 24 rows. Compute & Networking FY26Q3 YoY +64.0%, QoQ +23.2%.
-- Pattern: Compute QoQ slowed to +9.9% then +4.4% in FY26 H1, recovered to +23% in Q3.

SELECT
    dp.PeriodKey,
    ds.SegmentName,
    fs.Revenue_USDmm AS Revenue,
    LAG(fs.Revenue_USDmm, 1) OVER (
        PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder
    ) AS PriorQuarterRevenue,
    LAG(fs.Revenue_USDmm, 4) OVER (
        PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder
    ) AS YearAgoQuarterRevenue,
    ROUND(
        100.0 * (fs.Revenue_USDmm - LAG(fs.Revenue_USDmm, 1) OVER (
            PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder
        )) / LAG(fs.Revenue_USDmm, 1) OVER (
            PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder
        ),
        1
    ) AS QoQ_Pct,
    ROUND(
        100.0 * (fs.Revenue_USDmm - LAG(fs.Revenue_USDmm, 4) OVER (
            PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder
        )) / LAG(fs.Revenue_USDmm, 4) OVER (
            PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder
        ),
        1
    ) AS YoY_Pct
FROM FactSegment fs
JOIN DimPeriod dp ON fs.PeriodKey = dp.PeriodKey
JOIN DimSegment ds ON fs.SegmentKey = ds.SegmentKey
WHERE dp.Granularity = 'Quarter'
ORDER BY ds.SegmentKey, dp.SortOrder;