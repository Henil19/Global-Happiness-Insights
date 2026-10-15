"""Testable Streamlit dashboard transformations and Plotly chart builders."""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .analysis import COUNTRY, FACTOR_COLUMNS, SCORE, clean_and_validate, load_workbook, rank_countries

PALETTE = {"ink": "#18324A", "teal": "#187C78", "coral": "#D96B4A", "muted": "#6D7E8C", "grid": "#E5EBEF"}


def load_dashboard_data(project_root: str | Path) -> tuple[pd.DataFrame, dict]:
    source = Path(project_root) / "WHR_2025.xls"
    raw, sheets = load_workbook(source)
    cleaned, quality = clean_and_validate(raw)
    quality.update({"source_file": source.name, "source_sheets": sheets,
                    "dataset_year_coverage": "2022–2024 (report ranking period; workbook has no year column)"})
    return rank_countries(cleaned), quality


def filter_rankings(ranked: pd.DataFrame, countries=None, score_range=None,
                    view="All countries", search="") -> pd.DataFrame:
    result = ranked.copy()
    if countries:
        result = result[result[COUNTRY].isin(countries)]
    if score_range:
        result = result[result[SCORE].between(score_range[0], score_range[1])]
    if search.strip():
        result = result[result[COUNTRY].str.contains(search.strip(), case=False, regex=False)]
    if view == "Top 10":
        result = result.nsmallest(10, "Rank")
    elif view == "Bottom 10":
        result = result.nlargest(10, "Rank")
    return result.sort_values("Rank").reset_index(drop=True)


def country_profile(ranked: pd.DataFrame, country: str) -> pd.DataFrame:
    row = ranked.loc[ranked[COUNTRY].eq(country)].iloc[0]
    metrics = [SCORE, *FACTOR_COLUMNS.values()]
    averages = ranked[metrics].mean(numeric_only=True)
    return pd.DataFrame({
        "Indicator": ["Ladder score", *FACTOR_COLUMNS.keys()],
        "Country value": [row.get(col, np.nan) for col in metrics],
        "Dataset average": [averages.get(col, np.nan) for col in metrics],
        "Difference vs average": [row.get(col, np.nan) - averages.get(col, np.nan) for col in metrics],
    })


def scatter_figure(ranked: pd.DataFrame, label: str) -> go.Figure:
    col = FACTOR_COLUMNS[label]
    data = ranked.dropna(subset=[col, SCORE]).copy()
    corr = data[[col, SCORE]].corr(method="pearson").iloc[0, 1]
    fig = px.scatter(data, x=col, y=SCORE, hover_name=COUNTRY,
                     hover_data={"Rank": True, col: ":.3f", SCORE: ":.3f"},
                     color_discrete_sequence=[PALETTE["teal"]],
                     labels={col: label, SCORE: "Ladder score"},
                     title=f"Ladder score and {label.lower()} · Pearson r = {corr:.3f} · n = {len(data)}")
    fig.update_traces(marker={"size": 9, "opacity": .78}, selector={"mode": "markers"})
    fig.update_layout(template="plotly_white", height=430, margin={"l": 10,"r": 10,"t": 68,"b": 12},
                      font={"color": PALETTE["ink"]}, hoverlabel={"namelength": 0})
    fig.update_xaxes(showgrid=True, gridcolor=PALETTE["grid"])
    fig.update_yaxes(showgrid=True, gridcolor=PALETTE["grid"])
    return fig


def correlation_figure(ranked: pd.DataFrame, method="pearson") -> go.Figure:
    cols = [SCORE, *FACTOR_COLUMNS.values()]
    corr = ranked[cols].corr(method=method, min_periods=2)
    labels = ["Ladder score", *FACTOR_COLUMNS.keys()]
    fig = go.Figure(go.Heatmap(z=corr.to_numpy(), x=labels, y=labels, zmin=-1, zmax=1,
                               colorscale="RdBu", reversescale=True, colorbar={"title": "Correlation"},
                               text=np.round(corr.to_numpy(), 2), texttemplate="%{text:.2f}",
                               hovertemplate="%{y} × %{x}<br>Coefficient: %{z:.3f}<extra></extra>"))
    fig.update_layout(template="plotly_white", height=580, margin={"l": 10,"r": 10,"t": 30,"b": 80},
                      xaxis={"tickangle": -30}, font={"color": PALETTE["ink"]})
    return fig


def comparison_figure(ranked: pd.DataFrame) -> go.Figure:
    frame = ranked.copy()
    frame["Group"] = np.where(frame.Rank <= 10, "Top 10", np.where(frame.Rank > len(frame) - 10, "Bottom 10", "Other"))
    means = frame[frame.Group.isin(["Top 10", "Bottom 10"])].groupby("Group")[[*FACTOR_COLUMNS.values()]].mean().T
    means.index = list(FACTOR_COLUMNS.keys())
    means.index.name = "Indicator"
    plot_data = means.reset_index().melt(id_vars="Indicator", var_name="Group", value_name="Mean value")
    fig = px.bar(plot_data, x="Indicator", y="Mean value", color="Group", barmode="group",
                 color_discrete_map={"Top 10": PALETTE["teal"], "Bottom 10": PALETTE["coral"]},
                 labels={"Mean value": "Mean explanatory component", "Indicator": "Indicator"},
                 hover_data={"Mean value": ":.3f"})
    fig.update_layout(template="plotly_white", height=450, margin={"l": 10,"r": 10,"t": 22,"b": 80},
                      font={"color": PALETTE["ink"]}, legend_title_text="Ranking group")
    fig.update_xaxes(tickangle=-25)
    return fig
