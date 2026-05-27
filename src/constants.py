"""Centralised palette, slider bounds, copy strings, and state metadata."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"

SIR_RESULTS_PATH = MODELS_DIR / "sir_results.json"
MODEL_PATH = MODELS_DIR / "production_model.pkl"
FEATURES_PATH = DATA_DIR / "processed" / "selected_features.json"

GEOJSON_URL = (
    "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
)
STATE_FIPS_PREFIXES = {"09", "10", "36", "42"}

STATES = ["NY", "PA", "CT", "DE"]
STATE_NAMES = {
    "NY": "New York",
    "PA": "Pennsylvania",
    "CT": "Connecticut",
    "DE": "Delaware",
}
STATE_PR_AUC = {"NY": 0.74, "PA": 0.32, "CT": 0.30, "DE": 0.42}
STATE_CONFIDENCE = {
    "NY": ("High", 3),
    "PA": ("Low", 1),
    "CT": ("Low", 1),
    "DE": ("Very low", 1),
}

SLIDER_VAX = {"min": 0, "max": 40, "step": 1, "default": 0}
SLIDER_MOB = {"min": 0.0, "max": 1.0, "step": 0.05, "default": 1.0}
# Default baseline vaccination % used in the Variant C SIR calibration. User can
# override this overall, or per-state, from the sidebar.
SLIDER_VAX_BASELINE = {"min": 0, "max": 100, "step": 1, "default": 59}
VACCINATION_BASELINE_DEFAULT = 59
HORIZON_OPTIONS = [90, 180, 270, 365]
HORIZON_DEFAULT = 180

ALLOCATION_UNIFORM = "uniform"
ALLOCATION_TARGETED = "targeted"
ALLOCATION_OPTIMAL = "optimal"
ALLOCATION_OPTIONS = [
    ALLOCATION_UNIFORM,
    ALLOCATION_TARGETED,
    ALLOCATION_OPTIMAL,
]
ALLOCATION_DEFAULT = ALLOCATION_UNIFORM
ALLOCATION_LABELS = {
    ALLOCATION_UNIFORM: "Uniform (β = 0)",
    ALLOCATION_TARGETED: "Targeted (β = 1, proportional to vulnerability)",
    ALLOCATION_OPTIMAL: "Optimal (β chosen to minimise cases)",
}

# β sweep grid used by the case-minimising optimiser. Each value defines an
# allocation where per-county boost is proportional to p_outbreak ** beta,
# then water-filled if any county would exceed 100% coverage. β=0 collapses
# to uniform; β=1 is the standard targeted strategy; higher values
# concentrate the budget more aggressively.
OPTIMISER_BETA_GRID = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0)

# Legacy: peak threshold the old min-budget optimiser used. Retained because
# the methodology copy references it; no longer surfaced in the UI.
OPTIMISER_PEAK_THRESHOLD_PCT = 0.05

PR_AUC_OVERALL = 0.506
PR_AUC_RANDOM = 0.261

COLOR_SEQUENCE = "YlOrRd"
VAX_COLOR_SEQUENCE = "Greens"
BG = "#FFFFFF"
SURFACE = "#FAFAFA"
TEXT = "#1A1A1A"
MUTED = "#6B6B6B"
BORDER = "#E5E5E5"
ACCENT = "#B43A1E"
POSITIVE = "#3A7D5C"

FONT_STACK = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

APP_TITLE = "MODR — Respiratory Virus Vulnerability Explorer"
APP_SUBTITLE = (
    "Counties of New York, Pennsylvania, Connecticut, Delaware. "
    "Hypothetical scenarios, 90-to-365-day SIR simulation."
)
SIDEBAR_FOOTER = "ENGG2112 · 141 counties · XGBoost + SIR"
APP_FOOTER = "ENGG2112 Project MODR · University of Sydney · 2026"
