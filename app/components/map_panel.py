"""Map panel: renders the static baseline map or the animated SIR map."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.maps import build_animated_choropleth, build_baseline_choropleth


def render_baseline(flu: pd.DataFrame, geojson: dict, selected_states: list) -> None:
    fig = build_baseline_choropleth(flu, geojson, selected_states)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    st.markdown(
        '<p class="modr-caption">Predicted relative outbreak vulnerability per county '
        "(XGBoost output). Connecticut planning regions are absent from the Census GeoJSON; "
        "those tiles appear blank, but the counties are included in metrics and the "
        "state-level breakdown.</p>",
        unsafe_allow_html=True,
    )


def render_animated(
    long_df: pd.DataFrame, geojson: dict, selected_states: list, horizon: int
) -> None:
    fig = build_animated_choropleth(long_df, geojson, selected_states)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
    st.markdown(
        f'<p class="modr-caption">Each frame represents 2 days. Horizon: {horizon} days. '
        "Connecticut planning regions are absent from the Census GeoJSON; "
        "CT tiles appear blank but are counted in metrics and the breakdown chart.</p>",
        unsafe_allow_html=True,
    )
