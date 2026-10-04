from pathlib import Path

import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data" / "processed" / "fpna_model.csv"
OUTPUT = ROOT / "outputs" / "cost_centre_driver_analysis.csv"


def build_cost_centre_analysis():

    df = pd.read_csv(INPUT)

    df["month"] = pd.to_datetime(df["month"])

    # Aggregate cost-centre/category performance
    result = (
        df.groupby(
            [
                "cost_centre",
                "category",
            ],
            as_index=False,
        )[
            [
                "actual",
                "budget",
                "forecast",
                "variance",
            ]
        ]
        .sum()
    )

    # Variance %
    result["variance_pct"] = np.where(
        result["budget"].abs() > 0,
        result["variance"]
        / result["budget"].abs(),
        np.nan,
    )

    # Management favorable / unfavorable view
    #
    # Revenue:
    #   Actual > Budget = Favorable
    #
    # Expenses:
    #   Actual < Budget = Favorable

    result["management_impact"] = np.where(
        result["category"].eq("Revenue"),
        result["actual"] - result["budget"],
        result["budget"] - result["actual"],
    )

    result["favorable_flag"] = np.where(
        result["management_impact"] >= 0,
        "Favorable",
        "Unfavorable",
    )

    result["absolute_management_impact"] = (
        result["management_impact"].abs()
    )

    # Rank drivers within each category
    result["driver_rank"] = (
        result.groupby("category")[
            "absolute_management_impact"
        ]
        .rank(
            method="dense",
            ascending=False,
        )
        .astype(int)
    )

    # Sort largest management drivers first
    result = result.sort_values(
        "absolute_management_impact",
        ascending=False,
    )

    result.to_csv(
        OUTPUT,
        index=False,
    )

    print(
        f"Built cost-centre driver analysis: "
        f"{len(result):,} records"
    )

    print(
        f"Cost centres: "
        f"{result['cost_centre'].nunique()}"
    )

    print(
        "\nTop 15 management variance drivers:"
    )

    print(
        result[
            [
                "cost_centre",
                "category",
                "actual",
                "budget",
                "management_impact",
                "favorable_flag",
                "driver_rank",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )

    print(
        f"\nOutput: {OUTPUT}"
    )


if __name__ == "__main__":
    build_cost_centre_analysis()