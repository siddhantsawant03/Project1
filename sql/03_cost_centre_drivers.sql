SELECT cost_centre, category, SUM(actual) actual, SUM(budget) budget,
       SUM(actual)-SUM(budget) variance
FROM fpna_model GROUP BY cost_centre, category
ORDER BY ABS(SUM(actual)-SUM(budget)) DESC;
