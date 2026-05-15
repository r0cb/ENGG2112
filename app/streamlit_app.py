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
    sidebar,
)
from src.constants import APP_FOOTER, STATES  # noqa: E402
from src.data_loader import (  # noqa: E402
    build_animation_frame,
    load_adjacency,
    load_flu_df,
    load_geojson,
    load_sir_baseline,
)
from src.maps import build_state_summary_bars  # noqa: E402
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
def _scenario_run(vax_boost: float, mobility_factor: float, horizon: int) -> dict:
    flu = load_flu_df()
    adj = load_adjacency()
    return run_sir(
        flu, adj, T=horizon, vax_boost=vax_boost, mobility_factor=mobility_factor
    )


def main() -> None:
    _inject_css()
    header.render()

    controls = sidebar.render()

    flu = load_flu_df()
    geojson = load_geojson()
    selected = controls["states"] or STATES

    if controls["reset_clicked"]:
        for key in ("sim_result", "sim_metrics", "active_params"):
            st.session_state.pop(key, None)

    if controls["run_clicked"]:
        sim = _scenario_run(
            controls["vax_boost"], controls["mobility"], controls["horizon"]
        )
        st.session_state["sim_result"] = sim
        st.session_state["sim_metrics"] = aggregate_metrics(sim)
        st.session_state["active_params"] = {
            "vax_boost_pp": controls["vax_boost_pp"],
            "mobility": controls["mobility"],
            "horizon": controls["horizon"],
        }

    baseline_sim = _baseline_run(controls["horizon"])
    baseline_metrics = aggregate_metrics(baseline_sim)

    has_scenario = "sim_result" in st.session_state
    sim = st.session_state.get("sim_result", baseline_sim)
    sim_metrics = st.session_state.get("sim_metrics", baseline_metrics)

    confidence.render(selected)

    metrics_component.render(
        sim_metrics,
        baseline_metrics if has_scenario else None,
    )

    if has_scenario:
        long_df = build_animation_frame(sim, flu, stride=4)
        map_panel.render_animated(
            long_df,
            geojson,
            selected,
            horizon=st.session_state["active_params"]["horizon"],
        )
    else:
        map_panel.render_baseline(flu, geojson, selected)

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
