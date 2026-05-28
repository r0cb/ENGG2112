"""MODR — Respiratory Virus Vulnerability Explorer (Streamlit app)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="MODR — Respiratory Virus Vulnerability Explorer",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={},
)

from app.components import (  # noqa: E402
    confidence,
    header,
    howto,
    map_panel,
    methodology,
    metrics as metrics_component,
    optimisation,
    sidebar,
)
from src.constants import (  # noqa: E402
    ALLOCATION_DEFAULT,
    ALLOCATION_LABELS,
    ALLOCATION_TARGETED,
    ALLOCATION_UNIFORM,
    APP_FOOTER,
    STATES,
)
from src.data_loader import (  # noqa: E402
    apply_baseline,
    apply_seed,
    build_animation_frame,
    load_adjacency,
    load_flu_df,
    load_geojson,
    load_sir_baseline,
)
from src.maps import build_state_summary_bars  # noqa: E402
from src.optimisation import (  # noqa: E402
    targeted_vax_boost,
    vax_boost_for_strategy,
)
from src.sir import aggregate_metrics, run_sir  # noqa: E402


CSS_PATH = PROJECT_ROOT / "app" / "styles" / "main.css"


def _inject_css() -> None:
    with open(CSS_PATH) as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _baseline_key(
    baseline_overall: int, per_state_baselines: dict[str, int]
) -> tuple:
    """Hashable cache-key fragment for the user's chosen baseline V0."""
    return baseline_overall, tuple(sorted(per_state_baselines.items()))


def _flu_with_baseline_and_seed(
    baseline_overall: int,
    per_state_baselines: dict,
    seed_fips: tuple | list | None = None,
) -> "pd.DataFrame":
    flu = apply_baseline(load_flu_df(), baseline_overall, per_state_baselines)
    flu = apply_seed(flu, seed_fips=list(seed_fips) if seed_fips else None)
    return flu


def _effective_seed_fips(flu_df) -> list[str]:
    """The list of counties the SIR is actually seeded in. Mirrors the
    logic in apply_seed: the rows where I_init > 0 after apply_seed runs.
    Used by the map overlay so the visual marker is always correct
    regardless of whether the user is in default or choose mode."""
    return flu_df.loc[flu_df["I_init"] > 0, "fips_str"].tolist()


@st.cache_data(show_spinner=False)
def _baseline_run(
    horizon: int,
    baseline_overall: int,
    baseline_per_state: tuple,
    seed_fips: tuple,
) -> dict:
    flu = _flu_with_baseline_and_seed(
        baseline_overall, dict(baseline_per_state), seed_fips
    )
    adj = load_adjacency()
    return run_sir(flu, adj, T=horizon, vax_boost=0.0, mobility_factor=1.0)


@st.cache_data(show_spinner="Running SIR simulation across 141 counties...")
def _scenario_run(
    vax_boost_pp: int,
    mobility_factor: float,
    horizon: int,
    strategy: str,
    baseline_overall: int,
    baseline_per_state: tuple,
    seed_fips: tuple,
) -> dict:
    flu = _flu_with_baseline_and_seed(
        baseline_overall, dict(baseline_per_state), seed_fips
    )
    adj = load_adjacency()
    total_boost = vax_boost_pp / 100.0
    vb = vax_boost_for_strategy(flu, total_boost, strategy)
    return run_sir(
        flu, adj, T=horizon, vax_boost=vb, mobility_factor=mobility_factor
    )


def _add_v_eff_column(flu, vax_boost_pp, strategy):
    """Annotate the flu DataFrame with V_eff (effective coverage per county)
    for the chosen budget + strategy. Used by the Vaccination tab."""
    flu = flu.copy()
    total_boost = vax_boost_pp / 100.0
    if total_boost <= 0:
        flu["V_eff"] = flu["V0"].clip(0, 1)
        return flu
    vb = vax_boost_for_strategy(flu, total_boost, strategy)
    if isinstance(vb, pd.Series):
        boost_arr = vb.reindex(flu["fips_str"]).fillna(0).values
    else:
        boost_arr = np.full(len(flu), float(vb))
    flu["V_eff"] = np.clip(flu["V0"].values + boost_arr, 0, 1)
    return flu


def main() -> None:
    _inject_css()
    header.render()

    controls = sidebar.render()

    baseline_key = _baseline_key(
        controls["baseline_overall"], controls["per_state_baselines"]
    )
    baseline_overall = controls["baseline_overall"]
    baseline_per_state_tuple = baseline_key[1]

    # Staged = the user's current clicks (visual only). Committed = what the
    # SIR actually uses, only updated when Run scenario is clicked. This
    # separation means each click doesn't force a baseline_run recompute.
    staged_seeds = tuple(sorted(controls.get("seed_counties_staged") or ()))
    committed_seeds = tuple(
        sorted(st.session_state.get("seed_counties_committed", []) or ())
    )

    # flu (used for the SIR baseline metrics + Vaccination tab) uses committed.
    flu = _flu_with_baseline_and_seed(
        baseline_overall, controls["per_state_baselines"], committed_seeds
    )
    geojson = load_geojson()
    selected = controls["states"] or STATES

    strategy = st.session_state.get("strategy", ALLOCATION_DEFAULT)

    # Annotate flu with V_eff for the Vaccination tab. Uses the current slider
    # value so the coverage map updates instantly with the slider.
    flu_with_v_eff = _add_v_eff_column(
        flu, controls["vax_boost_pp"], strategy
    )

    if controls["reset_clicked"]:
        for key in (
            "sim_result",
            "sim_metrics",
            "active_params",
            "counterfactual_metrics",
        ):
            st.session_state.pop(key, None)
        st.session_state["_just_reset"] = True

    if controls["run_clicked"]:
        # Commit any staged click-seeds: they now become the active SIR
        # seeds. The rest of the script uses `committed_seeds` from here.
        st.session_state["seed_counties_committed"] = list(staged_seeds)
        committed_seeds = staged_seeds
        flu = _flu_with_baseline_and_seed(
            baseline_overall, controls["per_state_baselines"], committed_seeds
        )
        sim = _scenario_run(
            controls["vax_boost_pp"],
            controls["mobility"],
            controls["horizon"],
            strategy,
            baseline_overall,
            baseline_per_state_tuple,
            committed_seeds,
        )
        st.session_state["sim_result"] = sim
        st.session_state["sim_metrics"] = aggregate_metrics(sim)
        st.session_state["active_params"] = {
            "vax_boost_pp": controls["vax_boost_pp"],
            "mobility": controls["mobility"],
            "horizon": controls["horizon"],
            "strategy": strategy,
            "baseline_overall": baseline_overall,
            "seed_fips": committed_seeds,
        }
        # Always compute the other strategy's outcome at the same budget so
        # the comparison callout below can quantify the trade-off.
        other_strategy = (
            ALLOCATION_UNIFORM
            if strategy == ALLOCATION_TARGETED
            else ALLOCATION_TARGETED
        )
        other_sim = _scenario_run(
            controls["vax_boost_pp"],
            controls["mobility"],
            controls["horizon"],
            other_strategy,
            baseline_overall,
            baseline_per_state_tuple,
            committed_seeds,
        )
        st.session_state["counterfactual_metrics"] = aggregate_metrics(
            other_sim
        )
        st.session_state.pop("_just_reset", None)

    baseline_sim = _baseline_run(
        controls["horizon"],
        baseline_overall,
        baseline_per_state_tuple,
        committed_seeds,
    )
    baseline_metrics = aggregate_metrics(baseline_sim)

    has_scenario = "sim_result" in st.session_state
    sim = st.session_state.get("sim_result", baseline_sim)
    sim_metrics = st.session_state.get("sim_metrics", baseline_metrics)

    current_focus = st.session_state.get("focused_state")
    if current_focus and current_focus not in selected:
        current_focus = None
        st.session_state.pop("focused_state", None)

    new_focus = confidence.render(selected, current_focus)
    if new_focus != current_focus:
        if new_focus is None:
            st.session_state.pop("focused_state", None)
        else:
            st.session_state["focused_state"] = new_focus
        st.rerun()

    metrics_component.render(
        sim_metrics,
        baseline_metrics if has_scenario else None,
    )

    strategy_label = ALLOCATION_LABELS.get(strategy, strategy).split(" ")[0].lower()

    if has_scenario:
        horizon = st.session_state["active_params"]["horizon"]
        stride = (
            4 if horizon <= 180
            else 6 if horizon <= 270
            else 8 if horizon <= 365
            else 12 if horizon <= 540
            else 16
        )
        frame_days = stride * 0.5
        long_df = build_animation_frame(sim, flu, stride=stride)
        effective_seeds = _effective_seed_fips(flu)
        map_panel.render_animated(
            long_df,
            geojson,
            selected,
            horizon=horizon,
            frame_days=frame_days,
            focused_state=current_focus,
            flu_for_vax=flu_with_v_eff,
            vax_boost_pp=controls["vax_boost_pp"],
            strategy_label=strategy_label,
            seed_fips=effective_seeds,
        )
    else:
        # The static Outbreak Vulnerability map shows STAGED seeds (so the
        # user gets immediate visual feedback on every click), but if the
        # user hasn't queued anything yet, fall back to whatever the SIR is
        # currently running (committed → top-3 default).
        if controls["seed_mode"] == "choose" and staged_seeds:
            display_seeds = list(staged_seeds)
        else:
            display_seeds = _effective_seed_fips(flu)
        map_panel.render_baseline(
            flu_with_v_eff,
            geojson,
            selected,
            focused_state=current_focus,
            vax_boost_pp=controls["vax_boost_pp"],
            strategy_label=strategy_label,
            seed_fips=display_seeds,
        )
        if st.session_state.pop("_just_reset", False):
            st.caption("Viewing baseline scenario (no intervention applied).")

    # === Optimisation panel ===
    opt_controls = optimisation.render_controls()
    # The strategy radio lives in the optimisation panel, which renders AFTER
    # the V_eff calculation and the map. If the user has just toggled the
    # strategy, the rest of the page used the previous value. Trigger one
    # extra rerun so everything sees the new strategy on the next pass.
    if opt_controls["strategy"] != st.session_state.get(
        "_committed_strategy", ALLOCATION_DEFAULT
    ):
        st.session_state["_committed_strategy"] = opt_controls["strategy"]
        st.session_state["strategy"] = opt_controls["strategy"]
        st.rerun()
    if has_scenario:
        # Re-derive primary from the CURRENT radio (not active_params), so
        # the comparison labels stay correct when the user toggles the
        # strategy after a Run without re-running.
        optimisation.render_strategy_comparison(
            current_strategy=strategy,
            run_strategy=st.session_state["active_params"]["strategy"],
            sim_metrics=sim_metrics,
            counterfactual_metrics=st.session_state.get(
                "counterfactual_metrics"
            ),
            baseline_metrics=baseline_metrics,
        )

    howto.render()

    with st.expander("State-level peak infectious breakdown", expanded=False):
        fig = build_state_summary_bars(sim, flu)
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

    methodology.render()

    st.markdown(
        f'<div class="modr-footer">{APP_FOOTER}</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
