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
/* Reliability status badges */
.badge-green  { background:#1b7a3e; color:#fff; padding:4px 10px;
                border-radius:12px; font-weight:600; font-size:0.85rem; }
.badge-yellow { background:#9a6c00; color:#fff; padding:4px 10px;
                border-radius:12px; font-weight:600; font-size:0.85rem; }
.badge-red    { background:#8b1a1a; color:#fff; padding:4px 10px;
                border-radius:12px; font-weight:600; font-size:0.85rem; }

/* Data-source banner */
.synthetic-banner {
    background:#3a2800; border-left:4px solid #f0a500;
    padding:8px 14px; border-radius:4px;
    font-size:0.82rem; color:#f0a500; margin-bottom:12px;
}
.real-banner {
    background:#1a3a1a; border-left:4px solid #4caf50;
    padding:8px 14px; border-radius:4px;
    font-size:0.82rem; color:#4caf50; margin-bottom:12px;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
def main():
    st.sidebar.image("https://firms.modaps.eosdis.nasa.gov/img/firms_logo.png", width=140)
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
    st.sidebar.markdown("**Study Region**  \nPunjab & Haryana, India")
    st.sidebar.markdown("**Period**  \n2022–2024 (pilot)")
    st.sidebar.markdown("**Sensors**  \nMODIS SP C6.1 · VIIRS S-NPP SP C2")
    st.sidebar.markdown("**Data Source**  \n[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov)")

    # ── Route to pages ─────────────────────────────────────────────────────────────
    if page == "🏠 Overview":
        from pages import overview
        overview.render()
    elif page == "🗺️ Disagreement Atlas":
        from pages import disagreement_atlas
        disagreement_atlas.render()
    elif page == "🔬 Calibration Lab":
        from pages import calibration_lab
        calibration_lab.render()
    elif page == "📅 Fire Activity Calendar":
        from pages import fire_calendar
        fire_calendar.render()
    elif page == "📋 Methodology & Evidence":
        from pages import methodology
        methodology.render()


if __name__ == "__main__":
    main()
