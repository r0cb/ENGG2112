"""Vaccine distribution panel.

Simple two-strategy chooser presented as:
  [ off-white container ]
    Eyebrow + title + brief intro
    Radio (Uniform | Vulnerability-weighted)       ← top, prominent
    Two side-by-side explanation cards            ← below the choice
"""

from __future__ import annotations

import streamlit as st

from src.constants import (
    ALLOCATION_DEFAULT,
    ALLOCATION_LABELS,
    ALLOCATION_OPTIONS,
    ALLOCATION_TARGETED,
    ALLOCATION_UNIFORM,
)


def render_controls() -> dict:
    """Render the vaccine distribution panel and return the user's choice."""
    panel = st.container(border=True)
    with panel:
        # Pending strategy switches from external triggers (none today, but
        # the staging hook is kept for future use) are consumed before the
        # radio widget mounts.
        pending = st.session_state.pop("_strategy_pending", None)
        if pending is not None:
            st.session_state["strategy_radio"] = pending

        st.markdown(
            '<span class="modr-section-marker optimisation"></span>'
            '<div class="modr-section-box-eyebrow">Vaccine distribution</div>'
            '<div class="modr-section-box-title">How should the budget be spread?</div>'
            '<div class="modr-section-box-intro">'
            "Pick a rule for spreading the <b>Additional vaccination budget</b> "
            "(set in the sidebar) across the 141 counties. Both rules spend "
            "the <em>same</em> total number of doses — they differ only in "
            "<em>where</em> those doses land. The simulator below uses your "
            "choice to compute the outbreak curve and the metric deltas."
            "</div>",
            unsafe_allow_html=True,
        )

        strategy = st.radio(
            "Distribution strategy",
            options=ALLOCATION_OPTIONS,
            index=ALLOCATION_OPTIONS.index(
                st.session_state.get("strategy", ALLOCATION_DEFAULT)
            ),
            format_func=lambda s: ALLOCATION_LABELS[s],
            horizontal=True,
            label_visibility="collapsed",
            key="strategy_radio",
        )
        st.session_state["strategy"] = strategy

        st.markdown(
            '<hr class="modr-section-divider" />', unsafe_allow_html=True
        )

        col_uniform, col_targeted = st.columns(2, gap="medium")

        active_uniform = strategy == ALLOCATION_UNIFORM
        active_targeted = strategy == ALLOCATION_TARGETED

        with col_uniform:
            badge = (
                '<span class="modr-opt-card-active-badge">Active</span>'
                if active_uniform
                else ""
            )
            st.markdown(
                f'<div class="modr-opt-card {"is-active" if active_uniform else ""}">'
                f'<div class="modr-opt-card-header">'
                f"Uniform distribution {badge}"
                "</div>"
                '<div class="modr-opt-card-blurb">'
                "<b>Every county gets the same percentage-point boost.</b> "
                "If the slider is set to +10pp, every county lifts its "
                "vaccinated fraction by 10pp — NYC, rural PA, every county "
                "treated identically. This is the no-ML baseline: it ignores "
                "the vulnerability score entirely.<br><br>"
                "<b>When it tends to win:</b> when baseline coverage is low. "
                "Lifting the floor across the whole region matters more "
                "than topping up already-protected places."
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        with col_targeted:
            badge = (
                '<span class="modr-opt-card-active-badge">Active</span>'
                if active_targeted
                else ""
            )
            st.markdown(
                f'<div class="modr-opt-card {"is-active" if active_targeted else ""}">'
                f'<div class="modr-opt-card-header">'
                f"Vulnerability-weighted distribution {badge}"
                "</div>"
                '<div class="modr-opt-card-blurb">'
                "<b>Counties with higher predicted outbreak risk get more "
                "of the budget.</b> Each county's share is proportional to "
                "its XGBoost p_outbreak score. If a county would be pushed "
                "above 100% coverage, its leftover doses spill back into "
                "the pool and go to the next-best candidate — no vaccines "
                "wasted.<br><br>"
                "<b>When it tends to win:</b> when baseline coverage is "
                "already moderate-to-high. Concentrating extra doses on "
                "dense, high-contact counties stops outbreaks at their "
                "predicted origins."
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="modr-opt-footnote">'
            "Run a scenario after switching strategies to see the case "
            "comparison appear below — the model tells you which one wins "
            "for your specific settings."
            "</div>",
            unsafe_allow_html=True,
        )

    return {"strategy": strategy}


def render_strategy_gain(
    primary_strategy: str,
    primary_metrics: dict,
    counterfactual_metrics: dict | None,
) -> None:
    """Side-by-side comparison: how many cases each strategy would have
    produced at the current settings. Always shown when a scenario is
    active.
    """
    if counterfactual_metrics is None:
        return
    other_strategy = (
        ALLOCATION_UNIFORM
        if primary_strategy == ALLOCATION_TARGETED
        else ALLOCATION_TARGETED
    )
    primary_cases = primary_metrics["new_infections"]
    other_cases = counterfactual_metrics["new_infections"]
    primary_label = ALLOCATION_LABELS[primary_strategy]
    other_label = ALLOCATION_LABELS[other_strategy]

    delta = other_cases - primary_cases  # +ve means primary is better

    if abs(delta) < 1:
        st.markdown(
            '<div class="modr-opt-gain neutral">'
            "<b>Strategy comparison.</b> "
            f"<b>{primary_label}</b> and <b>{other_label}</b> produce nearly "
            "identical case totals at these settings. The choice of "
            "distribution rule matters more at moderate budgets and with "
            "non-uniform baseline coverage."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    if delta > 0:
        # Active strategy wins
        st.markdown(
            f'<div class="modr-opt-gain positive">'
            f"<b>Strategy comparison — {primary_label} wins.</b><br>"
            f"At the current budget and baseline, your chosen "
            f"<b>{primary_label}</b> averts "
            f"<b>{int(round(delta)):,}</b> more cases than "
            f"<b>{other_label}</b> would have at the same total budget."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        if primary_strategy == ALLOCATION_TARGETED:
            insight = (
                "Targeting concentrated doses on already-well-vaccinated "
                "high-vulnerability counties, where the marginal vaccine "
                "has diminishing returns. Uniform reached less-vaccinated "
                "counties, where each dose moved the population closer to "
                "herd immunity. Try lowering the baseline slider — "
                "vulnerability-weighting should flip back to winning."
            )
        else:
            insight = (
                "Vulnerability weighting routed more doses to the densest, "
                "highest-contact counties — exactly the ones the SIR is "
                "most sensitive to."
            )
        st.markdown(
            f'<div class="modr-opt-gain negative">'
            f"<b>Strategy comparison — {other_label} would have done better.</b>"
            f"<br>Switching to <b>{other_label}</b> at the same total "
            f"budget would avert <b>{int(round(-delta)):,}</b> more cases "
            f"than your current <b>{primary_label}</b> choice.<br><br>"
            f"{insight}"
            "</div>",
            unsafe_allow_html=True,
        )
