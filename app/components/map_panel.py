"""Map panel: two tabs.

Tab 1 — Outbreak. The vulnerability map (baseline) or the time-animated SIR
infection map (scenario active). 2x2 small-multiples grid by default, single
big map when one state is focused.

Tab 2 — Vaccination. Green-scale map of effective vaccination coverage per
county = baseline V0 + per-county boost (uniform or targeted). Static — does
not animate, since vaccination state in the SIR is set at t=0.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.constants import STATE_NAMES, STATES
from src.maps import (
    build_animated_choropleth,
    build_baseline_choropleth,
    build_single_state_choropleth,
    build_single_state_vaccination_choropleth,
    build_synced_grid_animated_choropleth,
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


def _render_vaccination_tab(
    flu: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    focused_state: str | None,
    vax_boost_pp: int,
    strategy_label: str,
) -> None:
    """Static green-scale coverage map. Same layout contract as the outbreak
    tab (single big map when focused, 2x2 grid otherwise)."""
    state_order = _ordered_states(selected_states)
    is_focused = focused_state and focused_state in state_order
    target_states = [focused_state] if is_focused else state_order

    df = flu[flu["state"].isin(target_states)].copy()
    if "V_eff" not in df.columns:
        df["V_eff"] = df["V0"]

    # Shared range across all visible panels so the user can compare counties
    # across states. Tight padding keeps the variation visible — without this
    # the 0-100% range squashes everything into the dark-green band when the
    # user has a 50%+ baseline.
    v = df["V_eff"].values
    if len(v) and v.max() > v.min():
        range_color = (
            max(0.0, float(v.min()) - 0.02),
            min(1.0, float(v.max()) + 0.02),
        )
    else:
        # All counties at the same coverage (no targeting, no boost variation):
        # still show some context by spanning ±10pp around the value.
        val = float(v.mean()) if len(v) else 0.5
        range_color = (max(0.0, val - 0.1), min(1.0, val + 0.1))

    if len(target_states) <= 1:
        # one big map
        state_df = df[df["state"] == target_states[0]]
        fig = build_single_state_vaccination_choropleth(
            state_df,
            geojson,
            show_colorbar=True,
            height=520,
            range_color=range_color,
        )
        st.plotly_chart(fig, use_container_width=True, config=_BASELINE_CONFIG)
    else:
        rows = [target_states[i : i + 2] for i in range(0, len(target_states), 2)]
        for row_idx, row in enumerate(rows):
            cols = st.columns(len(row), gap="small")
            for col_idx, (col, state) in enumerate(zip(cols, row)):
                with col:
                    _state_label(STATE_NAMES[state])
                    state_df = df[df["state"] == state]
                    show_cb = row_idx == 0 and col_idx == len(row) - 1
                    fig = build_single_state_vaccination_choropleth(
                        state_df,
                        geojson,
                        show_colorbar=show_cb,
                        range_color=range_color,
                    )
                    st.plotly_chart(
                        fig, use_container_width=True, config=_BASELINE_CONFIG
                    )

    _ct_warning(focused_state, selected_states)
    if vax_boost_pp > 0:
        st.markdown(
            f'<p class="modr-caption">Effective coverage = baseline V<sub>0</sub> + '
            f"<b>{vax_boost_pp} pp</b> intervention, allocated <b>{strategy_label}</b>. "
            "Darker green = higher vaccination.</p>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p class="modr-caption">Showing baseline V<sub>0</sub>. Move the '
            "Additional vaccination budget slider in the sidebar to see how "
            "the chosen allocation strategy reshapes coverage.</p>",
            unsafe_allow_html=True,
        )


def _render_outbreak_tab_baseline(
    flu: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    focused_state: str | None,
) -> None:
    state_order = _ordered_states(selected_states)
    is_focused = focused_state and focused_state in state_order

    if is_focused or len(state_order) <= 1:
        fig = build_baseline_choropleth(flu, geojson, selected_states, focused_state)
        st.plotly_chart(fig, use_container_width=True, config=_BASELINE_CONFIG)
    else:
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
        '<p class="modr-caption">Predicted relative outbreak vulnerability '
        "per county (XGBoost output).</p>",
        unsafe_allow_html=True,
    )


def _render_outbreak_tab_animated(
    long_df: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    horizon: int,
    frame_days: float,
    focused_state: str | None,
) -> None:
    state_order = _ordered_states(selected_states)
    is_focused = focused_state and focused_state in state_order

    if is_focused or len(state_order) <= 1:
        fig = build_animated_choropleth(
            long_df, geojson, selected_states, focused_state
        )
        st.plotly_chart(fig, use_container_width=True, config=_ANIMATED_CONFIG)
    else:
        scoped = long_df[long_df["state"].isin(state_order)]
        fig = build_synced_grid_animated_choropleth(scoped, geojson, state_order)
        st.plotly_chart(fig, use_container_width=True, config=_ANIMATED_CONFIG)

    _ct_warning(focused_state, selected_states)
    caption = _focus_caption(focused_state, selected_states)
    if caption:
        st.markdown(f'<p class="modr-caption">{caption}</p>', unsafe_allow_html=True)
    frame_label = (
        f"{frame_days:.0f}" if frame_days == int(frame_days) else f"{frame_days:.1f}"
    )
    st.markdown(
        f'<p class="modr-caption">Each frame represents {frame_label} days. '
        f"Horizon: {horizon} days. All panels animate in sync from the shared "
        "play button below the grid.</p>",
        unsafe_allow_html=True,
    )


def render_baseline(
    flu: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    focused_state: str | None = None,
    vax_boost_pp: int = 0,
    strategy_label: str = "uniform",
) -> None:
    tab_outbreak, tab_vax = st.tabs(["Outbreak vulnerability", "Vaccination coverage"])
    with tab_outbreak:
        _render_outbreak_tab_baseline(flu, geojson, selected_states, focused_state)
    with tab_vax:
        _render_vaccination_tab(
            flu, geojson, selected_states, focused_state, vax_boost_pp, strategy_label
        )


def render_animated(
    long_df: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    horizon: int,
    frame_days: float = 2.0,
    focused_state: str | None = None,
    flu_for_vax: pd.DataFrame | None = None,
    vax_boost_pp: int = 0,
    strategy_label: str = "uniform",
) -> None:
    tab_outbreak, tab_vax = st.tabs(["Outbreak progression", "Vaccination coverage"])
    with tab_outbreak:
        _render_outbreak_tab_animated(
            long_df, geojson, selected_states, horizon, frame_days, focused_state
        )
    with tab_vax:
        if flu_for_vax is None:
            st.info("No vaccination data available for this scenario.")
            return
        _render_vaccination_tab(
            flu_for_vax,
            geojson,
            selected_states,
            focused_state,
            vax_boost_pp,
            strategy_label,
        )
