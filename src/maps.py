"""Plotly figure builders applying a single scientific-minimalist theme."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.constants import (
    ACCENT,
    BG,
    BORDER,
    COLOR_SEQUENCE,
    FONT_STACK,
    MUTED,
    POSITIVE,
    STATE_NAMES,
    STATES,
    TEXT,
    VAX_COLOR_SEQUENCE,
)


# Lon/lat bounds tight to NY, PA, CT, DE — used to zoom the single big USA
# choropleth onto our 4-state region. Without this, scope='usa' overrides
# fitbounds='locations' and the map shows the entire continental USA with
# the states as a tiny cluster in the upper-east.
FOUR_STATE_LON_RANGE = (-80.8, -71.5)
# DE's southernmost county (Sussex) hits ~38.45N — with a 38.3 lower bound,
# mercator's bounds-respecting render clipped the bottom of DE. Padded south
# (37.8) and north (45.8) gives every state ~0.5° clearance from the edges.
FOUR_STATE_LAT_RANGE = (37.8, 45.8)


def _zoom_to_four_states(fig: go.Figure) -> go.Figure:
    """Force the geo to the NY-PA-CT-DE bounding box. Called after
    _apply_scientific_theme on the single-USA-map choropleths.

    NOTE: scope='usa' implies the albers-usa projection, which IGNORES
    lonaxis/lataxis range — it has fixed parameters that always show all
    50 states. To honour our 4-state bounding box we must drop scope='usa'
    and switch to an explicit projection (mercator) that respects range.
    """
    fig.update_geos(
        scope=None,
        projection=dict(type="mercator"),
        fitbounds=False,
        lonaxis=dict(range=list(FOUR_STATE_LON_RANGE)),
        lataxis=dict(range=list(FOUR_STATE_LAT_RANGE)),
        visible=False,
        showcoastlines=False,
        showland=False,
        showcountries=False,
        showsubunits=False,
        showlakes=False,
        showocean=False,
        bgcolor=BG,
    )
    return fig


def _add_seed_overlay(
    fig: go.Figure,
    geojson: dict,
    seed_fips: list | tuple | None,
) -> go.Figure:
    """Overlay a transparent choropleth with a thick green outline on the
    given seed counties. Used to mark outbreak-origin counties on the
    Outbreak Vulnerability map (both single-state and per-panel grid)."""
    if not seed_fips:
        return fig
    seeds = [str(f) for f in seed_fips]
    fig.add_trace(
        go.Choropleth(
            geojson=geojson,
            locations=seeds,
            z=[1] * len(seeds),
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            showscale=False,
            marker_line_color=POSITIVE,
            marker_line_width=3.5,
            hovertemplate="<b>Outbreak seed</b><br>FIPS %{location}<extra></extra>",
            name="Seeds",
        )
    )
    return fig


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


def build_vaccination_choropleth(
    flu: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    focused_state: str | None = None,
    range_color: tuple[float, float] | None = None,
) -> go.Figure:
    """Single big USA-scoped green choropleth of effective vaccination
    coverage (V_eff) across all selected states. Mirrors the structure of
    build_baseline_choropleth so the two tabs render symmetrically; only
    the colour scheme and metric column differ."""
    state_order = _ordered_states(selected_states)
    if focused_state and focused_state in state_order:
        state_order = [focused_state]
    df = flu[flu["state"].isin(state_order)].copy()
    if range_color is None:
        range_color = (0.0, 1.0)

    fig = px.choropleth(
        df,
        geojson=geojson,
        locations="fips_str",
        color="V_eff",
        color_continuous_scale=VAX_COLOR_SEQUENCE,
        range_color=list(range_color),
        scope="usa",
        hover_name="county",
        hover_data={
            "state": True,
            "V0": ":.1%",
            "V_eff": ":.1%",
            "p_outbreak": ":.3f",
            "fips_str": False,
        },
        labels={
            "V_eff": "Coverage",
            "V0": "Baseline",
            "p_outbreak": "P(outbreak)",
        },
    )
    fig.update_traces(marker_line_color=BG, marker_line_width=0.5)
    fig = _apply_scientific_theme(fig)
    fig = _zoom_to_four_states(fig)
    fig.update_layout(
        coloraxis_colorbar=dict(
            title=dict(
                text="% vaccinated",
                font=dict(color=MUTED, family=FONT_STACK, size=11),
            ),
            thickness=10,
            tickfont=dict(size=11, color=MUTED, family=FONT_STACK),
            outlinewidth=0,
            tickformat=".0%",
        ),
        height=560,
    )
    return fig


def build_single_state_vaccination_choropleth(
    state_df: pd.DataFrame,
    geojson: dict,
    show_colorbar: bool = False,
    height: int = 280,
    range_color: tuple[float, float] | None = None,
) -> go.Figure:
    """Green-scale county map of effective vaccination coverage (V_eff)
    after the user's chosen baseline + any allocation boost. Counties with
    higher coverage shade darker green.

    Expects state_df to carry a V_eff column in [0, 1] (fractional).
    Pass `range_color` to share a color scale across multiple per-state
    panels; defaults to a tight (min - 2pp, max + 2pp) auto-range based on
    the panel's own data."""
    if range_color is None:
        v = state_df["V_eff"].values
        if len(v):
            range_color = (
                max(0.0, float(v.min()) - 0.02),
                min(1.0, float(v.max()) + 0.02),
            )
        else:
            range_color = (0.0, 1.0)
    fig = px.choropleth(
        state_df,
        geojson=geojson,
        locations="fips_str",
        color="V_eff",
        color_continuous_scale=VAX_COLOR_SEQUENCE,
        range_color=list(range_color),
        hover_name="county",
        hover_data={
            "state": True,
            "V0": ":.1%",
            "V_eff": ":.1%",
            "p_outbreak": ":.3f",
            "fips_str": False,
        },
        labels={
            "V_eff": "Coverage",
            "V0": "Baseline",
            "p_outbreak": "P(outbreak)",
        },
    )
    fig.update_traces(marker_line_color=BG, marker_line_width=0.5)
    fig.update_geos(fitbounds="locations", visible=False, bgcolor=BG)
    fig.update_layout(
        template="plotly_white",
        font=dict(family=FONT_STACK, size=11, color=TEXT),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        showlegend=False,
    )
    if show_colorbar:
        fig.update_layout(
            coloraxis_colorbar=dict(
                title=dict(
                    text="% vaccinated",
                    font=dict(color=MUTED, family=FONT_STACK, size=10),
                ),
                thickness=8,
                len=0.85,
                tickfont=dict(size=10, color=MUTED, family=FONT_STACK),
                outlinewidth=0,
                tickformat=".0%",
            ),
        )
    else:
        fig.update_layout(coloraxis_showscale=False)
    return fig


def build_single_state_choropleth(
    state_df: pd.DataFrame,
    geojson: dict,
    show_colorbar: bool = False,
    height: int = 280,
    seed_fips: list | tuple | None = None,
) -> go.Figure:
    """Small choropleth focused on a single state for use inside a 2x2 grid
    layout. Each chart is independent — Plotly fitbounds='locations' centres
    the state in its own canvas, no facet arithmetic required."""
    fig = px.choropleth(
        state_df,
        geojson=geojson,
        locations="fips_str",
        color="p_outbreak",
        color_continuous_scale=COLOR_SEQUENCE,
        range_color=[0, 1],
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
    fig.update_geos(fitbounds="locations", visible=False, bgcolor=BG)
    fig.update_layout(
        template="plotly_white",
        font=dict(family=FONT_STACK, size=11, color=TEXT),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        showlegend=False,
    )
    if show_colorbar:
        fig.update_layout(
            coloraxis_colorbar=dict(
                title=dict(
                    text="P(outbreak)",
                    font=dict(color=MUTED, family=FONT_STACK, size=10),
                ),
                thickness=8,
                len=0.85,
                tickfont=dict(size=10, color=MUTED, family=FONT_STACK),
                outlinewidth=0,
                tickformat=".2f",
            ),
        )
    else:
        fig.update_layout(coloraxis_showscale=False)
    # Overlay any seed counties with a thick green outline so the user can
    # see exactly where the SIR will start the outbreak.
    if seed_fips:
        # Only mark seeds that belong to this state's data (so a NY seed
        # doesn't decorate the PA panel and vice versa).
        valid = set(state_df["fips_str"].values)
        local_seeds = [f for f in seed_fips if f in valid]
        fig = _add_seed_overlay(fig, geojson, local_seeds)
    return fig


def build_synced_grid_animated_choropleth(
    long_df: pd.DataFrame,
    geojson: dict,
    state_order: list,
    seed_fips: list | tuple | None = None,
) -> go.Figure:
    """One figure containing a 2x2 (or 1x2 / 1x1) grid of per-state animated
    choropleths driven by a single shared timeline slider.

    Replaces the previous approach of rendering four independent
    px.choropleth animations, which spawned four sliders and quadrupled the
    Plotly DOM footprint. Here we use plotly.subplots.make_subplots and build
    frames manually so all panels advance through Day t together.
    """
    color_max = max(long_df["I_pct"].max(), 1e-6)
    days = sorted(long_df["day"].unique())

    n = len(state_order)
    n_cols = min(2, n)
    n_rows = (n + 1) // 2

    specs = [
        [{"type": "choropleth"} for _ in range(n_cols)] for _ in range(n_rows)
    ]
    titles = [STATE_NAMES[s] for s in state_order]
    while len(titles) < n_rows * n_cols:
        titles.append("")

    fig = make_subplots(
        rows=n_rows,
        cols=n_cols,
        specs=specs,
        subplot_titles=titles,
        horizontal_spacing=0.06,
        vertical_spacing=0.12,
    )

    state_dfs = {
        s: long_df[long_df["state"] == s].set_index("day") for s in state_order
    }

    first_day = days[0]
    for i, state in enumerate(state_order):
        row = (i // n_cols) + 1
        col = (i % n_cols) + 1
        sdf = state_dfs[state]
        try:
            day0 = sdf.loc[[first_day]]
        except KeyError:
            day0 = sdf.iloc[:0]
        fig.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=day0["fips"].tolist(),
                z=day0["I_pct"].tolist(),
                colorscale=COLOR_SEQUENCE,
                zmin=0,
                zmax=color_max,
                showscale=(i == (n_cols - 1)),  # only the first row's right cell
                marker_line_color=BG,
                marker_line_width=0.4,
                customdata=day0[["county"]].values,
                hovertemplate="<b>%{customdata[0]}</b><br>"
                "I_pct: %{z:.4f}%<extra></extra>",
                colorbar=dict(
                    title=dict(
                        text="% infectious",
                        font=dict(color=MUTED, family=FONT_STACK, size=10),
                    ),
                    thickness=8,
                    len=0.85,
                    tickfont=dict(size=10, color=MUTED, family=FONT_STACK),
                    outlinewidth=0,
                    tickformat=".3f",
                ),
            ),
            row=row,
            col=col,
        )

    for i in range(n):
        geo_idx = i + 1
        geo_key = "geo" if geo_idx == 1 else f"geo{geo_idx}"
        fig.update_layout(
            **{geo_key: dict(fitbounds="locations", visible=False, bgcolor=BG)}
        )

    frames = []
    for day in days:
        frame_traces = []
        for state in state_order:
            sdf = state_dfs[state]
            try:
                d = sdf.loc[[day]]
            except KeyError:
                d = sdf.iloc[:0]
            frame_traces.append(
                go.Choropleth(
                    locations=d["fips"].tolist(),
                    z=d["I_pct"].tolist(),
                    customdata=d[["county"]].values,
                )
            )
        frames.append(go.Frame(data=frame_traces, name=f"{day:.0f}"))
    fig.frames = frames

    fig.update_layout(
        height=300 * n_rows + 140,
        margin=dict(l=20, r=20, t=40, b=80),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family=FONT_STACK, size=12, color=TEXT),
        showlegend=False,
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                buttons=[
                    dict(
                        label="▶",
                        method="animate",
                        args=[
                            None,
                            dict(
                                frame=dict(duration=120, redraw=True),
                                fromcurrent=True,
                                transition=dict(duration=60),
                            ),
                        ],
                    ),
                    dict(
                        label="■",
                        method="animate",
                        args=[
                            [None],
                            dict(frame=dict(duration=0), mode="immediate"),
                        ],
                    ),
                ],
                x=0.0,
                y=-0.06,
                xanchor="left",
                yanchor="top",
                bgcolor=BG,
                bordercolor=TEXT,
                borderwidth=1,
                font=dict(color=TEXT, family=FONT_STACK, size=11),
            )
        ],
        sliders=[
            dict(
                active=0,
                steps=[
                    dict(
                        args=[
                            [f"{day:.0f}"],
                            dict(
                                frame=dict(duration=0, redraw=True),
                                mode="immediate",
                            ),
                        ],
                        label=f"{day:.0f}",
                        method="animate",
                    )
                    for day in days
                ],
                x=0.08,
                len=0.9,
                y=-0.06,
                xanchor="left",
                yanchor="top",
                currentvalue=dict(
                    prefix="Day ",
                    font=dict(color=TEXT, family=FONT_STACK, size=12),
                ),
                bgcolor=BORDER,
                bordercolor=BORDER,
                activebgcolor=TEXT,
                font=dict(color=MUTED, family=FONT_STACK, size=10),
            )
        ],
    )

    for ann in fig.layout.annotations:
        ann.font = dict(color=TEXT, family=FONT_STACK, size=14)
        ann.yshift = 4

    if seed_fips:
        # The overlay marks the outbreak origin on every animation frame.
        fig = _add_seed_overlay(fig, geojson, list(seed_fips))

    return fig


def build_single_state_animated_choropleth(
    state_long_df: pd.DataFrame,
    geojson: dict,
    color_max: float,
    show_colorbar: bool = False,
    height: int = 280,
) -> go.Figure:
    """Animated single-state choropleth for the 2x2 scenario grid. Shares the
    color_max across all four panels so the colour scale is comparable."""
    fig = px.choropleth(
        state_long_df,
        geojson=geojson,
        locations="fips",
        color="I_pct",
        animation_frame="day",
        color_continuous_scale=COLOR_SEQUENCE,
        range_color=[0, color_max],
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
    fig.update_geos(fitbounds="locations", visible=False, bgcolor=BG)
    fig.update_layout(
        template="plotly_white",
        font=dict(family=FONT_STACK, size=11, color=TEXT),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        margin=dict(l=0, r=0, t=0, b=30),
        height=height + 40,
        showlegend=False,
    )
    if show_colorbar:
        fig.update_layout(
            coloraxis_colorbar=dict(
                title=dict(
                    text="% infectious",
                    font=dict(color=MUTED, family=FONT_STACK, size=10),
                ),
                thickness=8,
                len=0.85,
                tickfont=dict(size=10, color=MUTED, family=FONT_STACK),
                outlinewidth=0,
                tickformat=".3f",
            ),
        )
    else:
        fig.update_layout(coloraxis_showscale=False)
    fig = _style_animation_controls(fig)
    return fig


def build_baseline_choropleth(
    flu: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    focused_state: str | None = None,
    seed_fips: list | tuple | None = None,
) -> go.Figure:
    """Big single-state choropleth used by the focused (one-state) view.

    The 2x2 grid view in map_panel.py builds its panels via
    build_single_state_choropleth, so this function is only reached when one
    state is selected (or focused). state_order is collapsed to a single state.
    """
    state_order = _ordered_states(selected_states)
    if focused_state and focused_state in state_order:
        state_order = [focused_state]
    df = flu[flu["state"].isin(state_order)].copy()

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
    fig = _zoom_to_four_states(fig)
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
        height=560,
    )
    if seed_fips:
        valid = set(df["fips_str"].values)
        local_seeds = [f for f in seed_fips if f in valid]
        fig = _add_seed_overlay(fig, geojson, local_seeds)
    return fig


def build_animated_choropleth(
    long_df: pd.DataFrame,
    geojson: dict,
    selected_states: list,
    focused_state: str | None = None,
    seed_fips: list | tuple | None = None,
) -> go.Figure:
    """Big single-state animated SIR choropleth used by the focused view.

    The 2x2 grid view in map_panel.py builds its panels via
    build_single_state_animated_choropleth, so this function is only reached
    when one state is selected (or focused).
    """
    state_order = _ordered_states(selected_states)
    if focused_state and focused_state in state_order:
        state_order = [focused_state]
    df = long_df[long_df["state"].isin(state_order)].copy()
    df = df.sort_values("day")
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
    fig = _zoom_to_four_states(fig)
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
        height=560,
    )
    fig = _style_animation_controls(fig)
    if seed_fips:
        fig = _add_seed_overlay(fig, geojson, list(seed_fips))
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
