"""Header block: title, subtitle, divider."""

import streamlit as st

from src.constants import APP_SUBTITLE, APP_TITLE


def render() -> None:
    st.markdown(
        f"""
        <div>
            <h1 class="modr-title">{APP_TITLE}</h1>
            <p class="modr-subtitle">{APP_SUBTITLE}</p>
            <hr class="modr-hr" />
        </div>
        """,
        unsafe_allow_html=True,
    )
