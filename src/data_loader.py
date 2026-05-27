"""Cached loaders for SIR baseline, GeoJSON, model artifact."""

from __future__ import annotations

import json
import pickle
from collections import defaultdict

import numpy as np
import pandas as pd
import requests
import streamlit as st

from src.constants import (
    GEOJSON_URL,
    MODEL_PATH,
    SIR_RESULTS_PATH,
    STATE_FIPS_PREFIXES,
)
from src.sir import GAMMA


@st.cache_resource
def load_sir_baseline() -> dict:
    """Parse models/sir_results.json. Adjacency is left as a list of pairs;
    use `load_adjacency()` for the folded dict."""
    with open(SIR_RESULTS_PATH) as f:
        return json.load(f)


@st.cache_resource
def load_flu_df() -> pd.DataFrame:
    """Reconstruct the per-county DataFrame expected by run_sir.

    Seeds I_init = 10 in the top-3 counties by p_outbreak (NB09 cell 8 convention).
    """
    sir = load_sir_baseline()
    flu = pd.DataFrame(
        [
            {
                "fips_str": c["fips"],
                "county": c["county"],
                "state": c["state"],
                "N": float(c["pop_total"]),
                "V0": c["pct_vaccinated"] / 100,
                "p_outbreak": c["p_outbreak"],
                "beta": c["beta"],
                "gamma": c["gamma"] if c.get("gamma") else GAMMA,
                "peak_infected_pct_baseline": c["peak_infected_pct"],
            }
            for c in sir["counties"]
        ]
    )
    flu["I_init"] = 0.0
    top3 = flu.nlargest(3, "p_outbreak").index
    flu.loc[top3, "I_init"] = 10.0
    return flu


@st.cache_resource
def load_adjacency() -> dict:
    """Fold the list of [a, b] pairs in sir_results.json into an undirected dict."""
    sir = load_sir_baseline()
    adj = defaultdict(list)
    for a, b in sir["adjacency"]:
        adj[a].append(b)
        adj[b].append(a)
    return dict(adj)


@st.cache_resource
def load_geojson() -> dict:
    """Fetch the Plotly county GeoJSON and filter to NY/PA/CT/DE features only."""
    resp = requests.get(GEOJSON_URL, timeout=30)
    resp.raise_for_status()
    full = resp.json()
    return {
        "type": "FeatureCollection",
        "features": [
            f for f in full["features"] if f["id"][:2] in STATE_FIPS_PREFIXES
        ],
    }


@st.cache_resource
def load_model_artifact() -> dict:
    """Load the production XGBoost artifact. Used in the Methodology section only."""
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def apply_baseline(
    flu_df: pd.DataFrame,
    overall_pct: float,
    per_state_pct: dict | None = None,
) -> pd.DataFrame:
    """Return a copy of `flu_df` with the V0 column rewritten to reflect the
    user's chosen baseline vaccination assumptions.

    overall_pct sets a uniform baseline across all 141 counties. If
    per_state_pct is provided, each state in the dict overrides the overall
    value for its rows. Values are expected as percentages (0-100); they get
    divided by 100 internally to match the fractional V0 the SIR uses.
    """
    out = flu_df.copy()
    out["V0"] = float(overall_pct) / 100.0
    if per_state_pct:
        for state, pct in per_state_pct.items():
            if pct is None or pct == overall_pct:
                # Skip identity overrides so a per-state slider that matches
                # the overall doesn't accidentally pin the value when the user
                # changes the overall slider afterwards.
                continue
            out.loc[out["state"] == state, "V0"] = float(pct) / 100.0
    return out


def baseline_seeded_fips(flu: pd.DataFrame) -> list:
    """Return the 3 fips that get I_init seeding (top 3 by p_outbreak)."""
    return flu.loc[flu["I_init"] > 0, "fips_str"].tolist()


def build_animation_frame(sim: dict, flu: pd.DataFrame, stride: int = 4) -> pd.DataFrame:
    """Convert a sim result into a long-form DataFrame for px.choropleth animation.

    Stride 4 over the 361-point 0.5-day series gives ~91 frames at 2-day resolution.
    """
    t = sim["t"][::stride]
    I = sim["I"][:, ::stride]
    N = sim["N"]
    I_pct = (I / N[:, None]) * 100

    fips_order = sim["fips_order"]
    flu_indexed = flu.set_index("fips_str")

    rows = []
    for ci, fips in enumerate(fips_order):
        row = flu_indexed.loc[fips]
        for ti, day in enumerate(t):
            rows.append(
                {
                    "fips": fips,
                    "county": row["county"],
                    "state": row["state"],
                    "day": float(day),
                    "I_pct": float(I_pct[ci, ti]),
                    "vax_pct": float(row["V0"] * 100),
                    "p_outbreak": float(row["p_outbreak"]),
                }
            )
    return pd.DataFrame(rows)
