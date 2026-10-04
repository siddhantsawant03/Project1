SELECT COUNT(*) rows,
       COUNT(DISTINCT month) months,
       COUNT(DISTINCT cost_centre) cost_centres,
       COUNT(DISTINCT company_code) companies,
       SUM(CASE WHEN month IS NULL THEN 1 ELSE 0 END) missing_months
FROM fpna_model;
