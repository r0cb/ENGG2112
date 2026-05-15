"""Multi-county SIR simulator. Lifted from notebooks/09_sir_simulation.ipynb cell 12.

Pure Python — no Streamlit imports. Reproducible via np.random.seed(42).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp

np.random.seed(42)

GAMMA = 1 / 7
R0_BASE = 1.3
BETA_BASE = R0_BASE * GAMMA
ML_SCALE = 0.5
ALPHA = 0.02
T_SIM = 180
SEED_N = 10


def _build_ode(beta_arr, gamma_arr, N_arr, adj_pairs, alpha, mobility_factor):
    eff_alpha = alpha * mobility_factor

    def rhs(t, y):
        S = y[0::3]
        I = y[1::3]

        local_foi = beta_arr * I / N_arr

        imported = np.zeros(len(N_arr))
        for (i, j) in adj_pairs:
            imported[i] += I[j] / N_arr[j]
        imported *= eff_alpha

        foi = local_foi + imported
        dS = -foi * S
        dI = foi * S - gamma_arr * I
        dR = gamma_arr * I

        out = np.empty_like(y)
        out[0::3] = dS
        out[1::3] = dI
        out[2::3] = dR
        return out

    return rhs


def run_sir(
    flu_df: pd.DataFrame,
    adj: dict,
    T: int = T_SIM,
    vax_boost: float = 0.0,
    mobility_factor: float = 1.0,
    alpha: float = ALPHA,
) -> dict:
    """Multi-county SIR with adjacency-driven spatial coupling.

    Parameters
    ----------
    flu_df : DataFrame with columns fips_str, N, V0, beta, gamma, I_init.
    adj : dict mapping fips_str -> list of neighbour fips_str (undirected).
    T : simulation horizon in days.
    vax_boost : additional vaccination fraction on top of V0 (0..1).
    mobility_factor : scales inter-county coupling alpha (0 = isolated, 1 = baseline).

    Returns
    -------
    dict with keys:
        t (n_timepoints,), S/I/R (n_counties, n_timepoints), N (n_counties,),
        fips_order (list[str]), peak_infected_pct (n_counties,), peak_day (n_counties,).
    """
    fips_order = flu_df["fips_str"].tolist()
    fips_idx = {f: i for i, f in enumerate(fips_order)}
    n = len(fips_order)

    _df = flu_df.set_index("fips_str")
    beta_arr = _df["beta"].reindex(fips_order).values
    gamma_arr = _df["gamma"].reindex(fips_order).values
    N_arr = _df["N"].reindex(fips_order).values
    V0_arr = _df["V0"].reindex(fips_order).values
    I0_arr = _df["I_init"].reindex(fips_order).values

    vax_eff = np.clip(V0_arr + vax_boost, 0, 1)
    R_init = N_arr * vax_eff
    S_init = np.clip(N_arr - R_init - I0_arr, 0, None)

    y0 = np.zeros(3 * n)
    y0[0::3] = S_init
    y0[1::3] = I0_arr
    y0[2::3] = R_init

    adj_pairs = [
        (fips_idx[a], fips_idx[b])
        for a, neighbours in adj.items()
        for b in neighbours
        if a in fips_idx and b in fips_idx
    ]

    rhs = _build_ode(beta_arr, gamma_arr, N_arr, adj_pairs, alpha, mobility_factor)
    t_eval = np.linspace(0, T, T * 2 + 1)

    sol = solve_ivp(
        rhs, [0, T], y0, method="RK45", t_eval=t_eval, rtol=1e-4, atol=1e-6
    )

    S = sol.y[0::3]
    I = sol.y[1::3]
    R = sol.y[2::3]

    I_rate = I / N_arr[:, None]

    return {
        "t": sol.t,
        "S": S,
        "I": I,
        "R": R,
        "N": N_arr,
        "fips_order": fips_order,
        "peak_infected_pct": I_rate.max(axis=1) * 100,
        "peak_day": sol.t[I_rate.argmax(axis=1)],
    }


def aggregate_metrics(sim: dict) -> dict:
    """Compute region-level summary metrics from a sim result."""
    I_agg = sim["I"].sum(axis=0)
    N_tot = sim["N"].sum()

    total_peak_pct = float(I_agg.max() / N_tot * 100)
    peak_day = float(sim["t"][int(np.argmax(I_agg))])
    total_reached_pct = float(sim["R"][:, -1].sum() / N_tot * 100)

    R_init = sim["R"][:, 0].sum()
    R_final = sim["R"][:, -1].sum()
    new_infections = float(R_final - R_init)
    new_infections_pct = float(new_infections / N_tot * 100)

    return {
        "total_peak_pct": total_peak_pct,
        "peak_day": peak_day,
        "total_reached_pct": total_reached_pct,
        "new_infections": new_infections,
        "new_infections_pct": new_infections_pct,
        "N_total": float(N_tot),
    }
