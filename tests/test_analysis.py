import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from happiness_analysis.analysis import (
    COUNTRY, SCORE, FACTOR_COLUMNS, clean_and_validate, compare_groups,
    correlate, format_p_value, load_workbook, make_summary, rank_countries,
)


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df, cls.sheets = load_workbook("WHR_2025.xls")

    def test_load_actual_workbook(self):
        self.assertEqual(self.sheets, ["Sheet1"])
        self.assertEqual(self.df.shape, (147, 11))
        self.assertTrue(self.df[COUNTRY].is_unique)

    def test_missing_workbook_has_actionable_message(self):
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(FileNotFoundError, "place the workbook here as WHR_2025.xls"):
                load_workbook(Path(folder) / "WHR_2025.xls")

    def test_cleaning_preserves_rows_and_missing_values(self):
        cleaned, report = clean_and_validate(self.df)
        self.assertEqual(len(cleaned), len(self.df))
        self.assertEqual(report["rows_removed"], 0)
        self.assertEqual(cleaned.isna().sum().to_dict(), self.df.isna().sum().to_dict())
        self.assertEqual(int(cleaned["Explained by: Healthy life expectancy"].isna().sum()), 1)

    def test_rankings_and_country_results(self):
        cleaned, _ = clean_and_validate(self.df)
        ranked = rank_countries(cleaned)
        self.assertEqual(len(ranked.head(10)), 10)
        self.assertEqual(len(ranked.tail(10)), 10)
        self.assertEqual(ranked.iloc[0][COUNTRY], "Finland")
        self.assertAlmostEqual(ranked.iloc[0][SCORE], 7.736)
        self.assertEqual(ranked.iloc[-1][COUNTRY], "Afghanistan")
        self.assertAlmostEqual(ranked.iloc[-1][SCORE], 1.364)
        self.assertEqual(ranked["Rank"].tolist(), list(range(1, 148)))

    def test_correlations_pairwise_missing(self):
        cleaned, _ = clean_and_validate(self.df)
        result = correlate(cleaned).set_index("factor")
        row = result.loc["Healthy life expectancy"]
        self.assertEqual(row["pearson_n"], 146)
        self.assertEqual(row["spearman_n"], 146)
        self.assertEqual(row["missing_factor"], 1)
        self.assertEqual(row["missing_either"], 1)
        self.assertTrue(np.isfinite(row["pearson_r"]))

    def test_group_comparison_counts(self):
        cleaned, _ = clean_and_validate(self.df)
        result = compare_groups(rank_countries(cleaned))
        self.assertTrue((result["top10_n"] <= 10).all())
        self.assertTrue((result["bottom10_n"] <= 10).all())
        self.assertEqual(result.loc[result.factor == "GDP per capita", "top10_n"].iloc[0], 10)

    def test_duplicate_countries_rejected(self):
        duplicated = pd.concat([self.df, self.df.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Duplicate country"):
            clean_and_validate(duplicated)

    def test_absent_factor_is_documented(self):
        reduced = self.df.drop(columns=[FACTOR_COLUMNS["Generosity"]])
        result = correlate(reduced).set_index("factor")
        self.assertEqual(result.loc["Generosity", "status"], "factor column absent")
        self.assertEqual(result.loc["Generosity", "pearson_n"], 0)

    def _summary(self, correlations):
        cleaned, _ = clean_and_validate(self.df)
        ranked = rank_countries(cleaned)
        return make_summary(ranked, correlations, compare_groups(ranked), "fixture.xls")

    def test_summary_all_positive_reports_no_negative(self):
        summary = self._summary(pd.DataFrame([
            {"factor": "A", "pearson_r": .7, "pearson_p_value": 1e-20, "pearson_n": 10,
             "spearman_rho": .6, "spearman_p_value": .00001, "spearman_n": 10, "missing_factor": 0, "status": "ok"},
            {"factor": "B", "pearson_r": .1, "pearson_p_value": .4, "pearson_n": 10,
             "spearman_rho": .2, "spearman_p_value": .3, "spearman_n": 10, "missing_factor": 0, "status": "ok"},
        ]))
        self.assertIn("Strongest positive Pearson association: A", summary)
        self.assertIn("No negative Pearson coefficients were observed", summary)
        self.assertIn("Weakest absolute Pearson association: B", summary)
        self.assertIn("p=1e-20", summary)
        self.assertNotIn("p=0.0000", summary)

    def test_summary_reports_strongest_negative_only_when_present(self):
        summary = self._summary(pd.DataFrame([
            {"factor": "Positive", "pearson_r": .5, "pearson_p_value": .01, "pearson_n": 12,
             "spearman_rho": .5, "spearman_p_value": .01, "spearman_n": 12, "missing_factor": 0, "status": "ok"},
            {"factor": "Negative", "pearson_r": -.8, "pearson_p_value": .001, "pearson_n": 12,
             "spearman_rho": -.7, "spearman_p_value": .002, "spearman_n": 12, "missing_factor": 0, "status": "ok"},
            {"factor": "Less negative", "pearson_r": -.2, "pearson_p_value": .2, "pearson_n": 12,
             "spearman_rho": -.1, "spearman_p_value": .5, "spearman_n": 12, "missing_factor": 0, "status": "ok"},
        ]))
        self.assertIn("Strongest negative Pearson association: Negative (r=-0.800", summary)

    def test_summary_handles_empty_and_invalid_correlations(self):
        empty = self._summary(pd.DataFrame(columns=["factor", "pearson_r", "pearson_p_value", "pearson_n",
                                                    "spearman_rho", "spearman_p_value", "spearman_n", "missing_factor"]))
        self.assertIn("No positive Pearson coefficients were observed", empty)
        self.assertIn("No negative Pearson coefficients were observed", empty)
        invalid = self._summary(pd.DataFrame([
            {"factor": "NaN", "pearson_r": np.nan, "pearson_p_value": np.nan, "status": "ok"},
            {"factor": "Inf", "pearson_r": np.inf, "pearson_p_value": -1, "status": "ok"},
            {"factor": "Invalid status", "pearson_r": -.9, "pearson_p_value": .001, "status": "factor column absent"},
        ]))
        self.assertIn("No negative Pearson coefficients were observed", invalid)
        self.assertNotIn("Strongest negative Pearson association", invalid)

    def test_p_value_formatting(self):
        self.assertEqual(format_p_value(9.636164648994058e-36), "9.636e-36")
        self.assertEqual(format_p_value(.5132203231), "0.5132")
        self.assertEqual(format_p_value(np.nan), "not available")
        self.assertEqual(format_p_value(None), "not available")
        self.assertEqual(format_p_value(-.1), "invalid")
        self.assertEqual(format_p_value(1.1), "invalid")
        self.assertEqual(format_p_value(.0001), "0.0001")
        self.assertEqual(format_p_value(.00009999), "9.999e-05")


if __name__ == "__main__":
    unittest.main()
