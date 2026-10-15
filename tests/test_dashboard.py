import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from happiness_analysis.analysis import (
    COUNTRY, FACTOR_COLUMNS, SCORE, compare_groups, correlate, load_workbook, clean_and_validate, rank_countries,
)
from happiness_analysis.dashboard import (
    correlation_figure, country_profile, filter_rankings, load_dashboard_data, scatter_figure,
)
from happiness_analysis.deep_analysis import (
    build_executive_summary, missing_summary, outlier_summary, country_comparison,
)

ROOT = Path(__file__).resolve().parents[1]


class DashboardTransformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ranked, cls.quality = load_dashboard_data(ROOT)

    def test_filter_search_views_and_score_range(self):
        all_rows = filter_rankings(self.ranked, search="land")
        self.assertIn("Finland", all_rows[COUNTRY].tolist())
        top = filter_rankings(self.ranked, view="Top 10")
        bottom = filter_rankings(self.ranked, view="Bottom 10")
        self.assertEqual(len(top), 10)
        self.assertEqual(len(bottom), 10)
        self.assertEqual(top.iloc[0][COUNTRY], "Finland")
        limited = filter_rankings(self.ranked, score_range=(7, 8))
        self.assertTrue(limited[SCORE].between(7, 8).all())

    def test_country_profile_and_missing_handling(self):
        profile = country_profile(self.ranked, "Finland")
        self.assertEqual(len(profile), 7)
        self.assertEqual(profile.loc[0, "Country value"], 7.736)
        self.assertTrue(np.isfinite(profile.loc[0, "Dataset average"]))
        for country in ["Oman", "Tajikistan", "State of Palestine"]:
            source_row = self.ranked.loc[self.ranked[COUNTRY].eq(country)].iloc[0]
            missing_factor = next(column for column in FACTOR_COLUMNS.values() if pd.isna(source_row[column]))
            detail = country_profile(self.ranked, country)
            indicator = next(name for name, column in FACTOR_COLUMNS.items() if column == missing_factor)
            value = detail.loc[detail.Indicator.eq(indicator), "Country value"].iloc[0]
            difference = detail.loc[detail.Indicator.eq(indicator), "Difference vs average"].iloc[0]
            self.assertTrue(pd.isna(value))
            self.assertTrue(pd.isna(difference))

    def test_plotly_builders_exclude_missing_pairwise(self):
        fig = scatter_figure(self.ranked, "Healthy life expectancy")
        self.assertEqual(len(fig.data[0].x), 146)
        heatmap = correlation_figure(self.ranked, "spearman")
        self.assertEqual(len(heatmap.data), 1)
        self.assertEqual(heatmap.data[0].z.shape, (7, 7))

    def test_deep_summaries_and_original_csv_consistency(self):
        self.assertEqual(int(missing_summary(self.ranked.drop(columns="Rank")).missing_count.sum()), 6)
        self.assertEqual(len(outlier_summary(self.ranked.drop(columns="Rank"))), 7)
        pair = country_comparison(self.ranked)
        self.assertEqual(pair[COUNTRY].tolist(), ["Finland", "India"])
        no_india = self.ranked.loc[~self.ranked[COUNTRY].eq("India")].copy()
        no_india_corr = pd.DataFrame(columns=["factor", "pearson_r"])
        no_india_summary = build_executive_summary(
            no_india, no_india_corr, compare_groups(no_india),
            missing_summary(no_india.drop(columns="Rank")), outlier_summary(no_india.drop(columns="Rank")),
        )
        self.assertIn("India is not present", no_india_summary)
        self.assertIn("No negative Pearson coefficients were observed", no_india_summary)
        old = pd.read_csv(ROOT / "outputs" / "top_10_countries.csv")
        pd.testing.assert_frame_equal(self.ranked.head(10)[old.columns], old, check_dtype=False)
        source_group = compare_groups(self.ranked)
        saved_group = pd.read_csv(ROOT / "outputs" / "group_comparison.csv")
        for column in ["top10_mean", "bottom10_mean", "absolute_difference_top_minus_bottom"]:
            np.testing.assert_allclose(source_group[column], saved_group[column], rtol=1e-12, equal_nan=True)
        for column in ["top10_n", "bottom10_n"]:
            np.testing.assert_array_equal(source_group[column], saved_group[column])
        current_corr = correlate(self.ranked.drop(columns="Rank"))
        old_corr = pd.read_csv(ROOT / "outputs" / "correlation_analysis.csv")
        for column in ["pearson_r", "pearson_p_value", "spearman_rho", "spearman_p_value"]:
            np.testing.assert_allclose(current_corr[column], old_corr[column], rtol=1e-12, equal_nan=True)
        for column in ["pearson_n", "spearman_n", "missing_factor", "missing_score", "missing_either"]:
            np.testing.assert_array_equal(current_corr[column], old_corr[column])
        self.assertEqual(self.ranked[COUNTRY].nunique(), 147)
        self.assertEqual(len(old), 10)
        self.assertEqual(len(pd.read_csv(ROOT / "outputs" / "bottom_10_countries.csv")), 10)
        summary = (ROOT / "outputs" / "analysis_summary.md").read_text(encoding="utf-8")
        self.assertIn("No negative Pearson coefficients were observed", summary)
        self.assertIn("Social support (r=0.812, p=9.636e-36)", summary)
        self.assertNotIn("p=0.0000", summary)
        self.assertAlmostEqual(current_corr.loc[current_corr.factor.eq("Generosity"), "pearson_p_value"].iloc[0], .5132203231182889)

    def test_streamlit_app_renders(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        self.assertFalse(app.exception, msg=str(app.exception))
        self.assertTrue(any("Global Happiness Insights 2025" in str(el.value) for el in app.title))
        score_filter = next(item for item in app.slider if item.label == "Ladder score range")
        self.assertEqual(score_filter.value, (float(self.ranked[SCORE].min()), float(self.ranked[SCORE].max())))

    def test_streamlit_ranking_search_and_views(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        next(item for item in app.selectbox if item.label == "Explore").select("Rankings").run()
        view = next(item for item in app.segmented_control if item.label == "Ranking view")
        view.set_value("Top 10").run()
        self.assertTrue(any("Showing 10 countries" in str(item.value) for item in app.caption))
        next(item for item in app.segmented_control if item.label == "Ranking view").set_value("Bottom 10").run()
        self.assertTrue(any("Showing 10 countries" in str(item.value) for item in app.caption))
        next(item for item in app.segmented_control if item.label == "Ranking view").set_value("All countries").run()
        next(item for item in app.text_input if item.label == "Search country").set_value("Finland").run()
        self.assertFalse(app.exception, msg=str(app.exception))
        self.assertTrue(any("Showing 1 countries" in str(item.value) for item in app.caption))

    def test_streamlit_data_quality_page_renders(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        app.selectbox[0].select("Data quality").run()
        self.assertFalse(app.exception, msg=str(app.exception))
        self.assertTrue(any("Data quality and missing values" in str(el.value) for el in app.subheader))

    def test_streamlit_factor_and_method_controls(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        nav = next(item for item in app.selectbox if item.label == "Explore")
        nav.select("Relationships").run()
        self.assertFalse(app.exception, msg=str(app.exception))
        dashboard_corr = app.dataframe[0].value
        social = dashboard_corr.loc[dashboard_corr.factor.eq("Social support")].iloc[0]
        generosity = dashboard_corr.loc[dashboard_corr.factor.eq("Generosity")].iloc[0]
        self.assertEqual(social["Pearson p-value"], "9.636e-36")
        self.assertEqual(generosity["Pearson p-value"], "0.5132")
        for factor in FACTOR_COLUMNS:
            control = next(item for item in app.selectbox if item.label == "Indicator")
            control.select(factor).run()
            self.assertFalse(app.exception, msg=f"{factor}: {app.exception}")
        method = next(item for item in app.segmented_control if item.label == "Correlation method")
        method.set_value("spearman").run()
        self.assertFalse(app.exception, msg=str(app.exception))

    def test_streamlit_group_comparison_uses_current_analysis(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        next(item for item in app.selectbox if item.label == "Explore").select("Top vs bottom").run()
        actual = app.dataframe[0].value
        expected = pd.read_csv(ROOT / "outputs" / "group_comparison.csv")
        np.testing.assert_allclose(actual.absolute_difference_top_minus_bottom,
                                   expected.absolute_difference_top_minus_bottom, rtol=1e-12)
        self.assertFalse(app.exception, msg=str(app.exception))

    def test_streamlit_country_detail_selection(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        next(item for item in app.selectbox if item.label == "Explore").select("Country detail").run()
        country = next(item for item in app.selectbox if item.label == "Country")
        country.select("India").run()
        self.assertFalse(app.exception, msg=str(app.exception))
        self.assertEqual(next(item for item in app.selectbox if item.label == "Country").value, "India")


if __name__ == "__main__":
    unittest.main()
