# Project Journal — MODR

> **Purpose**: A chronological record of the project's development — what we tried, what failed, what we learned, what we decided. This is the document to read when writing the methodology section of the final report or onboarding a new team member.

> **For**: ENGG2112 supervisors, examiners, future maintainers
> **By**: Roc Barraket (with AI development assistance from Anthropic Claude)

---

## How to use this document

- **Sessions** are dated phases of work. Each session has a goal, what we tried, what we learned, and the decision that came out of it.
- **Decisions** are bolded — these are the choices that shaped the project's direction.
- **Dead ends** are kept here intentionally. They show methodological rigour: we considered alternatives and rejected them for stated reasons.
- **Citations** point to `REFERENCES.md` for academic sources and to specific commits / notebooks for implementation details.

---

## Session 1 — Initial Setup with Sydney SA2 Data

**Date**: March 2026
**Goal**: Build a flu vulnerability prediction model using Australian census + flu surveillance data, anchored in Sydney suburbs (SA2 level, ~550 areas).

### What we did
- Set up project scaffolding, GitHub repo, master plan
- Downloaded ABS 2021 Census data at SA2 level (population, age, income, employment)
- Downloaded NNDSS national flu surveillance data
- Built initial data exploration notebook merging the two

### What we found
The fundamental data sources didn't align geographically:
- ABS Census: SA2 level (~550 NSW suburbs)
- NNDSS flu data: **state level only** (not SA2)

### The hack we tried
We tried "age-weighted apportionment" — distribute state-level flu cases down to SA2s in proportion to each SA2's age distribution.

### Why we abandoned it
Identified a **critical methodological flaw**: we were using age structure to *manufacture* outcome labels and then using age as a *predictor*. This is circular logic — the model would inevitably "discover" age as a top predictor because we'd encoded that relationship into the labels.

### Decision
**Abandon the Australian data pipeline. Find a country/region where flu cases and demographics exist at the same geographic granularity, with no apportionment hack required.**

---

## Session 2 — Search for Geographically Aligned Data

**Date**: April 2026
**Goal**: Find a flu surveillance dataset matched to a fine-grained demographic dataset.

### Candidates investigated

| Region | Flu data granularity | Demographic granularity | Verdict |
|---|---|---|---|
| **United Kingdom** | UKHSA mostly state-equivalent (PHE region) | MSOA (~7,000 areas) | ❌ Granularity mismatch; mostly COVID data |
| **Germany** | RKI SurvStat at Landkreis (~400 districts) | Destatis at Landkreis | ✅ Aligned — but feature taxonomy mismatch with US Census |
| **United States** | Varies by state | County (FIPS) — universally available | ⚠️ Most states publish only state-level; some publish county-level |
| **France** | Sentinelles (clinical not lab-confirmed) | INSEE communes | ❌ Different surveillance method |

### Why we picked the US
- US Census ACS provides consistent county-level demographics for all 50 states via free public API
- Some states publish county-level lab-confirmed flu (the question was *which* states)
- Stays in English with no translation issues
- Familiar education/income/race taxonomy (no German Hauptschule-vs-American-bachelor headache)

### Decision
**Pivot from Australian SA2 to US county-level analysis. Start by investigating which US states publish county-level flu data.**

---

## Session 3 — New York State as a Beachhead

**Date**: April 24-25, 2026
**Goal**: Build the pipeline using New York data and verify it works end-to-end.

### What we got
- NY State Department of Health publishes lab-confirmed influenza cases by county since 2009-10 season
- 62 NY counties × 17 flu seasons = 1,054 raw observations
- Census ACS provides matching county demographics

### What we built
A complete monolithic notebook (`01_data_exploration.ipynb`) doing data loading → feature engineering → outbreak labelling → linear regression + logistic regression on **a single 2024-25 season cross-section** (62 counties).

### Results
- Linear regression test R² = **−0.891** (worse than predicting the mean!)
- Logistic regression accuracy = **62.5%** (worse than the 75% majority baseline)
- ROC AUC = **0.583** (barely above random)

### Diagnosis
**Severe overfitting**: 15 features fitted on 62 observations (4:1 ratio). Rule of thumb requires 10–20 obs per feature minimum.

### Decision
**The pipeline works; the sample size doesn't. Either reduce features or increase sample size. We choose to expand the dataset.**

---

## Session 4 — Methodology Debate: Panel vs Multi-State

**Date**: April 29, 2026
**Goal**: Decide how to expand the sample size while preserving methodological cleanliness.

### Options considered

#### Option A: Temporal panel (one state, many seasons)
Use NY's 17 seasons × 62 counties = 1,032 observations.
- ✅ No new data acquisition
- ❌ **Pseudo-replication**: same county appears 17 times with nearly identical demographics. Effective sample size is closer to 62 than 1,032 because the within-county observations aren't truly independent.

#### Option B: Multi-state cross-section
Combine multiple US states each providing one season's worth of county data.
- ✅ Genuine independent observations
- ✅ Geographic diversity
- ❌ Many states don't publish county-level flu data; acquisition is harder
- ❌ Cross-state surveillance differences (testing rates, reporting practices)

#### Option C: International expansion
Pull German RKI Landkreis data (~400 districts).
- ✅ Large sample size
- ❌ **Surveillance + demographic taxonomy incompatibility**. Pooling US + German data introduces ecological fallacy at country scale.

#### Option D: Hybrid (cross-section primary, panel sensitivity)
Get multi-state cross-section as primary analysis. Use NY temporal panel as a separate sensitivity check.

### Decision
**Pursue Option D (hybrid). Cross-state expansion as primary, NY temporal panel as sensitivity. International data reserved for optional external validation if time permits.**

---

## Session 5 — State-by-State Hunt for County Flu Data

**Date**: April 29-30, 2026
**Goal**: Identify every US state publishing public county-level flu data via API.

### Strategy
Programmatically test each state's open data portal. Don't trust descriptions or research-agent claims — verify granularity by hitting the actual API and counting unique geographic values.

### What we found

| State | Outcome | Evidence |
|---|---|---|
| **NY** | ✅ County-level | 62 counties × 17 seasons confirmed via API |
| **PA** | ✅ County-level | 67 counties via Socrata API (`mrpb-ugjv`) |
| **CT** | ✅ Planning regions | 9 planning regions via Socrata API (`4rss-apm8`) |
| **DE** | ✅ County-level | 3 counties + 6 seasons via Socrata API (`46y5-s57v`) |
| **CA** | ❌ State / HHS region only | CHHS dataset explicitly excludes influenza |
| **FL** | ❌ Not reported | Florida law doesn't require flu case reporting |
| **VA** | ❌ Health district level | API confirmed `County FIPS` column is empty |
| **CO** | ❌ Statewide totals | All current data has `level_=ALL` |
| **RI** | ❌ Cloudflare-blocked | No API access |
| **NJ, MD, IA, UT, ME, VT, NH, NM, NE, KS, OK, DC** | ❌ No flu datasets | Empty Socrata catalog searches |
| **TX, OH, IL, MI, MN, MA, WI** | ❌ PDF-only | Surveillance reports only |
| **LA, MO** | ❌ Tableau dashboards | No programmatic access |

### Surprising findings
- **Connecticut transitioned from 8 counties to 9 planning regions in 2022** for Census purposes. The CT health data conveniently includes both old county FIPS *and* new planning region FIPS in the same row. We use planning regions to match ACS 2022.
- **Earlier research agents claimed VA and CO had county-level data** — they didn't. Always verify granularity programmatically, not from descriptions.

### Decision
**Final cross-section: NY (62) + PA (67) + CT (9) + DE (3) = 141 areas. This is the maximum US sample size obtainable via public APIs.**

---

## Session 6 — Methodology: Outbreak Labelling

**Date**: April 30, 2026
**Goal**: Decide how to construct the binary outbreak label for the model.

### Considered options

#### Pooled labelling
Top 25% of all 141 areas combined.
- Problem: cross-state surveillance differences confound. PA's "cumulative cases per 100K" is not directly comparable to NY's "lab-confirmed cases per 100K". Pooling treats them as if they are.

#### Within-state labelling
Top 25% within each state separately.
- Sidesteps surveillance bias
- Asks: *"Among NY counties, which had relatively worse flu burden? Among PA counties, which had relatively worse flu burden?"* — separately
- The model learns: *"What demographic profile makes a county relatively vulnerable within its state's flu surveillance regime?"*

#### Absolute threshold
Outbreak = >X cases per 100K (where X is some absolute threshold).
- Cleaner academically but every state would have a different "outbreak rate"
- Sensitive to overall season severity (mild years would have ~0 outbreaks; bad years would have many)

### Decision
**Within-state labelling. Add `state` as a categorical feature so the model can implicitly learn state-level baseline differences.**

---

## Session 7 — Methodology: Cross-Section vs Weekly Granularity

**Date**: April 30, 2026
**Goal**: Decide the time-aggregation level for the model.

### Considered: weekly granularity
141 areas × ~33 weeks per season = ~4,650 rows.

### Why we rejected it
1. **Wrong unit of analysis**: SIR simulation needs *one* P(outbreak) per county, not per week
2. **Pseudo-replication × 33**: same county appears 33 times per season with constant demographics
3. **Severe class imbalance**: most weeks have ~0 cases (off-season)
4. **Frontend mismatch**: the visualisation has a county dimension, not a weekly one

### What we kept from weekly data
We compute **per-season metrics from the underlying weekly data** as engineered features:
- `peak_week_cases` — outbreak intensity
- `weeks_active` — outbreak duration
- `time_to_peak` — outbreak speed (NEW)
- `outbreak_steepness` = peak / time_to_peak — climb rate (NEW)

### Decision
**Seasonal granularity for the model row, but engineer outbreak-dynamics features from underlying weekly data.**

---

## Session 8 — Building the Master DataFrame

**Date**: May 1, 2026
**Goal**: Merge all sources into the canonical analytical dataset.

### What got built

#### `notebooks/00_data_acquisition.ipynb`
- NY: 1,032 panel observations (62 × 17 seasons)
- PA: 67 obs (1 season — only available)
- CT: 27 obs (9 planning regions × 3 seasons)
- DE: 18 obs (3 counties × 6 seasons)
- ACS demographics for all 141 areas
- Census Gazetteer for land area

#### `notebooks/01_master_dataframe.ipynb`
- Merges flu + demographics + land area on FIPS
- Engineers 11 rate-based features (density, % elderly, poverty rate, public transit %, etc.)
- Computes outbreak label (within-state top 25%)
- Outputs:
  - `master_counties.csv` (141 × 38) — primary cross-section
  - `master_panel.csv` (1,144 × 38) — panel for sensitivity

#### `docs/data_dictionary.md`
Auto-generated column reference documenting every variable's formula and ACS source code.

#### `REFERENCES.md`
Comprehensive citations for all data sources, methodology references (LASSO, RF, XGBoost, SIR), software libraries.

### Validation
- All 141 FIPS codes match between flu data, ACS, and land area files
- Zero missing values in features or target
- All ranges sensible (population 2.5K to 2.6M, density 3 to 37,000 per sq mi)

### Decision
**Master dataset is locked. All downstream notebooks (02 onwards) consume `master_counties.csv` as the canonical input.**

---

## Session 9 — Exploratory Data Analysis (Current)

**Date**: May 1, 2026 →
**Goal**: Explore distributions, validate the outbreak label, identify multicollinearity, generate insights for feature selection.

### Notebook 02 covers
1. Univariate distributions of features and outcomes
2. Outbreak label validation (does it look sensible per state?)
3. Bivariate analysis: features vs flu rate, features vs outbreak label
4. Correlation matrix + multicollinearity check
5. Geographic patterns
6. Outlier identification
7. State-level differences

### Findings
*(To be filled in once Notebook 02 runs)*

---

## Upcoming Work

### Session 10 — Feature Selection (Notebook 03)
Multi-method consensus across:
- Pearson + Spearman correlation
- Mutual information
- VIF (multicollinearity)
- LASSO with CV
- Random Forest permutation importance
- Recursive Feature Elimination with CV

Final feature list = features appearing in top-K of ≥3 methods, plus domain-required features (`vax_rate` proxy + mobility) for policy-lever support in the frontend.

### Session 11 — Model Comparison (Notebooks 04-08)
Train and tune four models with the same cross-validation setup:
- Logistic regression (interpretable baseline)
- Random Forest (non-linear, robust)
- XGBoost (often best on tabular)
- KNN (non-parametric)

Headline metric: **PR-AUC** (handles class imbalance better than ROC-AUC).
Tie-breaker: calibration (Brier score, calibration curve).

### Session 12 — SIR Simulation (Notebook 09)
Compartmental Susceptible-Infected-Recovered model with predicted P(outbreak) modulating the transmission rate β per county. County adjacency for inter-county transmission. Policy levers shift β (mobility) and the susceptible pool (vaccination).

### Session 13 — Web Frontend
Flask backend serves model predictions + simulation outputs. JavaScript frontend renders county map (folium / leaflet), policy sliders, animated outbreak progression.

### Session 14 — Report Writing + Demo
Methodology section draws heavily on this journal. Demo shows the live tool with policy interventions.

---

## Key Methodological Themes

These run through the project:

1. **Verify, don't trust**: every dataset claim was tested by hitting the API and counting unique geographic values. Multiple research agents claimed states had county-level data when they didn't.

2. **Cleaner is better than bigger**: we rejected international pooling (would have been ~500 extra obs) because the surveillance / taxonomy mismatch would have introduced more noise than signal. 141 clean obs > 600 noisy obs.

3. **Acknowledge limitations**: cross-state surveillance differences are real and confound naive comparisons. Within-state labelling makes these limitations explicit and tractable.

4. **Rate-based features always**: every feature is normalised by an appropriate denominator (population, labour force, commuters, housing units). Otherwise large urban areas would always look "high" on every count metric.

5. **Reproducibility**: every dataset is regeneratable from APIs by Notebook 00. The processed master CSVs are versioned in git so collaborators don't have to re-run.

---

## What I'd Do Differently With Hindsight

- **Start with multi-state US**, not Sydney SA2. Would have saved 1-2 weeks of pipeline work.
- **Verify research-agent claims earlier**. Spent ~half a session chasing CA/FL/VA/CO before testing them directly.
- **Build the master dataframe before doing detailed exploration**. The original monolithic notebook conflated acquisition, merging, EDA, and modelling — making it hard to iterate.

---

## How to Cite This Work

> Barraket, R., et al. (2026). *MODR: Mapping and Optimising Disease Response — A County-Level Influenza Vulnerability Model*. ENGG2112 Engineering Project. https://github.com/r0cb/ENGG2112

---

*This journal is updated at the end of each major work session. See git log for granular history.*
