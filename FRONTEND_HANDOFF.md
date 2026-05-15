# Frontend Handoff — MODR Project

> **How to use this**: Paste this entire document as the first message of a new chat. The chat will have full context to start designing/building the web frontend without needing the prior conversation history.
>
> **Project**: ENGG2112 Project MODR (Mapping and Optimising Disease Response)
> **Repo**: https://github.com/r0cb/ENGG2112
> **Local path**: `/Users/rocbarraket/Documents/ENGG2112/ENGG2112_Project`
> **Last updated**: 2026-05-15

---

## 0. TL;DR for the New Chat

A university ML pipeline predicts respiratory virus (flu + COVID + RSV) outbreak vulnerability across 141 US counties (NY/PA/CT/DE). The ML model + SIR simulator + static HTML maps are all done. **You're building the user-facing web app** with policy sliders (vaccination, mobility) that re-run the SIR simulation interactively.

Recommended stack: **Streamlit** (fastest path) or **Flask + Plotly.js** (more control). Both are documented below.

---

## 1. Project State (What's Already Built)

### Notebooks (in `notebooks/`)

| # | Notebook | Purpose |
|---|---|---|
| 00 | `00_data_acquisition.ipynb` | Per-source data download (NY/PA/CT/DE flu, COVID, RSV, ACS, PLACES) |
| 01 | `01_master_dataframe.ipynb` | Build stacked master DataFrame |
| 02 | `02_eda.ipynb` | Legacy EDA (uses old flu-only CSV — pre-pivot, ignore for frontend) |
| 03 | `03_feature_selection.ipynb` | Multi-method consensus feature selection |
| 04 | `04_model_logistic.ipynb` | Logistic regression baseline |
| 05 | `05_model_random_forest.ipynb` | Random Forest |
| 06 | `06_model_xgboost.ipynb` | XGBoost (RandomizedSearchCV optimised) ← **production model lives here** |
| 07 | `07_model_knn.ipynb` | KNN baseline |
| 08 | `08_model_comparison.ipynb` | Bootstrap CI + per-state comparison + production selection |
| 09 | `09_sir_simulation.ipynb` | County-level SIR ODE model with adjacency, policy scenarios |
| 10 | `10_map_visualization.ipynb` | Plotly choropleth + animated HTML maps |

### Production model artifact

**XGBoost (optimised)** lives at `models/production_model.pkl`. Inference pattern:

```python
import pickle, pandas as pd

with open('models/production_model.pkl', 'rb') as f:
    art = pickle.load(f)

# art keys:
#   'model_name'           : 'XGB'
#   'model'                : XGBClassifier (fitted on all 357 rows)
#   'isotonic_calibrator'  : IsotonicRegression — apply to raw proba
#   'scaler'               : StandardScaler for the demographic features
#   'feature_names'        : ordered list of all 10 features (use this order!)
#   'demographic_features' : 5 demographic features (need scaling)
#   'disease_dummies'      : 2 disease dummies (FLU, RSV; COVID is reference)
#   'state_dummies'        : 3 state dummies (DE, NY, PA; CT is reference)
#   'best_params'          : XGB hyperparameters
#   'oof_pr_auc'           : 0.506 (cross-validated)
```

### Datasets

`data/processed/master_stacked.csv` (357 rows, 40 cols):
- 141 flu rows (NY 62 + PA 67 + CT 9 PRs + DE 3)
- 140 COVID rows (NY 62 + PA 67 + CT 8 old counties + DE 3, Jun 2022 – May 2023 endemic phase)
- 76 RSV rows (PA 67 + CT 9)

Each row is one `(county, disease)` observation. Outbreak label = top 25% within (disease, state) by per-capita rate.

For the **frontend**, the relevant subset is the **141 flu rows** (one per county). The SIR sim operates only on these — COVID/RSV rows are used only for model training.

---

## 2. Honest Performance Calibration ⚠️ READ THIS

The frontend needs to communicate model uncertainty correctly. Here are the actual numbers:

### Headline performance
- **PR-AUC: 0.506** (95% CI 0.40–0.60)
- **Random baseline: 0.261**
- **Lift: ~1.94× over random**
- **Verdict: real signal, modest predictive power**

### Per-state heterogeneity (critical for UI design)

| State | n | PR-AUC | Reliability |
|---|---|---|---|
| NY | 124 | **0.74** | Genuinely predictive |
| PA | 201 | 0.32 | Barely above random (0.26) |
| CT | 26 | 0.30 | Barely above random |
| DE | 6 | 0.42 | Unreliable (n=6) |

**The model works on NY and is barely better than random on the other three states**. The aggregate 0.506 is lifted by NY alone.

### Implications for UI

1. **DO NOT present predictions as a confident "vulnerability score"** — they're a *relative ranking within state*
2. **Add a confidence indicator** based on state (NY = high confidence, PA/CT/DE = low confidence)
3. **Use neutral language**: "predicted relative vulnerability" or "modelled risk rank", not "probability of outbreak"
4. **The point of the frontend is exploration, not forecasting** — frame it as "what-if" scenarios under hypothetical policies, not as a real-world prediction system

### Stable model features (most reliable signal)

3 of 10 coefficients have stable signs across 1000 bootstrap resamples:
- `avg_household_size` (positive — crowded households increase outbreak risk)
- `pct_foreign_born` (positive — proxy for urban density/connectivity)
- `public_transport_pct` (positive — high-contact commuting)

These are the most defensible "story" features. The frontend can confidently show "counties with high X have higher predicted risk".

---

## 3. The SIR Simulator (Notebook 09 → `sir_results.json`)

### Math
Per-county SIR ODE:
- **γ** = 1/7 (7-day recovery)
- **β_county** = β_base × (1 + α × (p_outbreak − 0.5)) where β_base = R0 × γ, R0 = 1.3, α = 0.02, ML_scale = 0.5
- Initial conditions: 10 seed cases distributed to top-3 counties by p_outbreak
- Vaccination: uniform 58.9% (Variant C — found that real per-county vaccination produces *negative* rank correlation, so use mean)
- Adjacency-driven spatial coupling (per-county neighbour list)
- 180-day simulation horizon (90 timepoints, 2-day steps)

### Output structure (`models/sir_results.json`)
```json
{
  "metadata": {
    "production_model": "XGBoost",
    "pr_auc": 0.506,
    "gamma": 0.143,
    "R0_base": 1.3,
    "beta_base": 0.186,
    "ML_scale": 0.5,
    "alpha": 0.02,
    "T_days": 180,
    "seed_n": 10,
    "n_counties": 141
  },
  "counties": [
    {
      "fips": "09110",
      "county": "CAPITOL",
      "state": "CT",
      "pop_total": 977165,
      "pct_vaccinated": 58.9,
      "p_outbreak": 0.153,
      "beta": 0.200,
      "gamma": 0.143,
      "peak_infected_pct": 0.0,
      "peak_day": 0.0,
      "I_series": [0.0, 0.0, ...],   // 90-element array
      "t_series": [0.0, 2.0, ...]    // 90-element array (days)
    },
    ...
  ],
  "adjacency": { "09110": ["36005", ...], ... },
  "scenarios": { "baseline": {...}, "no_vax": {...}, ... }
}
```

### Re-running SIR with user parameters

The SIR function is in NB09 (cell ~11) and NB10 (cell 10). Signature:
```python
def run_sir(flu_df, adj, T=180, vax_boost=0.0, mobility_factor=1.0):
    """
    flu_df          : DataFrame with columns fips_str, N, V0, I_init, beta, gamma
    adj             : dict {fips: [neighbour_fips, ...]}
    T               : simulation days
    vax_boost       : ADDITIONAL fraction vaccinated (0.0 to 0.4 makes sense)
    mobility_factor : multiplier on spatial coupling (1.0 = unchanged, 0.0 = isolated)
    Returns: dict {fips: {'t': array, 'S': array, 'I': array, 'R': array}}
    """
```

Extract this into `src/sir.py` for the Flask backend.

### Performance
141 counties × 180 days runs in ~0.5–1 second in pure Python. **Fast enough for interactive use** (no need to port to JS or precompute).

---

## 4. Existing HTML Maps (Reference Implementations)

In `models/`:

| File | Size | Type | Shows |
|---|---|---|---|
| `map_vulnerability.html` | 4.7 MB | Static choropleth | XGBoost P(outbreak) per county |
| `map_sir_baseline.html` | 13.5 MB | Animated choropleth (120 days) | SIR with real vaccination |
| `map_sir_novax.html` | 13.3 MB | Animated choropleth (120 days) | SIR counterfactual (no vaccination) |

These are self-contained Plotly HTML files. **They work as standalone reference for what the frontend should produce dynamically.**

⚠️ **Don't serve these huge HTML files directly to the browser** — instead, regenerate the visualisations live via Plotly.js in JS, or have the Flask backend return the JSON data for client-side rendering.

---

## 5. Frontend Goals (From Project Plan)

The user-facing app should:

1. Display a county-level **choropleth map** of NY/PA/CT/DE coloured by predicted vulnerability
2. Provide **policy sliders**:
   - Vaccination boost (e.g. 0 to +40 percentage points above current)
   - Mobility factor (e.g. 0.0 to 1.0 multiplier on adjacency-driven spread)
3. Re-run the SIR simulation with the modified parameters when the user moves a slider
4. Display **outbreak metrics** that update live:
   - Peak infection %
   - Days to peak
   - Total cases averted (vs baseline)
5. Show per-county info on hover (county name, state, predicted P(outbreak), peak %)

---

## 6. Tech Stack Options

### Option A: Streamlit (RECOMMENDED for MVP)

**Why**: Sliders, plotly maps, file-loading, and reactive UI come essentially for free.

```python
import streamlit as st, pickle, json, plotly.express as px

@st.cache_resource
def load_model_and_sir():
    with open('models/production_model.pkl', 'rb') as f:
        model = pickle.load(f)
    with open('models/sir_results.json') as f:
        sir = json.load(f)
    return model, sir

model, sir = load_model_and_sir()

st.title("Respiratory Virus Vulnerability Explorer")
vax_boost = st.slider("Vaccination boost (% pts)", 0.0, 40.0, 0.0) / 100
mobility = st.slider("Mobility factor", 0.0, 1.0, 1.0)

if st.button("Run scenario"):
    results = run_sir(...)  # ~1 second
    # render plotly choropleth from results
    fig = px.choropleth(...)
    st.plotly_chart(fig)
```

**Time to MVP: ~2 hours**

### Option B: Flask + vanilla JS + Plotly.js

**Why**: More UI control, can be deployed as a static-ish site, more customisable.

```
app/
├── app.py              # Flask: routes /, /api/baseline, /api/simulate
├── sir.py              # Extracted from NB09 — pure Python SIR ODE
├── inference.py        # Loads production_model.pkl
├── static/
│   ├── index.html      # Main page
│   ├── style.css
│   └── main.js         # Plotly + slider wiring
└── templates/
```

Backend endpoint design:
```python
@app.route('/api/simulate', methods=['POST'])
def simulate():
    p = request.json
    results = run_sir(
        flu_seeded, adj_dict,
        T=p.get('T', 120),
        vax_boost=p.get('vax_boost', 0.0),
        mobility_factor=p.get('mobility', 1.0),
    )
    return jsonify({
        'counties': [
            {'fips': f, 'I_series': r['I'].tolist(), 'peak_pct': float(r['I'].max()*100)}
            for f, r in results.items()
        ],
        't_series': list(results[next(iter(results))]['t']),
    })
```

Frontend pattern:
```javascript
async function runScenario() {
    const params = {
        vax_boost: parseFloat(document.getElementById('vax').value) / 100,
        mobility: parseFloat(document.getElementById('mobility').value),
    };
    const r = await fetch('/api/simulate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(params)
    });
    const data = await r.json();
    renderMap(data);  // Plotly.js update
}
```

**Time to MVP: ~1-2 days**

---

## 7. Concrete First Steps (For the New Chat to Execute)

1. **Pick stack**: Streamlit or Flask (recommend Streamlit unless deliverable requires Flask).
2. **Extract SIR code** from NB09 (sections 5-7) into `src/sir.py`. Test it works standalone with the existing `flu_seeded` DataFrame and `adj_dict`.
3. **Extract or recreate `flu_seeded` + `adj_dict`** as cached resources. The simplest way is to load from `sir_results.json` (counties + adjacency are already in there).
4. **Build the basic UI**: title, two sliders, "Run scenario" button, a choropleth placeholder.
5. **Wire up the SIR call**: on button click, run SIR with slider values, update the choropleth.
6. **Add metrics**: peak infection %, days to peak, total cases averted vs baseline.
7. **Per-county tooltips** on the map.
8. **Polish**: add the honest uncertainty framing (see Section 2 above), add an "About this model" explainer, hide non-NY/PA/CT/DE states on the map.

---

## 8. Critical Files to Reference

| Path | What it contains |
|---|---|
| `data/processed/master_stacked.csv` | 357-row dataset (40 cols) |
| `data/processed/selected_features.json` | Feature list for the model |
| `models/production_model.pkl` | XGBoost + isotonic + scaler |
| `models/sir_results.json` | Pre-computed baseline (141 counties, full series, adjacency) |
| `models/map_*.html` | Reference: what static maps look like |
| `notebooks/09_sir_simulation.ipynb` | SIR ODE + adjacency — extract `run_sir()` from here |
| `notebooks/10_map_visualization.ipynb` | Plotly choropleth setup — adapt for live data |
| `REFERENCES.md` | Citations for the report |
| `MASTER_PLAN.md` | Original architecture |
| `PROJECT_JOURNAL.md` | Decision history |
| `results_log.md` | Performance benchmarks per model |

---

## 9. Known Issues to Surface in the UI

1. **NY-bias**: model works much better on NY (PR-AUC 0.74) than other states (~0.30). Add a confidence indicator.
2. **CT geographic asymmetry**: COVID rows use old counties (FIPS 09001-09015); flu/RSV rows use new planning regions (FIPS 09110-09190). The maps use planning regions throughout.
3. **Multi-disease label**: "outbreak" means "top 25% within disease+state", not "absolute probability". UI text should reflect this.
4. **Limited coverage**: only NY/PA/CT/DE — other states should be greyed out or zoomed out.
5. **Large HTML maps**: don't serve `models/map_*.html` directly (13 MB). Regenerate live.

---

## 10. Quick-Start Code Snippets

### Load model + scaler + calibrator
```python
import pickle
with open('models/production_model.pkl', 'rb') as f:
    art = pickle.load(f)
model         = art['model']
scaler        = art['scaler']
iso           = art['isotonic_calibrator']
feature_names = art['feature_names']  # the order matters!
demo_features = art['demographic_features']  # need scaling
```

### Predict P(outbreak) for one county-disease combination
```python
import pandas as pd
demo_row = pd.DataFrame([{
    'pct_foreign_born':     12.5,
    'pop_density_per_sqmi': 1200,
    'avg_household_size':   2.4,
    'public_transport_pct': 8.0,
    'pct_elderly':          17.5,
}])
X_demo = scaler.transform(demo_row[demo_features])

X_full = pd.DataFrame(X_demo, columns=demo_features)
# disease_FLU, disease_RSV; COVID is reference (both 0 = COVID)
X_full['disease_FLU'] = 1     # this row is flu
X_full['disease_RSV'] = 0
# state_DE, state_NY, state_PA; CT is reference
X_full['state_NY'] = 1
X_full['state_DE'] = 0
X_full['state_PA'] = 0
X_full = X_full[feature_names]  # reorder to match training

p_raw        = model.predict_proba(X_full.values)[:, 1]
p_calibrated = iso.predict(p_raw)
```

### Load and use baseline SIR results
```python
import json
with open('models/sir_results.json') as f:
    sir = json.load(f)

baseline_peaks = {c['fips']: c['peak_infected_pct'] for c in sir['counties']}

# All-county time series:
for c in sir['counties'][:5]:
    print(c['fips'], c['county'], 'peak%:', c['peak_infected_pct'])
```

### Run SIR with user-modified parameters
Extract `run_sir()` from `notebooks/09_sir_simulation.ipynb` (around cell 11). Key signature:
```python
def run_sir(flu_df, adj, T=180, vax_boost=0.0, mobility_factor=1.0):
    """Returns: dict {fips: {'t': array, 'S': array, 'I': array, 'R': array}}"""
```

To rebuild `flu_df` and `adj` from `sir_results.json`:
```python
flu_df = pd.DataFrame([{
    'fips_str': c['fips'],
    'N':        float(c['pop_total']),
    'V0':       c['pct_vaccinated'] / 100,
    'beta':     c['beta'],
    'gamma':    c['gamma'],
    'I_init':   1.0 if c['fips'] in TOP_3_FIPS else 0.0,  # seed top-3 counties
} for c in sir['counties']])
adj = {fips: nbrs for fips, nbrs in sir['adjacency'].items()}
```

---

## 11. What to NOT Re-Do

Don't redo:
- ❌ Data acquisition (NB00 done)
- ❌ Feature engineering (NB01 done)
- ❌ Model training/comparison (NB04–08 done; XGBoost is the production model)
- ❌ SIR simulator core logic (NB09 done; extract `run_sir()` to a module)
- ❌ Plotly map design (NB10 done; reference the HTML output for visual design)

All of these are "production" — just wire them into a web app.

---

## 12. State of GitHub vs Local

**As of the handoff time**, the local repo has uncommitted changes that fix a discrepancy:

- `models/production_model.pkl` was stale (had old XGB params, not the optimised ones in `xgb_metrics.json`). **Local has been rebuilt** to use the optimised XGB.
- `notebooks/09_sir_simulation.ipynb` was hardcoded to load `rf_model.pkl`. **Local has been patched** to load `production_model.pkl`.
- `notebooks/10_map_visualization.ipynb` had "Random Forest" labels in markdown + plotly titles. **Local has been patched** to say "XGBoost (optimised)".
- `sir_results.json` was generated from RF. **Local has been re-generated** from XGBoost.
- `models/map_*.html` were the RF versions. **Local has been re-generated** from the XGBoost SIR results.

If the user wants to push these fixes before starting the frontend, do so first. If not, the new chat can either:
(a) pull the older state from GitHub and ignore the issue (the SIR + maps will use RF, mismatching the official production model — but it still works), OR
(b) re-run NB09 and NB10 to regenerate locally

---

## 13. Open Questions for the New Chat

- **Streamlit vs Flask**: speed-to-MVP vs UI control trade-off
- **Hosting**: localhost only, or deployed (Render, Railway, etc.)?
- **Choropleth detail**: just colour-by-vulnerability, or also animated SIR over time?
- **Comparison view**: split-screen (baseline vs intervention) or overlay?
- **Mobile responsiveness**: required or desktop-only?
- **How much uncertainty to surface**: subtle indicator, or prominent disclaimer?

---

## 14. Honest Framing for the App's "About" Text

Since the model has modest performance with strong state heterogeneity, the frontend should communicate appropriate humility. Suggested phrasing:

> *"This tool explores hypothetical respiratory virus outbreak scenarios across counties in New York, Pennsylvania, Connecticut, and Delaware. The underlying ML model predicts relative vulnerability ranking based on demographic features. Performance is meaningful but modest (PR-AUC 0.51, vs random 0.26), and varies substantially across states (strongest in NY, weakest in PA). The SIR simulation runs over 180 days and is intended for exploring 'what-if' scenarios under different policy interventions — not as a real-world forecasting system."*

---

## End of Handoff

Paste this entire document as the first message of a new chat. Add any specific direction at the top (e.g. "I want to use Streamlit, deploy to localhost only, and prioritise getting an MVP working in 2 hours"), then the new conversation has full context to build the frontend.
