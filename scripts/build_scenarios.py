from pathlib import Path

import pandas as pd


# ============================================================
# Project paths
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

OUTPUT = ROOT / "outputs"

FORECAST_FILE = OUTPUT / "forecast_analysis.csv"
SCENARIO_FILE = OUTPUT / "scenario_analysis.csv"

OUTPUT.mkdir(parents=True, exist_ok=True)


# ============================================================
# Scenario assumptions
# ============================================================

SCENARIOS = {
    "Base": {
        "revenue_growth": 0.00,
        "cogs_change": 0.00,
        "personnel_change": 0.00,
        "opex_change": 0.00,
        "depreciation_change": 0.00,
    },
    "Upside": {
        "revenue_growth": 0.05,
        "cogs_change": -0.02,
        "personnel_change": 0.00,
        "opex_change": 0.00,
        "depreciation_change": 0.00,
    },
    "Downside": {
        "revenue_growth": -0.05,
        "cogs_change": 0.03,
        "personnel_change": 0.02,
        "opex_change": 0.03,
        "depreciation_change": 0.00,
    },
}


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 70)
    print("ENTERPRISE FP&A — SCENARIO / PLANNING ENGINE")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Load forecast
    # --------------------------------------------------------

    print("\n[1/5] Loading 2026 forecast...")

    if not FORECAST_FILE.exists():
        raise FileNotFoundError(
            f"Forecast file not found: {FORECAST_FILE}"
        )

    forecast = pd.read_csv(FORECAST_FILE)

    required_columns = [
        "month",
        "Revenue",
        "COGS",
        "Personnel",
        "Opex",
        "Depreciation",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in forecast.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Forecast is missing required columns: {missing_columns}"
        )

    forecast["month"] = pd.to_datetime(
        forecast["month"]
    )

    numeric_columns = [
        "Revenue",
        "COGS",
        "Personnel",
        "Opex",
        "Depreciation",
    ]

    for column in numeric_columns:
        forecast[column] = pd.to_numeric(
            forecast[column],
            errors="coerce"
        )

    forecast = forecast.dropna(
        subset=["month"] + numeric_columns
    )

    print(
        f"Forecast rows loaded: {len(forecast)}"
    )

    print(
        f"Forecast period: "
        f"{forecast['month'].min().date()} → "
        f"{forecast['month'].max().date()}"
    )


    # --------------------------------------------------------
    # 2. Build scenarios
    # --------------------------------------------------------

    print("\n[2/5] Building Base / Upside / Downside scenarios...")

    scenario_rows = []

    for scenario_name, assumptions in SCENARIOS.items():

        for _, row in forecast.iterrows():

            revenue = (
                row["Revenue"]
                * (1 + assumptions["revenue_growth"])
            )

            cogs = (
                row["COGS"]
                * (1 + assumptions["cogs_change"])
            )

            personnel = (
                row["Personnel"]
                * (1 + assumptions["personnel_change"])
            )

            opex = (
                row["Opex"]
                * (1 + assumptions["opex_change"])
            )

            depreciation = (
                row["Depreciation"]
                * (1 + assumptions["depreciation_change"])
            )

            gross_profit = revenue - cogs

            operating_expenses = (
                personnel
                + opex
                + depreciation
            )

            operating_profit = (
                gross_profit
                - operating_expenses
            )

            gross_margin_pct = (
                gross_profit / revenue * 100
                if revenue != 0
                else 0
            )

            operating_margin_pct = (
                operating_profit / revenue * 100
                if revenue != 0
                else 0
            )

            scenario_rows.append(
                {
                    "scenario": scenario_name,
                    "month": row["month"],
                    "revenue": revenue,
                    "cogs": cogs,
                    "gross_profit": gross_profit,
                    "personnel": personnel,
                    "opex": opex,
                    "depreciation": depreciation,
                    "operating_expenses": operating_expenses,
                    "operating_profit": operating_profit,
                    "gross_margin_pct": gross_margin_pct,
                    "operating_margin_pct": operating_margin_pct,
                    "revenue_growth_pct": (
                        assumptions["revenue_growth"] * 100
                    ),
                    "cogs_change_pct": (
                        assumptions["cogs_change"] * 100
                    ),
                    "personnel_change_pct": (
                        assumptions["personnel_change"] * 100
                    ),
                    "opex_change_pct": (
                        assumptions["opex_change"] * 100
                    ),
                    "depreciation_change_pct": (
                        assumptions["depreciation_change"] * 100
                    ),
                }
            )

    scenarios = pd.DataFrame(
        scenario_rows
    )


    # --------------------------------------------------------
    # 3. Validate calculations
    # --------------------------------------------------------

    print("\n[3/5] Validating scenario calculations...")

    scenarios["gross_profit_check"] = (
        scenarios["revenue"]
        - scenarios["cogs"]
        - scenarios["gross_profit"]
    )

    scenarios["operating_profit_check"] = (
        scenarios["gross_profit"]
        - scenarios["operating_expenses"]
        - scenarios["operating_profit"]
    )

    gross_profit_error = (
        scenarios["gross_profit_check"]
        .abs()
        .max()
    )

    operating_profit_error = (
        scenarios["operating_profit_check"]
        .abs()
        .max()
    )

    print(
        f"Gross profit reconciliation: "
        f"{gross_profit_error:.6f}"
    )

    print(
        f"Operating profit reconciliation: "
        f"{operating_profit_error:.6f}"
    )

    if gross_profit_error > 0.01:
        raise ValueError(
            "Gross profit scenario reconciliation failed."
        )

    if operating_profit_error > 0.01:
        raise ValueError(
            "Operating profit scenario reconciliation failed."
        )

    scenarios = scenarios.drop(
        columns=[
            "gross_profit_check",
            "operating_profit_check",
        ]
    )


    # --------------------------------------------------------
    # 4. Export detailed scenario analysis
    # --------------------------------------------------------

    print("\n[4/5] Exporting scenario analysis...")

    scenarios.to_csv(
        SCENARIO_FILE,
        index=False,
    )

    print(
        f"Scenario rows: {len(scenarios)}"
    )

    print(
        f"Scenarios: "
        f"{', '.join(SCENARIOS.keys())}"
    )

    print(
        f"Output: {SCENARIO_FILE}"
    )


    # --------------------------------------------------------
    # 5. Scenario summary
    # --------------------------------------------------------

    print("\n[5/5] Building scenario summary...")

    summary = (
        scenarios
        .groupby("scenario", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            gross_profit=("gross_profit", "sum"),
            personnel=("personnel", "sum"),
            opex=("opex", "sum"),
            depreciation=("depreciation", "sum"),
            operating_profit=("operating_profit", "sum"),
        )
    )

    summary["gross_margin_pct"] = (
        summary["gross_profit"]
        / summary["revenue"]
        * 100
    )

    summary["operating_margin_pct"] = (
        summary["operating_profit"]
        / summary["revenue"]
        * 100
    )

    print(
        summary.to_string(index=False)
    )

    print("\n" + "=" * 70)
    print("SCENARIO ENGINE BUILT SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()