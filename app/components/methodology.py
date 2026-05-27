"""Methodology / About expandable block."""

from __future__ import annotations

import streamlit as st


def render() -> None:
    with st.expander(
        "About this tool · methodology · limitations", expanded=False
    ):
        st.markdown(
            """
### What this is

This tool explores hypothetical respiratory virus outbreak scenarios across
counties in New York, Pennsylvania, Connecticut, and Delaware. The underlying
machine learning model predicts a relative vulnerability ranking based on
demographic features; the SIR simulation runs that ranking forward through a
hypothetical 90 — 365-day window to show how policy interventions would change
the spatial spread. **It is not a real-world forecasting system.**

### The machine learning model

A gradient-boosted classifier (XGBoost) was trained on 357 county-disease
observations across flu, COVID, and RSV. Performance is meaningful but
modest: overall PR-AUC is **0.506** versus a random baseline of **0.261**, a
roughly **1.94× lift**. State-by-state breakdown:

| State | n | PR-AUC | Reliability |
|---|---|---|---|
| New York | 124 | 0.74 | Genuinely predictive |
| Pennsylvania | 201 | 0.32 | Barely above random |
| Connecticut | 26 | 0.30 | Barely above random |
| Delaware | 6 | 0.42 | Unreliable (n = 6) |

The aggregate number is lifted by New York alone — treat predictions in PA,
CT, and DE as exploratory rather than load-bearing.

### Three stable model features

Across 1,000 bootstrap resamples, three feature coefficients keep the same
sign with high confidence:

- **Average household size** (positive — crowded households increase risk)
- **Percent foreign born** (positive — proxy for urban density / connectivity)
- **Public transport commuting share** (positive — high-contact commuting)

### The SIR simulation

Each county follows a standard susceptible-infectious-recovered ODE with
spatial coupling along the county-adjacency graph:

- Recovery rate **γ = 1 / 7** (seven-day infectious period, seasonal flu)
- Baseline reproduction number **R₀ = 1.3**, so **β_base ≈ 0.186**
- Per-county β is scaled up to 50 % by the ML p_outbreak score
- Inter-county coupling **α = 0.02**, scaled by the **Mobility factor** slider
- Vaccination is set by the **Baseline vaccination** slider (defaults to 59 %,
  the regional mean used in the Variant-C calibration). The **Per-state
  baselines** expander lets you override individual states. The **Additional
  vaccination budget** slider adds percentage points on top of the baseline
- Ten initial infections are seeded in the three counties with the highest
  predicted vulnerability; the epidemic spreads from there through adjacency
- Simulation horizon: 90, 180, 270, or 365 days, evaluated at 0.5-day
  resolution and downsampled to 2-4 day frames for the animation

### The map tabs

- **Outbreak tab.** Red-orange choropleth. In the default view, shows
  XGBoost-predicted P(outbreak) per county. After a scenario runs, shows
  the animated % infectious over time, advancing through the simulation
  horizon via the shared play button.
- **Vaccination tab.** Green choropleth. Always static — shows the
  effective vaccination coverage per county at t=0, which equals the
  chosen baseline plus the additional budget allocated through the chosen
  strategy. Use it to see *where* the targeted strategy actually concentrates
  vaccinations.

### The Optimisation panel

The XGBoost score is treated as an *allocation signal*, not just a
prediction:

- **Allocation strategy** routes the same total vaccination budget either
  uniformly or proportionally to each county's predicted vulnerability.
  Under targeted allocation, the per-county additional vaccination is
  `boost_c ∝ p_outbreak_c`, normalised so the population-weighted mean
  matches the uniform alternative — same total people vaccinated, just
  redistributed.
- **Auto-optimiser** sweeps the vaccination budget in 2pp steps from 0 to
  40pp and returns the smallest value whose regional peak infection stays
  at or below 0.05% of population, given the current mobility factor and
  allocation strategy. It then sets the sidebar slider so the user can
  immediately play the optimal scenario.

### Known limitations

1. **NY-bias.** The model is genuinely predictive only in New York. Predictions
   for PA, CT, and DE are barely above random.
2. **Connecticut GeoJSON gap.** Connecticut switched from old counties (FIPS
   09001–09015) to planning regions (FIPS 09110–09190) in 2022. The standard
   US Census GeoJSON used by Plotly still uses the old counties, so CT
   planning regions appear blank on the map. Their values are included in
   metrics and the breakdown chart. Adding a custom planning-regions GeoJSON
   is future work.
3. **Outbreak label semantics.** "Outbreak" means "top 25 % within
   disease + state by per-capita rate", not an absolute probability of disease
   incidence. Predictions are a relative ranking within state, not a
   calibrated probability of any specific event.
4. **Coverage.** Only NY, PA, CT, DE are modelled. Other US states are not
   included in the underlying training data.
5. **Single-snapshot dynamics.** The SIR runs are deterministic — for a given
   slider configuration the result is reproducible (`np.random.seed(42)`) but
   no uncertainty band is shown.

### Citations

See `REFERENCES.md` in the project repository for the full citation list
covering the data sources (CDC FluView, HHS COVID-19 Reported Patient Impact,
RSV-NET, ACS, PLACES) and the methodological literature.
            """
        )
