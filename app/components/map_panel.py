"""Map panel: renders the static baseline map or the animated SIR map."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.maps import build_animated_choropleth, build_baseline_choropleth


def _focus_caption(focused_state: str | None, selected_states: list) -> str:
    if focused_state and focused_state in selected_states:
        return (
            f"Focused on a single state. Click the highlighted state pill again "
            f"or press 'Show all states' to return to the grid view."
        )
    if len(selected_states) > 1:
        return "Showing all selected states side by side. Click a state pill above to focus on one."
    return ""


def render_baseline(
    flu: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    focused_state: str | None = None,
) -> None:
    fig = build_baseline_choropleth(flu, geojson, selected_states, focused_state)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    if "CT" in selected_states:
        st.info(
            "Connecticut planning regions appear blank on the map — the US Census GeoJSON "
            "predates Connecticut's 2022 county-to-planning-region transition. Connecticut is "
            "still counted in the metric cards and the state-level breakdown chart below."
        )
    caption = _focus_caption(focused_state, selected_states)
    if caption:
        st.markdown(
            f'<p class="modr-caption">{caption}</p>', unsafe_allow_html=True
        )
    st.markdown(
        '<p class="modr-caption">Predicted relative outbreak vulnerability per county '
        "(XGBoost output).</p>",
        unsafe_allow_html=True,
    )


def render_animated(
    long_df: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    horizon: int,
    frame_days: float = 2.0,
    focused_state: str | None = None,
) -> None:
    fig = build_animated_choropleth(
        long_df, geojson, selected_states, focused_state
    )
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    if "CT" in selected_states:
        st.info(
            "Connecticut planning regions appear blank on the animated map — "
            "the US Census GeoJSON predates Connecticut's 2022 county-to-planning-region "
            "transition. Connecticut is still counted in the metric cards and the state-level "
            "breakdown chart below."
        )
    caption = _focus_caption(focused_state, selected_states)
    if caption:
        st.markdown(
            f'<p class="modr-caption">{caption}</p>', unsafe_allow_html=True
        )
    frame_label = f"{frame_days:.0f}" if frame_days == int(frame_days) else f"{frame_days:.1f}"
    st.markdown(
        f'<p class="modr-caption">Each frame represents {frame_label} days. '
        f"Horizon: {horizon} days.</p>",
        unsafe_allow_html=True,
    )
