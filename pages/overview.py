"""Page 1 — Overview: summary statistics, sensor counts, AOI map."""

import sys
from pathlib import Path
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pages.data_loader import load_data, data_source_banner


def render() -> None:
    st.title("🛰️ SensorScope — Overview")
    st.caption("Explainable MODIS–VIIRS Harmonization | Punjab & Haryana, India")

    data = load_data()
    data_source_banner(data["using_real_data"])

    # ── Top metrics ────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("MODIS Records", f"{data['n_modis']:,}")
    col2.metric("VIIRS Records", f"{data['n_viirs']:,}")

    disagree = data["disagree"]
    if not disagree.empty:
        both = int(disagree["has_both"].sum())
        m_only = int(disagree["modis_only"].sum())
        v_only = int(disagree["viirs_only"].sum())
        col3.metric("Both-sensor cells", f"{both:,}")
        col4.metric("MODIS-only cells", f"{m_only:,}")
        col5.metric("VIIRS-only cells", f"{v_only:,}")
    else:
        col3.metric("Both-sensor cells", "—")
        col4.metric("MODIS-only cells", "—")
        col5.metric("VIIRS-only cells", "—")

    st.divider()

    # ── Two columns: map + monthly chart ──────────────────────────────────────
    left, right = st.columns([1.2, 1])

    with left:
        st.subheader("📍 Detection locations")
        combined = data["combined"]
        if not combined.empty:
            sample = combined.sample(min(3000, len(combined)), random_state=42)
            scatter_fn = getattr(px, "scatter_map", None) or px.scatter_mapbox
            style_kw = {"map_style": "carto-darkmatter"} if hasattr(px, "scatter_map") else {"mapbox_style": "carto-darkmatter"}
            fig = scatter_fn(
                sample,
                lat="latitude", lon="longitude",
                color="sensor",
                color_discrete_map={"MODIS": "#FF6B35", "VIIRS": "#1E90FF"},
                center=dict(lat=30.8, lon=75.3),
                zoom=6.8,
                opacity=0.6,
                hover_data={"frp_mw": ":.1f", "acq_date": True, "daynight": True},
                title="Sampled fire hotspots — Punjab & Haryana",
                **style_kw,
            )
            fig.update_traces(marker=dict(size=5))
            fig.update_layout(height=420, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No detection data loaded yet.")

    with right:
        st.subheader("📊 Monthly detection counts")
        if not disagree.empty and "year" in disagree.columns:
            monthly = (
                disagree.groupby(["year", "month"])
                .agg(modis=("count_modis", "sum"), viirs=("count_viirs", "sum"))
                .reset_index()
            )
            monthly["period"] = monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2)
            monthly = monthly.sort_values("period")

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=monthly["period"], y=monthly["modis"],
                name="MODIS", marker_color="#FF6B35", opacity=0.8,
            ))
            fig2.add_trace(go.Bar(
                x=monthly["period"], y=monthly["viirs"],
                name="VIIRS", marker_color="#1E90FF", opacity=0.8,
            ))
            fig2.update_layout(
                barmode="group", height=420,
                xaxis_title="Month", yaxis_title="Grid-cell detections",
                legend=dict(orientation="h", y=1.02),
                margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                font_color="#fafafa",
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Processing disagreement data…")

    # ── Reliability summary ────────────────────────────────────────────────────
    st.divider()
    st.subheader("🔒 Calibration Reliability Summary")

    st.markdown(
        "> **Pilot Study Region (Punjab & Haryana):** The regional Context-Aware Calibration (Model C) "
        "is **🟢 Reliable** across the evaluated study domain ($N=2,554$ co-active pairs, held-out validation MAE = 26.19 MW, bias = +8.1% $\\le 15%$ tolerance). "
        "The table below audits the spatial transferability and input domain limits across each individual $0.1^\\circ$ analysis cell."
    )

    rel = data["reliability"]
    if not rel.empty:
        counts = rel["status"].value_counts()
        g = counts.get("green", 0)
        y = counts.get("yellow", 0)
        r = counts.get("red", 0)
        total = len(rel)

        rc1, rc2, rc3 = st.columns(3)
        rc1.markdown(f'<span class="badge-green">🟢 Reliable</span> &nbsp; **{g}** of {total} grid cells', unsafe_allow_html=True)
        rc2.markdown(f'<span class="badge-yellow">🟡 Caution</span> &nbsp; **{y}** of {total} grid cells', unsafe_allow_html=True)
        rc3.markdown(f'<span class="badge-red">🔴 Abstain</span> &nbsp; **{r}** of {total} grid cells', unsafe_allow_html=True)

        with st.expander("View full per-cell reliability audit table"):
            display = rel[["grid_lat", "grid_lon", "n_paired_obs", "status_label",
                           "val_mae", "val_bias_pct", "reason"]].copy()
            display.columns = ["Lat", "Lon", "Local Pairs", "Status",
                               "Val MAE (MW)", "Val bias %", "Scientific Rationale"]
            st.dataframe(display, use_container_width=True)
    else:
        st.info("Reliability analysis not yet available — requires paired MODIS+VIIRS observations.")

    # ── About box ─────────────────────────────────────────────────────────────
    st.divider()
    with st.expander("ℹ️ About SensorScope"):
        st.markdown("""
**SensorScope** investigates why MODIS and VIIRS satellite instruments report different fire
observations for the same location and time, derives a validated common-reference fire activity
measure where the data supports it, and **visibly abstains** when it cannot make a reliable correction.

**Key principle:** A missing FIRMS record does not mean zero fire activity. It may mean
the satellite did not observe that location, or clouds obscured the view.

**Data:** NASA FIRMS Standard Processing — the internally consistent, well-calibrated record
intended for scientific analysis. SP data has a ~3-month availability lag vs. NRT.

**Pilot region:** Punjab & Haryana, India — a high-intensity agricultural burning area
with clear seasonal peaks (Oct–Nov Kharif stubble, Apr–May Rabi stubble).
        """)
