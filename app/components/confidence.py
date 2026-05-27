"""Per-state confidence pill strip — clickable, toggles single-state focus."""

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


def render(selected_states: list, focused_state: str | None) -> str | None:
    """Render the per-state pill strip + a 'Show all states' reset.

    Returns the new focused_state (or None for 2x2 grid view).
    Buttons toggle: clicking an inactive pill focuses that state; clicking the
    currently-focused pill clears focus.
    """
    st.markdown(
        '<div class="modr-section-label modr-confidence-header">Per-state model confidence</div>'
        '<div class="modr-confidence-hint">'
        "Click a state to drill into it. Click the highlighted state again "
        "or 'Show all states' to return to the side-by-side grid."
        "</div>",
        unsafe_allow_html=True,
    )

    new_focus = focused_state
    cols = st.columns([1, 1, 1, 1, 0.9], gap="small")
    for col, s in zip(cols[:4], STATES):
        with col:
            label, filled = STATE_CONFIDENCE[s]
            pr_auc = STATE_PR_AUC[s]
            help_text = (
                f"State PR-AUC {pr_auc:.2f} vs {PR_AUC_RANDOM:.2f} random baseline. "
                f"{'Click to clear focus.' if focused_state == s else 'Click to focus the map on this state.'}"
            )
            is_active = focused_state == s
            is_selected = s in selected_states
            is_disabled = not is_selected
            button_label = (
                f"{STATE_NAMES[s].upper()}  {_dots(filled)}\n{label} confidence"
            )
            clicked = st.button(
                button_label,
                key=f"pill_{s}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
                disabled=is_disabled,
                help=help_text,
            )
            if clicked:
                new_focus = None if is_active else s

    with cols[4]:
        if focused_state:
            if st.button(
                "Show all states",
                key="pill_reset",
                use_container_width=True,
                type="secondary",
            ):
                new_focus = None
        else:
            # Visual spacer so the row height matches when no reset button shown.
            st.markdown("&nbsp;", unsafe_allow_html=True)

    return new_focus
