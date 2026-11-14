"""
SensorScope — Main Streamlit entry point.
Run with: streamlit run app.py
"""

import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SensorScope",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS theme ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide Streamlit auto-generated page navigation to preserve custom SensorScope nav */
[data-testid="stSidebarNav"], .css-1dp5vir {
    display: none !important;
}

/* Reliability status badges */
.badge-green  { background:#1b7a3e; color:#fff; padding:4px 10px;
                border-radius:12px; font-weight:600; font-size:0.85rem; }
.badge-yellow { background:#9a6c00; color:#fff; padding:4px 10px;
                border-radius:12px; font-weight:600; font-size:0.85rem; }
.badge-red    { background:#8b1a1a; color:#fff; padding:4px 10px;
                border-radius:12px; font-weight:600; font-size:0.85rem; }

/* Data-source banner - theme-safe high contrast */
.synthetic-banner {
    background: rgba(230, 81, 0, 0.12); border: 1px solid rgba(230, 81, 0, 0.35);
    border-left: 5px solid #e65100; padding: 10px 14px; border-radius: 6px;
    font-size: 0.88rem; color: inherit; margin-bottom: 12px;
}
.real-banner {
    background: rgba(46, 125, 50, 0.12); border: 1px solid rgba(46, 125, 50, 0.35);
    border-left: 5px solid #2e7d32; padding: 10px 14px; border-radius: 6px;
    font-size: 0.88rem; color: inherit; margin-bottom: 12px;
}

/* Theme-adaptive Reliability Gate Cards */
.gate-card-green {
    background: rgba(46, 125, 50, 0.10);
    border: 1px solid rgba(46, 125, 50, 0.30);
    border-left: 5px solid #2e7d32;
    padding: 14px 16px;
    border-radius: 8px;
    margin-bottom: 10px;
}
.gate-card-yellow {
    background: rgba(230, 81, 0, 0.10);
    border: 1px solid rgba(230, 81, 0, 0.30);
    border-left: 5px solid #e65100;
    padding: 14px 16px;
    border-radius: 8px;
    margin-bottom: 10px;
}
.gate-card-red {
    background: rgba(198, 40, 40, 0.10);
    border: 1px solid rgba(198, 40, 40, 0.30);
    border-left: 5px solid #c62828;
    padding: 14px 16px;
    border-radius: 8px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
def main():
    st.sidebar.markdown(
        '<div style="background:linear-gradient(135deg, #0b3d91 0%, #1a1a3a 100%); '
        'color:white; padding:10px 14px; border-radius:8px; font-weight:700; '
        'font-size:1.0rem; text-align:center; margin-bottom:12px; border:1px solid #1E90FF;">'
        '🛰️ NASA FIRMS · SensorScope'
        '</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.title("🛰️ SensorScope")
    st.sidebar.caption("Explainable MODIS–VIIRS Harmonization")

    page = st.sidebar.radio(
        "Navigate",
        [
            "🏠 Overview",
            "🗺️ Disagreement Atlas",
            "🔬 Calibration Lab",
            "📅 Fire Activity Calendar",
            "📋 Methodology & Evidence",
        ],
    )

    st.sidebar.divider()
    st.sidebar.markdown("**Study Region**  \nPunjab & Haryana, India  \n*(73.8°E–77.5°E, 29.5°N–32.5°N)*")
    st.sidebar.markdown("**Evaluation Period**  \nNov 1–10 (2022 Train · 2023 Eval)  \n*Strict November 1–10 Calibration Cohort*")
    st.sidebar.markdown("**Archive Ingestion**  \n2022–2024 Pilot Records")
    st.sidebar.markdown("**Sensors Harmonized**  \nMODIS SP C6.1 (Aqua)  \nVIIRS SP C2 (Suomi-NPP)")
    st.sidebar.markdown("**Data Source**  \n[NASA FIRMS Standard Processing](https://firms.modaps.eosdis.nasa.gov)")

    # ── Route to pages ─────────────────────────────────────────────────────────────
    import importlib
    if page == "🏠 Overview":
        from pages import overview
        importlib.reload(overview)
        overview.render()
    elif page == "🗺️ Disagreement Atlas":
        from pages import disagreement_atlas
        importlib.reload(disagreement_atlas)
        disagreement_atlas.render()
    elif page == "🔬 Calibration Lab":
        from pages import calibration_lab
        importlib.reload(calibration_lab)
        calibration_lab.render()
    elif page == "📅 Fire Activity Calendar":
        from pages import fire_calendar
        importlib.reload(fire_calendar)
        fire_calendar.render()
    elif page == "📋 Methodology & Evidence":
        from pages import methodology
        importlib.reload(methodology)
        methodology.render()


if __name__ == "__main__":
    main()
