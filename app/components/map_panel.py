"""Map panel: renders the static baseline map or the animated SIR map."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.maps import build_animated_choropleth, build_baseline_choropleth


def render_baseline(flu: pd.DataFrame, geojson: dict, selected_states: list) -> None:
    fig = build_baseline_choropleth(flu, geojson, selected_states)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    if "CT" in selected_states:
        st.info(
            "Connecticut planning regions appear blank on the map — the US Census GeoJSON "
            "predates Connecticut's 2022 county-to-planning-region transition. Connecticut is "
            "still counted in the metric cards and the state-level breakdown chart below."
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
) -> None:
    fig = build_animated_choropleth(long_df, geojson, selected_states)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    if "CT" in selected_states:
        st.info(
            "Connecticut planning regions appear blank on the animated map — "
            "the US Census GeoJSON predates Connecticut's 2022 county-to-planning-region "
            "transition. Connecticut is still counted in the metric cards and the state-level "
            "breakdown chart below."
        )
    frame_label = f"{frame_days:.0f}" if frame_days == int(frame_days) else f"{frame_days:.1f}"
    st.markdown(
        f'<p class="modr-caption">Each frame represents {frame_label} days. '
        f"Horizon: {horizon} days.</p>",
        unsafe_allow_html=True,
    )
