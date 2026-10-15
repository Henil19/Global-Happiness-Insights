from pathlib import Path

import streamlit as st

from happiness_analysis.analysis import COUNTRY, FACTOR_COLUMNS, SCORE, compare_groups, correlate, format_p_value
from happiness_analysis.dashboard import (
    comparison_figure, correlation_figure, country_profile, filter_rankings,
    load_dashboard_data, scatter_figure,
)
from happiness_analysis.deep_analysis import missing_summary, outlier_summary

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Global Happiness Insights", page_icon=":material/insights:",
                   layout="wide", initial_sidebar_state="expanded")


@st.cache_data(show_spinner="Loading and validating the supplied workbook…")
def cached_data():
    return load_dashboard_data(ROOT)


try:
    ranked, quality = cached_data()
except FileNotFoundError as exc:
    st.error(str(exc), icon=":material/dataset:")
    st.stop()

with st.sidebar:
    st.title("Global happiness")
    st.caption("World Happiness Report 2025 · country-level analysis")
    page = st.selectbox("Explore", ["Overview", "Rankings", "Relationships", "Top vs bottom", "Country detail", "Data quality"])
    st.divider()
    countries = st.multiselect("Filter countries", ranked[COUNTRY].tolist(), placeholder="All countries")
    score_range = st.slider("Ladder score range", float(ranked[SCORE].min()), float(ranked[SCORE].max()),
                            (float(ranked[SCORE].min()), float(ranked[SCORE].max())), step=.001)
    st.caption("Regional and income filters are unavailable because the supplied workbook has no such fields.")
    st.caption("Source: supplied WHR_2025.xls")

filtered = filter_rankings(ranked, countries=countries, score_range=score_range)

st.title("Global Happiness Insights 2025")
st.caption("A reproducible exploration of country ladder scores and the report’s explanatory components.")

if filtered.empty:
    st.warning("No countries match the current filters. Adjust the country selection or score range.", title="No matching countries")
    st.stop()

if page == "Overview":
    low, high = ranked.iloc[-1], ranked.iloc[0]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Countries", f"{len(ranked):,}", border=True)
    k2.metric("Highest ranked", f"{high[COUNTRY]} · {high[SCORE]:.3f}", border=True)
    k3.metric("Lowest ranked", f"{low[COUNTRY]} · {low[SCORE]:.3f}", border=True)
    k4.metric("Score range", f"{high[SCORE]-low[SCORE]:.3f}", border=True)
    st.subheader("Country rankings")
    st.write("Use the ranking and relationship pages to search, sort, and explore the country scores.")
    st.plotly_chart(comparison_figure(ranked), width="stretch", theme="streamlit", alt="Top and bottom ten explanatory component comparison")
    st.info("Ladder score is the country happiness ranking measure. The ‘explained by’ variables are report decomposition components. Correlation describes association and does not establish causation.", title="How to read this dashboard")

elif page == "Rankings":
    st.subheader("Country ranking table")
    mode = st.segmented_control("Ranking view", ["All countries", "Top 10", "Bottom 10"], default="All countries")
    query = st.text_input("Search country", placeholder="Type a country name")
    table = filter_rankings(ranked, countries=countries, score_range=score_range,
                            view=mode or "All countries", search=query)
    st.caption(f"Showing {len(table)} countries. Click column headers to sort.")
    st.dataframe(table[["Rank", COUNTRY, SCORE]], hide_index=True, height=560,
                 column_config={"Rank": st.column_config.NumberColumn("Rank", format="%d"),
                                SCORE: st.column_config.NumberColumn("Ladder score", format="%.3f")},
                 alt="Interactive country rankings with rank and Ladder score")

elif page == "Relationships":
    st.subheader("Happiness and explanatory components")
    st.caption("Each point is a country. Missing values are excluded separately for each plot. Pearson r summarizes linear association; it does not show causation.")
    chosen = st.selectbox("Indicator", list(FACTOR_COLUMNS.keys()))
    st.plotly_chart(scatter_figure(filtered, chosen), width="stretch", alt=f"Ladder score versus {chosen} by country")
    st.subheader("Correlation heatmap")
    method = st.segmented_control("Correlation method", ["pearson", "spearman"], default="pearson", format_func=str.title)
    st.plotly_chart(correlation_figure(filtered, method or "pearson"), width="stretch",
                    alt=f"Country correlation heatmap using {method or 'pearson'} correlations")
    st.caption("Pearson measures linear association. Spearman measures monotonic rank association. Both use pairwise complete observations.")
    corr = correlate(filtered.drop(columns="Rank"))
    display_corr = corr[["factor", "pearson_r", "pearson_p_value", "pearson_n", "spearman_rho", "spearman_p_value", "spearman_n", "missing_either"]].copy()
    display_corr["pearson_p_value"] = display_corr["pearson_p_value"].map(format_p_value)
    display_corr["spearman_p_value"] = display_corr["spearman_p_value"].map(format_p_value)
    display_corr = display_corr.rename(columns={"pearson_p_value": "Pearson p-value", "spearman_p_value": "Spearman p-value"})
    st.dataframe(display_corr, hide_index=True,
                 alt="Pearson and Spearman correlation tests with formatted p-values and sample sizes")

elif page == "Top vs bottom":
    st.subheader("Top 10 and bottom 10 countries")
    st.plotly_chart(comparison_figure(ranked), width="stretch", alt="Average explanatory component values for top and bottom ten countries")
    groups = compare_groups(ranked)
    st.dataframe(groups, hide_index=True, alt="Actual top ten and bottom ten indicator averages and differences")
    st.caption("Differences use top-10 mean minus bottom-10 mean. Percentage differences are omitted because these additive components do not have a meaningful ratio zero point.")

elif page == "Country detail":
    st.subheader("Country profile")
    default = "Finland" if "Finland" in filtered[COUNTRY].values else filtered.iloc[0][COUNTRY]
    selected = st.selectbox("Country", filtered[COUNTRY].tolist(), index=filtered[COUNTRY].tolist().index(default))
    row = filtered.loc[filtered[COUNTRY].eq(selected)].iloc[0]
    a, b, c = st.columns(3)
    a.metric("Rank", f"#{int(row.Rank)}")
    b.metric("Ladder score", f"{row[SCORE]:.3f}")
    c.metric("Dataset score average", f"{ranked[SCORE].mean():.3f}")
    profile = country_profile(ranked, selected)
    st.dataframe(profile, hide_index=True, column_config={
        "Country value": st.column_config.NumberColumn(format="%.3f"),
        "Dataset average": st.column_config.NumberColumn(format="%.3f"),
        "Difference vs average": st.column_config.NumberColumn(format="%+.3f"),
    }, alt=f"{selected} indicator values compared with dataset averages")
    st.caption("Averages are calculated from available values only. Missing country values remain blank.")

elif page == "Data quality":
    st.subheader("Data quality and missing values")
    st.write(f"Source workbook: **WHR_2025.xls**, sheet `Sheet1`, {quality['rows_after_cleaning']} rows × {quality['columns_after_cleaning']} columns. "
             "The workbook has no year, region, or income-level fields. Report coverage is 2022–2024, not annual row-level observations.")
    st.markdown("No rows were removed and no values were imputed. Pairwise complete rows are used separately for each correlation. Group averages use available observations. Outliers are flagged for review using the 1.5×IQR rule and are not removed.")
    st.dataframe(missing_summary(ranked.drop(columns="Rank")), hide_index=True,
                 column_config={"missing_percent": st.column_config.NumberColumn("Missing (%)", format="%.2f")},
                 alt="Missing-value count and percentage for every source field")
    st.subheader("Outlier summary")
    st.dataframe(outlier_summary(ranked.drop(columns="Rank")), hide_index=True,
                 alt="Tukey 1.5 times interquartile range outlier counts for score and available factors")
    st.subheader("Cleaning decisions")
    for item in quality["cleaning_decisions"]:
        st.markdown(f"- {item}")
    st.json({"source": quality["source_file"], "sheets": quality["source_sheets"],
             "rows_before": quality["rows_before_cleaning"], "rows_after": quality["rows_after_cleaning"],
             "missing_after_cleaning": quality["missing_after_cleaning"]})

st.divider()
st.caption("Country-level descriptive analysis. Correlations do not establish causation. Reconstructed project analysis, not a recovery of the original internship code or exact results.")
