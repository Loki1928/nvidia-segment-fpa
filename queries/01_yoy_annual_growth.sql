-- Question: How much did NVIDIA's total revenue grow each year?
-- Expected output: 3 rows (FY24, FY25, FY26)
-- FY24 PriorRevenue will be NULL because there's no FY23 data.
-- Output verified: FY25 +114.2%, FY26 +65.5%. FY24 PriorYearRevenue NULL as expected.

WITH annual_revenue AS (
    SELECT
        dp.FiscalYear,
        dp.SortOrder,
        SUM(fs.Revenue_USDmm) AS Revenue
    FROM FactSegment fs
    JOIN DimPeriod dp ON fs.PeriodKey = dp.PeriodKey
    WHERE dp.Granularity = 'Annual'
    GROUP BY dp.FiscalYear, dp.SortOrder
)
SELECT
    FiscalYear,
    Revenue,
    LAG(Revenue) OVER (ORDER BY SortOrder) AS PriorYearRevenue,
    Revenue - LAG(Revenue) OVER (ORDER BY SortOrder) AS YoY_Abs,
    ROUND(
        100.0 * (Revenue - LAG(Revenue) OVER (ORDER BY SortOrder))
        / LAG(Revenue) OVER (ORDER BY SortOrder),
        1
    ) AS YoY_Pct
FROM annual_revenue
ORDER BY SortOrder;