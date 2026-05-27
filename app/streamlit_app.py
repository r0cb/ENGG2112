"""MODR — Respiratory Virus Vulnerability Explorer (Streamlit app)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
    map_panel,
    methodology,
    metrics as metrics_component,
    optimisation,
    sidebar,
)
from src.constants import (  # noqa: E402
    ALLOCATION_DEFAULT,
    ALLOCATION_TARGETED,
    ALLOCATION_UNIFORM,
    APP_FOOTER,
    OPTIMISER_PEAK_THRESHOLD_PCT,
    STATES,
)
from src.data_loader import (  # noqa: E402
    build_animation_frame,
    load_adjacency,
    load_flu_df,
    load_geojson,
    load_sir_baseline,
)
from src.maps import build_state_summary_bars  # noqa: E402
from src.optimisation import (  # noqa: E402
    find_min_vax_for_threshold,
    targeted_vax_boost,
    vax_boost_for_strategy,
)
from src.sir import aggregate_metrics, run_sir  # noqa: E402


CSS_PATH = PROJECT_ROOT / "app" / "styles" / "main.css"


def _inject_css() -> None:
    with open(CSS_PATH) as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _baseline_run(horizon: int) -> dict:
    """Cached run at the default policy (V0 baseline, mobility 1.0)."""
    flu = load_flu_df()
    adj = load_adjacency()
    return run_sir(flu, adj, T=horizon, vax_boost=0.0, mobility_factor=1.0)


@st.cache_data(show_spinner="Running SIR simulation across 141 counties...")
def _scenario_run(
    vax_boost_pp: int,
    mobility_factor: float,
    horizon: int,
    strategy: str,
) -> dict:
    """Run SIR under the user's chosen policy + allocation strategy.

    Cache key includes strategy so toggling Uniform↔Targeted reuses results
    instead of recomputing.
    """
    flu = load_flu_df()
    adj = load_adjacency()
    total_boost = vax_boost_pp / 100.0
    vb = vax_boost_for_strategy(flu, total_boost, strategy)
    return run_sir(
        flu, adj, T=horizon, vax_boost=vb, mobility_factor=mobility_factor
    )


@st.cache_data(show_spinner="Searching for the minimum vaccination budget...")
def _optimise_min_vax(
    mobility_factor: float, horizon: int, strategy: str, threshold_pct: float
) -> dict:
    flu = load_flu_df()
    adj = load_adjacency()
    return find_min_vax_for_threshold(
        flu, adj, horizon, mobility_factor, strategy, threshold_pct
    )


def main() -> None:
    _inject_css()
    header.render()

    controls = sidebar.render()

    flu = load_flu_df()
    geojson = load_geojson()
    selected = controls["states"] or STATES

    if controls["reset_clicked"]:
        for key in (
            "sim_result",
            "sim_metrics",
            "active_params",
            "counterfactual_metrics",
            "opt_result",
        ):
            st.session_state.pop(key, None)
        st.session_state["_just_reset"] = True

    if controls["run_clicked"]:
        strategy = st.session_state.get("strategy", ALLOCATION_DEFAULT)
        sim = _scenario_run(
            controls["vax_boost_pp"],
            controls["mobility"],
            controls["horizon"],
            strategy,
        )
        st.session_state["sim_result"] = sim
        st.session_state["sim_metrics"] = aggregate_metrics(sim)
        st.session_state["active_params"] = {
            "vax_boost_pp": controls["vax_boost_pp"],
            "mobility": controls["mobility"],
            "horizon": controls["horizon"],
            "strategy": strategy,
        }
        # Always also compute the uniform counterfactual at the same budget so
        # the optimisation gain callout has something to compare against.
        if strategy == ALLOCATION_TARGETED:
            uniform_sim = _scenario_run(
                controls["vax_boost_pp"],
                controls["mobility"],
                controls["horizon"],
                ALLOCATION_UNIFORM,
            )
            st.session_state["counterfactual_metrics"] = aggregate_metrics(
                uniform_sim
            )
        else:
            st.session_state.pop("counterfactual_metrics", None)
        st.session_state.pop("_just_reset", None)

    baseline_sim = _baseline_run(controls["horizon"])
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

    if has_scenario:
        horizon = st.session_state["active_params"]["horizon"]
        stride = 4 if horizon <= 180 else (6 if horizon <= 270 else 8)
        frame_days = stride * 0.5
        long_df = build_animation_frame(sim, flu, stride=stride)
        map_panel.render_animated(
            long_df,
            geojson,
            selected,
            horizon=horizon,
            frame_days=frame_days,
            focused_state=current_focus,
        )
    else:
        map_panel.render_baseline(
            flu, geojson, selected, focused_state=current_focus
        )
        if st.session_state.pop("_just_reset", False):
            st.caption("Viewing baseline scenario (no intervention applied).")

    # === Optimisation panel ===
    opt_controls = optimisation.render_controls()
    if opt_controls["optimise_clicked"]:
        opt_result = _optimise_min_vax(
            controls["mobility"],
            controls["horizon"],
            opt_controls["strategy"],
            OPTIMISER_PEAK_THRESHOLD_PCT,
        )
        st.session_state["opt_result"] = opt_result
        if opt_result["optimal_pp"] is not None:
            # Stage the override; the sidebar consumes it on the NEXT render,
            # before instantiating the slider widget. Direct assignment after
            # widget creation raises StreamlitAPIException.
            st.session_state["_vax_pp_pending"] = int(opt_result["optimal_pp"])
            st.rerun()
    optimisation.render_result(
        st.session_state.get("opt_result"), opt_controls["strategy"]
    )

    if has_scenario:
        optimisation.render_strategy_gain(
            st.session_state["active_params"]["strategy"],
            sim_metrics,
            st.session_state.get("counterfactual_metrics"),
        )

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
