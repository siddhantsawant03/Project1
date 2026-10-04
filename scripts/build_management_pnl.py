from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "pnl_monthly.csv"
OUTPUT = ROOT / "outputs" / "management_pnl_monthly.csv"


def build_management_pnl():

    df = pd.read_csv(INPUT)

    df["month"] = pd.to_datetime(df["month"])

    # Convert category rows into columns.
    pivot = df.pivot(
        index="month",
        columns="category",
        values=[
            "actual",
            "budget",
            "forecast",
        ],
    )

    pivot.columns = [
        f"{measure}_{category.lower()}"
        for measure, category in pivot.columns
    ]

    pivot = pivot.reset_index()

    # -------------------------
    # Actual P&L
    # -------------------------

    pivot["actual_gross_profit"] = (
        pivot["actual_revenue"]
        - pivot["actual_cogs"]
    )

    pivot["actual_operating_profit"] = (
        pivot["actual_gross_profit"]
        - pivot["actual_personnel"]
        - pivot["actual_opex"]
        - pivot["actual_depreciation"]
    )

    # -------------------------
    # Budget P&L
    # -------------------------

    pivot["budget_gross_profit"] = (
        pivot["budget_revenue"]
        - pivot["budget_cogs"]
    )

    pivot["budget_operating_profit"] = (
        pivot["budget_gross_profit"]
        - pivot["budget_personnel"]
        - pivot["budget_opex"]
        - pivot["budget_depreciation"]
    )

    # -------------------------
    # Forecast P&L
    # -------------------------

    pivot["forecast_gross_profit"] = (
        pivot["forecast_revenue"]
        - pivot["forecast_cogs"]
    )

    pivot["forecast_operating_profit"] = (
        pivot["forecast_gross_profit"]
        - pivot["forecast_personnel"]
        - pivot["forecast_opex"]
        - pivot["forecast_depreciation"]
    )

    # -------------------------
    # Margins
    # -------------------------

    pivot["actual_gross_margin_pct"] = (
        pivot["actual_gross_profit"]
        / pivot["actual_revenue"]
    )

    pivot["budget_gross_margin_pct"] = (
        pivot["budget_gross_profit"]
        / pivot["budget_revenue"]
    )

    pivot["forecast_gross_margin_pct"] = (
        pivot["forecast_gross_profit"]
        / pivot["forecast_revenue"]
    )

    pivot["actual_operating_margin_pct"] = (
        pivot["actual_operating_profit"]
        / pivot["actual_revenue"]
    )

    pivot["budget_operating_margin_pct"] = (
        pivot["budget_operating_profit"]
        / pivot["budget_revenue"]
    )

    pivot["forecast_operating_margin_pct"] = (
        pivot["forecast_operating_profit"]
        / pivot["forecast_revenue"]
    )

    # -------------------------
    # Actual vs Budget variance
    # -------------------------

    pivot["revenue_variance"] = (
        pivot["actual_revenue"]
        - pivot["budget_revenue"]
    )

    pivot["gross_profit_variance"] = (
        pivot["actual_gross_profit"]
        - pivot["budget_gross_profit"]
    )

    pivot["operating_profit_variance"] = (
        pivot["actual_operating_profit"]
        - pivot["budget_operating_profit"]
    )

    pivot["revenue_variance_pct"] = (
        pivot["revenue_variance"]
        / pivot["budget_revenue"]
    )

    pivot["gross_profit_variance_pct"] = (
        pivot["gross_profit_variance"]
        / pivot["budget_gross_profit"]
    )

    pivot["operating_profit_variance_pct"] = (
        pivot["operating_profit_variance"]
        / pivot["budget_operating_profit"].abs()
    )

    # -------------------------
    # Forecast vs Budget
    # -------------------------

    pivot["forecast_revenue_variance"] = (
        pivot["forecast_revenue"]
        - pivot["budget_revenue"]
    )

    pivot["forecast_gross_profit_variance"] = (
        pivot["forecast_gross_profit"]
        - pivot["budget_gross_profit"]
    )

    pivot["forecast_operating_profit_variance"] = (
        pivot["forecast_operating_profit"]
        - pivot["budget_operating_profit"]
    )

    # -------------------------
    # Sort and save
    # -------------------------

    pivot = pivot.sort_values("month")

    pivot.to_csv(
        OUTPUT,
        index=False,
    )

    print(
        f"Built management P&L: "
        f"{len(pivot)} monthly records"
    )

    print(
        f"Period: "
        f"{pivot['month'].min().date()} "
        f"to "
        f"{pivot['month'].max().date()}"
    )

    print(
        f"Output: {OUTPUT}"
    )


if __name__ == "__main__":
    build_management_pnl()