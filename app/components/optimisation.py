"""Optimisation panel: dedicated section that makes the 'O' in MODR
visible. Sits below the map and exposes the two intervention-allocation
levers — strategy choice and auto-optimiser — with plain-language
explanations of what each lever does to the simulator output.
"""

from __future__ import annotations

import streamlit as st

from src.constants import (
    ALLOCATION_DEFAULT,
    ALLOCATION_LABELS,
    ALLOCATION_OPTIONS,
    ALLOCATION_TARGETED,
    ALLOCATION_UNIFORM,
    OPTIMISER_PEAK_THRESHOLD_PCT,
)


def render_controls() -> dict:
    """Render the two-card optimisation panel and return the user's choices.

    Layout:
      OPTIMISATION
      brief one-line description
      [ Strategy card ]   [ Auto-optimiser card ]

    The optimiser button only sets a session_state flag; the streamlit_app
    main flow inspects that flag, runs the grid search (cached), and writes
    the result back to the vaccination slider.
    """
    st.markdown(
        '<div class="modr-section-label">Optimisation</div>'
        '<div class="modr-optimisation-intro">'
        "MODR's vulnerability score is not just a prediction — it is an "
        "allocation signal. The controls below turn that signal into "
        "decisions about <em>how</em> intervention budget should be spent."
        "</div>",
        unsafe_allow_html=True,
    )

    col_strategy, col_optimiser = st.columns(2, gap="medium")

    with col_strategy:
        st.markdown(
            '<div class="modr-opt-card">'
            '<div class="modr-opt-card-header">ALLOCATION STRATEGY</div>'
            '<div class="modr-opt-card-blurb">'
            "Same total vaccination budget, distributed differently. "
            "<b>Uniform</b> adds the boost equally to every county. "
            "<b>Targeted</b> routes the same number of vaccinations "
            "preferentially to high-vulnerability counties, proportional to "
            "their XGBoost p_outbreak score."
            "</div>",
            unsafe_allow_html=True,
        )
        strategy = st.radio(
            "Allocation strategy",
            options=ALLOCATION_OPTIONS,
            index=ALLOCATION_OPTIONS.index(
                st.session_state.get("strategy", ALLOCATION_DEFAULT)
            ),
            format_func=lambda s: ALLOCATION_LABELS[s],
            label_visibility="collapsed",
            key="strategy_radio",
        )
        st.session_state["strategy"] = strategy
        st.markdown(
            '<div class="modr-opt-card-effect">'
            "Effect on the model: rescales the per-county <b>S<sub>0</sub></b> "
            "compartment. The total population vaccinated stays constant; only "
            "<em>where</em> those vaccines land changes."
            "</div></div>",
            unsafe_allow_html=True,
        )

    with col_optimiser:
        st.markdown(
            '<div class="modr-opt-card">'
            '<div class="modr-opt-card-header">AUTO-OPTIMISE</div>'
            f'<div class="modr-opt-card-blurb">'
            f"Find the <b>smallest vaccination budget</b> that keeps the "
            f"regional epidemic peak below "
            f"<b>{OPTIMISER_PEAK_THRESHOLD_PCT:.2f}% of population</b>, given "
            "the current mobility factor and allocation strategy. "
            "Sweeps the budget in 2pp steps and picks the minimum that "
            "clears the threshold."
            "</div>",
            unsafe_allow_html=True,
        )
        optimise_clicked = st.button(
            "Find minimum vaccination budget",
            key="optimise_btn",
            type="primary",
            use_container_width=True,
        )
        st.markdown(
            '<div class="modr-opt-card-effect">'
            "Effect on the model: re-runs the SIR ~21 times across vaccination "
            "values and writes the optimal value back to the sidebar slider."
            "</div></div>",
            unsafe_allow_html=True,
        )

    return {
        "strategy": strategy,
        "optimise_clicked": optimise_clicked,
    }


def render_result(opt_result: dict | None, strategy: str) -> None:
    """Render the result of the most recent auto-optimiser run, if any."""
    if not opt_result:
        return
    optimal = opt_result.get("optimal_pp")
    threshold = opt_result.get("threshold_pct", OPTIMISER_PEAK_THRESHOLD_PCT)
    if optimal is None:
        st.warning(
            f"No vaccination budget in the 0-40pp range kept peak infection "
            f"below {threshold:.2f}%. Try lowering the mobility factor as well."
        )
        return
    strategy_label = ALLOCATION_LABELS.get(strategy, strategy)
    st.success(
        f"**Optimal budget under {strategy_label}**: +{optimal} pp keeps "
        f"peak infection at or below {threshold:.2f}% of population. "
        "The sidebar vaccination slider has been set to this value — click "
        "**Run scenario** to play the simulation."
    )


def render_strategy_gain(
    primary_strategy: str,
    primary_metrics: dict,
    counterfactual_metrics: dict | None,
) -> None:
    """If the user picked the targeted strategy, show how many more cases
    that targeted allocation averted vs the uniform alternative at the same
    total budget."""
    if primary_strategy != ALLOCATION_TARGETED or counterfactual_metrics is None:
        return
    delta = (
        counterfactual_metrics["new_infections"] - primary_metrics["new_infections"]
    )
    if abs(delta) < 1:
        st.markdown(
            '<div class="modr-opt-gain neutral">'
            "Targeted vs uniform allocation: no measurable difference at this "
            "budget. The allocation lever bites harder at moderate budgets."
            "</div>",
            unsafe_allow_html=True,
        )
        return
    if delta > 0:
        st.markdown(
            f'<div class="modr-opt-gain positive">'
            f"<b>Optimisation gain.</b> Targeted allocation averted "
            f"<b>{int(round(delta)):,}</b> additional cases compared to "
            "uniform allocation at the same total vaccination budget."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="modr-opt-gain negative">'
            f"At this budget, the targeted strategy added "
            f"<b>{int(round(-delta)):,}</b> cases versus uniform — likely a "
            "boundary effect where the targeted vaccinations crowd already-"
            "well-vaccinated counties. Try a lower budget."
            "</div>",
            unsafe_allow_html=True,
        )
