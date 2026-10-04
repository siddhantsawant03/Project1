SELECT month, category, SUM(actual) actual, SUM(budget) budget,
       SUM(actual)-SUM(budget) variance,
       (SUM(actual)-SUM(budget))/NULLIF(SUM(budget),0) variance_pct
FROM fpna_model GROUP BY month, category ORDER BY month, category;
