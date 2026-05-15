"""Per-state confidence indicator pill strip."""

from __future__ import annotations

import streamlit as st

from src.constants import (
    PR_AUC_RANDOM,
    STATE_CONFIDENCE,
    STATE_NAMES,
    STATE_PR_AUC,
    STATES,
)


def _dots(filled: int, total: int = 3) -> str:
    return "●" * filled + "○" * (total - filled)


def render(selected_states: list) -> None:
    pills = []
    for s in STATES:
        label, filled = STATE_CONFIDENCE[s]
        pr_auc = STATE_PR_AUC[s]
        dim_cls = "" if s in selected_states else "dim"
        tooltip = (
            f"State PR-AUC {pr_auc:.2f} vs {PR_AUC_RANDOM:.2f} random baseline"
        )
        pills.append(
            f'<span class="modr-pill {dim_cls}" title="{tooltip}">'
            f'<span class="state-name">{STATE_NAMES[s]}</span>'
            f'<span class="state-dots">{_dots(filled)}</span>'
            f'<span class="state-label">{label} confidence</span>'
            f"</span>"
        )
    st.markdown(
        '<div class="modr-section-label">Per-state model confidence</div>'
        f'<div class="modr-confidence-row">{"".join(pills)}</div>',
        unsafe_allow_html=True,
    )
