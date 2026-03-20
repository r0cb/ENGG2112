# MASTER PLAN — ENGG2112 Flu Spread Simulation

> **How to use this document:** Paste the contents of this file at the start of any AI chat (Claude, Copilot, ChatGPT) to give the model full project context before asking it for help. Keep it up to date as the project evolves.

---

## 1. Project Overview

**Title:** Disease Spread Prediction Model Across Population Centres
**Course:** ENGG2112
**Disease:** Influenza (seasonal flu)
**Anchor city:** Sydney, Australia (SA2-level suburbs)

### Problem Statement
Influenza spreads unevenly across urban populations — high-density, elderly, low-vaccination suburbs experience disproportionate outbreaks. We want a tool that (a) predicts which suburbs are most vulnerable using demographic ML, and (b) simulates how an outbreak would progress through the city over time, and (c) lets a user tweak policy variables (vaccination rate, mobility restrictions) to see how interventions reduce spread.

### End Goal
A locally hosted website that:
- Displays a 50×50 animated suburb grid coloured by infection percentage
- Shows per-cluster infection stats on hover
- Provides sliders for vaccination rate and commuter restriction per cluster
- Outputs peak infection %, days to peak, and estimated lives affected vs baseline

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  DATA SOURCES                                                   │
│  ABS SA2 Census → age, income, density                         │
│  ABS Journey to Work → commuter flows between SA2s             │
│  NSW Health flu surveillance → ILI rates by region/season      │
│  NCIRS vaccination reports → flu vax coverage by age group     │
└───────────────────┬─────────────────────────────────────────────┘
                    │ merge on SA2 code
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  DATA PREPROCESSING  (pandas / Jupyter)                        │
│  Normalise features, create outbreak label (ILI > 5% = 1)     │
└───────────────────┬─────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  ML MODEL  (scikit-learn)                                       │
│  Input:  median_age, pct_elderly, median_income,               │
│          pop_density, vax_rate, commuter_flow_score            │
│  Output: spreadability_score (0–1) = predict_proba()          │
│          outbreak_binary (0/1)    = predict()                  │
│  Model:  Logistic Regression (start) → Random Forest (v2)     │
└───────────────────┬─────────────────────────────────────────────┘
                    │ spreadability_score → β per cell
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  SIR SIMULATION  (Python)                                       │
│  Grid: 2D array of SA2 clusters (~50–80 Sydney suburbs)        │
│  Each cell: S, I, R compartments                               │
│  β = spreadability_score × β_max                               │
│  γ = 1/7 (flu recovery ~7 days)                                │
│  Inter-cluster spread: weighted by commuter flow               │
│  Trigger: if I/N > 2% → seed neighbours                       │
│  Policy levers:                                                 │
│    - vax_rate slider → recompute spreadability_score via ML    │
│    - commuter_restriction (0–1) → multiply inter-cluster prob  │
└───────────────────┬─────────────────────────────────────────────┘
                    │ time-step JSON
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  WEB FRONTEND  (Flask + JavaScript)                             │
│  Animated 50×50 grid — cells coloured by infection %          │
│  Per-cluster stats panel on hover                              │
│  Policy sliders: vaccination rate, commuter restriction        │
│  Run simulation button → calls Flask API                       │
│  Results panel: peak %, days to peak, lives affected           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Sources

All datasets are free and publicly available. The **join key** across all ABS datasets is the **SA2 code** (a 9-digit ABS geographic identifier for Sydney suburbs).

| Dataset | Source | Direct URL | Format | Geographic level | Key columns |
|---|---|---|---|---|---|
| SA2 Demographics (age, income, density) | ABS 2021 Census — DataPacks | https://www.abs.gov.au/census/find-census-data/datapacks | ZIP → CSV | SA2 | `sa2_code`, `median_age`, `pct_65_plus`, `median_household_income`, `pop_density` |
| Commuter flows | ABS 2021 Census — DataPacks (Working Population Profile) | https://www.abs.gov.au/census/find-census-data/datapacks | ZIP → CSV | SA2 / DZN | `origin_sa2`, `destination_sa2`, `commuter_count` |
| Flu ILI rates | NNDSS Public Dataset (influenza) — 2008–2024 | https://www.cdc.gov.au/resources/publications/nndss-dataset-influenza | Excel (46 MB) | State → LHD | `region`, `season`, `ili_rate_pct` |
| Vaccination coverage | NCIRS — Influenza Vaccination Coverage Data | https://ncirs.org.au/influenza-vaccination-coverage-data | Web table + PDF | State (NSW), by age group | `age_group`, `state`, `vax_coverage_pct` |

**Download instructions:**
1. **ABS DataPacks** → Select "2021" → "General Community Profile" → geography "SA2" → filter to NSW → download ZIP → extract CSVs into `data/raw/abs_sa2_demographics/`
2. **ABS Journey to Work** → Same DataPacks portal → select "Working Population Profile" → SA2 level → NSW → extract into `data/raw/abs_journey_to_work/`
3. **NNDSS influenza Excel** → Download from the URL above (free, no login) → save to `data/raw/nndss_influenza.xlsx`
4. **NCIRS vaccination** → Visit URL above → copy table data for NSW by age group into `data/raw/ncirs_vaccination_coverage.csv`

**Note on ILI geographic granularity:** The NNDSS data is at state level; NSW Health reports are by Local Health District (LHD). You will need to map LHD → SA2 using the ABS correspondence tables (available at abs.gov.au → Statistical Geography). This mapping is done in `notebooks/01_data_exploration.ipynb` Section 2.

---

## 4. ML Model Specification

### Features (per SA2 suburb)
| Feature | Description | Source |
|---|---|---|
| `median_age` | Median age of residents | ABS Census |
| `pct_elderly` | % of population aged 65+ | ABS Census |
| `median_income` | Median weekly household income | ABS Census |
| `pop_density` | Population per km² | ABS Census |
| `vax_rate` | Flu vaccination coverage (weighted by age group) | NCIRS |
| `commuter_flow_score` | Outbound commuters / total population | ABS Journey to Work |

### Label
`outbreak` = 1 if ILI rate exceeded **5%** in any week of a season, else 0.
This threshold is adjustable — defined in `notebooks/01_data_exploration.ipynb` Section 6.

### Training approach
1. **Logistic Regression** (Phase 2, Weeks 3–4) — interpretable baseline, `predict_proba()` output used directly as `spreadability_score`
2. **Random Forest** (Phase 2 extension) — compare accuracy, feature importance plot
3. Evaluation: accuracy, precision, recall, AUC-ROC on 20% held-out test set

### Key scikit-learn calls
```python
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score

# spreadability_score = model.predict_proba(X)[:, 1]
# outbreak_binary     = model.predict(X)
```

---

## 5. SIR Simulation Specification

### Compartments (per grid cell per time step)
- **S** — Susceptible (not yet infected)
- **I** — Infected (currently infectious)
- **R** — Recovered (immune for season)

### Update equations (discrete, daily time steps)
```
new_infections = β × S × (I / N)
new_recoveries = γ × I

S(t+1) = S(t) - new_infections
I(t+1) = I(t) + new_infections - new_recoveries
R(t+1) = R(t) + new_recoveries
```

### Parameter derivation
- `β` (transmission rate per cell) = `spreadability_score × β_max` where `β_max ≈ 0.5` (tunable)
- `γ` (recovery rate) = `1/7` (average flu infectious period = 7 days)
- `R0` implied = `β / γ` — should be ~1.2–1.4 for seasonal flu

### Inter-cluster spread
At each time step, if `I/N > 0.02` (2% threshold):
```
spread_prob = commuter_flow_fraction × (1 - commuter_restriction) × I/N
```
Each adjacent cluster receives a seeding proportion of new infections weighted by this probability.

### Policy levers (user-controlled)
| Lever | Effect |
|---|---|
| `vax_rate` slider (per cluster) | Re-runs ML model with updated vax_rate → new spreadability_score → new β |
| `commuter_restriction` (0.0–1.0) | Multiplies inter-cluster spread_prob by `(1 - restriction)` |

---

## 6. Eight-Week Timeline & Task Assignments

### Phase 1 — Foundation & Data (Weeks 1–2)
| Owner | Task |
|---|---|
| **SOFTWARE** | Set up GitHub repo, Kanban board (GitHub Projects), shared Jupyter environment |
| **BIOMEDICAL 1** | Download ABS SA2 Census data — age, income, population density for Sydney |
| **BIOMEDICAL 2** | Source NSW Health flu surveillance data + ABS flu vaccination rates |
| **BIOMEDICAL 3** | Source ABS Journey to Work commuter flow data between SA2 regions |
| **WHOLE TEAM** | Agree on SA2 region subset (~50–80 Sydney suburbs), define outbreak label threshold, merge all datasets on SA2 code |

### Phase 2 — ML Model (Weeks 3–4)
| Owner | Task |
|---|---|
| **BIOMEDICAL 1** | EDA notebook — distributions, correlations, feature visualisations |
| **BIOMEDICAL 2** | Feature engineering — normalise, encode, build train/test split |
| **BIOMEDICAL 3** | Train logistic regression — evaluate accuracy, precision, recall, AUC |
| **SOFTWARE** | Wrap trained model as callable Python function: demographics in → spreadability_score + binary out |
| **WHOLE TEAM** | Model review — interpret coefficients, validate biomedical intuition (older + unvaccinated = higher score?) |

### Phase 3 — SIR Simulation (Weeks 5–6)
| Owner | Task |
|---|---|
| **BIOMEDICAL 2+3** | Implement SIR model — β per cell derived from spreadability score, γ from flu recovery literature (~7 days) |
| **SOFTWARE** | Build grid engine — 2D array of SA2 clusters, time-step loop, commuter-weighted inter-cluster spread |
| **BIOMEDICAL 1** | Validate simulation against known 2019 Sydney flu season data — does spread pattern roughly match? |
| **SOFTWARE** | Add policy lever hooks — vaccination rate and commuter multiplier per cluster as adjustable inputs |

### Phase 4 — Frontend & Polish (Weeks 7–8)
| Owner | Task |
|---|---|
| **SOFTWARE** | Build Flask API — endpoints for running simulation, adjusting levers, returning time-step data as JSON |
| **SOFTWARE** | Build grid visualisation — animated colour-coded grid, per-cluster infection % on hover |
| **BIOMEDICAL 2+3** | Write results panel — peak infection %, days to peak, estimated lives affected, comparison vs baseline |
| **BIOMEDICAL 1** | Build policy panel UI — vaccination sliders per zone, commuter restriction toggle, "run simulation" button |
| **WHOLE TEAM** | End-to-end testing, report writing, final demo prep — focus on 2–3 compelling "what-if" scenarios |

---

## 7. Compelling Demo Scenarios (for report conclusions)

Run these three side-by-side to make the policy argument:
1. **Baseline** — Sydney 2019 flu season, no intervention
2. **Targeted vaccination** — boost vax rate by 20% in the 5 highest-spreadability clusters only
3. **Early mobility restriction** — 50% commuter restriction starting at day 7 of outbreak

Report output for each: peak infection %, days to peak, total infected proportion.

---

## 8. Coding Conventions

- **Python version:** 3.11
- **Key libraries:** `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `seaborn`, `flask`
- **Notebooks:** one notebook per phase, numbered `01_`, `02_`, `03_`
- **Source modules:** reusable functions go in `src/` as `.py` files, imported into notebooks
- **Data paths:** always relative to repo root, e.g. `data/raw/abs_sa2_demographics.csv`
- **Git:** commit after each working milestone; use branch per feature; PR to main with one reviewer

---

## 9. Team Git Workflow

### The weekly cycle
```
Start of week                              End of week (team meeting)
     │                                            │
     ▼                                            ▼
git pull origin main          ─────────►  open PR → team reviews → merge to main
     │                                            ▲
     ▼                                            │
git checkout -b yourname/week-N-feature           │
     │                                            │
     │  (do your work)                            │
     ▼                                            │
git push origin yourname/week-N-feature  ─────────┘
```

### Week-by-week commands

**Start of every week — pull latest main and create your branch:**
```bash
git checkout main
git pull origin main
git checkout -b yourname/week-N-what-you-are-doing
# e.g. git checkout -b roc/week1-repo-setup
# e.g. git checkout -b alice/week2-abs-demographics
```

**While working — commit often:**
```bash
git add notebooks/01_data_exploration.ipynb   # add specific files, not git add .
git commit -m "short description of what you did"
git push origin yourname/week-N-what-you-are-doing
```

**End of week — open a Pull Request for the team to review at the meeting:**
```bash
gh pr create --title "Week N: [your name] — what you did" --body "Summary of changes"
# Or open it on github.com/r0cb/ENGG2112/pulls
```

**At the meeting — team reviews, discusses, then merges the PRs you agree on:**
```bash
# After approval on GitHub:
gh pr merge <PR-number> --merge
```

### Branch naming convention
`yourname/week-N-short-description`
- `roc/week1-repo-setup`
- `alice/week2-abs-demographics`
- `ben/week3-logistic-regression`
- `sarah/week4-sir-model`

### Rules
- **Never commit directly to `main`** — always work on a branch
- **Never commit files in `data/`** — they are gitignored; share data via Google Drive or a shared folder
- **One notebook edit per branch** — avoids merge conflicts in `.ipynb` files
- If you get a merge conflict, ask the software student (Roc) to resolve it

---

## 10. Glossary

| Term | Definition |
|---|---|
| SA2 | Statistical Area Level 2 — ABS geographic unit roughly equivalent to a suburb (~10,000 residents) |
| ILI | Influenza-like illness — the clinical proxy used in surveillance data |
| SIR | Susceptible-Infected-Recovered compartmental epidemic model |
| β | Transmission rate — probability of infection per susceptible-infected contact per day |
| γ | Recovery rate — fraction of infected who recover per day (= 1/infectious_period) |
| R0 | Basic reproduction number = β / γ — average new infections per case in fully susceptible population |
| Spreadability score | ML model output (0–1): probability that a suburb experiences an outbreak given its demographics |
| FIPS / SA2 code | Geographic join key used to merge datasets |
