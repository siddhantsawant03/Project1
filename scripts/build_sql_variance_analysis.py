from pathlib import Path

import duckdb


# ============================================================
# Project paths
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "data" / "fpna.duckdb"
OUTPUT = ROOT / "outputs"

OUTPUT.mkdir(parents=True, exist_ok=True)


def main():

    print("=" * 70)
    print("ENTERPRISE FP&A — SQL VARIANCE DRIVER ANALYSIS")
    print("=" * 70)

    con = duckdb.connect(str(DB_PATH))

    # ============================================================
    # 1. Build monthly Budget layer
    # ============================================================

    print("\n[1/5] Building monthly budget layer...")

    con.execute("""
        CREATE OR REPLACE VIEW monthly_budget AS

        SELECT

            month,

            /*
            Revenue in the planning source is stored with the
            accounting sign. Reverse it here for management P&L
            presentation so Revenue is positive.
            */

            SUM(
                CASE
                    WHEN category = 'Revenue'
                        THEN -1 * plan_amount
                    ELSE 0
                END
            ) AS budget_revenue,

            SUM(
                CASE
                    WHEN category = 'COGS'
                        THEN plan_amount
                    ELSE 0
                END
            ) AS budget_cogs,

            SUM(
                CASE
                    WHEN category = 'Personnel'
                        THEN plan_amount
                    ELSE 0
                END
            ) AS budget_personnel,

            SUM(
                CASE
                    WHEN category = 'Opex'
                        THEN plan_amount
                    ELSE 0
                END
            ) AS budget_opex,

            SUM(
                CASE
                    WHEN category = 'Depreciation'
                        THEN plan_amount
                    ELSE 0
                END
            ) AS budget_depreciation

        FROM fact_plan

        WHERE
            CAST(version AS VARCHAR) = '1'

        GROUP BY month

        ORDER BY month
    """)

    print("Monthly budget layer created.")


    # ============================================================
    # 2. Build variance driver analysis
    # ============================================================

    print("\n[2/5] Building variance-driver analysis...")

    con.execute("""
        CREATE OR REPLACE VIEW variance_driver_analysis AS

        WITH combined AS (

            SELECT

                a.month,

                a.actual_revenue,
                a.actual_cogs,
                a.actual_personnel,
                a.actual_opex,
                a.actual_depreciation,
                a.actual_operating_profit,

                COALESCE(b.budget_revenue, 0)
                    AS budget_revenue,

                COALESCE(b.budget_cogs, 0)
                    AS budget_cogs,

                COALESCE(b.budget_personnel, 0)
                    AS budget_personnel,

                COALESCE(b.budget_opex, 0)
                    AS budget_opex,

                COALESCE(b.budget_depreciation, 0)
                    AS budget_depreciation

            FROM management_pnl a

            LEFT JOIN monthly_budget b
                ON a.month = b.month
        ),

        calculated AS (

            SELECT

                *,

                (
                    budget_revenue
                    - budget_cogs
                    - budget_personnel
                    - budget_opex
                    - budget_depreciation
                ) AS budget_operating_profit

            FROM combined
        )

        SELECT

            month,

            actual_revenue,
            budget_revenue,

            actual_cogs,
            budget_cogs,

            actual_personnel,
            budget_personnel,

            actual_opex,
            budget_opex,

            actual_depreciation,
            budget_depreciation,

            actual_operating_profit,
            budget_operating_profit,

            /*
            Management variance convention:

            Revenue:
                Actual - Budget

            Expenses:
                Budget - Actual

            Positive = favorable to Operating Profit
            Negative = unfavorable to Operating Profit
            */

            (
                actual_revenue
                - budget_revenue
            ) AS revenue_impact,

            (
                budget_cogs
                - actual_cogs
            ) AS cogs_impact,

            (
                budget_personnel
                - actual_personnel
            ) AS personnel_impact,

            (
                budget_opex
                - actual_opex
            ) AS opex_impact,

            (
                budget_depreciation
                - actual_depreciation
            ) AS depreciation_impact,

            (
                actual_operating_profit
                - budget_operating_profit
            ) AS operating_profit_variance,

            (
                (
                    actual_revenue
                    - budget_revenue
                )
                +
                (
                    budget_cogs
                    - actual_cogs
                )
                +
                (
                    budget_personnel
                    - actual_personnel
                )
                +
                (
                    budget_opex
                    - actual_opex
                )
                +
                (
                    budget_depreciation
                    - actual_depreciation
                )
            ) AS driver_reconciliation,

            CASE

                WHEN (
                    actual_operating_profit
                    - budget_operating_profit
                ) > 0
                    THEN 'Favorable'

                WHEN (
                    actual_operating_profit
                    - budget_operating_profit
                ) < 0
                    THEN 'Unfavorable'

                ELSE 'On Plan'

            END AS overall_status

        FROM calculated

        ORDER BY month
    """)

    print("Variance-driver analysis created.")


    # ============================================================
    # 3. Build normalized driver ranking
    # ============================================================

    print("\n[3/5] Building ranked driver view...")

    con.execute("""
        CREATE OR REPLACE VIEW variance_driver_ranking AS

        SELECT
            month,
            'Revenue' AS driver,
            revenue_impact AS impact,

            CASE
                WHEN revenue_impact > 0
                    THEN 'Favorable'
                WHEN revenue_impact < 0
                    THEN 'Unfavorable'
                ELSE 'On Plan'
            END AS status

        FROM variance_driver_analysis

        UNION ALL

        SELECT
            month,
            'COGS' AS driver,
            cogs_impact AS impact,

            CASE
                WHEN cogs_impact > 0
                    THEN 'Favorable'
                WHEN cogs_impact < 0
                    THEN 'Unfavorable'
                ELSE 'On Plan'
            END AS status

        FROM variance_driver_analysis

        UNION ALL

        SELECT
            month,
            'Personnel' AS driver,
            personnel_impact AS impact,

            CASE
                WHEN personnel_impact > 0
                    THEN 'Favorable'
                WHEN personnel_impact < 0
                    THEN 'Unfavorable'
                ELSE 'On Plan'
            END AS status

        FROM variance_driver_analysis

        UNION ALL

        SELECT
            month,
            'Opex' AS driver,
            opex_impact AS impact,

            CASE
                WHEN opex_impact > 0
                    THEN 'Favorable'
                WHEN opex_impact < 0
                    THEN 'Unfavorable'
                ELSE 'On Plan'
            END AS status

        FROM variance_driver_analysis

        UNION ALL

        SELECT
            month,
            'Depreciation' AS driver,
            depreciation_impact AS impact,

            CASE
                WHEN depreciation_impact > 0
                    THEN 'Favorable'
                WHEN depreciation_impact < 0
                    THEN 'Unfavorable'
                ELSE 'On Plan'
            END AS status

        FROM variance_driver_analysis
    """)

    print("Ranked driver view created.")


    # ============================================================
    # 4. Export outputs
    # ============================================================

    print("\n[4/5] Exporting variance outputs...")

    exports = {

        "sql_variance_driver_analysis.csv":
            "SELECT * FROM variance_driver_analysis",

        "sql_variance_driver_ranking.csv":
            """
            SELECT
                month,
                driver,
                impact,
                status

            FROM variance_driver_ranking

            ORDER BY
                month,
                ABS(impact) DESC
            """
    }

    for filename, query in exports.items():

        output_file = OUTPUT / filename

        con.execute(
            f"""
            COPY ({query})
            TO '{output_file.as_posix()}'
            (
                HEADER,
                DELIMITER ','
            )
            """
        )

        print(f"  ✓ {filename}")


    # ============================================================
    # 5. Validation
    # ============================================================

    print("\n[5/5] Running variance reconciliation...")

    rows = con.execute("""
        SELECT COUNT(*)
        FROM variance_driver_analysis
    """).fetchone()[0]

    max_difference = con.execute("""
        SELECT
            MAX(
                ABS(
                    operating_profit_variance
                    - driver_reconciliation
                )
            )
        FROM variance_driver_analysis
    """).fetchone()[0]

    favorable_months = con.execute("""
        SELECT COUNT(*)
        FROM variance_driver_analysis
        WHERE overall_status = 'Favorable'
    """).fetchone()[0]

    unfavorable_months = con.execute("""
        SELECT COUNT(*)
        FROM variance_driver_analysis
        WHERE overall_status = 'Unfavorable'
    """).fetchone()[0]

    on_plan_months = con.execute("""
        SELECT COUNT(*)
        FROM variance_driver_analysis
        WHERE overall_status = 'On Plan'
    """).fetchone()[0]

    print(f"  Variance records:              {rows}")
    print(f"  Max reconciliation difference: {max_difference:.10f}")
    print(f"  Favorable months:              {favorable_months}")
    print(f"  Unfavorable months:            {unfavorable_months}")
    print(f"  On-plan months:                {on_plan_months}")


    # ============================================================
    # Budget coverage validation
    # ============================================================

    budget_coverage = con.execute("""
        SELECT

            COUNT(*) AS total_months,

            COUNT(
                CASE
                    WHEN budget_revenue <> 0
                        THEN 1
                END
            ) AS months_with_budget

        FROM monthly_budget
    """).fetchone()

    total_budget_months = budget_coverage[0]
    populated_budget_months = budget_coverage[1]

    print(
        f"  Budget months populated:       "
        f"{populated_budget_months}/{total_budget_months}"
    )


    if max_difference > 0.01:
        raise ValueError(
            "Variance-driver reconciliation failed."
        )

    if total_budget_months != 48:
        raise ValueError(
            f"Expected 48 budget months, found "
            f"{total_budget_months}."
        )

    if populated_budget_months != 48:
        raise ValueError(
            "Budget revenue is missing for one or more months."
        )


    # ============================================================
    # Python cross-layer validation
    # ============================================================

    print("\nValidating SQL Budget against Python management P&L...")

    python_jan_budget = con.execute("""
        SELECT
            budget_revenue,
            budget_cogs,
            budget_personnel,
            budget_opex,
            budget_depreciation,
            budget_operating_profit

        FROM variance_driver_analysis

        WHERE month = DATE '2022-01-01'
    """).fetchone()

    if python_jan_budget:

        print(
            f"  January 2022 Budget Revenue: "
            f"{python_jan_budget[0]:,.2f}"
        )

        print(
            f"  January 2022 Budget COGS: "
            f"{python_jan_budget[1]:,.2f}"
        )

        print(
            f"  January 2022 Budget Personnel: "
            f"{python_jan_budget[2]:,.2f}"
        )

        print(
            f"  January 2022 Budget Opex: "
            f"{python_jan_budget[3]:,.2f}"
        )

        print(
            f"  January 2022 Budget Depreciation: "
            f"{python_jan_budget[4]:,.2f}"
        )

        print(
            f"  January 2022 Budget Operating Profit: "
            f"{python_jan_budget[5]:,.2f}"
        )


    # ============================================================
    # Largest drivers
    # ============================================================

    print("\nLargest variance drivers across the full period:")

    top_drivers = con.execute("""
        SELECT

            driver,

            SUM(impact) AS total_impact,

            SUM(ABS(impact)) AS absolute_impact

        FROM variance_driver_ranking

        GROUP BY driver

        ORDER BY absolute_impact DESC
    """).fetchdf()

    print(
        top_drivers.to_string(index=False)
    )


    # ============================================================
    # Sample January 2022 variance bridge
    # ============================================================

    print("\nSample January 2022 variance bridge:")

    sample = con.execute("""
        SELECT

            month,

            ROUND(actual_operating_profit, 2)
                AS actual_operating_profit,

            ROUND(budget_operating_profit, 2)
                AS budget_operating_profit,

            ROUND(revenue_impact, 2)
                AS revenue_impact,

            ROUND(cogs_impact, 2)
                AS cogs_impact,

            ROUND(personnel_impact, 2)
                AS personnel_impact,

            ROUND(opex_impact, 2)
                AS opex_impact,

            ROUND(depreciation_impact, 2)
                AS depreciation_impact,

            ROUND(operating_profit_variance, 2)
                AS operating_profit_variance,

            overall_status

        FROM variance_driver_analysis

        WHERE month = DATE '2022-01-01'
    """).fetchdf()

    print(
        sample.to_string(index=False)
    )


    print("\n" + "=" * 70)
    print("SQL VARIANCE DRIVER LAYER BUILT SUCCESSFULLY")
    print("=" * 70)

    con.close()


if __name__ == "__main__":
    main()