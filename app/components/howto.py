"""How it works panel: a brief onboarding section for first-time visitors.

Sits at the bottom of the main column, after the optimisation panel and
before the methodology expander. Four numbered cards walk through the
intended user flow: set scenario → design intervention → read outcome →
optimise.
"""

from __future__ import annotations

import streamlit as st


_STEPS = [
    (
        "Set the scenario",
        "Sidebar",
        "Pick which states to model, set the baseline vaccination rate "
        "(overall and per state), choose how connected counties are "
        "(<b>mobility factor</b>) and how many days to simulate "
        "(<b>horizon</b>).",
    ),
    (
        "Add a vaccination budget",
        "Sidebar",
        "Use the <b>Additional vaccination budget</b> slider to set a "
        "fixed pool of doses, expressed as a percentage of regional "
        "population. At +10pp, that's roughly 4 million doses across the "
        "four states combined.",
    ),
    (
        "Pick a distribution strategy",
        "Vaccine distribution panel",
        "Choose <b>Uniform</b> (every county gets the same percentage-point "
        "boost) or <b>Vulnerability-weighted</b> (counties with higher "
        "predicted outbreak risk get more, with overflow redistributed if "
        "any county hits 100% coverage).",
    ),
    (
        "Read the outcome",
        "Map tabs + metric cards + comparison",
        "Click <b>Run scenario</b>, then watch the Outbreak tab animate "
        "and switch to the Vaccination tab to see how your doses were "
        "distributed. Below the map, a comparison callout tells you which "
        "strategy would have minimised cases at these settings.",
    ),
]


def render() -> None:
    panel = st.container(border=True)
    with panel:
        st.markdown(
            '<span class="modr-section-marker howto"></span>'
            '<div class="modr-section-box-eyebrow">How it works</div>'
            '<div class="modr-section-box-title">A four-step tour of the tool</div>'
            '<div class="modr-section-box-intro">'
            "First time on this page? MODR is a two-stage tool: an "
            "<b>XGBoost vulnerability model</b> ranks 141 counties across "
            "NY, PA, CT, DE by predicted outbreak risk, and a per-county "
            "<b>SIR simulator</b> turns those rankings into outbreak "
            "curves you can replay under different policy choices. The "
            "four cards below walk through the typical flow."
            "</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(4, gap="small")
        for col, (i, (title, where, body)) in zip(cols, enumerate(_STEPS, start=1)):
            with col:
                st.markdown(
                    f'<div class="modr-howto-step">'
                    f'<div class="modr-howto-step-num">{i:02d}</div>'
                    f'<div class="modr-howto-step-title">{title}</div>'
                    f'<div class="modr-howto-step-body">{body}'
                    f'<br><br><em>{where}</em></div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
