"""Optimisation helpers that turn the XGBoost vulnerability score from a
prediction into an allocation signal.

Single public entry point: `targeted_vax_boost` converts a fixed
vaccination budget (a fractional percentage of regional population) into a
per-county boost array weighted by the predicted outbreak probability,
preserving the total population-weighted spend and redistributing overflow
from saturated counties.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.constants import ALLOCATION_TARGETED, ALLOCATION_UNIFORM
from src.sir import aggregate_metrics, run_sir


def targeted_vax_boost(
    flu_df: pd.DataFrame, total_boost: float, cap: float = 1.0
) -> pd.Series:
    """Distribute `total_boost` (a population-weighted percentage-point
    fraction, e.g. 0.10 for +10pp) across counties proportionally to the
    XGBoost p_outbreak score, *with redistribution* so we never waste
    vaccinations on counties that would be pushed above the `cap` (default
    100% coverage).

    Conceptual model:
    - There is a fixed budget of vaccinations measured in people:
        budget = total_boost × Σ pop_c
    - Each county's allocation is proportional to its p_outbreak weight.
    - If a county's V_eff would exceed `cap`, it is capped at exactly `cap`
      and the unused vaccines are redistributed to the still-eligible
      counties, again proportionally to weight. Iterate until no county is
      over the cap (typically 1-3 passes).
    - Total people vaccinated stays equal to the uniform alternative — no
      vaccines are lost to clipping.

    Returns a Series indexed by fips_str ready to pass to run_sir.
    """
    if total_boost <= 0:
        return pd.Series(0.0, index=flu_df["fips_str"].values)

    weights = flu_df["p_outbreak"].clip(lower=1e-6).values
    pop = flu_df["N"].values
    V0 = flu_df["V0"].values
    n = len(flu_df)
    fips = flu_df["fips_str"].values

    target_people = total_boost * pop.sum()
    boost = np.zeros(n)
    eligible = np.ones(n, dtype=bool)

    for _ in range(20):
        if not eligible.any():
            break
        idx = np.where(eligible)[0]
        w = weights[idx]
        denom = float((w * pop[idx]).sum())
        if denom <= 0 or target_people <= 0:
            break
        K = target_people / denom
        proposed = K * w
        V_eff_proposed = V0[idx] + proposed
        over = V_eff_proposed > cap
        if not over.any():
            boost[idx] = proposed
            target_people = 0.0
            break
        # Cap counties whose proposed allocation exceeds the ceiling
        over_idx = idx[over]
        boost[over_idx] = np.clip(cap - V0[over_idx], 0.0, None)
        target_people -= float((boost[over_idx] * pop[over_idx]).sum())
        eligible[over_idx] = False

    return pd.Series(boost, index=fips)


def vax_boost_for_strategy(
    flu_df: pd.DataFrame,
    total_boost: float,
    strategy: str,
) -> float | pd.Series:
    """Return a vax_boost value compatible with sir.run_sir for the chosen
    allocation strategy."""
    if strategy == ALLOCATION_TARGETED:
        return targeted_vax_boost(flu_df, total_boost)
    return float(total_boost)


def _legacy_find_min_vax_for_threshold(
    flu_df: pd.DataFrame,
    adj: dict,
    horizon: int,
    mobility_factor: float,
    strategy: str,
    threshold_pct: float,
    vax_max_pp: int = 40,
    step_pp: int = 2,
) -> dict:
    """Grid search the vaccination budget for the smallest pp value whose
    peak_pct stays at or below `threshold_pct`. Returns a result dict with
    the optimal budget, the achieved peak, and the full sweep trace for
    plotting.

    The sweep is coarse-grained (default 2pp steps) so the whole 0-40pp range
    is 21 SIR runs, ~3-5 seconds total. SIR results upstream are cached.
    """
    sweep = []
    found = None
    for pp in range(0, vax_max_pp + 1, step_pp):
        boost = pp / 100.0
        vb = vax_boost_for_strategy(flu_df, boost, strategy)
        sim = run_sir(
            flu_df, adj, T=horizon, vax_boost=vb, mobility_factor=mobility_factor
        )
        metrics = aggregate_metrics(sim)
        peak_pct = metrics["total_peak_pct"]
        sweep.append({"vax_pp": pp, "peak_pct": peak_pct})
        if peak_pct <= threshold_pct and found is None:
            found = pp
    return {
        "optimal_pp": found,
        "threshold_pct": threshold_pct,
        "sweep": sweep,
        "strategy": strategy,
        "mobility_factor": mobility_factor,
    }
