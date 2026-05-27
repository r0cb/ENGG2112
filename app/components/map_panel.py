"""Map panel: renders the static baseline map or the animated SIR map.

Two display modes:
- Focused (single state selected via pill click, OR only one state in the multi-
  selector): one big choropleth zoomed to that state.
- Grid (default for >=2 selected states): a 2x2 layout of small per-state
  choropleths built with st.columns so each state is independently centred and
  labelled. No facet arithmetic, no aspect-ratio overflow.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.constants import STATE_NAMES, STATES
from src.maps import (
    build_animated_choropleth,
    build_baseline_choropleth,
    build_single_state_animated_choropleth,
    build_single_state_choropleth,
)


_BASELINE_CONFIG = {
    "displaylogo": False,
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
    "staticPlot": False,
}
_ANIMATED_CONFIG = {
    "displaylogo": False,
    "scrollZoom": False,
    "doubleClick": False,
    "modeBarButtonsToRemove": [
        "pan2d", "lasso2d", "select2d", "zoom2d", "zoomIn2d", "zoomOut2d",
        "autoScale2d", "resetScale2d", "toImage",
    ],
}


def _ordered_states(selected_states: list) -> list:
    return [s for s in STATES if s in selected_states]


def _focus_caption(focused_state: str | None, selected_states: list) -> str:
    if focused_state and focused_state in selected_states:
        return (
            "Focused on a single state. Click the highlighted state pill again "
            "or press 'Show all states' to return to the grid view."
        )
    if len(selected_states) > 1:
        return "Showing all selected states side by side. Click a state pill above to focus on one."
    return ""


def _state_label(name: str) -> None:
    st.markdown(
        f'<div class="modr-state-facet-label">{name}</div>',
        unsafe_allow_html=True,
    )


def _ct_warning(focused_state: str | None, selected_states: list) -> None:
    """Show the CT GeoJSON-gap notice only when CT is actually rendered on the
    map: grid mode with CT selected, or focused mode with CT as the focus."""
    if focused_state and focused_state in selected_states:
        if focused_state != "CT":
            return
    elif "CT" not in selected_states:
        return
    st.info(
        "Connecticut planning regions appear blank — the US Census GeoJSON "
        "predates Connecticut's 2022 county-to-planning-region transition. "
        "Connecticut is still counted in the metric cards and the state-level "
        "breakdown chart below."
    )


def render_baseline(
    flu: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    focused_state: str | None = None,
) -> None:
    state_order = _ordered_states(selected_states)
    is_focused = focused_state and focused_state in state_order

    if is_focused or len(state_order) <= 1:
        # Single big map
        fig = build_baseline_choropleth(flu, geojson, selected_states, focused_state)
        st.plotly_chart(fig, use_container_width=True, config=_BASELINE_CONFIG)
    else:
        # 2x2 grid: rows of up to 2 states each
        rows = [state_order[i : i + 2] for i in range(0, len(state_order), 2)]
        for row_idx, row in enumerate(rows):
            cols = st.columns(len(row), gap="small")
            for col_idx, (col, state) in enumerate(zip(cols, row)):
                with col:
                    _state_label(STATE_NAMES[state])
                    state_df = flu[flu["state"] == state]
                    show_cb = row_idx == 0 and col_idx == len(row) - 1
                    fig = build_single_state_choropleth(
                        state_df, geojson, show_colorbar=show_cb
                    )
                    st.plotly_chart(
                        fig, use_container_width=True, config=_BASELINE_CONFIG
                    )

    _ct_warning(focused_state, selected_states)
    caption = _focus_caption(focused_state, selected_states)
    if caption:
        st.markdown(f'<p class="modr-caption">{caption}</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="modr-caption">Predicted relative outbreak vulnerability per '
        "county (XGBoost output).</p>",
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
    state_order = _ordered_states(selected_states)
    is_focused = focused_state and focused_state in state_order

    if is_focused or len(state_order) <= 1:
        # Single big animated map
        fig = build_animated_choropleth(
            long_df, geojson, selected_states, focused_state
        )
        st.plotly_chart(fig, use_container_width=True, config=_ANIMATED_CONFIG)
    else:
        # 2x2 grid of small animated maps. Color scale is shared (computed once
        # across the full long_df) so visual intensity is comparable.
        scoped = long_df[long_df["state"].isin(state_order)]
        color_max = max(scoped["I_pct"].max(), 1e-6)
        rows = [state_order[i : i + 2] for i in range(0, len(state_order), 2)]
        for row_idx, row in enumerate(rows):
            cols = st.columns(len(row), gap="small")
            for col_idx, (col, state) in enumerate(zip(cols, row)):
                with col:
                    _state_label(STATE_NAMES[state])
                    state_df = scoped[scoped["state"] == state]
                    show_cb = row_idx == 0 and col_idx == len(row) - 1
                    fig = build_single_state_animated_choropleth(
                        state_df, geojson, color_max, show_colorbar=show_cb
                    )
                    st.plotly_chart(
                        fig, use_container_width=True, config=_ANIMATED_CONFIG
                    )

    _ct_warning(focused_state, selected_states)
    caption = _focus_caption(focused_state, selected_states)
    if caption:
        st.markdown(f'<p class="modr-caption">{caption}</p>', unsafe_allow_html=True)
    frame_label = (
        f"{frame_days:.0f}" if frame_days == int(frame_days) else f"{frame_days:.1f}"
    )
    st.markdown(
        f'<p class="modr-caption">Each frame represents {frame_label} days. '
        f"Horizon: {horizon} days. In grid view, each state animates independently — "
        "press play on any panel; they're computed from the same simulation.</p>",
        unsafe_allow_html=True,
    )
