# References — ENGG2112 Project MODR

This document lists all data sources, software dependencies, and methodological references used in the MODR (Mapping and Optimising Disease Response) project. Last updated April 2026.

---

## 1. Data Sources

### 1.1 Influenza Surveillance Data

#### New York State (Primary)
- **Title**: Influenza Laboratory-Confirmed Cases by County, Beginning 2009-10 Season
- **Publisher**: New York State Department of Health
- **URL**: https://health.data.ny.gov/Health/Influenza-Laboratory-Confirmed-Cases-by-County-Beg/jr8b-6gh6
- **API endpoint**: `https://health.data.ny.gov/resource/jr8b-6gh6.csv`
- **License**: NY State Open Data (public domain)
- **Coverage**: 62 counties × 17 seasons (2009-10 through 2025-26)
- **Reporting authority**: Mandatory laboratory reporting under NY Public Health Law §2.10
- **Accessed**: April 2026

#### Pennsylvania
- **Title**: Cumulative Influenza and RSV Case Counts by County 2025-2026 Respiratory Virus Season
- **Publisher**: Pennsylvania Department of Health
- **URL**: https://data.pa.gov/Health/Cumulative-Influenza-and-RSV-Case-Counts-by-County/mrpb-ugjv
- **API endpoint**: `https://data.pa.gov/resource/mrpb-ugjv.csv`
- **License**: PA Open Data
- **Coverage**: 67 counties × 1 season (2025-26 in progress)
- **Updates**: Weekly during flu season
- **Accessed**: April 2026

#### Connecticut
- **Title**: Connecticut Reportable Disease Case List with the County of Residence
- **Publisher**: Connecticut Department of Public Health
- **URL**: https://data.ct.gov/Health-and-Human-Services/Connecticut-Reportable-Disease-Case-List-with-the-/4rss-apm8
- **API endpoint**: `https://data.ct.gov/resource/4rss-apm8.csv`
- **License**: CT Open Data
- **Coverage**: 9 Planning Regions × 3 seasons (2022-23, 2023-24, 2024-25)
- **Geographic note**: Connecticut transitioned from 8 counties to 9 Planning Regions for Census purposes in 2022 (see Section 1.3 below)
- **Accessed**: April 2026

#### Delaware
- **Title**: Delaware Influenza Cases
- **Publisher**: Delaware Health and Social Services
- **URL**: https://data.delaware.gov/Health/Delaware-Influenza-Cases/46y5-s57v
- **API endpoint**: `https://data.delaware.gov/resource/46y5-s57v.csv`
- **License**: Delaware Open Data
- **Coverage**: 3 counties (Kent, New Castle, Sussex) × 6 seasons (2019-20 through 2025-26)
- **Accessed**: April 2026

### 1.2 Demographic Data

#### US Census Bureau — American Community Survey 5-Year Estimates
- **Title**: ACS 2022 5-Year Detailed Tables
- **Publisher**: US Census Bureau
- **URL**: https://www.census.gov/programs-surveys/acs/
- **API documentation**: https://www.census.gov/data/developers/data-sets/acs-5year.html
- **API endpoint**: `https://api.census.gov/data/2022/acs/acs5`
- **License**: Public domain (US federal government)
- **Variables used**: see `docs/data_dictionary.md` for full ACS variable codes
- **Accessed**: April 2026

#### US Census Bureau — 2022 Gazetteer Files (Land Area)
- **Title**: 2022 Gazetteer File: Counties
- **Publisher**: US Census Bureau, Geography Division
- **URL**: https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.2022.html
- **Direct download**: `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2022_Gazetteer/2022_Gaz_counties_national.zip`
- **License**: Public domain
- **Variables used**: GEOID (FIPS), ALAND_SQMI (land area in square miles)
- **Accessed**: April 2026

### 1.3 Geographic Reference Files

#### Connecticut Planning Regions (Post-2022)
- **Title**: Final Notice of Geographic Boundary Change — Connecticut Planning Regions
- **Publisher**: US Census Bureau / Office of Management and Budget
- **URL**: https://www.federalregister.gov/documents/2022/06/06/2022-12063/change-to-county-equivalents-in-the-state-of-connecticut-for-statistical-purposes
- **Notes**: Connecticut's 8 historical counties were replaced by 9 Census-recognised Planning Regions effective for ACS 2022 onwards. FIPS codes 09110-09190.

### 1.4 Sources Investigated and Excluded

The following sources were investigated but found unsuitable for our cross-sectional analysis:

| State / Source | Reason Excluded |
|---|---|
| California (CDPH Respiratory Virus Dashboard) | HHS region-level only, not county |
| Florida (FL FluReview) | State law does not require individual flu case reporting |
| Virginia (VDH PUD Influenza Labs) | State-level only; ED visits at health-district level (41), not county |
| Colorado (CDPHE) | Current data is statewide only; 2015-2019 county data is single static aggregate |
| Rhode Island | Open data portal Cloudflare-blocked |
| New Jersey, Maryland, Iowa, Utah, Maine, Vermont, NH, NM, NE, KS, OK, DC | No flu datasets at open data portals |
| Massachusetts, Michigan, Minnesota, Wisconsin, Texas, Ohio, Illinois | PDF-only or HHS-region-only surveillance |
| Louisiana, Missouri | Tableau dashboards without programmatic access |
| Germany RKI SurvStat (international) | Excluded due to incompatible surveillance definitions and demographic taxonomies; reserved for potential external validation analysis |

---

## 2. Methodological References

### 2.1 Panel Data Methodology

- Wooldridge, J. M. (2010). *Econometric Analysis of Cross Section and Panel Data* (2nd ed.). MIT Press.
- Allison, P. D. (2009). *Fixed Effects Regression Models*. SAGE Publications.

### 2.2 Spatial Epidemiology and Disease Mapping

- Wakefield, J. (2007). Disease mapping and spatial regression with count data. *Biostatistics*, 8(2), 158-183. https://doi.org/10.1093/biostatistics/kxl008
- Lemaitre, J. C., et al. (2018). Geographic origin and dynamics of influenza in the United States. *Proceedings of the National Academy of Sciences*, 115(7), 1564-1569.
- Reich, N. G., et al. (2019). Accuracy of real-time multi-model ensemble forecasts for seasonal influenza in the U.S. *PLoS Computational Biology*, 15(11).

### 2.3 Influenza Epidemiology

- CDC FluView Interactive — National Center for Immunization and Respiratory Diseases. https://www.cdc.gov/flu/weekly/
- CDC Influenza Hospitalization Surveillance Network (FluSurv-NET). https://www.cdc.gov/flu/weekly/influenza-hospitalization-surveillance.htm
- World Health Organization. Global Influenza Programme. https://www.who.int/teams/global-influenza-programme

### 2.4 Feature Selection Methods (Notebook 03)

- **LASSO regression**: Tibshirani, R. (1996). Regression shrinkage and selection via the lasso. *Journal of the Royal Statistical Society Series B*, 58(1), 267-288.
- **Recursive Feature Elimination**: Guyon, I., et al. (2002). Gene selection for cancer classification using support vector machines. *Machine Learning*, 46(1-3), 389-422.
- **Mutual Information**: Cover, T. M., & Thomas, J. A. (2006). *Elements of Information Theory* (2nd ed.). Wiley-Interscience.
- **Variance Inflation Factor**: O'Brien, R. M. (2007). A caution regarding rules of thumb for variance inflation factors. *Quality & Quantity*, 41(5), 673-690.
- **Permutation Importance**: Altmann, A., et al. (2010). Permutation importance: a corrected feature importance measure. *Bioinformatics*, 26(10), 1340-1347.

### 2.5 Machine Learning Models (Notebooks 04-08)

- **Logistic Regression**: Hosmer, D. W., Lemeshow, S., & Sturdivant, R. X. (2013). *Applied Logistic Regression* (3rd ed.). Wiley.
- **Random Forest**: Breiman, L. (2001). Random forests. *Machine Learning*, 45(1), 5-32.
- **Gradient Boosting**: Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 785-794.
- **K-Nearest Neighbors**: Cover, T., & Hart, P. (1967). Nearest neighbor pattern classification. *IEEE Transactions on Information Theory*, 13(1), 21-27.

### 2.6 Model Calibration and Evaluation

- **Probability calibration**: Niculescu-Mizil, A., & Caruana, R. (2005). Predicting good probabilities with supervised learning. *Proceedings of the 22nd International Conference on Machine Learning*, 625-632.
- **Brier score**: Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review*, 78(1), 1-3.
- **PR-AUC for imbalanced classes**: Saito, T., & Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. *PLOS ONE*, 10(3).

### 2.7 SIR Compartmental Model

- Kermack, W. O., & McKendrick, A. G. (1927). A contribution to the mathematical theory of epidemics. *Proceedings of the Royal Society A*, 115(772), 700-721.
- Anderson, R. M., & May, R. M. (1992). *Infectious Diseases of Humans: Dynamics and Control*. Oxford University Press.

### 2.8 Model Interpretability

- **SHAP values**: Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems*, 30.

---

## 3. Software and Libraries

### 3.1 Core Libraries

| Library | Version | Purpose | Citation |
|---|---|---|---|
| Python | 3.11+ | Programming language | https://www.python.org/ |
| pandas | 2.x | Data manipulation | McKinney, W. (2010). Data structures for statistical computing in Python. *Proceedings of the 9th Python in Science Conference*, 56-61. |
| NumPy | 1.x | Numerical computing | Harris, C. R., et al. (2020). Array programming with NumPy. *Nature*, 585(7825), 357-362. |
| scikit-learn | 1.x | Machine learning | Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research*, 12, 2825-2830. |
| Matplotlib | 3.x | Plotting | Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. *Computing in Science & Engineering*, 9(3), 90-95. |
| Seaborn | 0.13+ | Statistical visualisation | Waskom, M. L. (2021). seaborn: statistical data visualization. *Journal of Open Source Software*, 6(60), 3021. |

### 3.2 ML and Statistical Libraries

| Library | Purpose |
|---|---|
| XGBoost | Gradient boosting (Notebook 06) |
| statsmodels | Statistical inference, VIF |
| SHAP | Model interpretability |

### 3.3 Web and Visualisation (Notebooks 09+)

| Library | Purpose |
|---|---|
| Flask | Backend web framework |
| Folium | Interactive maps |
| Plotly | Interactive plots |

---

## 4. Project Internal Documents

| Document | Path | Purpose |
|---|---|---|
| Master Plan | `MASTER_PLAN.md` | Overall project architecture, timeline, team responsibilities |
| Data Dictionary | `docs/data_dictionary.md` | Definitions of all columns in `master_counties.csv` (auto-generated by Notebook 01) |
| README | `README.md` | Quick-start and notebook overview |

---

## 5. How to Cite This Project

If reproducing or extending this work, please cite as:

> Barraket, R., et al. (2026). *MODR: Mapping and Optimising Disease Response — A County-Level Influenza Vulnerability Model*. ENGG2112 Engineering Project, [University Name].

---

## 6. Acknowledgements

- US Census Bureau for free public ACS API access
- New York State, Pennsylvania, Connecticut, and Delaware Departments of Health for public county-level surveillance data
- Anthropic Claude for AI-assisted development
