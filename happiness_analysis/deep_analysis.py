"""Additional summaries for missingness, outliers, and country comparisons."""
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis import COUNTRY, FACTOR_COLUMNS, SCORE, correlate, compare_groups, format_p_value, rank_countries


def missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "column": df.columns,
        "missing_count": [int(df[c].isna().sum()) for c in df.columns],
        "row_count": len(df),
        "missing_percent": [float(df[c].isna().mean() * 100) for c in df.columns],
    })


def outlier_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Flag Tukey 1.5×IQR observations; summarize, never drop or cap them."""
    columns = [SCORE, *FACTOR_COLUMNS.values()]
    rows = []
    for col in columns:
        if col not in df:
            continue
        values = df[col].dropna()
        q1, q3 = values.quantile([.25, .75])
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = values.lt(low) | values.gt(high)
        rows.append({"column": col, "valid_n": len(values), "q1": float(q1), "q3": float(q3),
                     "iqr": float(iqr), "lower_bound": float(low), "upper_bound": float(high),
                     "outlier_count": int(mask.sum()),
                     "outlier_countries": "; ".join(df.loc[mask.index[mask], COUNTRY].astype(str).tolist())})
    return pd.DataFrame(rows)


def country_comparison(ranked: pd.DataFrame, names=("Finland", "India")) -> pd.DataFrame:
    cols = ["Rank", COUNTRY, SCORE]
    return ranked.loc[ranked[COUNTRY].isin(names), cols].reset_index(drop=True)


def _sample_size_text(value) -> str:
    number = pd.to_numeric(value, errors="coerce")
    return str(int(number)) if pd.notna(number) and np.isfinite(number) and number >= 0 and float(number).is_integer() else "not available"


def build_executive_summary(ranked: pd.DataFrame, correlations: pd.DataFrame, groups: pd.DataFrame,
                            missing: pd.DataFrame, outliers: pd.DataFrame) -> str:
    top, bottom = ranked.iloc[0], ranked.iloc[-1]
    gap = float(top[SCORE] - bottom[SCORE])
    india = ranked.loc[ranked[COUNTRY].str.casefold().eq("india")]
    india_text = (f"India ranks {int(india['Rank'].iloc[0])} with score {india[SCORE].iloc[0]:.3f}."
                  if len(india) else "India is not present in the supplied workbook.")
    valid = correlations.copy()
    if "status" in valid:
        valid = valid.loc[valid.status.eq("ok")]
    if {"pearson_r", "factor"}.issubset(valid.columns):
        valid["pearson_r"] = pd.to_numeric(valid.pearson_r, errors="coerce")
        valid = valid.loc[np.isfinite(valid.pearson_r) & valid.factor.notna()]
    else:
        valid = pd.DataFrame(columns=["factor", "pearson_r"])
    positives = valid.loc[valid.pearson_r.gt(0)]
    negatives = valid.loc[valid.pearson_r.lt(0)]
    association_lines = []
    if len(positives):
        best = positives.loc[positives.pearson_r.idxmax()]
        association_lines.append(
            f"Strongest positive Pearson association: {best.factor} (r={best.pearson_r:.3f}, "
            f"p={format_p_value(best.get('pearson_p_value'))}, n={_sample_size_text(best.get('pearson_n'))})."
        )
    else:
        association_lines.append("No positive Pearson coefficients were observed among valid results.")
    if len(negatives):
        negative = negatives.loc[negatives.pearson_r.idxmin()]
        association_lines.append(
            f"Strongest negative Pearson association: {negative.factor} (r={negative.pearson_r:.3f}, "
            f"p={format_p_value(negative.get('pearson_p_value'))}, n={_sample_size_text(negative.get('pearson_n'))})."
        )
    else:
        association_lines.append("No negative Pearson coefficients were observed among valid results.")
    if len(valid):
        weak = valid.loc[valid.pearson_r.abs().idxmin()]
        association_lines.append(
            f"Weakest absolute Pearson association: {weak.factor} (r={weak.pearson_r:.3f}, "
            f"p={format_p_value(weak.get('pearson_p_value'))}, n={_sample_size_text(weak.get('pearson_n'))})."
        )
    else:
        association_lines.append("Pearson association summaries are unavailable because there are no valid coefficients.")
    if len(groups) and "absolute_difference_top_minus_bottom" in groups:
        differences = pd.to_numeric(groups.absolute_difference_top_minus_bottom, errors="coerce")
        differences = differences.loc[np.isfinite(differences)]
        largest = groups.loc[differences.abs().idxmax()] if len(differences) else None
    else:
        largest = None
    largest_text = (f"The largest top-10 minus bottom-10 mean gap among the six indicators is "
                    f"{largest['factor']} ({largest.absolute_difference_top_minus_bottom:.3f})."
                    if largest is not None else "Top-versus-bottom indicator differences are unavailable.")
    missing_cells = int(missing.missing_count.sum())
    return ("# Executive summary\n\n"
            f"The supplied World Happiness Report 2025 workbook contains {len(ranked)} unique country rows. "
            f"{top[COUNTRY]} ranks first ({top[SCORE]:.3f}) and {bottom[COUNTRY]} ranks last ({bottom[SCORE]:.3f}), "
            f"a Ladder score gap of {gap:.3f}. {india_text}\n\n"
            f"{' '.join(association_lines)} These are country-level associations, not evidence of causation. "
            f"{largest_text}\n\n"
            f"The source contains {missing_cells} missing cells across {len(missing)} fields. Correlations use pairwise complete rows; "
            f"group averages use available observations. No values were imputed and no outliers were dropped. Outliers are flagged "
            f"with the 1.5×IQR rule for review. The workbook has no region or income category and no year-level observations, "
            f"so regional comparisons and annual trends are unavailable. This new project analysis does not claim to reproduce "
            f"the original internship analysis.\n")


def write_deep_outputs(ranked: pd.DataFrame, root: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    root = Path(root)
    frame = ranked.drop(columns="Rank") if "Rank" in ranked else ranked
    corr = correlate(frame)
    groups = compare_groups(ranked)
    missing = missing_summary(frame)
    outliers = outlier_summary(frame)
    (root / "outputs").mkdir(exist_ok=True)
    missing.to_csv(root / "outputs/missing_data_summary.csv", index=False)
    outliers.to_csv(root / "outputs/outlier_summary.csv", index=False)
    (root / "outputs/executive_summary.md").write_text(
        build_executive_summary(ranked, corr, groups, missing, outliers), encoding="utf-8")
    return missing, outliers


def main() -> None:
    from .analysis import clean_and_validate, load_workbook
    root = Path(__file__).resolve().parents[1]
    raw, _ = load_workbook(root / "WHR_2025.xls")
    cleaned, _ = clean_and_validate(raw)
    write_deep_outputs(rank_countries(cleaned), root)
    print(f"Deep analysis outputs written to {root / 'outputs'}")


if __name__ == "__main__":
    main()
