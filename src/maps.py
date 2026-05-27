"""Plotly figure builders applying a single scientific-minimalist theme."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.constants import (
    ACCENT,
    BG,
    BORDER,
    COLOR_SEQUENCE,
    FONT_STACK,
    MUTED,
    STATE_NAMES,
    STATES,
    TEXT,
)


def _apply_scientific_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        font=dict(family=FONT_STACK, size=12, color=TEXT),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        margin=dict(l=0, r=0, t=10, b=10),
        showlegend=False,
        coloraxis_colorbar=dict(
            thickness=10,
            tickfont=dict(size=11, color=MUTED, family=FONT_STACK),
            outlinewidth=0,
            tickformat=".3f",
            ticklen=4,
        ),
    )
    fig.update_layout(title_text="")
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor=BG,
    )
    return fig


def _style_animation_controls(fig: go.Figure) -> go.Figure:
    """Make Plotly's play/pause and frame slider match the monochrome theme."""
    if not fig.layout.updatemenus:
        return fig

    for menu in fig.layout.updatemenus:
        menu.bgcolor = BG
        menu.bordercolor = TEXT
        menu.borderwidth = 1
        menu.font = dict(color=TEXT, family=FONT_STACK, size=11)
        for btn in menu.buttons:
            if btn.args and len(btn.args) > 1:
                args1 = btn.args[1]
                if isinstance(args1, dict):
                    if "frame" in args1:
                        args1["frame"]["duration"] = 120
                    if "transition" in args1:
                        args1["transition"]["duration"] = 60

    for slider in fig.layout.sliders or []:
        slider.bgcolor = BORDER
        slider.bordercolor = BORDER
        slider.activebgcolor = TEXT
        slider.font = dict(color=MUTED, family=FONT_STACK, size=10)
        slider.currentvalue = dict(
            visible=True,
            prefix="Day ",
            xanchor="left",
            font=dict(color=TEXT, family=FONT_STACK, size=12),
        )

    return fig


def _ordered_states(selected_states: list) -> list:
    """Preserve canonical NY, PA, CT, DE order, filtered to selected."""
    return [s for s in STATES if s in selected_states]


# Hand-tuned lon/lat bounding boxes per state. Padded ~0.3 deg so labels and
# coastline don't clip. Used in 2x2 facet mode to override the USA-wide scope
# that otherwise comes with px.choropleth.
STATE_GEO_RANGES = {
    "NY": dict(lonrange=[-80.0, -71.5], latrange=[40.3, 45.2]),
    "PA": dict(lonrange=[-80.8, -74.4], latrange=[39.5, 42.5]),
    "CT": dict(lonrange=[-74.0, -71.5], latrange=[40.8, 42.2]),
    "DE": dict(lonrange=[-76.0, -74.8], latrange=[38.3, 40.0]),
}


def _format_state_facets(fig: go.Figure, state_order: list) -> go.Figure:
    """Replace px's 'state=NY' annotations with the full state name + zoom each
    geo subplot to its state's bounding box. Without this the choropleth would
    render at USA scope (tiny state in a continent-wide canvas)."""
    fig.for_each_annotation(
        lambda a: a.update(
            text=STATE_NAMES.get(a.text.split("=")[-1], a.text.split("=")[-1]),
            font=dict(color=TEXT, family=FONT_STACK, size=13),
            yshift=-4,
        )
    )
    layout_updates = {}
    for i, state in enumerate(state_order):
        geo_key = "geo" if i == 0 else f"geo{i + 1}"
        ranges = STATE_GEO_RANGES.get(state)
        if not ranges:
            continue
        layout_updates[geo_key] = dict(
            scope="north america",
            fitbounds=False,
            visible=False,
            bgcolor=BG,
            lonaxis=dict(range=ranges["lonrange"]),
            lataxis=dict(range=ranges["latrange"]),
            showcoastlines=False,
            showland=False,
            showcountries=False,
        )
    fig.update_layout(**layout_updates)
    return fig


def build_baseline_choropleth(
    flu: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    focused_state: str | None = None,
) -> go.Figure:
    """Static map of predicted outbreak vulnerability (p_outbreak).

    When `focused_state` is set OR only one state is selected, render a single
    big choropleth zoomed to that state. Otherwise render a 2x2 small-multiples
    grid with one panel per selected state.
    """
    state_order = _ordered_states(selected_states)
    if focused_state and focused_state in state_order:
        state_order = [focused_state]
    df = flu[flu["state"].isin(state_order)].copy()
    df["state"] = pd.Categorical(df["state"], categories=state_order, ordered=True)
    df = df.sort_values("state")

    single = len(state_order) == 1
    facet_kwargs = (
        {}
        if single
        else dict(facet_col="state", facet_col_wrap=2, facet_col_spacing=0.02)
    )

    fig = px.choropleth(
        df,
        geojson=geojson,
        locations="fips_str",
        color="p_outbreak",
        color_continuous_scale=COLOR_SEQUENCE,
        range_color=[0, 1],
        scope="usa",
        hover_name="county",
        hover_data={
            "state": True,
            "V0": ":.1%",
            "p_outbreak": ":.3f",
            "fips_str": False,
        },
        labels={"p_outbreak": "P(outbreak)", "V0": "Vaccinated"},
        **facet_kwargs,
    )
    fig.update_traces(marker_line_color=BG, marker_line_width=0.5)
    fig = _apply_scientific_theme(fig)
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(
                text="P(outbreak)",
                font=dict(color=MUTED, family=FONT_STACK, size=11),
            ),
            thickness=10,
            tickfont=dict(size=11, color=MUTED, family=FONT_STACK),
            outlinewidth=0,
            tickformat=".2f",
        ),
    )
    if single:
        fig.update_layout(height=560)
    else:
        n_rows = (len(state_order) + 1) // 2
        fig.update_layout(height=340 * n_rows + 80)
        fig = _format_state_facets(fig, state_order)
    return fig


def build_animated_choropleth(
    long_df: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    focused_state: str | None = None,
) -> go.Figure:
    """Animated SIR choropleth: % infectious per county over time.

    Same dual-mode contract as build_baseline_choropleth: single big map when
    one state is focused/selected, else 2x2 small-multiples grid.
    """
    state_order = _ordered_states(selected_states)
    if focused_state and focused_state in state_order:
        state_order = [focused_state]
    df = long_df[long_df["state"].isin(state_order)].copy()
    df["state"] = pd.Categorical(df["state"], categories=state_order, ordered=True)
    df = df.sort_values(["state", "day"])
    color_max = max(df["I_pct"].max(), 1e-6)

    single = len(state_order) == 1
    facet_kwargs = (
        {}
        if single
        else dict(facet_col="state", facet_col_wrap=2, facet_col_spacing=0.02)
    )

    fig = px.choropleth(
        df,
        geojson=geojson,
        locations="fips",
        color="I_pct",
        animation_frame="day",
        color_continuous_scale=COLOR_SEQUENCE,
        range_color=[0, color_max],
        scope="usa",
        hover_name="county",
        hover_data={
            "state": True,
            "vax_pct": ":.1f",
            "p_outbreak": ":.3f",
            "I_pct": ":.4f",
            "day": False,
            "fips": False,
        },
        labels={
            "I_pct": "% infectious",
            "vax_pct": "Vaccinated %",
            "p_outbreak": "P(outbreak)",
        },
        **facet_kwargs,
    )
    fig.update_traces(marker_line_color=BG, marker_line_width=0.4)
    fig = _apply_scientific_theme(fig)
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(
                text="% infectious",
                font=dict(color=MUTED, family=FONT_STACK, size=11),
            ),
            thickness=10,
            tickfont=dict(size=11, color=MUTED, family=FONT_STACK),
            outlinewidth=0,
            tickformat=".3f",
        ),
    )
    if single:
        fig.update_layout(height=560)
    else:
        n_rows = (len(state_order) + 1) // 2
        fig.update_layout(height=340 * n_rows + 100)
        fig = _format_state_facets(fig, state_order)
    fig = _style_animation_controls(fig)
    return fig


def build_state_summary_bars(sim: dict, flu: pd.DataFrame) -> go.Figure:
    """Per-state peak infectious % horizontal bar chart."""
    flu_indexed = flu.set_index("fips_str")
    rows = []
    for fips, peak_pct in zip(sim["fips_order"], sim["peak_infected_pct"]):
        rows.append(
            {
                "state": flu_indexed.loc[fips, "state"],
                "peak_pct": float(peak_pct),
            }
        )
    df = pd.DataFrame(rows)
    state_summary = (
        df.groupby("state")["peak_pct"].max().reset_index().sort_values("peak_pct")
    )

    fig = px.bar(
        state_summary,
        x="peak_pct",
        y="state",
        orientation="h",
        labels={"peak_pct": "Peak county infectious (%)", "state": ""},
    )
    fig.update_traces(marker_color=ACCENT, marker_line_width=0)
    fig.update_layout(
        template="plotly_white",
        font=dict(family=FONT_STACK, size=12, color=TEXT),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        margin=dict(l=0, r=0, t=10, b=10),
        height=200,
        xaxis=dict(gridcolor="#F0F0F0", linecolor=BORDER, tickformat=".3f"),
        yaxis=dict(gridcolor=BG, linecolor=BORDER),
        showlegend=False,
    )
    return fig
