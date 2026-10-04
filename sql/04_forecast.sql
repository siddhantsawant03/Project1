SELECT month, category, SUM(budget) budget, SUM(forecast) rolling_forecast,
       SUM(forecast)-SUM(budget) forecast_vs_budget
FROM fpna_model GROUP BY month, category ORDER BY month, category;
