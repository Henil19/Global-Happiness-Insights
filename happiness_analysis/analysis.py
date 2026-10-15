"""Load, validate, analyze, and export World Happiness Report country data."""
from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

SOURCE_FILE = "WHR_2025.xls"
SCORE = "Ladder score"
COUNTRY = "Country name"
FACTOR_COLUMNS = {
    "GDP per capita": "Explained by: Log GDP per capita",
    "Social support": "Explained by: Social support",
    "Healthy life expectancy": "Explained by: Healthy life expectancy",
    "Freedom to make life choices": "Explained by: Freedom to make life choices",
    "Generosity": "Explained by: Generosity",
    "Perceptions of corruption": "Explained by: Perceptions of corruption",
}
EXPECTED_COLUMNS = [COUNTRY, SCORE, "upperwhisker", "lowerwhisker", *FACTOR_COLUMNS.values(), "Dystopia + residual"]


def load_workbook(path: str | Path) -> tuple[pd.DataFrame, list[str]]:
    """Load all sheets and concatenate them; report source sheets in order."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Obtain the World Happiness Report 2025 Figure 2.1 data "
            "from https://www.worldhappiness.report/data-sharing/ and place the workbook here as WHR_2025.xls."
        )
    book = pd.ExcelFile(path, engine="xlrd")
    frames = [pd.read_excel(book, sheet_name=sheet) for sheet in book.sheet_names]
    if not frames:
        book.close()
        raise ValueError("Workbook contains no sheets")
    frame = pd.concat(frames, ignore_index=True)
    sheets = list(book.sheet_names)
    book.close()
    return frame, sheets


def clean_and_validate(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply conservative cleanup; retain rows and missing values, never impute."""
    before_rows = len(raw)
    before_missing = raw.isna().sum().astype(int).to_dict()
    df = raw.copy()
    # Normalize header/country whitespace only. No rows or cells are filled/dropped.
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    if COUNTRY not in df or SCORE not in df:
        raise ValueError(f"Required columns missing: {COUNTRY!r}, {SCORE!r}")
    df[COUNTRY] = df[COUNTRY].astype("string").str.strip()
    if df[COUNTRY].isna().any() or (df[COUNTRY] == "").any():
        raise ValueError("Country names must be present and non-empty")
    numeric = [c for c in df.columns if c != COUNTRY]
    for col in numeric:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Expected numeric values in {col!r}; found {df[col].dtype}")
    if df[COUNTRY].duplicated().any():
        duplicates = df.loc[df[COUNTRY].duplicated(keep=False), COUNTRY].tolist()
        raise ValueError(f"Duplicate country rows: {duplicates}")
    if df[SCORE].isna().any() or not np.isfinite(df[SCORE].dropna()).all():
        raise ValueError("Ladder score must be complete and finite for ranking")
    if not df[SCORE].between(0, 10).all():
        raise ValueError("Ladder scores fall outside the expected 0–10 scale")
    quality = {
        "rows_before_cleaning": before_rows,
        "rows_after_cleaning": len(df),
        "rows_removed": before_rows - len(df),
        "columns_before_cleaning": int(raw.shape[1]),
        "columns_after_cleaning": int(df.shape[1]),
        "missing_before_cleaning": before_missing,
        "missing_after_cleaning": df.isna().sum().astype(int).to_dict(),
        "duplicate_country_rows": 0,
        "cleaning_decisions": [
            "Trim whitespace from column headers and country names.",
            "Retain all source rows; no rows were removed.",
            "Retain all source missing values; no imputation was performed.",
            "Validate required fields, country uniqueness, numeric types, finite scores, and the 0–10 score range.",
        ],
        "validation": "passed",
    }
    return df, quality


def rank_countries(df: pd.DataFrame) -> pd.DataFrame:
    """Rank countries by descending Ladder score, preserving country rows."""
    result = df.sort_values([SCORE, COUNTRY], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    result.insert(0, "Rank", np.arange(1, len(result) + 1))
    return result


def correlate(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, col in FACTOR_COLUMNS.items():
        if col not in df:
            rows.append({"factor": label, "column": col, "pearson_r": np.nan, "pearson_p_value": np.nan,
                         "pearson_n": 0, "spearman_rho": np.nan, "spearman_p_value": np.nan,
                         "spearman_n": 0, "missing_factor": None, "missing_score": int(df[SCORE].isna().sum()),
                         "missing_either": None, "status": "factor column absent"})
            continue
        pair = df[[SCORE, col]]
        missing_factor = int(pair[col].isna().sum())
        missing_score = int(pair[SCORE].isna().sum())
        valid = pair.dropna()
        n = len(valid)
        if n < 2:
            pearson = spearman = (np.nan, np.nan)
        else:
            pearson = stats.pearsonr(valid[SCORE], valid[col])
            spearman = stats.spearmanr(valid[SCORE], valid[col])
        rows.append({"factor": label, "column": col, "pearson_r": float(pearson.statistic),
                     "pearson_p_value": float(pearson.pvalue), "pearson_n": n,
                     "spearman_rho": float(spearman.statistic), "spearman_p_value": float(spearman.pvalue),
                     "spearman_n": n, "missing_factor": missing_factor, "missing_score": missing_score,
                     "missing_either": len(pair) - n, "status": "ok"})
    return pd.DataFrame(rows)


def compare_groups(ranked: pd.DataFrame) -> pd.DataFrame:
    top, bottom = ranked.head(10), ranked.tail(10)
    rows = []
    for label, col in FACTOR_COLUMNS.items():
        if col not in ranked:
            rows.append({"factor": label, "column": col, "top10_mean": np.nan, "bottom10_mean": np.nan,
                         "absolute_difference_top_minus_bottom": np.nan, "percentage_difference_vs_bottom10": np.nan,
                         "top10_n": 0, "bottom10_n": 0, "status": "factor column absent"})
            continue
        a, b = top[col].dropna(), bottom[col].dropna()
        am = float(a.mean()) if len(a) else np.nan
        bm = float(b.mean()) if len(b) else np.nan
        diff = am - bm if len(a) and len(b) else np.nan
        # These report components are additive index/decomposition values. A ratio
        # percentage depends on an arbitrary zero, so report it as not meaningful.
        pct = np.nan
        rows.append({"factor": label, "column": col, "top10_mean": am, "bottom10_mean": bm,
                     "absolute_difference_top_minus_bottom": diff, "percentage_difference_vs_bottom10": pct,
                     "top10_n": len(a), "bottom10_n": len(b), "status": "ok"})
    return pd.DataFrame(rows)


def _as_finite_number(value: Any) -> float | None:
    """Convert a result to a finite float, returning None for invalid values."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if np.isfinite(number) else None


def format_p_value(value: Any) -> str:
    """Format p-values consistently without rounding small values to zero."""
    number = _as_finite_number(value)
    if number is None:
        return "not available"
    if not 0 <= number <= 1:
        return "invalid"
    if number == 0:
        return "0 (underflow)"
    if number < 0.0001:
        return f"{number:.4g}"
    return f"{number:.4g}"


def _format_number(value: Any, digits: int = 3) -> str:
    number = _as_finite_number(value)
    return "not available" if number is None else f"{number:.{digits}f}"


def _valid_pearson_rows(corr: pd.DataFrame) -> pd.DataFrame:
    """Return rows with finite Pearson coefficients and usable factor labels."""
    if not isinstance(corr, pd.DataFrame) or not {"factor", "pearson_r"}.issubset(corr.columns):
        return pd.DataFrame(columns=["factor", "pearson_r"])
    rows = corr.copy()
    if "status" in rows:
        rows = rows.loc[rows["status"].eq("ok")]
    rows["pearson_r"] = pd.to_numeric(rows["pearson_r"], errors="coerce")
    rows = rows.loc[np.isfinite(rows["pearson_r"]) & rows["factor"].notna()]
    return rows


def make_summary(ranked: pd.DataFrame, corr: pd.DataFrame, groups: pd.DataFrame, source: str) -> str:
    gap = float(ranked.iloc[0][SCORE] - ranked.iloc[-1][SCORE])
    out = ["# Global Happiness Insights 2025 — reconstructed analysis", "",
           f"Source workbook: `{source}`. Country ranking uses `Ladder score`; ranks are assigned by descending score.",
           "The workbook has no year column. The report identifies these country rankings as Gallup World Poll life evaluations averaged over 2022–2024.",
           "This is a new analysis of the supplied dataset. It does not recover or claim to reproduce the original internship code or presentation results.", "",
           "## Ranking results", "",
           f"{len(ranked)} country rows ranked. Highest score: {ranked.iloc[0][COUNTRY]} ({ranked.iloc[0][SCORE]:.3f}); "
           f"lowest: {ranked.iloc[-1][COUNTRY]} ({ranked.iloc[-1][SCORE]:.3f}); score gap: {gap:.3f}.", ""]
    for name in ["Finland", "India"]:
        found = ranked[ranked[COUNTRY].str.casefold() == name.casefold()]
        if len(found):
            r = found.iloc[0]
            out.append(f"{name}: rank {int(r['Rank'])}, score {r[SCORE]:.3f}.")
        else:
            out.append(f"{name}: not present in the supplied workbook.")
    out += ["", "## Correlations", "", "Pairwise complete observations are used independently for each factor; missing values are not imputed. Correlation describes association and does not establish causation.", "",
            "| Factor | Pearson r (p), n | Spearman ρ (p), n | Missing factor values |", "|---|---:|---:|---:|"]
    for _, r in corr.iterrows():
        p_pearson = format_p_value(r.get("pearson_p_value"))
        p_spearman = format_p_value(r.get("spearman_p_value"))
        n_pearson = _format_sample_size(r.get("pearson_n"))
        n_spearman = _format_sample_size(r.get("spearman_n"))
        out.append(f"| {r.get('factor', 'Unavailable')} | {_format_number(r.get('pearson_r'))} (p={p_pearson}), {n_pearson} | {_format_number(r.get('spearman_rho'))} (p={p_spearman}), {n_spearman} | {_format_number(r.get('missing_factor'), 0)} |")
    valid = _valid_pearson_rows(corr)
    out.append("")
    positive = valid.loc[valid["pearson_r"].gt(0)]
    negative = valid.loc[valid["pearson_r"].lt(0)]
    if len(positive):
        pos = positive.loc[positive["pearson_r"].idxmax()]
        out.append(f"Strongest positive Pearson association: {pos['factor']} (r={pos['pearson_r']:.3f}, p={format_p_value(pos.get('pearson_p_value'))}).")
    else:
        out.append("No positive Pearson coefficients were observed among valid results.")
    if len(negative):
        neg = negative.loc[negative["pearson_r"].idxmin()]
        out.append(f"Strongest negative Pearson association: {neg['factor']} (r={neg['pearson_r']:.3f}, p={format_p_value(neg.get('pearson_p_value'))}).")
    else:
        out.append("No negative Pearson coefficients were observed among valid results.")
    if len(valid):
        weak = valid.loc[valid["pearson_r"].abs().idxmin()]
        out.append(f"Weakest absolute Pearson association: {weak['factor']} (r={weak['pearson_r']:.3f}, p={format_p_value(weak.get('pearson_p_value'))}).")
    else:
        out.append("Weakest absolute Pearson association is unavailable because no valid coefficients were calculated.")
    out += ["", "## Top 10 versus bottom 10", "", "Differences are top-10 mean minus bottom-10 mean. Percentage differences are omitted because these explained-by components are additive index/decomposition values whose zero point does not support a meaningful ratio comparison.", "",
            "| Factor | Top 10 mean | Bottom 10 mean | Difference | Difference vs bottom (%) | n top / bottom |", "|---|---:|---:|---:|---:|---:|"]
    for _, r in groups.iterrows():
        out.append(f"| {r['factor']} | {_format_number(r['top10_mean'])} | {_format_number(r['bottom10_mean'])} | {_format_number(r['absolute_difference_top_minus_bottom'])} | {_format_number(r['percentage_difference_vs_bottom10'], 1)} | {int(r['top10_n'])} / {int(r['bottom10_n'])} |")
    out += ["", "## Limitations and cleaning", "", "All source countries have unique names and all ladder scores are present. Source missingness is retained; no imputation or row deletion was performed. The explanatory columns are the report's 'explained by' components, which are descriptive decomposition values and should not be interpreted as causal effects.", ""]
    return "\n".join(out)


def _format_sample_size(value: Any) -> str:
    number = _as_finite_number(value)
    return str(int(number)) if number is not None and number >= 0 and number.is_integer() else "not available"


def run_analysis(project_dir: str | Path) -> dict[str, Any]:
    project_dir = Path(project_dir)
    src = project_dir / SOURCE_FILE
    raw, sheets = load_workbook(src)
    cleaned, quality = clean_and_validate(raw)
    ranked = rank_countries(cleaned)
    top, bottom = ranked.head(10), ranked.tail(10)
    corr = correlate(cleaned)
    groups = compare_groups(ranked)
    outdir = project_dir / "outputs"
    figdir = outdir / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(outdir / "cleaned_happiness.csv", index=False)
    top.to_csv(outdir / "top_10_countries.csv", index=False)
    bottom.to_csv(outdir / "bottom_10_countries.csv", index=False)
    corr.to_csv(outdir / "correlation_analysis.csv", index=False)
    groups.to_csv(outdir / "group_comparison.csv", index=False)
    quality.update({"source_file": SOURCE_FILE, "source_sheets": sheets, "source_shape": list(raw.shape),
                    "countries": int(cleaned[COUNTRY].nunique()), "score_column": SCORE,
                    "score_min": float(cleaned[SCORE].min()), "score_max": float(cleaned[SCORE].max()),
                    "python_version": platform.python_version(), "dataset_year_coverage": "2022–2024 (report ranking period; workbook has no year column)",
                    "interpretation": "Country-level ranking associations; no causal inference."})
    (outdir / "data_quality_report.json").write_text(json.dumps(quality, indent=2, ensure_ascii=True), encoding="utf-8")
    (outdir / "analysis_summary.md").write_text(make_summary(ranked, corr, groups, SOURCE_FILE), encoding="utf-8")
    from .visuals import create_figures
    create_figures(ranked, cleaned, figdir)
    return {"cleaned": cleaned, "ranked": ranked, "top": top, "bottom": bottom,
            "correlations": corr, "group_comparison": groups, "quality": quality,
            "score_gap": float(ranked.iloc[0][SCORE] - ranked.iloc[-1][SCORE]), "outdir": outdir}
