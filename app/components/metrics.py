"""Custom metric cards (HTML, NOT st.metric)."""

from __future__ import annotations

import streamlit as st


def _format_int(n: float) -> str:
    return f"{int(round(n)):,}"


def _card(label: str, value: str, unit: str = "", delta_html: str = "") -> str:
    unit_html = f'<span class="unit">{unit}</span>' if unit else ""
    return (
        f'<div class="modr-metric">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}{unit_html}</div>'
        f"{delta_html}"
        f"</div>"
    )


def _delta(value: float, kind: str, suffix: str = "") -> str:
    """kind: 'better', 'worse', 'neutral'. value is the delta magnitude (already signed)."""
    if value == 0 or value is None:
        return '<div class="delta neutral">no change vs baseline</div>'
    arrow = "▼" if value < 0 else "▲"
    cls = kind
    return (
        f'<div class="delta {cls}">{arrow} '
        f"{abs(value):.2g}{suffix} vs baseline</div>"
    )


def render(metrics: dict, baseline_metrics: dict | None) -> None:
    """metrics, baseline_metrics: outputs of sir.aggregate_metrics()."""
    peak_pct = metrics["total_peak_pct"]
    peak_day = metrics["peak_day"]
    new_inf_pct = metrics["new_infections_pct"]
    new_inf = metrics["new_infections"]

    if baseline_metrics is not None:
        d_peak = peak_pct - baseline_metrics["total_peak_pct"]
        peak_delta_html = _delta(
            d_peak,
            kind="better" if d_peak < 0 else ("worse" if d_peak > 0 else "neutral"),
            suffix=" pp",
        )

        d_day = peak_day - baseline_metrics["peak_day"]
        if abs(d_day) < 0.5:
            peak_day_delta_html = (
                '<div class="delta neutral">same as baseline</div>'
            )
        else:
            arrow = "▼" if d_day < 0 else "▲"
            cls = "better" if d_day < 0 else "worse"
            peak_day_delta_html = (
                f'<div class="delta {cls}">{arrow} {abs(d_day):.0f} day'
                f"{'s' if abs(d_day) >= 2 else ''} "
                f"{'earlier' if d_day < 0 else 'later'} vs baseline</div>"
            )

        averted = baseline_metrics["new_infections"] - new_inf
        if abs(averted) < 1:
            averted_html = '<div class="delta neutral">no change vs baseline</div>'
        else:
            arrow = "▼" if averted > 0 else "▲"
            cls = "better" if averted > 0 else "worse"
            averted_html = (
                f'<div class="delta {cls}">{arrow} {_format_int(abs(averted))} '
                f"cases {'averted' if averted > 0 else 'added'}</div>"
            )
    else:
        peak_delta_html = '<div class="delta neutral">baseline</div>'
        peak_day_delta_html = '<div class="delta neutral">baseline</div>'
        averted_html = '<div class="delta neutral">baseline</div>'

    cards = "".join(
        [
            _card(
                "Peak simultaneous infection",
                f"{peak_pct:.2g}",
                unit="% pop",
                delta_html=peak_delta_html,
            ),
            _card(
                "Day of regional peak",
                f"{peak_day:.0f}",
                unit="day",
                delta_html=peak_day_delta_html,
            ),
            _card(
                "New infections",
                f"{new_inf_pct:.2g}",
                unit="% pop",
                delta_html=(
                    f'<div class="delta neutral">{_format_int(new_inf)} people</div>'
                ),
            ),
            _card(
                "Outcome vs baseline",
                f"{_format_int(abs(baseline_metrics['new_infections'] - new_inf)) if baseline_metrics else '—'}",
                unit="cases",
                delta_html=averted_html,
            ),
        ]
    )

    st.markdown(
        f'<div class="modr-metric-row">{cards}</div>',
        unsafe_allow_html=True,
    )
