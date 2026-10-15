"""Charts for country rankings, selected factors, and correlations."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .analysis import COUNTRY, FACTOR_COLUMNS, SCORE

sns.set_theme(style="whitegrid", context="notebook")


def create_figures(ranked: pd.DataFrame, df: pd.DataFrame, output_dir: str | Path) -> None:
    output_dir = Path(output_dir)
    for label, subset, filename, color in [
        ("Top 10 happiest countries", ranked.head(10).sort_values(SCORE), "top_10_ranking.png", "#218c74"),
        ("Bottom 10 countries", ranked.tail(10).sort_values(SCORE), "bottom_10_ranking.png", "#c44536"),
    ]:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(subset[COUNTRY], subset[SCORE], color=color)
        ax.set(title=label, xlabel="Ladder score", ylabel="Country")
        fig.tight_layout(); fig.savefig(output_dir / filename, dpi=160); plt.close(fig)
    for label in ["GDP per capita", "Social support", "Healthy life expectancy"]:
        col = FACTOR_COLUMNS[label]
        pair = df[[col, SCORE]].dropna()
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.regplot(data=pair, x=col, y=SCORE, lowess=False,
                    scatter_kws={"alpha": .75, "s": 38}, line_kws={"color": "#d35400"}, ax=ax)
        ax.set(title=f"Happiness and {label.lower()}", xlabel=label, ylabel="Ladder score")
        fig.tight_layout(); fig.savefig(output_dir / f"scatter_{label.lower().replace(' ', '_')}.png", dpi=160); plt.close(fig)
    cols = [SCORE, *FACTOR_COLUMNS.values()]
    matrix = df[cols].corr(method="pearson", min_periods=2)
    pretty = ["Ladder score", *FACTOR_COLUMNS.keys()]
    matrix.index = pretty; matrix.columns = pretty
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(matrix, annot=True, fmt=".2f", cmap="vlag", center=0, vmin=-1, vmax=1,
                square=True, linewidths=.5, ax=ax)
    ax.set_title("Pearson correlation heatmap (pairwise complete data)")
    fig.tight_layout(); fig.savefig(output_dir / "correlation_heatmap.png", dpi=160); plt.close(fig)
