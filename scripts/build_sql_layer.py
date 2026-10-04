from pathlib import Path



import duckdb





# ============================================================

# Project paths

# ============================================================



ROOT = Path(__file__).resolve().parents[1]



RAW = (

    ROOT

    / "data"

    / "raw"

    / "sap-fpa-dataset"

    / "sapajaykumar-sap-fpa-dataset-f2a9d2e"

    / "data"

)



OUTPUT = ROOT / "outputs"

DB_PATH = ROOT / "data" / "fpna.duckdb"



OUTPUT.mkdir(parents=True, exist_ok=True)





# ============================================================

# Helper functions

# ============================================================



def sql_path(path: Path) -> str:

    """Return a DuckDB-safe forward-slash path."""

    return path.as_posix()





def main():



    print("=" * 70)

    print("ENTERPRISE FP&A — DUCKDB SQL LAYER")

    print("=" * 70)



    con = duckdb.connect(str(DB_PATH))



    # ========================================================

    # 1. Register source tables

    # ========================================================



    print("\n[1/10] Registering source tables...")



    con.execute(f"""

        CREATE OR REPLACE VIEW dim_gl_account AS

        SELECT *

        FROM read_csv_auto(

            '{sql_path(RAW / "dim_gl_account.csv")}'

        );

    """)



    con.execute(f"""

        CREATE OR REPLACE VIEW dim_cost_center AS

        SELECT *

        FROM read_csv_auto(

            '{sql_path(RAW / "dim_cost_center.csv")}'

        );

    """)



    con.execute(f"""

        CREATE OR REPLACE VIEW dim_company_code AS

        SELECT *

        FROM read_csv_auto(

            '{sql_path(RAW / "dim_company_code.csv")}'

        );

    """)



    con.execute(f"""

        CREATE OR REPLACE VIEW plan_versions AS

        SELECT *

        FROM read_csv_auto(

            '{sql_path(RAW / "plan_versions.csv")}'

        );

    """)



    con.execute(f"""

        CREATE OR REPLACE VIEW acdoca_actuals AS

        SELECT *

        FROM read_csv_auto(

            '{sql_path(RAW / "acdoca_actuals.csv")}'

        );

    """)



    print("Source tables registered.")





    # ========================================================

    # 2. Actuals staging

    # ========================================================



    print("\n[2/10] Building actuals staging layer...")



    con.execute("""

        CREATE OR REPLACE VIEW stg_actuals AS



        SELECT



            CAST(a.BUKRS AS VARCHAR) AS company_code,



            CAST(a.BELNR AS VARCHAR) AS document_number,



            CAST(a.GJAHR AS INTEGER) AS fiscal_year,



            CAST(a.MONAT AS INTEGER) AS fiscal_month,



            TRY_CAST(a.BUDAT AS DATE) AS posting_date,



            CAST(a.HKONT AS VARCHAR) AS gl_account,



            CAST(a.KOSTL AS VARCHAR) AS cost_center,



            CAST(a.PRCTR AS VARCHAR) AS profit_center,



            CAST(a.SHKZG AS VARCHAR) AS debit_credit,



            CAST(a.DMBTR AS DOUBLE) AS amount_local,



            CASE

                WHEN UPPER(TRIM(a.SHKZG)) = 'H'

                    THEN -1 * CAST(a.DMBTR AS DOUBLE)

                ELSE CAST(a.DMBTR AS DOUBLE)

            END AS signed_amount



        FROM acdoca_actuals a

    """)



    print("Actuals staging created.")





    # ========================================================

    # 3. Actuals analytical fact

    # ========================================================



    print("\n[3/10] Building analytical actuals fact...")



    con.execute("""

        CREATE OR REPLACE VIEW fact_actuals AS



        SELECT



            a.company_code,



            a.document_number,



            a.fiscal_year,



            a.fiscal_month,



            MAKE_DATE(

                a.fiscal_year,

                CASE

                    WHEN a.fiscal_month BETWEEN 1 AND 12

                        THEN a.fiscal_month

                    ELSE 12

                END,

                1

            ) AS month,



            a.posting_date,



            a.gl_account,



            g.TXT50 AS gl_description,



            CASE

                WHEN UPPER(TRIM(g.CATEGORY)) = 'REVENUE'

                    THEN 'Revenue'



                WHEN UPPER(TRIM(g.CATEGORY)) = 'COGS'

                    THEN 'COGS'



                WHEN UPPER(TRIM(g.CATEGORY)) = 'PERSONNEL'

                    THEN 'Personnel'



                WHEN UPPER(TRIM(g.CATEGORY)) = 'OPEX'

                    THEN 'Opex'



                WHEN UPPER(TRIM(g.CATEGORY)) = 'DEPRECIATION'

                    THEN 'Depreciation'



                ELSE 'Balance Sheet'

            END AS category,



            a.cost_center,



            c.KOSTL_GROUP AS cost_center_group,



            c.CC_TYPE AS cost_center_type,



            a.profit_center,



            CASE



                /*

                SAP sign convention:

                Revenue is generally credit-positive.

                Reverse it for management P&L presentation.

                */



                WHEN UPPER(TRIM(g.CATEGORY)) = 'REVENUE'

                    THEN -1 * a.signed_amount



                ELSE a.signed_amount



            END AS actual



        FROM stg_actuals a



        LEFT JOIN dim_gl_account g

            ON CAST(a.gl_account AS VARCHAR)

             = CAST(g.HKONT AS VARCHAR)



        LEFT JOIN dim_cost_center c

            ON CAST(a.company_code AS VARCHAR)

             = CAST(c.BUKRS AS VARCHAR)



            AND CAST(a.cost_center AS VARCHAR)

             = CAST(c.KOSTL AS VARCHAR)



        WHERE UPPER(TRIM(g.CATEGORY)) IN (

            'REVENUE',

            'COGS',

            'PERSONNEL',

            'OPEX',

            'DEPRECIATION'

        )

    """)



    print("Analytical actuals fact created.")





    # ========================================================

    # 4. Planning / budget fact

    # ========================================================



    print("\n[4/10] Building planning fact...")



    con.execute("""

        CREATE OR REPLACE VIEW fact_plan AS



        SELECT



            CAST(p.BUKRS AS VARCHAR) AS company_code,



            CAST(p.GJAHR AS INTEGER) AS fiscal_year,



            CAST(p.MONAT AS INTEGER) AS fiscal_month,



            MAKE_DATE(

                CAST(p.GJAHR AS INTEGER),



                CASE

                    WHEN CAST(p.MONAT AS INTEGER) BETWEEN 1 AND 12

                        THEN CAST(p.MONAT AS INTEGER)

                    ELSE 12

                END,



                1

            ) AS month,



            CAST(p.VERSION AS VARCHAR) AS version,



            CAST(p.VERSION_TXT AS VARCHAR) AS version_description,



            CAST(p.KOSTL AS VARCHAR) AS cost_center,



            CAST(p.PRCTR AS VARCHAR) AS profit_center,



            CAST(p.HKONT AS VARCHAR) AS gl_account,



            CASE

                WHEN UPPER(TRIM(p.CATEGORY)) = 'REVENUE'

                    THEN 'Revenue'



                WHEN UPPER(TRIM(p.CATEGORY)) = 'COGS'

                    THEN 'COGS'



                WHEN UPPER(TRIM(p.CATEGORY)) = 'PERSONNEL'

                    THEN 'Personnel'



                WHEN UPPER(TRIM(p.CATEGORY)) = 'OPEX'

                    THEN 'Opex'



                WHEN UPPER(TRIM(p.CATEGORY)) = 'DEPRECIATION'

                    THEN 'Depreciation'



                ELSE 'Balance Sheet'

            END AS category,



            CASE



                WHEN UPPER(TRIM(p.CATEGORY)) = 'REVENUE'

                    THEN -1 * CAST(p.DMBTR AS DOUBLE)



                ELSE CAST(p.DMBTR AS DOUBLE)



            END AS plan_amount



        FROM plan_versions p



        WHERE UPPER(TRIM(p.CATEGORY)) IN (

            'REVENUE',

            'COGS',

            'PERSONNEL',

            'OPEX',

            'DEPRECIATION'

        )

    """)



    print("Planning fact created.")





    # ========================================================

    # 5. Monthly P&L

    # ========================================================



    print("\n[5/10] Building monthly P&L view\...")



    con.execute("""

        CREATE OR REPLACE VIEW monthly_pnl AS



        SELECT



            month,



            SUM(

                CASE

                    WHEN category = 'Revenue'

                        THEN actual

                    ELSE 0

                END

            ) AS revenue,



            SUM(

                CASE

                    WHEN category = 'COGS'

                        THEN actual

                    ELSE 0

                END

            ) AS cogs,



            SUM(

                CASE

                    WHEN category = 'Personnel'

                        THEN actual

                    ELSE 0

                END

            ) AS personnel,



            SUM(

                CASE

                    WHEN category = 'Opex'

                        THEN actual

                    ELSE 0

                END

            ) AS opex,



            SUM(

                CASE

                    WHEN category = 'Depreciation'

                        THEN actual

                    ELSE 0

                END

            ) AS depreciation



        FROM fact_actuals



        GROUP BY month



        ORDER BY month

    """)



    print("Monthly P&L created.")





    # ========================================================

    # 6. Budget vs Actual

    # ========================================================



    print("\n[6/10] Building Budget vs Actual view\...")



    con.execute("""

        CREATE OR REPLACE VIEW budget_vs_actual AS



        WITH actuals AS (



            SELECT



                month,



                category,



                SUM(actual) AS actual



            FROM fact_actuals



            GROUP BY

                month,

                category

        ),



        budget AS (



            SELECT



                month,



                category,



                SUM(

    CASE

        WHEN category = 'Revenue'

            THEN -1 * plan_amount

        ELSE plan_amount

    END

) AS budget



            FROM fact_plan



            WHERE

                UPPER(TRIM(version)) = 'BUDGET'

                OR UPPER(TRIM(version_description))

                    LIKE '%BUDGET%'



            GROUP BY

                month,

                category

        )



        SELECT



            COALESCE(a.month, b.month) AS month,



            COALESCE(a.category, b.category) AS category,



            COALESCE(a.actual, 0) AS actual,



            COALESCE(b.budget, 0) AS budget,



            COALESCE(a.actual, 0)

            -

            COALESCE(b.budget, 0) AS variance



        FROM actuals a



        FULL OUTER JOIN budget b



            ON a.month = b.month



            AND a.category = b.category



        ORDER BY

            month,

            category

    """)



    print("Budget vs Actual created.")





    # ========================================================

    # 7. Management P&L

    # ========================================================



    print("\n[7/10] Building management P&L view\...")



    con.execute("""

        CREATE OR REPLACE VIEW management_pnl AS



        SELECT



            month,



            SUM(

                CASE

                    WHEN category = 'Revenue'

                        THEN actual

                    ELSE 0

                END

            ) AS actual_revenue,



            SUM(

                CASE

                    WHEN category = 'COGS'

                        THEN actual

                    ELSE 0

                END

            ) AS actual_cogs,



            SUM(

                CASE

                    WHEN category = 'Revenue'

                        THEN actual

                    ELSE 0

                END

            )

            -

            SUM(

                CASE

                    WHEN category = 'COGS'

                        THEN actual

                    ELSE 0

                END

            ) AS actual_gross_profit,



            SUM(

                CASE

                    WHEN category = 'Personnel'

                        THEN actual

                    ELSE 0

                END

            ) AS actual_personnel,



            SUM(

                CASE

                    WHEN category = 'Opex'

                        THEN actual

                    ELSE 0

                END

            ) AS actual_opex,



            SUM(

                CASE

                    WHEN category = 'Depreciation'

                        THEN actual

                    ELSE 0

                END

            ) AS actual_depreciation,



            SUM(

                CASE

                    WHEN category IN (

                        'Personnel',

                        'Opex',

                        'Depreciation'

                    )

                        THEN actual

                    ELSE 0

                END

            ) AS actual_operating_expenses,



            SUM(

                CASE

                    WHEN category = 'Revenue'

                        THEN actual

                    ELSE 0

                END

            )

            -

            SUM(

                CASE

                    WHEN category IN (

                        'COGS',

                        'Personnel',

                        'Opex',

                        'Depreciation'

                    )

                        THEN actual

                    ELSE 0

                END

            ) AS actual_operating_profit



        FROM fact_actuals



        GROUP BY month



        ORDER BY month

    """)



    print("Management P&L created.")





    # ========================================================

    # 8. Cost Centre Performance

    # ========================================================



    print("\n[8/10] Building cost centre performance view\...")



    con.execute("""

        CREATE OR REPLACE VIEW cost_centre_performance AS



        WITH actuals AS (



            SELECT



                company_code,



                cost_center,



                category,



                SUM(actual) AS actual



            FROM fact_actuals



            GROUP BY

                company_code,

                cost_center,

                category

        ),



        budget AS (



            SELECT



                company_code,



                cost_center,



                category,



                SUM(

                    CASE
                        WHEN category = 'Revenue'
                            THEN -1 * plan_amount
                        ELSE plan_amount
                    END
                ) AS budget



            FROM fact_plan



            WHERE CAST(version AS VARCHAR) = '1'



            GROUP BY

                company_code,

                cost_center,

                category

        )



        SELECT



            COALESCE(

                a.company_code,

                b.company_code

            ) AS company_code,



            COALESCE(

                a.cost_center,

                b.cost_center

            ) AS cost_center,



            COALESCE(

                a.category,

                b.category

            ) AS category,



            COALESCE(a.actual, 0) AS actual,



            COALESCE(b.budget, 0) AS budget,



            COALESCE(a.actual, 0)

            -

            COALESCE(b.budget, 0) AS variance



        FROM actuals a



        FULL OUTER JOIN budget b



            ON a.company_code = b.company_code



            AND a.cost_center = b.cost_center



            AND a.category = b.category



        ORDER BY

            company_code,

            cost_center,

            category

    """)



    print("Cost centre performance created.")





    # ========================================================

    # 9. Export analytical SQL outputs

    # ========================================================



    print("\n[9/10] Exporting SQL outputs...")



    exports = {



        "sql_monthly_pnl.csv":

            "SELECT * FROM monthly_pnl",



        "sql_budget_vs_actual.csv":

            "SELECT * FROM budget_vs_actual",



        "sql_management_pnl.csv":

            "SELECT * FROM management_pnl",



        "sql_cost_centre_performance.csv":

            "SELECT * FROM cost_centre_performance",



    }



    for filename, query in exports.items():



        output_file = OUTPUT / filename



        con.execute(

            f"""

            COPY ({query})

            TO '{sql_path(output_file)}'

            (

                HEADER,

                DELIMITER ','

            )

            """

        )



        print(f"  ✓ {filename}")





    # ========================================================

    # 10. Validation

    # ========================================================



    print("\n[10/10] Running SQL validation...")



    monthly_pnl_rows = con.execute(

        "SELECT COUNT(*) FROM monthly_pnl"

    ).fetchone()[0]



    budget_actual_rows = con.execute(

        "SELECT COUNT(*) FROM budget_vs_actual"

    ).fetchone()[0]



    management_pnl_rows = con.execute(

        "SELECT COUNT(*) FROM management_pnl"

    ).fetchone()[0]



    cost_centre_rows = con.execute(

        "SELECT COUNT(*) FROM cost_centre_performance"

    ).fetchone()[0]



    actual_min_month, actual_max_month = con.execute("""

        SELECT

            MIN(month),

            MAX(month)

        FROM fact_actuals

    """).fetchone()



    distinct_cost_centres = con.execute("""

        SELECT COUNT(DISTINCT cost_center)

        FROM fact_actuals

        WHERE cost_center IS NOT NULL

    """).fetchone()[0]



    print(f"  Monthly P&L rows:             {monthly_pnl_rows}")

    print(f"  Budget vs Actual rows:        {budget_actual_rows}")

    print(f"  Management P&L rows:          {management_pnl_rows}")

    print(f"  Cost centre rows:             {cost_centre_rows}")

    print(f"  Actual period:                {actual_min_month} → {actual_max_month}")

    print(f"  Distinct cost centres:        {distinct_cost_centres}")



    # --------------------------------------------------------

    # Management P&L reconciliation

    # --------------------------------------------------------



    reconciliation = con.execute("""

        SELECT

            MAX(

                ABS(

                    actual_revenue

                    - actual_cogs

                    - actual_gross_profit

                )

            ),



            MAX(

                ABS(

                    actual_gross_profit

                    - actual_operating_expenses

                    - actual_operating_profit

                )

            )



        FROM management_pnl

    """).fetchone()



    gross_profit_error = reconciliation[0] or 0

    operating_profit_error = reconciliation[1] or 0



    print(

        f"  Gross profit reconciliation: {gross_profit_error:.6f}"

    )



    print(

        f"  Operating profit reconciliation: "

        f"{operating_profit_error:.6f}"

    )



    if gross_profit_error > 0.01:

        raise ValueError(

            "Gross profit reconciliation failed."

        )



    if operating_profit_error > 0.01:

        raise ValueError(

            "Operating profit reconciliation failed."

        )



    print("\n" + "=" * 70)

    print("SQL LAYER BUILT SUCCESSFULLY")

    print("=" * 70)



    print(f"\nDuckDB database:")

    print(DB_PATH)



    print("\nSQL exports:")

    for filename in exports:

        print(f"  {OUTPUT / filename}")



    con.close()





if __name__ == "__main__":

    main()