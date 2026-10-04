-- Management P&L by month. Replace fpna_model with your SQL table/view.
SELECT month,
 SUM(CASE WHEN category='Revenue' THEN actual ELSE 0 END) revenue,
 SUM(CASE WHEN category='COGS' THEN actual ELSE 0 END) cogs,
 SUM(CASE WHEN category='Revenue' THEN actual ELSE 0 END)+SUM(CASE WHEN category='COGS' THEN actual ELSE 0 END) gross_profit,
 SUM(CASE WHEN category IN ('Personnel','Opex','Depreciation') THEN actual ELSE 0 END) operating_costs,
 SUM(CASE WHEN category IN ('Revenue','COGS','Personnel','Opex','Depreciation') THEN actual ELSE 0 END) operating_profit
FROM fpna_model GROUP BY month ORDER BY month;
