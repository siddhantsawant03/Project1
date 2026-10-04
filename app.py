from flask import Flask, render_template, jsonify, request
from pathlib import Path
import pandas as pd
import numpy as np
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.model import PROC, OUT


app = Flask(__name__)
ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------
# Configuration / validation
# ---------------------------------------------------------------------

MODEL_FILE = PROC / "fpna_model.csv"

if not MODEL_FILE.exists():
    raise FileNotFoundError(
        "Processed FP&A model not found. "
        "Run the data pipeline before starting the dashboard."
    )


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def safe(value):
    """Convert pandas / numpy values into JSON-safe values."""
    if pd.isna(value):
        return None

    if isinstance(value, (float, np.floating)):
        if not np.isfinite(value):
            return None
        return float(value)

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    return value


def clean(records):
    """Make dataframe records JSON serializable."""
    return [
        {key: safe(value) for key, value in record.items()}
        for record in records
    ]


def load_model():
    """Load the validated analytical model."""
    return pd.read_csv(
        MODEL_FILE,
        parse_dates=["month"]
    )


def apply_filters(df):
    """
    Apply dashboard filters.

    Supported:
        company
        year
        category
    """
    result = df.copy()

    company = request.args.get("company", "ALL")
    year = request.args.get("year", "ALL")
    category = request.args.get("category", "ALL")

    if company != "ALL":
        result = result[
            result["company_code"].astype(str) == str(company)
        ]

    if year != "ALL":
        result = result[
            result["month"].dt.year.astype(str) == str(year)
        ]

    if category != "ALL":
        result = result[
            result["category"].astype(str) == str(category)
        ]

    return result


def ensure_categories(df):
    """Ensure all management P&L categories exist."""
    required = [
        "Revenue",
        "COGS",
        "Personnel",
        "Opex",
        "Depreciation",
    ]

    for category in required:
        if category not in df.columns:
            df[category] = 0.0

    return df


def management_profit(category_frame, column):
    """
    Management operating profit:

        Revenue
        - COGS
        - Personnel
        - Opex
        - Depreciation

    The analytical model already stores expense categories
    as positive management values and Revenue as positive.
    """
    required = [
        "Revenue",
        "COGS",
        "Personnel",
        "Opex",
        "Depreciation",
    ]

    values = {
        category: float(
            category_frame.loc[category, column]
        )
        if category in category_frame.index
        else 0.0
        for category in required
    }

    return (
        values["Revenue"]
        - values["COGS"]
        - values["Personnel"]
        - values["Opex"]
        - values["Depreciation"]
    )


def read_output(filename):
    """Read an existing analytical output."""
    path = OUT / filename

    if not path.exists():
        return None

    return pd.read_csv(path)


# ---------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("dashboard.html")


# ---------------------------------------------------------------------
# Metadata / filters
# ---------------------------------------------------------------------

@app.route("/api/metadata")
def metadata():
    model = load_model()

    companies = sorted(
        model["company_code"]
        .astype(str)
        .dropna()
        .unique()
        .tolist()
    )

    years = sorted(
        model["month"]
        .dt.year
        .dropna()
        .unique()
        .tolist()
    )

    categories = [
        "Revenue",
        "COGS",
        "Personnel",
        "Opex",
        "Depreciation",
    ]

    return jsonify(
        {
            "companies": companies,
            "years": years,
            "categories": categories,
            "period_start": model["month"].min().strftime("%Y-%m-%d"),
            "period_end": model["month"].max().strftime("%Y-%m-%d"),
            "rows": int(len(model)),
        }
    )


# ---------------------------------------------------------------------
# Executive / core dashboard data
# ---------------------------------------------------------------------

@app.route("/api/data")
def api_data():

    model = apply_filters(load_model())

    if model.empty:
        return jsonify(
            {
                "empty": True,
                "message": "No records match the selected filters."
            }
        )

    # -------------------------------------------------------------
    # Monthly P&L
    # -------------------------------------------------------------

    monthly = (
        model
        .groupby(["month", "category"], as_index=False)
        [["actual", "budget", "forecast"]]
        .sum()
    )

    actual_pivot = (
        monthly
        .pivot(
            index="month",
            columns="category",
            values="actual"
        )
        .fillna(0)
    )

    budget_pivot = (
        monthly
        .pivot(
            index="month",
            columns="category",
            values="budget"
        )
        .fillna(0)
    )

    forecast_pivot = (
        monthly
        .pivot(
            index="month",
            columns="category",
            values="forecast"
        )
        .fillna(0)
    )

    actual_pivot = ensure_categories(actual_pivot)
    budget_pivot = ensure_categories(budget_pivot)
    forecast_pivot = ensure_categories(forecast_pivot)

    monthly_records = []

    for month in actual_pivot.index:

        revenue = float(actual_pivot.loc[month, "Revenue"])
        cogs = float(actual_pivot.loc[month, "COGS"])
        personnel = float(actual_pivot.loc[month, "Personnel"])
        opex = float(actual_pivot.loc[month, "Opex"])
        depreciation = float(
            actual_pivot.loc[month, "Depreciation"]
        )

        budget_revenue = float(
            budget_pivot.loc[month, "Revenue"]
        )
        budget_cogs = float(
            budget_pivot.loc[month, "COGS"]
        )
        budget_personnel = float(
            budget_pivot.loc[month, "Personnel"]
        )
        budget_opex = float(
            budget_pivot.loc[month, "Opex"]
        )
        budget_depreciation = float(
            budget_pivot.loc[month, "Depreciation"]
        )

        actual_gross_profit = revenue - cogs
        budget_gross_profit = budget_revenue - budget_cogs

        actual_operating_profit = (
            actual_gross_profit
            - personnel
            - opex
            - depreciation
        )

        budget_operating_profit = (
            budget_gross_profit
            - budget_personnel
            - budget_opex
            - budget_depreciation
        )

        forecast_revenue = float(
            forecast_pivot.loc[month, "Revenue"]
        )
        forecast_cogs = float(
            forecast_pivot.loc[month, "COGS"]
        )
        forecast_personnel = float(
            forecast_pivot.loc[month, "Personnel"]
        )
        forecast_opex = float(
            forecast_pivot.loc[month, "Opex"]
        )
        forecast_depreciation = float(
            forecast_pivot.loc[month, "Depreciation"]
        )

        forecast_operating_profit = (
            forecast_revenue
            - forecast_cogs
            - forecast_personnel
            - forecast_opex
            - forecast_depreciation
        )

        monthly_records.append(
            {
                "month": month.strftime("%Y-%m"),

                "revenue": revenue,
                "budget_revenue": budget_revenue,

                "cogs": cogs,
                "budget_cogs": budget_cogs,

                "personnel": personnel,
                "budget_personnel": budget_personnel,

                "opex": opex,
                "budget_opex": budget_opex,

                "depreciation": depreciation,
                "budget_depreciation": budget_depreciation,

                "gross_profit": actual_gross_profit,
                "budget_gross_profit": budget_gross_profit,

                "operating_profit": actual_operating_profit,
                "budget_operating_profit": budget_operating_profit,

                "profit_variance": (
                    actual_operating_profit
                    - budget_operating_profit
                ),

                "forecast_operating_profit":
                    forecast_operating_profit,

                "operating_margin": (
                    actual_operating_profit / revenue
                    if revenue != 0
                    else np.nan
                ),

                "budget_operating_margin": (
                    budget_operating_profit / budget_revenue
                    if budget_revenue != 0
                    else np.nan
                ),

                "forecast_operating_margin": (
                    forecast_operating_profit / forecast_revenue
                    if forecast_revenue != 0
                    else np.nan
                ),
            }
        )

    # -------------------------------------------------------------
    # Category analysis
    # -------------------------------------------------------------

    category = (
        model
        .groupby("category", as_index=False)
        [["actual", "budget", "forecast"]]
        .sum()
    )

    category["variance"] = (
        category["actual"]
        - category["budget"]
    )

    category["variance_pct"] = np.where(
        category["budget"] != 0,
        category["variance"] / category["budget"],
        np.nan
    )

    category["assessment"] = np.where(
        category["variance"] >= 0,
        "Favorable",
        "Unfavorable"
    )

    # -------------------------------------------------------------
    # Overall P&L
    # -------------------------------------------------------------

    category_index = category.set_index("category")

    revenue = float(
        category_index.loc["Revenue", "actual"]
    )

    budget_revenue = float(
        category_index.loc["Revenue", "budget"]
    )

    actual_operating_profit = management_profit(
        category_index,
        "actual"
    )

    budget_operating_profit = management_profit(
        category_index,
        "budget"
    )

    forecast_operating_profit = management_profit(
        category_index,
        "forecast"
    )

    gross_profit = (
        revenue
        - float(category_index.loc["COGS", "actual"])
    )

    budget_gross_profit = (
        budget_revenue
        - float(category_index.loc["COGS", "budget"])
    )

    forecast_revenue = float(
        category_index.loc["Revenue", "forecast"]
    )

    forecast_gross_profit = (
        forecast_revenue
        - float(category_index.loc["COGS", "forecast"])
    )

    # -------------------------------------------------------------
    # Cost centre analysis
    # -------------------------------------------------------------

    cost = (
        model
        .groupby("cost_centre", as_index=False)
        [["actual", "budget", "forecast"]]
        .sum()
    )

    cost["variance"] = (
        cost["actual"]
        - cost["budget"]
    )

    cost["variance_pct"] = np.where(
        cost["budget"] != 0,
        cost["variance"] / cost["budget"],
        np.nan
    )

    cost = cost.sort_values(
        "variance",
        ascending=True
    )

    # -------------------------------------------------------------
    # Driver analysis
    # -------------------------------------------------------------

    driver = category[
        category["category"].isin(
            [
                "Revenue",
                "COGS",
                "Personnel",
                "Opex",
                "Depreciation",
            ]
        )
    ].copy()

    driver["management_impact"] = np.where(
        driver["category"].eq("Revenue"),
        driver["actual"] - driver["budget"],
        driver["budget"] - driver["actual"]
    )

    driver["direction"] = np.where(
        driver["management_impact"] >= 0,
        "Favorable",
        "Unfavorable"
    )

    driver = driver.sort_values(
        "management_impact",
        ascending=False
    )

    # -------------------------------------------------------------
    # Forecast backtest
    # -------------------------------------------------------------

    backtest = read_output(
        "forecast_backtest_summary.csv"
    )

    if backtest is None:
        backtest_records = []
    else:
        backtest_records = clean(
            backtest.to_dict("records")
        )

    # -------------------------------------------------------------
    # Data quality
    # -------------------------------------------------------------

    quality_path = OUT / "data_quality.csv"

    if quality_path.exists():
        quality = (
            pd.read_csv(quality_path)
            .iloc[0]
            .to_dict()
        )
    else:
        quality = {}

    # -------------------------------------------------------------
    # Management signals
    # -------------------------------------------------------------

    largest_driver = (
        driver
        .assign(
            abs_impact=lambda x:
                x["management_impact"].abs()
        )
        .sort_values(
            "abs_impact",
            ascending=False
        )
        .iloc[0]
    )

    signals = [
        {
            "title": "Revenue performance",
            "text": (
                f"Revenue is "
                f"{abs((revenue - budget_revenue) / budget_revenue):.1%} "
                f"{'above' if revenue >= budget_revenue else 'below'} "
                f"budget."
                if budget_revenue != 0
                else "Budget baseline unavailable."
            ),
        },
        {
            "title": "Operating result",
            "text": (
                f"Operating profit is "
                f"{abs((actual_operating_profit - budget_operating_profit) / budget_operating_profit):.1%} "
                f"{'above' if actual_operating_profit >= budget_operating_profit else 'below'} "
                f"budget."
                if budget_operating_profit != 0
                else "Budget baseline unavailable."
            ),
        },
        {
            "title": "Largest variance driver",
            "text": (
                f"{largest_driver['category']} "
                f"({largest_driver['direction']})"
            ),
        },
    ]

    return jsonify(
        {
            "filters": {
                "company":
                    request.args.get("company", "ALL"),
                "year":
                    request.args.get("year", "ALL"),
                "category":
                    request.args.get("category", "ALL"),
            },

            "kpis": {
                "revenue": revenue,
                "budget_revenue": budget_revenue,
                "gross_profit": gross_profit,
                "budget_gross_profit":
                    budget_gross_profit,
                "operating_profit":
                    actual_operating_profit,
                "budget_operating_profit":
                    budget_operating_profit,
                "operating_margin":
                    (
                        actual_operating_profit / revenue
                        if revenue != 0
                        else np.nan
                    ),
                "budget_operating_margin":
                    (
                        budget_operating_profit
                        / budget_revenue
                        if budget_revenue != 0
                        else np.nan
                    ),
                "revenue_var":
                    revenue - budget_revenue,
                "gross_profit_var":
                    gross_profit - budget_gross_profit,
                "op_profit_var":
                    actual_operating_profit
                    - budget_operating_profit,
                "forecast_profit":
                    forecast_operating_profit,
                "forecast_gap":
                    forecast_operating_profit
                    - budget_operating_profit,
                "forecast_revenue":
                    forecast_revenue,
                "forecast_gross_profit":
                    forecast_gross_profit,
            },

            "monthly": monthly_records,

            "category":
                clean(category.to_dict("records")),

            "driver":
                clean(driver.to_dict("records")),

            "cost":
                clean(cost.to_dict("records")),

            "backtest":
                backtest_records,

            "quality":
                clean([quality])[0]
                if quality
                else {},

            "signals":
                signals,

            "period": {
                "start":
                    model["month"].min().strftime("%Y-%m"),
                "end":
                    model["month"].max().strftime("%Y-%m"),
            },
        }
    )


# ---------------------------------------------------------------------
# Scenario analysis
# ---------------------------------------------------------------------

@app.route("/api/scenario")
def api_scenario():

    scenario_file = OUT / "scenario_analysis.csv"

    if not scenario_file.exists():
        return jsonify(
            {
                "error":
                    "Scenario analysis output not found. "
                    "Run scripts/build_scenarios.py first."
            }
        ), 404

    scenario_data = pd.read_csv(
        scenario_file,
        parse_dates=["month"]
    )

    # Optional scenario filter.
    selected = request.args.get(
        "scenario",
        "ALL"
    )

    if selected != "ALL":
        scenario_data = scenario_data[
            scenario_data["scenario"] == selected
        ]

    return jsonify(
        {
            "records":
                clean(
                    scenario_data.to_dict(
                        "records"
                    )
                )
        }
    )


# ---------------------------------------------------------------------
# Methodology
# ---------------------------------------------------------------------

@app.route("/api/methodology")
def methodology():

    return jsonify(
        {
            "project": {
                "name":
                    "Enterprise FP&A Performance & Planning Analytics",
                "purpose":
                    "Management reporting, variance analysis, forecasting and scenario planning using a structured FP&A analytical model.",
                "data_type":
                    "Synthetic public research dataset designed for FP&A analysis.",
            },

            "pipeline": [
                {
                    "step": 1,
                    "title": "Source data",
                    "description":
                        "Loaded the published SAP-structured FP&A dataset containing accounting postings, planning versions and dimensional master data.",
                    "tools":
                        ["CSV", "Python", "Pandas"],
                },
                {
                    "step": 2,
                    "title": "Data preparation",
                    "description":
                        "Standardized SAP keys, dates, accounting categories and dimensional relationships before constructing the analytical model.",
                    "tools":
                        ["Python", "Pandas"],
                },
                {
                    "step": 3,
                    "title": "Accounting sign treatment",
                    "description":
                        "Applied accounting sign treatment and converted Revenue into a positive management-reporting measure so that the P&L can be interpreted naturally.",
                    "tools":
                        ["Python"],
                },
                {
                    "step": 4,
                    "title": "Management P&L",
                    "description":
                        "Constructed Revenue, COGS, Gross Profit, Personnel, Opex, Depreciation and Operating Profit.",
                    "tools":
                        ["Python", "SQL"],
                },
                {
                    "step": 5,
                    "title": "Budget vs Actual",
                    "description":
                        "Compared actual performance with the Budget planning version and calculated management-oriented variances.",
                    "tools":
                        ["SQL", "Python"],
                },
                {
                    "step": 6,
                    "title": "Variance decomposition",
                    "description":
                        "Decomposed Operating Profit variance into Revenue, COGS, Personnel, Opex and Depreciation impacts.",
                    "tools":
                        ["SQL", "Python"],
                },
                {
                    "step": 7,
                    "title": "Cost-centre analysis",
                    "description":
                        "Ranked cost centres by actual performance and budget variance to identify major contributors.",
                    "tools":
                        ["SQL", "Python"],
                },
                {
                    "step": 8,
                    "title": "Forecasting",
                    "description":
                        "Created a 2026 seasonal-naïve baseline using the corresponding prior-year month.",
                    "tools":
                        ["Python"],
                },
                {
                    "step": 9,
                    "title": "Forecast validation",
                    "description":
                        "Backtested the forecasting method against 2025 actuals and calculated MAE, MAPE and bias.",
                    "tools":
                        ["Python"],
                },
                {
                    "step": 10,
                    "title": "Scenario planning",
                    "description":
                        "Built Base, Upside and Downside analytical scenarios using explicit Revenue, COGS, Personnel and Opex assumptions.",
                    "tools":
                        ["Python"],
                },
                {
                    "step": 11,
                    "title": "SQL validation",
                    "description":
                        "Rebuilt key analytical views in DuckDB and reconciled SQL outputs against the Python analytical layer.",
                    "tools":
                        ["DuckDB", "SQL", "Python"],
                },
                {
                    "step": 12,
                    "title": "Management reporting",
                    "description":
                        "Published the validated analytical outputs into an Excel management model and this interactive dashboard.",
                    "tools":
                        ["Excel", "Flask", "Plotly"],
                },
            ],

            "controls": [
                "Gross Profit reconciliation",
                "Operating Profit reconciliation",
                "Python-to-SQL reconciliation",
                "Cost-centre reconciliation",
                "Forecast backtesting",
                "Duplicate analytical key check",
                "Date coverage check",
                "Dimensional coverage check",
            ],

            "outputs": [
                "Management P&L",
                "Budget vs Actual",
                "Variance Driver Analysis",
                "Cost Centre Analysis",
                "2026 Forecast",
                "Forecast Backtest",
                "Scenario Analysis",
                "Data Quality",
                "Excel Management Model",
                "Interactive Web Dashboard",
            ],
        }
    )


# ---------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------

@app.route("/api/health")
def health():

    model = load_model()

    return jsonify(
        {
            "status": "ok",
            "rows": int(len(model)),
            "months": int(model["month"].nunique()),
            "companies":
                int(model["company_code"].nunique()),
        }
    )


# ---------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )