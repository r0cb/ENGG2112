# Master Plan — Project MODR

> **Project**: Mapping and Optimising Disease Response (MODR)
> **Course**: ENGG2112 — Engineering Project
> **Team**: 1 software engineer + 3 biomedical engineers
> **Last updated**: May 2026

This document defines the **scope, architecture, and overall plan** of the project. Implementation details live in the notebooks; data source attribution lives in `REFERENCES.md`; the iterative decision history lives in `PROJECT_JOURNAL.md`.

---

## 1. Project Goal

Build a machine-learning model that predicts **county-level seasonal influenza vulnerability** across US states, then expose those predictions through an interactive web tool that simulates outbreak progression and allows users to test policy interventions (vaccination uptake, mobility restrictions).

### Why it matters
Influenza causes 12,000–52,000 US deaths annually with significant geographic heterogeneity. Public health resources are scarce, so identifying which areas are most vulnerable — and how policy levers shift outcomes — directly informs intervention prioritisation.

---

## 2. Scope

### Geographic
**141 US areas across 4 states**:
- New York: 62 counties
- Pennsylvania: 67 counties
- Connecticut: 9 planning regions
- Delaware: 3 counties

These are the only US states publishing public county-level lab-confirmed influenza data via API. Adding more states would require manual scraping of PDFs or non-public dashboards.

### Temporal
- **Cross-section**: most recent complete season per state (NY/CT/DE 2024-25, PA 2025-26)
- **Panel** (sensitivity): all available seasons per state, 1,144 observations across 17 seasons total

### Disease
Seasonal influenza only. COVID-19 explicitly excluded (no longer reflective of current real-world dynamics).

### Out of scope
- Predicting absolute case counts (we predict relative vulnerability within state)
- Real-time surveillance / forecasting (we model retrospective patterns)
- International data (reserved for optional external validation)

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  DATA SOURCES                                                        │
│  • State DOH (NY/PA/CT/DE) → flu cases by FIPS                       │
│  • US Census ACS 2022 → demographic features by FIPS                 │
│  • Census Gazetteer → land area for density                          │
└────────────────────┬─────────────────────────────────────────────────┘
                     │  Notebook 00 (acquisition)
                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│  MASTER DATAFRAME (Notebook 01)                                      │
│  • master_counties.csv: 141 areas × 38 cols                          │
│  • master_panel.csv:    1,144 obs × 38 cols                          │
│  • Outbreak label: top 25% within state by per-capita rate           │
└────────────────────┬─────────────────────────────────────────────────┘
                     │  Notebooks 02–03 (EDA + feature selection)
                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│  ML MODELLING (Notebooks 04–08)                                      │
│  Train + tune 4 candidate models with stratified 5-fold CV:          │
│  • Logistic Regression  (interpretable baseline)                     │
│  • Random Forest        (non-linear, robust)                         │
│  • Gradient Boosting    (XGBoost, often best on tabular)             │
│  • K-Nearest Neighbours (non-parametric)                             │
│  Compare on PR-AUC + calibration. Export winning model as `.pkl`.    │
└────────────────────┬─────────────────────────────────────────────────┘
                     │  P(outbreak) per area
                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│  SIR SIMULATION (Notebook 09)                                        │
│  Compartmental model with predicted P(outbreak) modifying β per      │
│  county. Spatial adjacency for inter-county transmission.            │
└────────────────────┬─────────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│  WEB FRONTEND (src/)                                                 │
│  Flask backend serves model predictions. JS frontend renders         │
│  county map + policy sliders + animated outbreak progression.        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Model

### Outcome (target variable)
- `outbreak`: binary label, 1 = top 25% of areas within the same state by `flu_rate_per_100k`

### Continuous outcome (for sensitivity)
- `flu_rate_per_100k`: total cases per 100,000 population during the season

### Predictor features (11 candidates)
All expressed as **rates / percentages** so they are comparable across areas of different size:

| Feature | Source |
|---|---|
| Population density (per sq mi) | Census ACS + Gazetteer |
| Median age | ACS B01002 |
| % elderly (65+) | ACS B01001 |
| Average household size | ACS B25010 |
| Median household income | ACS B19013 |
| Poverty rate | ACS B17001 |
| Unemployment rate | ACS B23025 |
| Public transport % of commuters | ACS B08301 |
| % bachelors+ degree | ACS B15003 |
| % non-white | ACS B02001 |
| % foreign-born | ACS B05002 |

Notebook 03 reduces this to ~5–7 features via multi-method feature selection consensus.

### Within-state outbreak labelling — methodology note
We label outbreak as top 25% **within each state** rather than pooled across states because absolute case counts are not directly comparable across states (different testing rates, different reporting practices). This sidesteps the cross-state surveillance bias. Documented in `docs/data_dictionary.md`.

---

## 5. Notebook Pipeline

| # | Notebook | Purpose | Status |
|---|---|---|---|
| 00 | `00_data_acquisition.ipynb` | Download + clean per-source flu + demographics CSVs | ✅ Done |
| 01 | `01_master_dataframe.ipynb` | Merge sources → master_counties.csv + master_panel.csv | ✅ Done |
| 02 | `02_eda.ipynb` | Distributions, correlations, geographic patterns, label validation | 🔄 In progress |
| 03 | `03_feature_selection.ipynb` | Multi-method consensus (filter + LASSO + RF + RFECV + VIF) | ⏳ Pending |
| 04 | `04_model_logistic.ipynb` | Logistic regression (baseline + interpretable) | ⏳ Pending |
| 05 | `05_model_random_forest.ipynb` | Random Forest with hyperparameter tuning | ⏳ Pending |
| 06 | `06_model_gradient_boosting.ipynb` | XGBoost or HistGradientBoosting | ⏳ Pending |
| 07 | `07_model_knn.ipynb` | K-Nearest Neighbors baseline | ⏳ Pending |
| 08 | `08_model_comparison.ipynb` | Side-by-side metrics, calibration, pick winner | ⏳ Pending |
| 09 | `09_sir_simulation.ipynb` | SIR compartmental model coupled to ML predictions | ⏳ Pending |

---

## 6. Methodology Decisions

These decisions are documented in detail in `PROJECT_JOURNAL.md`.

| Decision | Choice | Rationale |
|---|---|---|
| Geography | County-level US | Only granularity where flu cases align with demographics |
| States | NY+PA+CT+DE | Only states with public county-level flu APIs |
| Outcome | Binary outbreak (top 25% within state) | Sidesteps cross-state surveillance bias |
| Sample design | Cross-section primary, panel sensitivity | Cleaner statistical inference |
| Feature granularity | Seasonal aggregates with engineered dynamics | Matches model output unit (county vulnerability) |
| Model selection | PR-AUC headline + calibration tie-break | Better than ROC-AUC under class imbalance |
| Class imbalance | `class_weight='balanced'` | 25% positive class |
| Cross-validation | StratifiedGroupKFold for panel, Stratified for cross-section | Prevents county leakage in panel |
| International data | Excluded from pooling | Surveillance / demographic incompatibility |

---

## 7. Timeline (8 weeks)

| Week | Milestone |
|---|---|
| 1 | Data acquisition + master DF (Notebooks 00-01) — **complete** |
| 2 | EDA + feature selection (Notebooks 02-03) — **current** |
| 3-4 | Train all 4 ML models (Notebooks 04-07) |
| 5 | Model comparison + winner selection (Notebook 08) |
| 6 | SIR simulation (Notebook 09) |
| 7 | Flask backend + JS frontend |
| 8 | Polish + report writing + presentation prep |

**Slack week** built into Week 8 in case any earlier phase runs over.

---

## 8. Team Roles

| Member | Primary responsibility |
|---|---|
| Software Engineer | Notebooks pipeline, frontend implementation, GitHub workflow, deployment |
| Biomed 1 | Data sources / surveillance methodology, feature interpretation |
| Biomed 2 | SIR model parameters, epidemiological validation |
| Biomed 3 | Report writing, presentation, methodological soundness review |

Cross-functional: All members review feature selection and final model choice.

---

## 9. Deliverables

| Deliverable | Form |
|---|---|
| **Working web tool** | Locally hosted Flask + JS app with county map, policy sliders, animated SIR sim |
| **Final report** | Methodology, results, interpretation, limitations |
| **Presentation** | Live demo + slides |
| **GitHub repository** | All code, data pipelines, processed datasets, documentation |

---

## 10. Limitations & Caveats

To be acknowledged transparently in the final report:

1. **Cross-state surveillance differences**: NY, PA, CT, DE have different reporting practices. Mitigated by within-state labelling.
2. **Single ACS snapshot**: Demographics from 2022 used for all seasons. Demographics shift slowly so this is acceptable but should be noted.
3. **Connecticut Planning Regions**: CT changed from counties to planning regions in 2022. We use planning regions to match ACS, slightly different geography from CT's pre-2022 papers.
4. **Pennsylvania single season**: PA only publishes the current season. Cannot validate stability of PA's contribution across multiple seasons.
5. **Modest sample size**: 141 areas requires careful regularisation. Panel sensitivity analysis (1,144 obs) provides robustness check.
6. **Generalisation outside the 4 states**: Model trained on mid-Atlantic / Northeast US may not generalise to South or Mountain West.

---

## 11. References

See `REFERENCES.md` for complete data source attribution, methodology citations, and software bibliography.

See `PROJECT_JOURNAL.md` for the iterative development history and decision rationale.

See `docs/data_dictionary.md` for column-by-column documentation of `master_counties.csv`.
