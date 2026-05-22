-- Question: How fast is corporate unallocated cost (All Other) growing?
-- Context: Decision 2 - corporate cost is preserved as a separate segment row in quarterly,
-- -- Output verified: 8 rows. Three findings:
-- 1) FY25 full-year corporate cost = -$6,507M (NOT -$4.7B as initially memorised - prep doc needs update).
--    FY26 = -$8,910M. Caught the discrepancy by running the query and checking against prep notes.
-- 2) YoY growth rate is decelerating across FY26: +49.1% -> +37.5% -> +31.7%. 
--    Pattern consistent with SBC grant cycle (front-loaded annual grants) lapping.
-- 3) Corporate cost grew ~37% while revenue grew +65%. Positive operating leverage on the corporate line.
--    Cost as % of sales improved 5.0% -> 4.1%. Cost grew at half the rate of the business.

SELECT
    dp.PeriodKey,
    ds.SegmentName,
    fs.OperatingIncome_USDmm AS CorporateCost,
    LAG(fs.OperatingIncome_USDmm, 4) OVER (
        PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder
    ) AS YearAgoCorporateCost,
    fs.OperatingIncome_USDmm - LAG(fs.OperatingIncome_USDmm, 4) OVER (
        PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder
    ) AS YoY_Abs_Change,
    ROUND(
        100.0 * (fs.OperatingIncome_USDmm - LAG(fs.OperatingIncome_USDmm, 4) OVER (
            PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder
        )) / LAG(fs.OperatingIncome_USDmm, 4) OVER (
            PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder
        ),
        1
    ) AS YoY_Pct_Change,
    SUM(fs.OperatingIncome_USDmm) OVER (
        PARTITION BY dp.FiscalYear
    ) AS FY_RunningTotal
FROM FactSegment fs
JOIN DimPeriod dp ON fs.PeriodKey = dp.PeriodKey
JOIN DimSegment ds ON fs.SegmentKey = ds.SegmentKey
WHERE dp.Granularity = 'Quarter'
  AND ds.SegmentKey = 'OTH'
ORDER BY dp.SortOrder;