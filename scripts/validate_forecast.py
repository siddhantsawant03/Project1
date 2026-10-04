from pathlib import Path

import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "outputs" / "pnl_monthly.csv"
OUTPUT = ROOT / "outputs" / "forecast_backtest.csv"

CATEGORIES = [
    "Revenue",
    "COGS",
    "Personnel",
    "Opex",
    "Depreciation",
]


def seasonal_forecast(series, target_months):
    """
    Forecast each target month using the same month
    from the prior year.
    """

    results = []

    for month in target_months:

        comparable_month = (
            month - pd.DateOffset(years=1)
        )

        if comparable_month in series.index:
            value = series.loc[comparable_month]
        else:
            value = series.tail(12).mean()

        results.append(
            {
                "month": month,
                "forecast": float(value),
            }
        )

    return pd.DataFrame(results)


def build_backtest():

    df = pd.read_csv(INPUT)

    df["month"] = pd.to_datetime(df["month"])

    # --------------------------------------------------
    # Backtest period
    # --------------------------------------------------
    #
    # Pretend we are forecasting 2025 from information
    # available through December 2024.
    #
    # --------------------------------------------------

    target_months = pd.date_range(
        "2025-01-01",
        "2025-12-01",
        freq="MS",
    )

    results = []

    for category in CATEGORIES:

        category_df = (
            df[df["category"].eq(category)]
            .set_index("month")
            .sort_index()
        )

        historical = category_df.loc[
            category_df.index <= "2024-12-01",
            "actual",
        ]

        forecast = seasonal_forecast(
            historical,
            target_months,
        )

        actual = category_df.loc[
            target_months,
            "actual",
        ]

        forecast = forecast.set_index("month")

        comparison = pd.DataFrame(
            {
                "actual": actual,
                "forecast": forecast["forecast"],
            }
        )

        comparison["category"] = category

        comparison["error"] = (
            comparison["actual"]
            - comparison["forecast"]
        )

        comparison["absolute_error"] = (
            comparison["error"].abs()
        )

        comparison["absolute_percentage_error"] = (
            comparison["absolute_error"]
            / comparison["actual"].abs()
        )

        results.append(
            comparison.reset_index()
        )

    detail = pd.concat(
        results,
        ignore_index=True,
    )

    # --------------------------------------------------
    # Category-level summary
    # --------------------------------------------------

    summary = (
        detail
        .groupby("category")
        .agg(
            actual_total=("actual", "sum"),
            forecast_total=("forecast", "sum"),
            mae=("absolute_error", "mean"),
            mape=(
                "absolute_percentage_error",
                "mean",
            ),
            bias=("error", "mean"),
        )
        .reset_index()
    )

    summary["mape_pct"] = (
        summary["mape"] * 100
    )

    summary["forecast_bias_pct"] = (
        summary["bias"]
        / summary["actual_total"].abs()
        * 100
    )

    # --------------------------------------------------
    # Save detailed backtest
    # --------------------------------------------------

    detail.to_csv(
        OUTPUT,
        index=False,
    )

    SUMMARY_OUTPUT = (
        ROOT
        / "outputs"
        / "forecast_backtest_summary.csv"
    )

    summary.to_csv(
        SUMMARY_OUTPUT,
        index=False,
    )

    print(
        "Forecast backtest completed."
    )

    print(
        "\nCategory-level forecast performance:"
    )

    print(
        summary[
            [
                "category",
                "actual_total",
                "forecast_total",
                "mae",
                "mape_pct",
                "bias",
                "forecast_bias_pct",
            ]
        ].to_string(index=False)
    )

    print(
        f"\nDetailed output: {OUTPUT}"
    )

    print(
        f"Summary output: {SUMMARY_OUTPUT}"
    )


if __name__ == "__main__":
    build_backtest()