-- Question: How has the revenue mix between segments shifted over time?
-- Expected output: 6 rows (3 annual periods x 2 reported segments: CN, GFX).
-- All Other (OTH) absent at annual grain by design (see Decision 2 in decisions.md).
-- Mix_Pct sums to 100% per year, confirming PARTITION BY year works correctly.
-- Output verified: CN share FY24->FY26 went 77.8% -> 89.0% -> 89.6%.
-- Big shift happened in year 1 (FY24->FY25, +11.2pp). Year 2 was scale, not mix.

SELECT
    dp.FiscalYear,
    ds.SegmentName,
    fs.Revenue_USDmm AS Revenue,
    SUM(fs.Revenue_USDmm) OVER (PARTITION BY dp.FiscalYear) AS TotalRevenue,
    ROUND(
        100.0 * fs.Revenue_USDmm
        / SUM(fs.Revenue_USDmm) OVER (PARTITION BY dp.FiscalYear),
        1
    ) AS Mix_Pct
FROM FactSegment fs
JOIN DimPeriod dp ON fs.PeriodKey = dp.PeriodKey
JOIN DimSegment ds ON fs.SegmentKey = ds.SegmentKey
WHERE dp.Granularity = 'Annual'
ORDER BY dp.SortOrder, ds.SegmentKey;