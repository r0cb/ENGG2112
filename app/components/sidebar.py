"""Sidebar: state filter, policy sliders, vaccination baseline, run/reset."""

from __future__ import annotations

import streamlit as st

from src.constants import (
    HORIZON_DEFAULT,
    HORIZON_OPTIONS,
    SIDEBAR_FOOTER,
    SLIDER_MOB,
    SLIDER_VAX,
    SLIDER_VAX_BASELINE,
    STATE_NAMES,
    STATES,
    VACCINATION_BASELINE_DEFAULT,
)
from src.data_loader import load_flu_df


SEED_MODE_DEFAULT = "default"
SEED_MODE_CHOOSE = "choose"


def render() -> dict:
    """Render sidebar widgets and return current control values."""
    with st.sidebar:
        st.markdown(
            '<div class="modr-section-label">Policy controls</div>',
            unsafe_allow_html=True,
        )

        states = st.multiselect(
            "States",
            options=STATES,
            default=STATES,
            format_func=lambda s: STATE_NAMES[s],
        )

        # The auto-optimiser writes its recommended budget to
        # session_state["_vax_pp_pending"] before calling st.rerun(). We must
        # apply it BEFORE the slider widget is instantiated, otherwise
        # Streamlit raises StreamlitAPIException when assigning to a keyed
        # widget's session_state after creation.
        if "_vax_pp_pending" in st.session_state:
            st.session_state["vax_pp"] = st.session_state.pop("_vax_pp_pending")
        if "vax_pp" not in st.session_state:
            st.session_state["vax_pp"] = SLIDER_VAX["default"]
        vax_boost_pp = st.slider(
            "Additional vaccination budget (pp)",
            min_value=SLIDER_VAX["min"],
            max_value=SLIDER_VAX["max"],
            step=SLIDER_VAX["step"],
            key="vax_pp",
            help=(
                "A fixed-size pool of vaccinations expressed as percentage "
                "points of the regional population. Example: at +10 pp the "
                "budget is 10% of all four states' population, "
                "≈ 4 million doses. The Optimisation panel decides where they "
                "land: Uniform spreads them across every county equally; "
                "Targeted routes them to high-vulnerability counties first "
                "and redistributes any leftover from counties that hit 100% "
                "coverage — no vaccines are wasted."
            ),
        )

        mobility = st.slider(
            "Mobility factor",
            min_value=SLIDER_MOB["min"],
            max_value=SLIDER_MOB["max"],
            value=SLIDER_MOB["default"],
            step=SLIDER_MOB["step"],
            help="1.0 = baseline inter-county mixing. 0.0 = isolated counties.",
        )

        horizon = st.select_slider(
            "Horizon (days)",
            options=HORIZON_OPTIONS,
            value=HORIZON_DEFAULT,
        )

        st.markdown(
            '<div class="modr-section-label" style="margin-top:1.25rem">'
            "Baseline vaccination"
            "</div>",
            unsafe_allow_html=True,
        )

        # Auto-sync per-state sliders to the overall slider. Without this, a
        # per-state slider that the user hasn't touched still overrides the
        # overall value (its default value gets written into session_state on
        # first render and persists). We track the last *committed* overall
        # and, when the overall changes, advance any per-state slider whose
        # value matches the previous overall — i.e. the user hadn't deviated
        # from it. Per-state values that diverge from the previous overall are
        # treated as explicit overrides and left alone.
        if "baseline_overall" in st.session_state:
            current_overall = st.session_state["baseline_overall"]
            last_overall = st.session_state.get(
                "_baseline_overall_last", SLIDER_VAX_BASELINE["default"]
            )
            if current_overall != last_overall:
                for state in STATES:
                    pk = f"baseline_{state}"
                    if st.session_state.get(pk, last_overall) == last_overall:
                        st.session_state[pk] = current_overall
                st.session_state["_baseline_overall_last"] = current_overall

        baseline_overall = st.slider(
            "Overall (% pop)",
            min_value=SLIDER_VAX_BASELINE["min"],
            max_value=SLIDER_VAX_BASELINE["max"],
            value=SLIDER_VAX_BASELINE["default"],
            step=SLIDER_VAX_BASELINE["step"],
            key="baseline_overall",
            help=(
                "Sets the starting vaccinated fraction across all counties "
                "BEFORE any additional intervention. The Variant-C calibration "
                "used 59%; expose this so users can explore lower- and "
                "higher-coverage worlds."
            ),
        )
        # Initialise _last_overall on the very first run.
        st.session_state.setdefault("_baseline_overall_last", baseline_overall)

        per_state_baselines: dict[str, int] = {}
        with st.expander("Per-state baselines (optional)", expanded=False):
            st.caption(
                "Each per-state value overrides the overall baseline for that "
                "state. Move only the per-state slider when you want a state "
                "to diverge from the overall; touching the overall slider "
                "re-syncs any untouched states to the new value."
            )
            for state in STATES:
                key = f"baseline_{state}"
                if key not in st.session_state:
                    st.session_state[key] = baseline_overall
                val = st.slider(
                    f"{STATE_NAMES[state]} (% pop)",
                    min_value=SLIDER_VAX_BASELINE["min"],
                    max_value=SLIDER_VAX_BASELINE["max"],
                    step=SLIDER_VAX_BASELINE["step"],
                    key=key,
                )
                per_state_baselines[state] = val

        # === Outbreak origin ===
        # Consume any pending click-to-seed before the multiselect mounts, so
        # we don't get StreamlitAPIException when assigning to a keyed widget
        # after it's been created.
        pending_seed = st.session_state.pop("_seed_pending", None)
        if pending_seed:
            current = list(st.session_state.get("seed_counties", []))
            for f in pending_seed:
                if f not in current:
                    current.append(f)
            st.session_state["seed_counties"] = current
            st.session_state["seed_mode"] = SEED_MODE_CHOOSE

        st.markdown(
            '<div class="modr-section-label" style="margin-top:1.25rem">'
            "Outbreak origin"
            "</div>",
            unsafe_allow_html=True,
        )

        seed_mode = st.radio(
            "Seed mode",
            options=[SEED_MODE_DEFAULT, SEED_MODE_CHOOSE],
            format_func=lambda x: (
                "Top-3 vulnerability counties (default)"
                if x == SEED_MODE_DEFAULT
                else "Choose counties"
            ),
            key="seed_mode",
            label_visibility="collapsed",
        )

        seed_counties: list[str] = list(st.session_state.get("seed_counties", []))
        if seed_mode == SEED_MODE_CHOOSE:
            flu = load_flu_df()
            label_lookup = {
                row["fips_str"]: f"{STATE_NAMES[row['state']]} — {row['county']}"
                for _, row in flu.iterrows()
            }
            if seed_counties:
                # Show currently-seeded counties as a list with per-row remove
                # buttons. The seed list is driven entirely by map clicks now.
                st.markdown(
                    '<div class="modr-seed-list-label">CURRENTLY SEEDED</div>',
                    unsafe_allow_html=True,
                )
                for fips in list(seed_counties):
                    label = label_lookup.get(fips, fips)
                    col_label, col_remove = st.columns([0.78, 0.22])
                    col_label.markdown(
                        f'<div class="modr-seed-chip">{label}</div>',
                        unsafe_allow_html=True,
                    )
                    if col_remove.button(
                        "✕", key=f"seed_remove_{fips}", help=f"Remove {label}"
                    ):
                        new_list = [f for f in seed_counties if f != fips]
                        st.session_state["seed_counties"] = new_list
                        st.rerun()
                if st.button(
                    "Clear all seeds", key="seed_clear_all", use_container_width=True
                ):
                    st.session_state["seed_counties"] = []
                    st.rerun()
                seed_counties = list(st.session_state.get("seed_counties", []))
            else:
                st.caption(
                    "No seeds selected yet — click any county on the Outbreak "
                    "Vulnerability map to add one. Falls back to the top-3 "
                    "default until you do."
                )
        else:
            # Default mode: don't carry stale "Choose" seeds into the SIR. The
            # actual top-3 fips are highlighted on the map via the seed
            # overlay; the SIR uses apply_seed's fallback.
            seed_counties = []

        st.write("")
        run_clicked = st.button(
            "Run scenario", type="primary", use_container_width=True
        )
        reset_clicked = st.button(
            "Reset to baseline", type="secondary", use_container_width=True
        )

        st.markdown(
            f"""
            <div style="margin-top: 2rem; font-size: 0.8rem; color: #444444;
                        letter-spacing: 0.04em;">
                {SIDEBAR_FOOTER}
            </div>
            """,
            unsafe_allow_html=True,
        )

    return {
        "states": states,
        "vax_boost": vax_boost_pp / 100.0,
        "vax_boost_pp": vax_boost_pp,
        "mobility": float(mobility),
        "horizon": int(horizon),
        "baseline_overall": int(baseline_overall),
        "per_state_baselines": per_state_baselines,
        "seed_mode": seed_mode,
        "seed_counties": list(seed_counties),
        "run_clicked": run_clicked,
        "reset_clicked": reset_clicked,
    }
