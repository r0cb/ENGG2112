"""Optimisation helpers that turn the XGBoost vulnerability score from a
prediction into an allocation signal.

Two pieces:
- targeted_vax_boost: convert a uniform vaccination budget (X percentage
  points) into a per-county boost array weighted by the predicted outbreak
  probability, preserving the total population-weighted spend.
- find_min_vax_for_threshold: grid search the vaccination budget for the
  smallest amount that keeps the regional epidemic peak below a threshold,
  given a fixed mobility factor and allocation strategy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.constants import ALLOCATION_TARGETED, ALLOCATION_UNIFORM
from src.sir import aggregate_metrics, run_sir


def targeted_vax_boost(
    flu_df: pd.DataFrame, total_boost: float
) -> pd.Series:
    """Distribute `total_boost` (in percentage-point fraction, e.g. 0.10 for
    +10pp) across counties proportional to the XGBoost p_outbreak score, so
    that the population-weighted mean boost equals the uniform total_boost.

    Returns a Series indexed by fips_str ready to pass to run_sir.
    """
    if total_boost <= 0:
        return pd.Series(0.0, index=flu_df["fips_str"].values)
    weights = flu_df["p_outbreak"].clip(lower=1e-6).values
    pop = flu_df["N"].values
    # weighted mean of boost_c with weights = pop must equal total_boost
    # boost_c proportional to weights[c]; scale so weighted mean matches.
    raw = weights / weights.mean()
    boost = total_boost * raw
    # Population-weighted normalisation so the total vaccinated-person budget
    # matches uniform: sum(boost_c * pop_c) == total_boost * sum(pop_c)
    pop_weighted_mean = (boost * pop).sum() / pop.sum()
    if pop_weighted_mean > 0:
        boost = boost * (total_boost / pop_weighted_mean)
    return pd.Series(boost, index=flu_df["fips_str"].values)


def vax_boost_for_strategy(
    flu_df: pd.DataFrame, total_boost: float, strategy: str
) -> float | pd.Series:
    """Return a vax_boost value compatible with sir.run_sir for the chosen
    allocation strategy."""
    if strategy == ALLOCATION_TARGETED:
        return targeted_vax_boost(flu_df, total_boost)
    return float(total_boost)


def find_min_vax_for_threshold(
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
