# Global Happiness Insights 2025 — reconstructed analysis

Source workbook: `WHR_2025.xls`. Country ranking uses `Ladder score`; ranks are assigned by descending score.
The workbook has no year column. The report identifies these country rankings as Gallup World Poll life evaluations averaged over 2022–2024.
This is a new analysis of the supplied dataset. It does not recover or claim to reproduce the original internship code or presentation results.

## Ranking results

147 country rows ranked. Highest score: Finland (7.736); lowest: Afghanistan (1.364); score gap: 6.372.

Finland: rank 1, score 7.736.
India: rank 118, score 4.389.

## Correlations

Pairwise complete observations are used independently for each factor; missing values are not imputed. Correlation describes association and does not establish causation.

| Factor | Pearson r (p), n | Spearman ρ (p), n | Missing factor values |
|---|---:|---:|---:|
| GDP per capita | 0.763 (p=2.675e-29), 147 | 0.810 (p=1.925e-35), 147 | 0 |
| Social support | 0.812 (p=9.636e-36), 147 | 0.811 (p=1.49e-35), 147 | 0 |
| Healthy life expectancy | 0.712 (p=7.387e-24), 146 | 0.725 (p=4.466e-25), 146 | 1 |
| Freedom to make life choices | 0.634 (p=8.196e-18), 146 | 0.620 (p=7.302e-17), 146 | 1 |
| Generosity | 0.054 (p=0.5132), 147 | 0.099 (p=0.2345), 147 | 0 |
| Perceptions of corruption | 0.412 (p=2.303e-07), 146 | 0.370 (p=4.425e-06), 146 | 1 |

Strongest positive Pearson association: Social support (r=0.812, p=9.636e-36).
No negative Pearson coefficients were observed among valid results.
Weakest absolute Pearson association: Generosity (r=0.054, p=0.5132).

## Top 10 versus bottom 10

Differences are top-10 mean minus bottom-10 mean. Percentage differences are omitted because these explained-by components are additive index/decomposition values whose zero point does not support a meaningful ratio comparison.

| Factor | Top 10 mean | Bottom 10 mean | Difference | Difference vs bottom (%) | n top / bottom |
|---|---:|---:|---:|---:|---:|
| GDP per capita | 1.753 | 0.821 | 0.932 | not available | 10 / 10 |
| Social support | 1.685 | 0.831 | 0.854 | not available | 10 / 10 |
| Healthy life expectancy | 0.803 | 0.255 | 0.548 | not available | 10 / 10 |
| Freedom to make life choices | 0.918 | 0.478 | 0.441 | not available | 10 / 10 |
| Generosity | 0.137 | 0.088 | 0.049 | not available | 10 / 10 |
| Perceptions of corruption | 0.323 | 0.098 | 0.224 | not available | 10 / 10 |

## Limitations and cleaning

All source countries have unique names and all ladder scores are present. Source missingness is retained; no imputation or row deletion was performed. The explanatory columns are the report's 'explained by' components, which are descriptive decomposition values and should not be interpreted as causal effects.
