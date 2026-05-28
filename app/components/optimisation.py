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


def render_strategy_comparison(
    current_strategy: str,
    run_strategy: str,
    sim_metrics: dict,
    counterfactual_metrics: dict | None,
    baseline_metrics: dict | None,
) -> None:
    """Card-style side-by-side comparison of Uniform vs Vulnerability-weighted
    at the current scenario settings.

    The visual is two stat cards above a prose summary. Each card shows the
    strategy's total new infections, the percentage reduction vs the no-
    intervention baseline (so the absolute value of intervening shows), and
    flags for "Selected" (current radio) and "Winner" (fewer cases).

    The labels are derived from `current_strategy` — what the radio shows
    *right now* — not from `run_strategy`. This fixes the stale-state bug
    where toggling the radio after a Run kept the previous selection
    labelled as the user's choice.
    """
    if counterfactual_metrics is None or baseline_metrics is None:
        return

    # Figure out which metrics belong to which strategy. sim_metrics was
    # computed at run_strategy; counterfactual_metrics at the OTHER strategy.
    if run_strategy == ALLOCATION_UNIFORM:
        uniform_m = sim_metrics
        vuln_m = counterfactual_metrics
    else:
        uniform_m = counterfactual_metrics
        vuln_m = sim_metrics

    baseline_cases = float(baseline_metrics["new_infections"])
    uniform_cases = float(uniform_m["new_infections"])
    vuln_cases = float(vuln_m["new_infections"])

    def _pct_vs_baseline(cases: float) -> float:
        if baseline_cases <= 0:
            return 0.0
        return (baseline_cases - cases) / baseline_cases * 100.0

    uniform_pct = _pct_vs_baseline(uniform_cases)
    vuln_pct = _pct_vs_baseline(vuln_cases)
    winner = (
        ALLOCATION_UNIFORM
        if uniform_cases < vuln_cases
        else ALLOCATION_TARGETED
        if vuln_cases < uniform_cases
        else None
    )
    same = abs(uniform_cases - vuln_cases) < 1

    def _badges(strategy_key: str) -> str:
        bits = []
        if strategy_key == current_strategy:
            bits.append(
                '<span class="modr-cmp-badge modr-cmp-badge-selected">'
                "Your selection</span>"
            )
        if winner == strategy_key and not same:
            bits.append(
                '<span class="modr-cmp-badge modr-cmp-badge-winner">'
                "Fewer cases</span>"
            )
        return "".join(bits)

    def _card(strategy_key: str, cases: float, pct_reduction: float) -> str:
        label = ALLOCATION_LABELS[strategy_key]
        is_current = strategy_key == current_strategy
        is_winner = winner == strategy_key and not same
        cls = "modr-cmp-card"
        if is_current:
            cls += " is-selected"
        if is_winner:
            cls += " is-winner"
        return (
            f'<div class="{cls}">'
            f'<div class="modr-cmp-card-title">{label}</div>'
            f'<div class="modr-cmp-card-cases">'
            f"{int(round(cases)):,}<span class='modr-cmp-card-cases-unit'>"
            "total new infections</span></div>"
            f'<div class="modr-cmp-card-pct">'
            f"<b>−{pct_reduction:.1f}%</b> vs no-intervention baseline "
            f"({int(round(baseline_cases)):,} cases)"
            "</div>"
            f'<div class="modr-cmp-card-badges">{_badges(strategy_key)}</div>'
            "</div>"
        )

    cards = _card(ALLOCATION_UNIFORM, uniform_cases, uniform_pct) + _card(
        ALLOCATION_TARGETED, vuln_cases, vuln_pct
    )

    # Prose summary anchored to the current radio.
    if same:
        prose = (
            "<b>The two strategies produce near-identical totals at these "
            "settings.</b> Allocation matters more at moderate budgets and "
            "with lower baseline coverage — try moving those sliders to "
            "see the gap open up."
        )
    else:
        winner_label = ALLOCATION_LABELS[winner]
        loser_label = ALLOCATION_LABELS[
            ALLOCATION_UNIFORM
            if winner == ALLOCATION_TARGETED
            else ALLOCATION_TARGETED
        ]
        winner_cases = uniform_cases if winner == ALLOCATION_UNIFORM else vuln_cases
        loser_cases = vuln_cases if winner == ALLOCATION_UNIFORM else uniform_cases
        delta_cases = loser_cases - winner_cases
        rel_pct = (
            (delta_cases / loser_cases) * 100.0 if loser_cases > 0 else 0.0
        )
        current_is_winner = current_strategy == winner
        if current_is_winner:
            prose = (
                f"<b>{winner_label}</b> — your current choice — averts "
                f"<b>{int(round(delta_cases)):,}</b> more cases than "
                f"<b>{loser_label}</b> would at the same budget, a "
                f"<b>{rel_pct:.1f}%</b> reduction in cases versus the "
                "alternative rule. Keep this strategy active for the "
                "current settings."
            )
        else:
            prose = (
                f"<b>{winner_label}</b> averts "
                f"<b>{int(round(delta_cases)):,}</b> more cases than your "
                f"current <b>{loser_label}</b> selection — a "
                f"<b>{rel_pct:.1f}%</b> improvement on cases. Toggle the "
                "radio above to switch."
            )

    st.markdown(
        '<div class="modr-cmp-section">'
        '<div class="modr-cmp-header">Strategy comparison at this budget</div>'
        f'<div class="modr-cmp-cards">{cards}</div>'
        f'<div class="modr-cmp-prose">{prose}</div>'
        '<div class="modr-cmp-math">'
        "<b>How these numbers are computed.</b> "
        "Each card runs the full SIR over the chosen horizon with that "
        "strategy's per-county boost. <b>−X.X% vs baseline</b> = "
        "(baseline cases − strategy cases) / baseline cases. <b>Y.Y% "
        "improvement vs the alternative</b> = (alt-strategy cases − chosen-"
        "strategy cases) / alt-strategy cases. Baseline = no intervention "
        "(0 budget, full mobility) at the current vaccination baseline."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
