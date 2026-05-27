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

from src.constants import (
    ALLOCATION_OPTIMAL,
    ALLOCATION_TARGETED,
    ALLOCATION_UNIFORM,
    OPTIMISER_BETA_GRID,
)
from src.sir import aggregate_metrics, run_sir


def beta_vax_boost(
    flu_df: pd.DataFrame,
    total_boost: float,
    beta: float,
    cap: float = 1.0,
) -> pd.Series:
    """One-parameter family of vaccination allocations.

    Each county gets boost_c proportional to (p_outbreak_c) ** beta, with
    iterative water-filling: any county whose V_eff would exceed `cap` is
    pinned at the cap and its unused doses flow back into the budget for the
    still-eligible counties. The total population-weighted budget is
    preserved exactly — no doses wasted.

    Special cases:
    - beta = 0: pure uniform (every county gets the same percentage-point
      boost).
    - beta = 1: standard "targeted" allocation, proportional to p_outbreak.
    - beta > 1: progressively sharper concentration on high-vulnerability
      counties.
    """
    if total_boost <= 0:
        return pd.Series(0.0, index=flu_df["fips_str"].values)

    pop = flu_df["N"].values
    V0 = flu_df["V0"].values
    n = len(flu_df)
    fips = flu_df["fips_str"].values

    if beta == 0:
        weights = np.ones(n)
    else:
        weights = (flu_df["p_outbreak"].clip(lower=1e-6).values) ** float(beta)

    target_people = total_boost * pop.sum()
    boost = np.zeros(n)
    eligible = np.ones(n, dtype=bool)

    for _ in range(20):
        if not eligible.any():
            break
        idx = np.where(eligible)[0]
        w = weights[idx]
        denom = float((w * pop[idx]).sum())
        if denom <= 0 or target_people <= 1e-9:
            break
        K = target_people / denom
        proposed = K * w
        V_eff_proposed = V0[idx] + proposed
        over = V_eff_proposed > cap
        if not over.any():
            boost[idx] = proposed
            target_people = 0.0
            break
        over_idx = idx[over]
        boost[over_idx] = np.clip(cap - V0[over_idx], 0.0, None)
        target_people -= float((boost[over_idx] * pop[over_idx]).sum())
        eligible[over_idx] = False

    return pd.Series(boost, index=fips)


def find_optimal_allocation(
    flu_df: pd.DataFrame,
    adj: dict,
    horizon: int,
    mobility_factor: float,
    total_boost: float,
    beta_grid: tuple[float, ...] = OPTIMISER_BETA_GRID,
) -> dict:
    """Find the per-county allocation that minimises total new infections at
    the given vaccination budget.

    The search is over a one-parameter family of allocations (boost_c ∝
    p_outbreak_c^β with water-filling); we evaluate every β in `beta_grid`
    by running the full SIR, then return the configuration that produced
    the fewest new infections.

    This is a deliberate restriction of the full 141-dimensional allocation
    space to a one-dimensional family that is interpretable, fast to search
    (~7 SIR runs ≈ 4 seconds), and contains both natural endpoints (uniform
    at β=0, ML-proportional at β=1). It is a true minimisation within that
    family; finer free-allocation search is future work.

    Returns:
        dict with:
            best_beta: the sharpness that minimised total new infections
            best_boost: pd.Series of per-county boost (fractional)
            best_cases: number of new infections at the optimum
            best_sim: the SIR result at the optimum (reuse to skip a rerun)
            sweep: list of {beta, cases} dicts (full sweep for plotting)
    """
    sweep = []
    best = None
    for beta in beta_grid:
        boost = beta_vax_boost(flu_df, total_boost, beta)
        sim = run_sir(
            flu_df, adj, T=horizon, vax_boost=boost, mobility_factor=mobility_factor
        )
        metrics = aggregate_metrics(sim)
        cases = float(metrics["new_infections"])
        sweep.append({"beta": float(beta), "cases": cases})
        if best is None or cases < best["cases"]:
            best = {
                "beta": float(beta),
                "boost": boost,
                "cases": cases,
                "sim": sim,
                "metrics": metrics,
            }
    return {
        "best_beta": best["beta"],
        "best_boost": best["boost"],
        "best_cases": best["cases"],
        "best_sim": best["sim"],
        "best_metrics": best["metrics"],
        "sweep": sweep,
    }


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
    optimal_beta: float | None = None,
) -> float | pd.Series:
    """Return a vax_boost value compatible with sir.run_sir for the chosen
    allocation strategy.

    For strategy == ALLOCATION_OPTIMAL, the caller must supply the β that
    was selected by the case-minimising optimiser; we then materialise the
    same allocation. This makes the result deterministic and cacheable.
    """
    if strategy == ALLOCATION_TARGETED:
        return targeted_vax_boost(flu_df, total_boost)
    if strategy == ALLOCATION_OPTIMAL:
        if optimal_beta is None:
            # No optimiser run yet — fall back to uniform.
            return float(total_boost)
        return beta_vax_boost(flu_df, total_boost, optimal_beta)
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
