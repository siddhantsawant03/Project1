from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "outputs" / "pnl_monthly.csv"
OUTPUT = ROOT / "outputs" / "variance_driver_analysis.csv"


def build_variance_analysis():

    df = pd.read_csv(INPUT)

    df["month"] = pd.to_datetime(df["month"])

    pivot = df.pivot(
        index="month",
        columns="category",
        values=["actual", "budget"],
    )

    pivot.columns = [
        f"{measure}_{category.lower()}"
        for measure, category in pivot.columns
    ]

    pivot = pivot.reset_index()

    # --------------------------------------------------
    # Variance definition
    # --------------------------------------------------
    #
    # Revenue:
    # Higher actual revenue is favorable.
    #
    # Expenses:
    # Lower actual expense is favorable.
    #
    # Therefore:
    #
    # Revenue impact = Actual - Budget
    # Expense impact = Budget - Actual
    #
    # --------------------------------------------------

    pivot["revenue_impact"] = (
        pivot["actual_revenue"]
        - pivot["budget_revenue"]
    )

    pivot["cogs_impact"] = (
        pivot["budget_cogs"]
        - pivot["actual_cogs"]
    )

    pivot["personnel_impact"] = (
        pivot["budget_personnel"]
        - pivot["actual_personnel"]
    )

    pivot["opex_impact"] = (
        pivot["budget_opex"]
        - pivot["actual_opex"]
    )

    pivot["depreciation_impact"] = (
        pivot["budget_depreciation"]
        - pivot["actual_depreciation"]
    )

    # Total Operating Profit variance
    pivot["operating_profit_variance"] = (
        pivot["revenue_impact"]
        + pivot["cogs_impact"]
        + pivot["personnel_impact"]
        + pivot["opex_impact"]
        + pivot["depreciation_impact"]
    )

    # --------------------------------------------------
    # Reconciliation check
    # --------------------------------------------------

    pivot["variance_reconciliation_check"] = (
        pivot["operating_profit_variance"]
        - (
            pivot["revenue_impact"]
            + pivot["cogs_impact"]
            + pivot["personnel_impact"]
            + pivot["opex_impact"]
            + pivot["depreciation_impact"]
        )
    )

    # --------------------------------------------------
    # Driver ranking
    # --------------------------------------------------

    driver_columns = [
        "revenue_impact",
        "cogs_impact",
        "personnel_impact",
        "opex_impact",
        "depreciation_impact",
    ]

    pivot["largest_positive_driver"] = pivot[
        driver_columns
    ].idxmax(axis=1)

    pivot["largest_negative_driver"] = pivot[
        driver_columns
    ].idxmin(axis=1)

    # Absolute contribution
    pivot["total_absolute_driver_variance"] = pivot[
        driver_columns
    ].abs().sum(axis=1)

    for column in driver_columns:
        pivot[f"{column}_contribution_pct"] = (
            pivot[column].abs()
            / pivot["total_absolute_driver_variance"]
        )

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    pivot.to_csv(
        OUTPUT,
        index=False,
    )

    print(
        f"Built variance driver analysis: "
        f"{len(pivot)} monthly records"
    )

    print(
        f"Reconciliation max absolute difference: "
        f"{pivot['variance_reconciliation_check'].abs().max():,.6f}"
    )

    print(
        f"Output: {OUTPUT}"
    )


if __name__ == "__main__":
    build_variance_analysis()