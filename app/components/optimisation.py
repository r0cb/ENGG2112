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
    ALLOCATION_OPTIMAL,
    ALLOCATION_OPTIONS,
    ALLOCATION_TARGETED,
    ALLOCATION_UNIFORM,
    OPTIMISER_BETA_GRID,
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
        # Consume any pending strategy switch staged by the optimiser button
        # before the radio widget below is instantiated, otherwise Streamlit
        # raises StreamlitAPIException for modifying a keyed widget's state
        # after creation.
        pending = st.session_state.pop("_strategy_pending", None)
        if pending is not None:
            st.session_state["strategy_radio"] = pending
        st.markdown(
            '<span class="modr-section-marker optimisation"></span>'
            '<div class="modr-section-box-eyebrow">Optimisation</div>'
            '<div class="modr-section-box-title">Minimise cases at the current budget</div>'
            '<div class="modr-section-box-intro">'
            "Both cards work on the same problem: <b>given a fixed pool of "
            "vaccinations, distribute it so the SIR predicts the fewest "
            "total cases.</b> "
            "Card 01 lets you pick a preset distribution rule by hand. "
            "Card 02 hands the search over to the model: it sweeps a "
            "one-parameter family of allocations and returns the one that "
            "actually minimises cases at your current settings."
            "</div>",
            unsafe_allow_html=True,
        )

        col_strategy, col_optimiser = st.columns(2, gap="medium")

        with col_strategy:
            st.markdown(
                '<div class="modr-opt-card">'
                '<div class="modr-opt-card-header">01 · PICK A RULE</div>'
                '<div class="modr-opt-card-blurb">'
                "<b>Manual presets that distribute the budget by a rule.</b>"
                "<br><br>"
                "<b>Uniform</b> spreads the additional vaccinations evenly — "
                "every county gets the same percentage-point boost. The "
                "no-ML baseline.<br>"
                "<b>Targeted</b> routes the budget proportional to the "
                "XGBoost p_outbreak score, with any overflow above 100% "
                "redistributed to the next-best candidates.<br>"
                "<b>Optimal</b> uses the per-county allocation produced by "
                "Card 02; if you haven't run the optimiser yet, this falls "
                "back to uniform."
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
                "Effect on the model: rescales the per-county "
                "<b>S<sub>0</sub></b> compartment. The total population "
                "vaccinated is preserved; only <em>where</em> the doses land "
                "changes."
                "</div></div>",
                unsafe_allow_html=True,
            )

        with col_optimiser:
            n_betas = len(OPTIMISER_BETA_GRID)
            st.markdown(
                '<div class="modr-opt-card">'
                '<div class="modr-opt-card-header">02 · LET THE MODEL CHOOSE</div>'
                '<div class="modr-opt-card-blurb">'
                "<b>Numerical search for the allocation that minimises "
                "total new infections at the current budget.</b><br><br>"
                "We define a one-parameter family of allocations: each "
                "county gets boost proportional to "
                "<code>p_outbreak<sup>β</sup></code>, with water-fill "
                "redistribution when a county hits 100% coverage. β = 0 "
                f"recovers Uniform; β = 1 recovers Targeted; higher β "
                "concentrates the budget more aggressively on the highest-"
                "vulnerability counties."
                f"<br><br>"
                f"The optimiser sweeps "
                f"<b>{n_betas} values of β</b> and runs the full SIR for "
                "each, then picks the β with the fewest cases. Result is "
                "stored as the <b>Optimal</b> strategy and applied on the "
                "next scenario run."
                "</div>",
                unsafe_allow_html=True,
            )
            optimise_clicked = st.button(
                "Optimise allocation (minimise cases)",
                key="optimise_btn",
                type="primary",
                use_container_width=True,
            )
            st.markdown(
                '<div class="modr-opt-card-effect">'
                f"Effect on the model: runs the SIR {n_betas} times across "
                "different β values, stores the best per-county boost, and "
                "switches the strategy to <b>Optimal</b>."
                "</div></div>",
                unsafe_allow_html=True,
            )

    return {
        "strategy": strategy,
        "optimise_clicked": optimise_clicked,
    }


def render_result(opt_result: dict | None) -> None:
    """Surface the case-minimising optimiser's outcome.

    `opt_result` is the dict produced by find_optimal_allocation, plus an
    extra "uniform_cases" and "targeted_cases" key added by the streamlit
    main flow so we can quantify the gain vs both baselines.
    """
    if not opt_result:
        return
    best_beta = opt_result.get("best_beta")
    best_cases = opt_result.get("best_cases")
    uniform_cases = opt_result.get("uniform_cases")
    targeted_cases = opt_result.get("targeted_cases")
    if best_beta is None:
        return

    parts = [
        f"<b>Optimiser converged at β = {best_beta:g}</b> — that allocation "
        f"produced <b>{int(round(best_cases)):,}</b> total new infections, "
        "the minimum across the swept family."
    ]
    if uniform_cases is not None and uniform_cases > best_cases:
        averted = uniform_cases - best_cases
        parts.append(
            f"vs <b>Uniform</b>: averts <b>{int(round(averted)):,}</b> cases."
        )
    if targeted_cases is not None and targeted_cases > best_cases:
        averted = targeted_cases - best_cases
        parts.append(
            f"vs <b>Targeted</b>: averts <b>{int(round(averted)):,}</b> cases."
        )
    if uniform_cases is not None and targeted_cases is not None and (
        uniform_cases == best_cases or targeted_cases == best_cases
    ):
        parts.append(
            "(The optimum coincides with one of the presets — at these "
            "settings, the simple rule was already optimal within the "
            "β-family searched.)"
        )

    parts.append(
        "The <b>Optimal</b> radio in Card 01 is now selected. Click "
        "<b>Run scenario</b> in the sidebar to play the SIR animation with "
        "this allocation, or open the <b>Vaccination coverage</b> tab to "
        "see where the optimiser routed the doses."
    )

    body = "<br><br>".join(parts)
    st.markdown(
        f'<div class="modr-opt-gain positive">{body}</div>',
        unsafe_allow_html=True,
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
