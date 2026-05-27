"""Sidebar: state filter, policy sliders, run/reset buttons."""

from __future__ import annotations

import streamlit as st

from src.constants import (
    HORIZON_DEFAULT,
    HORIZON_OPTIONS,
    SIDEBAR_FOOTER,
    SLIDER_MOB,
    SLIDER_VAX,
    STATE_NAMES,
    STATES,
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
            "Vaccination budget (percentage points)",
            min_value=SLIDER_VAX["min"],
            max_value=SLIDER_VAX["max"],
            step=SLIDER_VAX["step"],
            key="vax_pp",
            help=(
                "Added on top of the regional 58.9% baseline. The allocation "
                "strategy in the Optimisation panel controls whether this "
                "budget is spread uniformly or routed to high-risk counties."
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
        "run_clicked": run_clicked,
        "reset_clicked": reset_clicked,
    }
