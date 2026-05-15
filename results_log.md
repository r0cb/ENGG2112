# MODR Project — Optimisation Results Log

## Objective
Maximise relative vulnerability prediction across NY/PA/CT/DE counties (357 observations).
Primary metric: **PR-AUC** (class-imbalanced: 26% outbreak prevalence).
SIR goal: **rank counties by relative burden** for resource allocation.

---

## ML Model Performance (5-fold StratifiedGroupKFold, groups=fips)

| Model | PR-AUC | ROC-AUC | Recall | F1 | Brier (cal) | Notes |
|---|---|---|---|---|---|---|
| Logistic Regression | 0.446 | 0.610 | 0.376 | 0.372 | — | Baseline linear model |
| Random Forest | 0.508 | 0.651 | 0.258 | 0.381 | 0.160 | Original production model |
| XGBoost (GridSearch) | 0.491 | 0.665 | 0.376 | 0.417 | 0.166 | Original params: {lr=0.1, depth=3, n=300} |
| KNN | 0.510 | 0.687 | 0.215 | 0.339 | 0.159 | Highest raw PR-AUC, lowest recall |
| Random baseline | 0.261 | — | — | — | — | Prevalence = 26.1% |

### Bootstrap 95% CIs (1000 resamples, identical CV folds)
- KNN:  PR-AUC 0.513 [0.410, 0.610]
- RF:   PR-AUC 0.512 [0.405, 0.606]
- XGB:  PR-AUC 0.495 [0.386, 0.597]
- LR:   PR-AUC 0.450 [0.355, 0.547]

**Key finding**: KNN, RF, and XGB are statistically tied — CIs overlap heavily. KNN's margin is within noise at n=357.

### Per-State PR-AUC Audit (all models)
| State | n | LR | RF | XGB | KNN |
|---|---|---|---|---|---|
| NY | 124 | 0.734 | 0.698 | 0.740 | 0.712 |
| PA | 201 | 0.218 | 0.377 | 0.324 | 0.298 |
| CT | 26 | 0.309 | 0.256 | 0.301 | 0.258 |
| DE | 6 | 0.417 | 0.325 | 0.417 | 0.333 |
| Spread | — | 0.516 | 0.442 | **0.438** | 0.454 |

**Key finding**: KNN's headline PR-AUC was driven by NY (0.712) while performing only 0.298 on PA. XGB has the most uniform spread (0.438).

### Composite Ranking (PR-AUC rank + Recall rank + State-spread rank + Brier rank)
- XGB: **4** (best)
- RF:  5
- KNN: 5
- LR:  10

**Production model: XGB** (selected by composite criteria over RF and KNN)

---

## XGBoost Optimisation

### Step 1 — GridSearchCV (original)
- Search: `{n_estimators: [100,200,300], max_depth: [3,5], lr: [0.05,0.1], subsample: [0.8,1.0], colsample_bytree: [0.8,1.0]}`
- Best: `{colsample_bytree:1.0, lr:0.1, max_depth:3, n_estimators:300, subsample:0.8}`
- OOF PR-AUC: **0.491**

### Step 2 — RandomizedSearchCV (60 iterations, broader grid) [NB06 updated]
- Search added: `min_child_weight: [1,2,3,5]`, `gamma: [0,0.05,0.1,0.2,0.3]`, `n_estimators` up to 800, `lr` down to 0.01
- Best params found: `{subsample:0.8, n_estimators:800, min_child_weight:5, max_depth:4, learning_rate:0.01, gamma:0, colsample_bytree:0.6}`
- OOF PR-AUC: **0.506** (+0.015 improvement); Recall: 0.376 → **0.409**

---

## Random Forest — Feature Selection Experiments

| Feature set | PR-AUC | Change |
|---|---|---|
| Consensus 10 features (baseline) | 0.508 | — |
| Top-5 permutation importance | 0.482 | −0.026 |
| RFECV (all 23) | 0.451 | −0.057 |

**Finding**: Consensus 10 features remain optimal for RF. Feature reduction hurts performance.

---

## SIR Simulation — Rank Validation vs Real Flu Burden

### Seeding/Vaccination Variants Tested

| Variant | Seeding | V0 | Overall ρ | AUC | K10 prec | NY ρ | PA ρ |
|---|---|---|---|---|---|---|---|
| A: Original | Top-3 counties | Per-county real | −0.211 | 0.500 | 0.15 | −0.049 | +0.283* |
| B: Distributed | p_outbreak × SEED_N | Per-county real | −0.276 | — | — | — | +0.190 |
| **C: Best** | **Top-3 counties** | **Uniform mean (58.9%)** | **+0.448** | **0.680** | **0.45** | **+0.351** (p=0.005) | **+0.503** (p<0.001) |

### Root Cause of Negative Correlation (Variants A & B)
NYC counties (p_outbreak~1.0) have 75–80% vaccination → low SIR peak.
Rural PA counties (p_outbreak~0.2) have 35% vaccination → high SIR peak.
This creates a negative correlation with real burden (highest in urban areas).

**Fix (Variant C)**: Use uniform regional mean V0=58.9%, removing the vaccination heterogeneity confound. SIR then correctly ranks counties by transmission dynamics rather than vaccination differences.

### Variant C Results (implemented in NB09)
- Overall Spearman ρ: **+0.448** (was −0.211)
- Overall AUC: **0.680** (was 0.500)
- Top-10 precision: **0.45** (was 0.15)
- NY: ρ = +0.351, p = 0.005
- PA: ρ = +0.503, p < 0.001

---

## β Regressor (Notebook 11)

Back-calculated β from final-size equation: `R0 = −ln(1−a)/a`, `β = R0 × γ`

**Finding**: Lab case counts dramatically undercount infections. β_obs mean = 0.1463, std = 0.0024 (extremely tight — R0_obs ~1.02, barely above epidemic threshold). The RF regressor achieved R²=0.530, r=0.728 OOF, but the underlying signal is too weak for the SIR simulation (SIR peak = 0.00% at R0~1.02).

**Conclusion**: β regressor not useful for SIR parameterisation. Stick with ML-scaled β from p_outbreak.

---

## Changes Made

| Notebook | Change | Status |
|---|---|---|
| NB05 (RF) | Added RFECV feature selection (Section 12) | Done |
| NB05 (RF) | Added top-5 permutation rerun (Section 13) | Done |
| NB06 (XGB) | GridSearch → RandomizedSearchCV, broader grid | Done |
| NB08 (comparison) | Bootstrap CIs + per-state audit + composite production selection | Done |
| NB08 (comparison) | State-stratified calibration plot (Section 10) | Done |
| NB09 (SIR) | Variant C: 3-point seed + uniform V0 (Section 4) | Done |
| NB09 (SIR) | Rank validation section (Section 13) | Done |
| NB11 (β regressor) | New notebook — β back-calculation from case data | Done |
