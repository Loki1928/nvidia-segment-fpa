-- Question: How fast are Data Center sub-lines (Compute vs Networking) growing?
-- Expected output: 16 rows (8 quarters x 2 sub-lines: DC_COMP, DC_NET).
-- QoQ_Pct NULL for FY25Q1 in each sub-line.
-- YoY_Pct NULL for all FY25 quarters (no FY24 quarterly data).
-- Watch for: DC_NET (Networking) FY26Q3 YoY should be around +160% (the AI cluster fabric story).
-- Output verified: 16 rows. DC-Networking FY26Q3 YoY +161.8%, FY26Q4 YoY +263.1%.
-- DC-Compute FY26Q2 QoQ went negative (-0.9%) while DC-Networking QoQ +46.3% same quarter.
-- Cleanest single piece of evidence of AI cluster buildout shift from chips to fabric.

SELECT
    dp.PeriodKey,
    dem.EndMarketName,
    fem.Revenue_USDmm AS Revenue,
    LAG(fem.Revenue_USDmm, 1) OVER (
        PARTITION BY dem.EndMarketKey ORDER BY dp.SortOrder
    ) AS PriorQuarterRevenue,
    LAG(fem.Revenue_USDmm, 4) OVER (
        PARTITION BY dem.EndMarketKey ORDER BY dp.SortOrder
    ) AS YearAgoQuarterRevenue,
    ROUND(
        100.0 * (fem.Revenue_USDmm - LAG(fem.Revenue_USDmm, 1) OVER (
            PARTITION BY dem.EndMarketKey ORDER BY dp.SortOrder
        )) / LAG(fem.Revenue_USDmm, 1) OVER (
            PARTITION BY dem.EndMarketKey ORDER BY dp.SortOrder
        ),
        1
    ) AS QoQ_Pct,
    ROUND(
        100.0 * (fem.Revenue_USDmm - LAG(fem.Revenue_USDmm, 4) OVER (
            PARTITION BY dem.EndMarketKey ORDER BY dp.SortOrder
        )) / LAG(fem.Revenue_USDmm, 4) OVER (
            PARTITION BY dem.EndMarketKey ORDER BY dp.SortOrder
        ),
        1
    ) AS YoY_Pct
FROM FactEndMarket fem
JOIN DimPeriod dp ON fem.PeriodKey = dp.PeriodKey
JOIN DimEndMarket dem ON fem.EndMarketKey = dem.EndMarketKey
WHERE dp.Granularity = 'Quarter'
  AND dem.IsSubline = 1
ORDER BY dem.EndMarketKey, dp.SortOrder;