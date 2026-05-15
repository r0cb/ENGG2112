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


def build_baseline_choropleth(
    flu: pd.DataFrame,
    geojson: dict,
    selected_states: list,
) -> go.Figure:
    """Static map of predicted outbreak vulnerability (p_outbreak)."""
    df = flu[flu["state"].isin(selected_states)].copy()

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
    fig.update_layout(height=560)
    return fig


def build_animated_choropleth(
    long_df: pd.DataFrame,
    geojson: dict,
    selected_states: list,
) -> go.Figure:
    """Animated SIR choropleth: % infectious per county over time."""
    df = long_df[long_df["state"].isin(selected_states)].copy()
    color_max = max(df["I_pct"].max(), 1e-6)

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
    fig.update_layout(height=560)
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
