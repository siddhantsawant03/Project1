from pathlib import Path
import zipfile
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"

CATEGORY_MAP = {
    "Revenue": "Revenue",
    "COGS": "COGS",
    "Personnel": "Personnel",
    "Opex": "Opex",
    "Depreciation": "Depreciation",
}


def _find_csv(root, name):
    hits = list(Path(root).rglob(name))
    return hits[0] if hits else None


def _norm_key(series):
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def source_root():
    direct = _find_csv(RAW, "acdoca_actuals.csv")

    if direct:
        return direct.parent

    zip_path = next(iter(RAW.glob("*.zip")), None)

    if zip_path:
        extract = RAW / "source"
        extract.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path) as z:
            z.extractall(extract)

        return extract

    raise FileNotFoundError(
        "Original FP&A dataset not found under data/raw. "
        "Run: python scripts\\download_data.py"
    )


def load_source():
    root = source_root()

    actual_path = _find_csv(root, "acdoca_actuals.csv")
    plan_path = _find_csv(root, "plan_versions.csv")
    gl_path = _find_csv(root, "dim_gl_account.csv")

    if not actual_path or not plan_path:
        raise FileNotFoundError(
            "Required original files acdoca_actuals.csv and/or "
            "plan_versions.csv were not found."
        )

    actuals = pd.read_csv(actual_path)
    plans = pd.read_csv(plan_path)

    if gl_path:
        gl = pd.read_csv(gl_path)

        actuals["HKONT"] = _norm_key(actuals["HKONT"])
        gl["HKONT"] = _norm_key(gl["HKONT"])

        actuals = actuals.merge(
            gl[["HKONT", "CATEGORY"]],
            on="HKONT",
            how="left",
        )

    return actuals, plans


def normalize_actuals(a):
    a = a.copy()

    a.columns = [str(c).strip() for c in a.columns]

    date_col = "BUDAT" if "BUDAT" in a.columns else "posting_date"

    a["month"] = (
        pd.to_datetime(a[date_col], errors="coerce")
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    amt = pd.to_numeric(
        a["DMBTR"],
        errors="coerce",
    ).fillna(0)

    if "SHKZG" in a.columns:
        sign = np.where(
            a["SHKZG"]
            .astype(str)
            .str.upper()
            .eq("H"),
            -1,
            1,
        )

        amt = amt * sign

    a["actual"] = amt

    a["cost_centre"] = (
        a["KOSTL"].astype(str).str.strip()
        if "KOSTL" in a.columns
        else "UNASSIGNED"
    )

    a["company_code"] = _norm_key(a["BUKRS"])

    if "CATEGORY" in a.columns:

        a["category"] = (
            a["CATEGORY"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # Standardize category names for the analytical model.
        a["category"] = a["category"].replace(
            {
                "REVENUE": "Revenue",
                "COGS": "COGS",
                "PERSONNEL": "Personnel",
                "OPEX": "Opex",
                "DEPRECIATION": "Depreciation",
                "BALANCE_SHEET": "Balance Sheet",
            }
        )

        # SAP credit postings make Revenue negative in the
        # accounting ledger. Reverse Revenue for management
        # P&L presentation.
        a.loc[
            a["category"].eq("Revenue"),
            "actual",
        ] *= -1

    else:
        raise ValueError(
            "CATEGORY was not available from dim_gl_account.csv. "
            "The original G/L dimension is required for the FP&A model."
        )

    return a[
        [
            "month",
            "company_code",
            "cost_centre",
            "category",
            "actual",
        ]
    ]


def normalize_plan(p):
    p = p.copy()

    p.columns = [str(c).strip() for c in p.columns]

    p["month"] = pd.to_datetime(
        dict(
            year=pd.to_numeric(
                p["GJAHR"],
                errors="coerce",
            ),
            month=pd.to_numeric(
                p["MONAT"],
                errors="coerce",
            ),
            day=1,
        ),
        errors="coerce",
    )

    p["company_code"] = _norm_key(p["BUKRS"])

    p["cost_centre"] = (
        p["KOSTL"]
        .astype(str)
        .str.strip()
    )

    p["category"] = (
        p["CATEGORY"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    p["category"] = p["category"].replace(
        {
            "REVENUE": "Revenue",
            "COGS": "COGS",
            "PERSONNEL": "Personnel",
            "OPEX": "Opex",
            "DEPRECIATION": "Depreciation",
            "BALANCE_SHEET": "Balance Sheet",
        }
    )

    p["amount"] = pd.to_numeric(
        p["DMBTR"],
        errors="coerce",
    ).fillna(0)

    p["version_name"] = (
        p["VERSION"]
        .map(
            {
                1: "Budget",
                2: "Rolling Forecast",
            }
        )
        .fillna(
            p["VERSION"].astype(str)
        )
    )

    return p[
        [
            "month",
            "company_code",
            "cost_centre",
            "category",
            "amount",
            "version_name",
        ]
    ]


def build(use_demo=False):

    if use_demo:
        raise ValueError(
            "Demo data is disabled for this project. "
            "Use the original published FP&A dataset."
        )

    PROC.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    actual_raw, plan_raw = load_source()

    actual = normalize_actuals(actual_raw)
    plan = normalize_plan(plan_raw)

    # Management P&L categories only.
    # Balance-sheet postings remain in the source data,
    # but are excluded from P&L reporting.
    pnl_categories = [
        "Revenue",
        "COGS",
        "Personnel",
        "Opex",
        "Depreciation",
    ]

    actual = actual[
        actual["category"].isin(pnl_categories)
    ]

    plan = plan[
        plan["category"].isin(pnl_categories)
    ]

    budget = (
        plan[
            plan["version_name"].eq("Budget")
        ]
        .rename(
            columns={
                "amount": "budget"
            }
        )
    )

    forecast = (
        plan[
            plan["version_name"].eq(
                "Rolling Forecast"
            )
        ]
        .rename(
            columns={
                "amount": "forecast"
            }
        )
    )

    keys = [
        "month",
        "company_code",
        "cost_centre",
        "category",
    ]

    actual = (
        actual
        .groupby(
            keys,
            as_index=False,
        )["actual"]
        .sum()
    )

    budget = (
        budget
        .groupby(
            keys,
            as_index=False,
        )["budget"]
        .sum()
    )

    forecast = (
        forecast
        .groupby(
            keys,
            as_index=False,
        )["forecast"]
        .sum()
    )

    for frame in (
        actual,
        budget,
        forecast,
    ):
        frame["company_code"] = _norm_key(
            frame["company_code"]
        )

        frame["cost_centre"] = (
            frame["cost_centre"]
            .astype(str)
            .str.strip()
        )

        frame["category"] = (
            frame["category"]
            .astype(str)
            .str.strip()
        )

    model = (
        actual
        .merge(
            budget,
            on=keys,
            how="outer",
        )
        .merge(
            forecast,
            on=keys,
            how="outer",
        )
        .fillna(0)
    )

    model["variance"] = (
        model["actual"]
        - model["budget"]
    )

    model["variance_pct"] = np.where(
        model["budget"] != 0,
        model["variance"]
        / model["budget"],
        np.nan,
    )

    model["forecast_variance"] = (
        model["forecast"]
        - model["budget"]
    )

    model.to_csv(
        PROC / "fpna_model.csv",
        index=False,
    )

    pnl = (
        model
        .groupby(
            [
                "month",
                "category",
            ]
        )[
            [
                "actual",
                "budget",
                "forecast",
            ]
        ]
        .sum()
        .reset_index()
    )

    pnl.to_csv(
        OUT / "pnl_monthly.csv",
        index=False,
    )

    cc = (
        model
        .groupby(
            [
                "cost_centre",
                "category",
            ]
        )[
            [
                "actual",
                "budget",
                "forecast",
            ]
        ]
        .sum()
        .reset_index()
    )

    cc.to_csv(
        OUT / "cost_centre_analysis.csv",
        index=False,
    )

    drv = (
        model
        .groupby(
            [
                "cost_centre",
                "category",
            ]
        )[
            [
                "actual",
                "budget",
                "variance",
            ]
        ]
        .sum()
        .reset_index()
    )

    drv["abs_variance"] = (
        drv["variance"].abs()
    )

    drv = drv.sort_values(
        "abs_variance",
        ascending=False,
    )

    drv.to_csv(
        OUT / "driver_analysis.csv",
        index=False,
    )

    q = {
        "rows": len(model),
        "months": int(
            model["month"].nunique()
        ),
        "cost_centres": int(
            model["cost_centre"].nunique()
        ),
        "companies": int(
            model["company_code"].nunique()
        ),
        "null_cells": int(
            model.isna().sum().sum()
        ),
        "duplicate_keys": int(
            model.duplicated(keys).sum()
        ),
    }

    pd.DataFrame([q]).to_csv(
        OUT / "data_quality.csv",
        index=False,
    )

    print(
        f"Built FP&A model from ORIGINAL published data: "
        f"{len(model):,} analytical rows | "
        f"{q['months']} months | "
        f"{q['companies']} companies | "
        f"{q['cost_centres']} cost centres"
    )

    return model