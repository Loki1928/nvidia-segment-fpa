-- Question: How is China revenue trending, and what does it say about export controls?
-- Approach: Use annual geography data only (clean CUST_HQ basis, no quarterly mixed-basis problem).
-- Output verified: 3 rows. FY26 China YoY -21.4% in a year overall grew +65%.
-- China share collapsed 20.2% -> 19.2% -> 9.1% across FY24/FY25/FY26.
-- FY25 was the peak ($25.0B). FY25->FY26 was a single-year inflection, not gradual decline.
-- Share decline preceded dollar decline: 20.2->19.2 share in FY25 even as China grew +103%.

WITH china_annual AS (
    SELECT
        dp.FiscalYear,
        dp.SortOrder,
        SUM(CASE WHEN fg.GeographyKey = 'CN_HK' THEN fg.Revenue_USDmm ELSE 0 END) AS ChinaRevenue,
        SUM(fg.Revenue_USDmm) AS TotalRevenue
    FROM FactGeography fg
    JOIN DimPeriod dp ON fg.PeriodKey = dp.PeriodKey
    WHERE dp.Granularity = 'Annual'
    GROUP BY dp.FiscalYear, dp.SortOrder
)
SELECT
    FiscalYear,
    ChinaRevenue,
    TotalRevenue,
    ROUND(100.0 * ChinaRevenue / TotalRevenue, 1) AS China_Share_Pct,
    LAG(ChinaRevenue) OVER (ORDER BY SortOrder) AS PriorYearChina,
    ChinaRevenue - LAG(ChinaRevenue) OVER (ORDER BY SortOrder) AS China_YoY_Abs,
    ROUND(
        100.0 * (ChinaRevenue - LAG(ChinaRevenue) OVER (ORDER BY SortOrder))
        / LAG(ChinaRevenue) OVER (ORDER BY SortOrder),
        1
    ) AS China_YoY_Pct
FROM china_annual
ORDER BY SortOrder;