# Global Happiness Insights 2025

A reproducible country-level analysis and interactive dashboard built from the World Happiness Report 2025 country ranking. This is a reconstructed analysis of the supplied dataset; it does not recover or claim to reproduce the original internship team's code or exact findings.

## Questions and features

- How are the 147 country records ordered by `Ladder score`? Where do Finland and India rank?
- How are the six available report components associated with Ladder score?
- How do the top and bottom ten countries compare on those components?
- What missing values and potential outliers are present?
- Explore rankings, score filters, six interactive scatter plots, Pearson/Spearman heatmaps, country profiles, missingness, and Tukey outlier summaries in Streamlit.

The explanatory fields are reported as “Explained by” components. They are descriptive report decomposition values; statistical association does not establish causation.

## Dataset, source, and coverage

The project reads `WHR_2025.xls` from the repository root. The workbook used for this run has one sheet (`Sheet1`), 147 unique country records, and 11 columns. It does not contain a year, region, or income-level field. The ranking represents 2022–2024 life evaluations, not annual country observations.

The World Happiness Report's official [Data Sharing page](https://www.worldhappiness.report/data-sharing/) provides the 2025 Figure 2.1 data for free download and cites the report. The page does not state an explicit open-data license or a clear redistribution grant. For that reason, the source workbook is excluded from public Git publication. Obtain the data from the official page, then save the supplied 2025 Figure 2.1 workbook in the project root with the exact filename `WHR_2025.xls`. Do not use another year's workbook. The application and analysis give a direct missing-file message if the file is absent.

Suggested citation: Helliwell, J. F., Layard, R., Sachs, J. D., De Neve, J.-E., Aknin, L. B., & Wang, S. (Eds.). (2025). *World Happiness Report 2025*. University of Oxford: Wellbeing Research Centre. See the official [2025 executive summary](https://worldhappiness.report/ed/2025/executive-summary/) and [data page](https://www.worldhappiness.report/data-sharing/).

Before public release, review the current source terms for both the workbook and row-level derived exports. No region, income, or year-over-year analysis is included because those fields are not in this workbook.

## Technology

Python 3.11+, pandas, NumPy, SciPy, Matplotlib, Seaborn, xlrd, Streamlit, and Plotly. Tests use the existing `unittest` test suite and Streamlit `AppTest`.

## Windows setup

Open PowerShell in the project folder. Create and activate a virtual environment, then install the listed packages:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Place the officially obtained `WHR_2025.xls` at the project root. The original workbook is only read; the analysis never writes to it.

## Run the project

Regenerate the analysis tables, report, quality report, and static figures:

```powershell
python -m happiness_analysis
python -m happiness_analysis.deep_analysis
```

Start the interactive dashboard:

```powershell
streamlit run app.py
```

Run the complete automated test suite:

```powershell
python -m unittest discover -s tests -v
```

Optional PowerPoint source: `presentation/build_deck.mjs`. Rebuilding the `.pptx` requires the `@oai/artifact-tool` package and presentation validation toolkit in addition to Node.js. Set `NODE_PATH` (or `RUNTIME_NODE_MODULES`) and `PRESENTATION_TOOLKIT_DIR` to those installed locations before running `node presentation/build_deck.mjs`; `PYTHON_EXECUTABLE` may be set to the Python executable used by the validator. These presentation tools are separate from the Python `requirements.txt`.

## Repository structure

```text
app.py
happiness_analysis/
  analysis.py       # workbook loading, validation, rankings, correlations and exports
  dashboard.py      # dashboard transformations and Plotly figures
  deep_analysis.py  # missingness, outliers and executive summary
  visuals.py        # static Matplotlib/Seaborn figures
outputs/            # generated CSV, JSON, Markdown and figure files
presentation/
  build_deck.mjs
  Global_Happiness_Insights_2025.pptx
tests/
  test_analysis.py
  test_dashboard.py
```

## Data quality and method

Cleaning trims whitespace from column headers and country names. It validates required columns, numeric types, unique/nonempty country names, finite Ladder scores, and the 0–10 score range. All 147 rows are retained; there is no imputation. The source contains six missing cells: one each in healthy life expectancy, freedom, and perceptions of corruption, and three in `Dystopia + residual`. Each correlation uses pairwise complete rows and reports its own sample size; means use available observations. Outliers are flagged with Tukey's 1.5×IQR rule and are not removed.

Pearson measures linear association; Spearman measures rank-based monotonic association. P-values are displayed in significant or scientific notation so small values are not rounded to zero; the CSV retains the full calculated floating-point values. P-values do not measure effect size or causation. Top-minus-bottom mean differences are reported, while percentage differences are omitted because the additive component scale does not have a meaningful ratio zero point.

## Verified findings

Recomputed from the supplied workbook by this project: Finland ranks first (7.736); Afghanistan ranks last (1.364); India ranks 118th (4.389); the score range is 6.372. Social support has the strongest positive Pearson correlation (r=0.812, p=9.64e-36, n=147). No negative Pearson coefficients were observed. Generosity has the weakest absolute Pearson correlation (r=0.054, p=0.5132, n=147), which is not statistically significant at the conventional 0.05 level. These are country-level associations, not causal effects.

## Dashboard screenshot

No screenshot is included yet. Slide 10 in the presentation contains a labeled placeholder. After launching the app, capture a genuine browser screenshot and save it as `presentation/dashboard_screenshot.png`; then replace the placeholder on slide 10 and add the image here. Do not use a mockup in place of the running application.

## Outputs

The analysis generates `cleaned_happiness.csv`, `top_10_countries.csv`, `bottom_10_countries.csv`, `correlation_analysis.csv`, `group_comparison.csv`, `data_quality_report.json`, `analysis_summary.md`, and six static PNG figures under `outputs/figures/`. The deeper analysis generates `missing_data_summary.csv`, `outlier_summary.csv`, and `executive_summary.md`. The 12-slide presentation is `presentation/Global_Happiness_Insights_2025.pptx`.
