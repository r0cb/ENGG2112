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
      [ off-white container, sectioned off from the map above ]
        OPTIMISATION
        intro framing both cards around the same goal: minimise cases
        [ Strategy card ]   [ Auto-optimiser card ]

    The optimiser button only sets a session_state flag; the streamlit_app
    main flow inspects that flag, runs the grid search (cached), and writes
    the result back to the vaccination slider.
    """
    panel = st.container(border=True)
    with panel:
        st.markdown(
            '<span class="modr-section-marker optimisation"></span>'
            '<div class="modr-section-box-eyebrow">Optimisation</div>'
            '<div class="modr-section-box-title">Two questions the model can answer</div>'
            '<div class="modr-section-box-intro">'
            "<b>Both controls below share the same goal: minimise total "
            "cases.</b> They answer different questions about how to get there. "
            "Card 01 asks: <em>given a fixed vaccination budget, how should "
            "I distribute it?</em> Card 02 asks: <em>how small a budget can "
            "I get away with and still keep the outbreak under control?</em>"
            "</div>",
            unsafe_allow_html=True,
        )

        col_strategy, col_optimiser = st.columns(2, gap="medium")

        with col_strategy:
            st.markdown(
                '<div class="modr-opt-card">'
                '<div class="modr-opt-card-header">01 · ALLOCATION STRATEGY</div>'
                '<div class="modr-opt-card-blurb">'
                "<b>Goal:</b> minimise cases at the current budget.<br><br>"
                "Both options spend the <em>same fixed pool</em> of "
                "vaccinations — they just distribute it differently. "
                "<b>Uniform</b> is the simple baseline: every county gets "
                "the same percentage-point increase, ignoring vulnerability. "
                "<b>Targeted</b> is the ML-guided heuristic: it routes more "
                "doses to high-vulnerability counties (proportional to "
                "XGBoost p_outbreak), redistributing leftover from any county "
                "that hits 100%. Which one actually wins on cases depends on "
                "your baseline, budget, and mobility — toggle and compare."
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
                '<div class="modr-opt-card-header">02 · BUDGET OPTIMISER</div>'
                f'<div class="modr-opt-card-blurb">'
                "<b>Goal:</b> spend as few doses as possible while still "
                "controlling the outbreak.<br><br>"
                "Finds the <b>smallest vaccination budget</b> that keeps the "
                "regional epidemic peak below "
                f"<b>{OPTIMISER_PEAK_THRESHOLD_PCT:.2f}% of population</b>, "
                "given the current mobility factor and allocation strategy. "
                "Sweeps the budget from 0 to 40pp in 2pp steps and picks the "
                "minimum that clears the threshold — the leanest plan still "
                "safe enough."
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
                "Effect on the model: re-runs the SIR ~21 times across "
                "vaccination values and writes the optimal budget back to "
                "the sidebar slider."
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
    """Render a side-by-side comparison of the two allocation strategies at
    the current scenario settings. Always shown when a scenario is active so
    the user can see at a glance which strategy actually minimises cases for
    this configuration.
    """
    if counterfactual_metrics is None:
        return
    # Normalise: figure out which strategy is the "other" one
    other_strategy = (
        ALLOCATION_UNIFORM
        if primary_strategy == ALLOCATION_TARGETED
        else ALLOCATION_TARGETED
    )
    primary_cases = primary_metrics["new_infections"]
    other_cases = counterfactual_metrics["new_infections"]
    primary_label = ALLOCATION_LABELS[primary_strategy].split(" ")[0]
    other_label = ALLOCATION_LABELS[other_strategy].split(" ")[0]

    delta = other_cases - primary_cases  # +ve means primary is better

    if abs(delta) < 1:
        st.markdown(
            '<div class="modr-opt-gain neutral">'
            "<b>Strategy comparison.</b> "
            f"At this configuration, <b>{primary_label}</b> and "
            f"<b>{other_label}</b> produce nearly identical case totals. "
            "The allocation lever has more impact at moderate budgets and "
            "with lower baseline vaccination — try changing those."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    if delta > 0:
        # Primary strategy is winning
        st.markdown(
            f'<div class="modr-opt-gain positive">'
            f"<b>Strategy comparison — {primary_label} wins.</b><br>"
            f"At the current budget and baseline, your chosen "
            f"<b>{primary_label}</b> allocation averts "
            f"<b>{int(round(delta)):,}</b> more cases than the "
            f"alternative <b>{other_label}</b> would have at the same total "
            f"budget. Both strategies pursue case minimisation; this one is "
            f"the better tool for the current configuration."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        # Other strategy would have won — surface the insight
        if primary_strategy == ALLOCATION_TARGETED:
            insight = (
                "Targeting concentrated doses on already-well-vaccinated "
                "high-vulnerability counties, where the marginal vaccine has "
                "diminishing returns. Uniform spread doses to less-vaccinated "
                "counties, where each additional dose moved the population "
                "closer to herd immunity. <br><br><b>Takeaway:</b> at high "
                "baseline coverage, floor matters more than ceiling. Try "
                "lowering the baseline slider — targeted should flip back "
                "to winning."
            )
        else:
            insight = (
                "Targeting routed more doses to the densest, highest-contact "
                "counties — exactly the ones the SIR is most sensitive to. "
                "The ML signal is paying off here."
            )
        st.markdown(
            f'<div class="modr-opt-gain negative">'
            f"<b>Strategy comparison — {other_label} would have done better.</b>"
            f"<br>"
            f"Switching to <b>{other_label}</b> at the same total budget would "
            f"avert <b>{int(round(-delta)):,}</b> more cases than your current "
            f"<b>{primary_label}</b> choice. "
            f"{insight}"
            "</div>",
            unsafe_allow_html=True,
        )
