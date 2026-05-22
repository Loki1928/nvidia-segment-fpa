-- Question: How is each segment's operating margin trending over time?
-- Approach: Operating margin = OperatingIncome / Revenue, computed per (period, segment).
-- Use quarterly data for granularity. Skip 'OTH' (All Other) since Revenue = 0 -> division by zero.
-- Output verified: 16 rows. Two findings worth flagging:
-- 1) Compute & Networking FY26Q1 margin cratered to 55.7% from 69.1% prior quarter,
--    snapped back to 68.6% next quarter. One-quarter event, not a trend. Almost certainly
--    the H20 inventory/purchase-commitment write-down (~$5.6B implied gap vs trend margin).
-- 2) Graphics margin expanded steadily across FY26 (36.7 -> 41.4 -> 41.8 -> 42.1).
--    Getting MORE profitable while shrinking in revenue mix - likely mix-up within Graphics
--    toward RTX 50-series.

SELECT
    dp.PeriodKey,
    ds.SegmentName,
    fs.Revenue_USDmm AS Revenue,
    fs.OperatingIncome_USDmm AS OperatingIncome,
    ROUND(100.0 * fs.OperatingIncome_USDmm / fs.Revenue_USDmm, 1) AS OpMargin_Pct,
    LAG(ROUND(100.0 * fs.OperatingIncome_USDmm / fs.Revenue_USDmm, 1), 1)
        OVER (PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder) AS PriorQ_Margin,
    LAG(ROUND(100.0 * fs.OperatingIncome_USDmm / fs.Revenue_USDmm, 1), 4)
        OVER (PARTITION BY ds.SegmentKey ORDER BY dp.SortOrder) AS YearAgo_Margin
FROM FactSegment fs
JOIN DimPeriod dp ON fs.PeriodKey = dp.PeriodKey
JOIN DimSegment ds ON fs.SegmentKey = ds.SegmentKey
WHERE dp.Granularity = 'Quarter'
  AND ds.SegmentKey != 'OTH'
ORDER BY ds.SegmentKey, dp.SortOrder;