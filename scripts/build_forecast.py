from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "outputs" / "pnl_monthly.csv"
OUTPUT = ROOT / "outputs" / "forecast_analysis.csv"

FORECAST_MONTHS = 12

CATEGORIES = [
    "Revenue",
    "COGS",
    "Personnel",
    "Opex",
    "Depreciation",
]


def seasonal_forecast(series, periods=12):
    """
    Transparent FP&A baseline forecast.

    Uses the corresponding month from the prior year
    to preserve observed seasonality.
    """

    series = series.sort_index()
    forecasts = []

    for i in range(1, periods + 1):

        target_month = (
            series.index.max()
            + pd.DateOffset(months=i)
        )

        comparable_month = (
            target_month
            - pd.DateOffset(years=1)
        )

        if comparable_month in series.index:
            value = series.loc[comparable_month]
        else:
            value = series.tail(12).mean()

        forecasts.append(
            {
                "month": target_month,
                "forecast": float(value),
            }
        )

    return pd.DataFrame(forecasts)


def build_forecast():

    df = pd.read_csv(INPUT)
    df["month"] = pd.to_datetime(df["month"])

    results = []

    for category in CATEGORIES:

        subset = (
            df[df["category"].eq(category)]
            .set_index("month")
            .sort_index()
        )

        forecast = seasonal_forecast(
            subset["actual"],
            periods=FORECAST_MONTHS,
        )

        forecast["category"] = category
        results.append(forecast)

    forecast_df = pd.concat(
        results,
        ignore_index=True,
    )

    pivot = forecast_df.pivot(
        index="month",
        columns="category",
        values="forecast",
    ).reset_index()

    for category in CATEGORIES:
        if category not in pivot.columns:
            pivot[category] = np.nan

    pivot["Gross Profit"] = (
        pivot["Revenue"]
        - pivot["COGS"]
    )

    pivot["Operating Profit"] = (
        pivot["Gross Profit"]
        - pivot["Personnel"]
        - pivot["Opex"]
        - pivot["Depreciation"]
    )

    pivot["Gross Margin %"] = (
        pivot["Gross Profit"]
        / pivot["Revenue"]
    )

    pivot["Operating Margin %"] = (
        pivot["Operating Profit"]
        / pivot["Revenue"]
    )

    pivot = pivot.sort_values("month")

    pivot.to_csv(
        OUTPUT,
        index=False,
    )

    print(
        f"Built forecast analysis: "
        f"{len(pivot)} forecast months"
    )

    print(
        f"Forecast period: "
        f"{pivot['month'].min().date()} "
        f"to "
        f"{pivot['month'].max().date()}"
    )

    print(
        f"Output: {OUTPUT}"
    )


if __name__ == "__main__":
    build_forecast()