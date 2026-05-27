"""Sidebar: state filter, policy sliders, vaccination baseline, run/reset."""

from __future__ import annotations

import streamlit as st

from src.constants import (
    HORIZON_DEFAULT,
    HORIZON_OPTIONS,
    SIDEBAR_FOOTER,
    SLIDER_MOB,
    SLIDER_VAX,
    SLIDER_VAX_BASELINE,
    STATE_NAMES,
    STATES,
    VACCINATION_BASELINE_DEFAULT,
)


def render() -> dict:
    """Render sidebar widgets and return current control values."""
    with st.sidebar:
        st.markdown(
            '<div class="modr-section-label">Policy controls</div>',
            unsafe_allow_html=True,
        )

        states = st.multiselect(
            "States",
            options=STATES,
            default=STATES,
            format_func=lambda s: STATE_NAMES[s],
        )

        # The auto-optimiser writes its recommended budget to
        # session_state["_vax_pp_pending"] before calling st.rerun(). We must
        # apply it BEFORE the slider widget is instantiated, otherwise
        # Streamlit raises StreamlitAPIException when assigning to a keyed
        # widget's session_state after creation.
        if "_vax_pp_pending" in st.session_state:
            st.session_state["vax_pp"] = st.session_state.pop("_vax_pp_pending")
        if "vax_pp" not in st.session_state:
            st.session_state["vax_pp"] = SLIDER_VAX["default"]
        vax_boost_pp = st.slider(
            "Additional vaccination budget (pp)",
            min_value=SLIDER_VAX["min"],
            max_value=SLIDER_VAX["max"],
            step=SLIDER_VAX["step"],
            key="vax_pp",
            help=(
                "Added on top of the baseline below. The allocation strategy "
                "in the Optimisation panel controls whether this budget is "
                "spread uniformly or routed to high-vulnerability counties."
            ),
        )

        mobility = st.slider(
            "Mobility factor",
            min_value=SLIDER_MOB["min"],
            max_value=SLIDER_MOB["max"],
            value=SLIDER_MOB["default"],
            step=SLIDER_MOB["step"],
            help="1.0 = baseline inter-county mixing. 0.0 = isolated counties.",
        )

        horizon = st.select_slider(
            "Horizon (days)",
            options=HORIZON_OPTIONS,
            value=HORIZON_DEFAULT,
        )

        st.markdown(
            '<div class="modr-section-label" style="margin-top:1.25rem">'
            "Baseline vaccination"
            "</div>",
            unsafe_allow_html=True,
        )

        baseline_overall = st.slider(
            "Overall (% pop)",
            min_value=SLIDER_VAX_BASELINE["min"],
            max_value=SLIDER_VAX_BASELINE["max"],
            value=SLIDER_VAX_BASELINE["default"],
            step=SLIDER_VAX_BASELINE["step"],
            key="baseline_overall",
            help=(
                "Sets the starting vaccinated fraction across all counties. "
                "The Variant-C calibration used 59%; expose this so users can "
                "explore lower- and higher-coverage worlds."
            ),
        )

        per_state_baselines: dict[str, int] = {}
        with st.expander("Per-state baselines (optional)", expanded=False):
            st.caption(
                "Each per-state value overrides the overall baseline for that "
                "state. Leave at the overall value to use it."
            )
            for state in STATES:
                key = f"baseline_{state}"
                if key not in st.session_state:
                    st.session_state[key] = baseline_overall
                val = st.slider(
                    f"{STATE_NAMES[state]} (% pop)",
                    min_value=SLIDER_VAX_BASELINE["min"],
                    max_value=SLIDER_VAX_BASELINE["max"],
                    step=SLIDER_VAX_BASELINE["step"],
                    key=key,
                )
                per_state_baselines[state] = val

        st.write("")
        run_clicked = st.button(
            "Run scenario", type="primary", use_container_width=True
        )
        reset_clicked = st.button(
            "Reset to baseline", type="secondary", use_container_width=True
        )

        st.markdown(
            f"""
            <div style="margin-top: 2rem; font-size: 0.8rem; color: #444444;
                        letter-spacing: 0.04em;">
                {SIDEBAR_FOOTER}
            </div>
            """,
            unsafe_allow_html=True,
        )

    return {
        "states": states,
        "vax_boost": vax_boost_pp / 100.0,
        "vax_boost_pp": vax_boost_pp,
        "mobility": float(mobility),
        "horizon": int(horizon),
        "baseline_overall": int(baseline_overall),
        "per_state_baselines": per_state_baselines,
        "run_clicked": run_clicked,
        "reset_clicked": reset_clicked,
    }
