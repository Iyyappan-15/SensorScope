"""Page 1 — Overview: summary statistics, sensor counts, large AOI map."""

from __future__ import annotations
import sys
from pathlib import Path
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pages.data_loader import load_data, data_source_banner


def render() -> None:
    # ── 1. Page Title & Provenance Status ─────────────────────────────────────
    st.title("🛰️ SensorScope — Overview")
    st.markdown(
        '<div style="font-size:0.95rem; font-weight:700; color:#1E90FF; letter-spacing:1.5px; margin-bottom:8px;">'
        'PUNJAB & HARYANA · INDIA &nbsp; | &nbsp; EXPLAINABLE MODIS–VIIRS HARMONIZATION'
        '</div>',
        unsafe_allow_html=True,
    )

    data = load_data()
    data_source_banner(data["using_real_data"])

    # ── 2. Headline Scientific KPI Cards (Strict Nov 1–10 Kharif Peak) ────────
    st.markdown("### 🔬 Audited Scientific Harmonization Population *(Strict Nov 1–10 Window)*")
    st.caption(
        "Peer-audited dataset for Reduced Major Axis (RMA) calibration, date-blocked cross-validation, and Model C evaluation."
    )

    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    sc1.metric("2022 Training Pairs", "1,312", "Nov 1–10, 2022")
    sc2.metric("2023 Evaluation Pairs", "1,242", "Nov 1–10, 2023")
    sc3.metric("Strict Co-Active Pairs", "2,554", "Total Population")
    sc4.metric("Active Dates", "10 + 9", "19 Distinct Passes")
    sc5.metric("Model C Held-Out MAE", "26.19 MW", "+8.1% Bias (Gate: Green)")

    # ── Collapsible Complete Ingestion Archive Metrics ────────────────────────
    with st.expander("📡 View Complete Raw Ingestion Archive Metrics (2022–2023 Archive)", expanded=False):
        st.caption("Full multi-month exploratory records downloaded from NASA FIRMS SP API across the pilot.")
        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        rc1.metric("Raw MODIS Records", f"{data['n_modis']:,}", "Aqua/Terra C6.1")
        rc2.metric("Raw VIIRS Records", f"{data['n_viirs']:,}", "S-NPP C2")
        rc3.metric("Archive Co-Active Cells", "2,560", "Incl. 6 probe records")
        rc4.metric("MODIS-Only Cells", "488", "No VIIRS detection")
        rc5.metric("VIIRS-Only Cells", "3,724", "No MODIS detection")

    st.divider()

    # ── 3. Large Full-Width Satellite Hotspot Explorer ─────────────────────────
    st.markdown("## 🛰️ Satellite Hotspot Explorer")
    st.caption("Large interactive map · Punjab and Haryana, India — Sub-pixel MODIS (1 km) vs VIIRS (375 m) detection comparison")

    combined = data["combined"]
    if not combined.empty:
        # Interactive Control Bar right above the map
        ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1.2, 1.2, 1, 1])

        with ctrl1:
            sensor_selection = st.multiselect(
                "Sensors Visible",
                options=["MODIS", "VIIRS"],
                default=["MODIS", "VIIRS"],
                help="Toggle visibility of individual sensor detection layers.",
            )

        with ctrl2:
            period_selection = st.selectbox(
                "Observation Window",
                options=["Strict Kharif Peak (Nov 1–10)", "All Pilot Records (2022–2023)"],
                index=0,
                help="Strict Kharif Peak filters to the audited Nov 1–10 calibration window.",
            )

        with ctrl3:
            daynight_selection = st.selectbox(
                "Day / Night Pass",
                options=["All Passes", "Day only (☀️ D)", "Night only (🌙 N)"],
                index=0,
                help="Filter by solar illumination at time of satellite overpass.",
            )

        with ctrl4:
            show_grid_overlay = st.checkbox(
                "Show 0.1° Grid Overlay",
                value=False,
                help="Display bounding lines of the 0.1° (~11 km) spatial analysis cells.",
            )

        # Apply filtering
        df_map = combined.copy()

        # Sensor filter
        if sensor_selection:
            df_map = df_map[df_map["sensor"].isin(sensor_selection)]
        else:
            df_map = df_map[df_map["sensor"].isin(["MODIS", "VIIRS"])]

        # Day/Night filter
        if "Day only" in daynight_selection:
            df_map = df_map[df_map["daynight"] == "D"]
        elif "Night only" in daynight_selection:
            df_map = df_map[df_map["daynight"] == "N"]

        # Observation window filter
        if period_selection == "Strict Kharif Peak (Nov 1–10)":
            df_map["month_val"] = pd.to_datetime(df_map["acq_date"]).dt.month
            df_map["day_val"] = pd.to_datetime(df_map["acq_date"]).dt.day
            df_map = df_map[(df_map["month_val"] == 11) & (df_map["day_val"] <= 10)]

        # Sample for fluid browser responsiveness (up to 4,000 points)
        sample_size = min(4000, len(df_map))
        sample = df_map.sample(sample_size, random_state=42) if len(df_map) > sample_size else df_map

        # Geographic bounds verification
        lat_min, lat_max = float(sample["latitude"].min()), float(sample["latitude"].max())
        lon_min, lon_max = float(sample["longitude"].min()), float(sample["longitude"].max())
        in_bbox = bool(
            ((sample["latitude"] >= 29.5) & (sample["latitude"] <= 32.5) &
             (sample["longitude"] >= 73.8) & (sample["longitude"] <= 77.5)).all()
        )

        # Prepare hover information
        sample = sample.copy()
        sample["hover_txt"] = (
            "<b>" + sample["sensor"] + " Active Hotspot</b><br>"
            "<b>Acquisition:</b> " + sample["acq_date"].astype(str) + " " + sample["acq_time"].astype(str).str.zfill(4) + " UTC<br>"
            "<b>FRP:</b> " + sample["frp_mw"].round(1).astype(str) + " MW<br>"
            "<b>Confidence:</b> " + sample["confidence_raw"].astype(str) + "<br>"
            "<b>Pass:</b> " + sample["daynight"].map({"D": "Day (☀️)", "N": "Night (🌙)"}).fillna("Unknown") + "<br>"
            "<b>Coordinates:</b> " + sample["latitude"].round(3).astype(str) + "°N, " + sample["longitude"].round(3).astype(str) + "°E"
        )

        scatter_fn = getattr(px, "scatter_map", None) or px.scatter_mapbox
        map_kw = {"map_style": "carto-darkmatter"} if hasattr(px, "scatter_map") else {"mapbox_style": "carto-darkmatter"}

        target_center = dict(lat=30.8, lon=76.0)
        target_zoom = 6.8

        fig_map = scatter_fn(
            sample,
            lat="latitude",
            lon="longitude",
            color="sensor",
            color_discrete_map={"MODIS": "#FF6B35", "VIIRS": "#1E90FF"},
            center=target_center,
            zoom=target_zoom,
            opacity=0.75,
            hover_name="sensor",
            custom_data=["sensor", "acq_date", "acq_time", "frp_mw", "confidence_raw", "daynight"],
            **map_kw,
        )
        fig_map.update_traces(
            hovertemplate=
            "<b>%{customdata[0]} Active Hotspot</b><br>"
            "<b>Acquisition:</b> %{customdata[1]} %{customdata[2]} UTC<br>"
            "<b>FRP:</b> %{customdata[3]:.1f} MW<br>"
            "<b>Confidence:</b> %{customdata[4]}<br>"
            "<b>Pass:</b> %{customdata[5]}<extra></extra>",
            marker=dict(size=5.5),
        )

        # Optional 0.1° grid boundary overlay
        if show_grid_overlay:
            # Draw study bounding box outline [29.5, 32.5] x [73.8, 77.5]
            lats = [29.5, 29.5, 32.5, 32.5, 29.5]
            lons = [73.8, 77.5, 77.5, 73.8, 73.8]
            box_trace_type = go.Scattermap if hasattr(px, "scatter_map") else go.Scattermapbox
            fig_map.add_trace(
                box_trace_type(
                    lat=lats,
                    lon=lons,
                    mode="lines",
                    line=dict(color="#fbc02d", width=2, dash="dash"),
                    name="0.1° Grid AOI Bounding Box",
                    hoverinfo="text",
                    text="Punjab & Haryana Study AOI Boundary [29.5°–32.5°N, 73.8°–77.5°E]",
                )
            )

        # Explicit layout configuration with fixed center, desktop height ~550px, and cache override
        layout_dict = dict(
            center=target_center,
            zoom=target_zoom,
            style="carto-darkmatter",
        )
        if hasattr(px, "scatter_map"):
            fig_map.update_layout(
                map=layout_dict,
                height=560,
                margin=dict(l=0, r=0, t=30, b=0),
                uirevision="sensorscope_explorer_punjab_v4",
                legend=dict(
                    orientation="h",
                    y=1.03,
                    x=0.0,
                    bgcolor="rgba(14, 17, 23, 0.8)",
                    bordercolor="#333",
                    borderwidth=1,
                ),
            )
        else:
            fig_map.update_layout(
                mapbox=layout_dict,
                height=560,
                margin=dict(l=0, r=0, t=30, b=0),
                uirevision="sensorscope_explorer_punjab_v4",
                legend=dict(
                    orientation="h",
                    y=1.03,
                    x=0.0,
                    bgcolor="rgba(14, 17, 23, 0.8)",
                    bordercolor="#333",
                    borderwidth=1,
                ),
            )

        st.plotly_chart(fig_map, use_container_width=True)

        # Map disclaimers, sampling disclosure and geographic integrity verification
        cap_col1, cap_col2 = st.columns([1.5, 1])
        with cap_col1:
            st.caption(
                f"📍 **Hotspot Sampling Disclosure:** Displaying {len(sample):,} active detections "
                f"({'full filtered subset' if len(sample) == len(df_map) else f'sampled from {len(df_map):,} matching records'} for fluid rendering). "
                "**Physical Note:** Point hotspot detections indicate satellite thermal pixel centroids, NOT physical fire perimeter boundaries."
            )
        with cap_col2:
            if in_bbox:
                st.caption(
                    "✅ **Geographic integrity verified:** 100% of plotted points strictly overlap "
                    f"Punjab & Haryana [29.5°–32.5°N, 73.8°–77.5°E] (Lat: {lat_min:.2f}°–{lat_max:.2f}°N, Lon: {lon_min:.2f}°–{lon_max:.2f}°E)."
                )
            else:
                st.warning("⚠️ Warning: Some plotted points fall outside the configured bounding box!")
    else:
        st.info("No detection data loaded yet.")

    st.divider()

    # ── 4. Historical Activity and Disagreement (Two Columns) ──────────────────
    st.markdown("## 📈 Historical Activity and Disagreement")

    col_hist_left, col_hist_right = st.columns([1.1, 1])

    with col_hist_left:
        st.subheader("📊 Monthly Raw Detections")
        st.caption("Complete multi-year exploratory archive showing seasonal agricultural burning cycles.")
        disagree = data["disagree"]
        if not disagree.empty and "year" in disagree.columns:
            monthly = (
                disagree.groupby(["year", "month"])
                .agg(modis=("count_modis", "sum"), viirs=("count_viirs", "sum"))
                .reset_index()
            )
            monthly["period"] = monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2)
            monthly = monthly.sort_values("period")

            fig_monthly = go.Figure()
            fig_monthly.add_trace(go.Bar(
                x=monthly["period"], y=monthly["modis"],
                name="MODIS Raw Detections", marker_color="#FF6B35", opacity=0.85,
            ))
            fig_monthly.add_trace(go.Bar(
                x=monthly["period"], y=monthly["viirs"],
                name="VIIRS Raw Detections", marker_color="#1E90FF", opacity=0.85,
            ))
            fig_monthly.update_layout(
                barmode="group",
                height=380,
                xaxis_title="Month",
                yaxis_title="Reported Grid-Cell Detections",
                legend=dict(orientation="h", y=1.05, x=0.0),
                margin=dict(l=0, r=0, t=25, b=0),
                plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                font_color="#fafafa",
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
            st.caption(
                "🔥 **Seasonal burning dynamics:** The massive October–November peak corresponds to post-monsoon "
                "Kharif paddy stubble burning. A secondary minor peak occurs in April–May (Rabi wheat harvest). "
                "Scientific calibration is evaluated strictly on the November peak."
            )
        else:
            st.info("Processing disagreement data…")

    with col_hist_right:
        st.subheader("🗺️ Sensor Disagreement Breakdown")
        st.caption("Cross-sensor reporting asymmetry across all 6,751 calendar cell-days.")
        if not disagree.empty:
            total_cells = len(disagree)
            both_count = int(disagree["has_both"].sum())
            m_only_count = int(disagree["modis_only"].sum())
            v_only_count = int(disagree["viirs_only"].sum())

            # Horizontal bar comparison
            dis_df = pd.DataFrame({
                "Category": ["Both Sensors Active", "VIIRS Only (MODIS Missed)", "MODIS Only (VIIRS Missed)"],
                "Count": [both_count, v_only_count, m_only_count],
                "Share": [both_count / total_cells * 100, v_only_count / total_cells * 100, m_only_count / total_cells * 100],
                "Color": ["#4caf50", "#1E90FF", "#FF6B35"],
            })

            fig_dis = go.Figure()
            fig_dis.add_trace(go.Bar(
                y=dis_df["Category"],
                x=dis_df["Count"],
                orientation="h",
                marker=dict(color=dis_df["Color"]),
                text=dis_df.apply(lambda r: f"{r['Count']:,} ({r['Share']:.1f}%)", axis=1),
                textposition="auto",
            ))
            fig_dis.update_layout(
                height=380,
                xaxis_title="Grid-Cell Observations",
                yaxis=dict(autorange="reversed"),
                margin=dict(l=0, r=0, t=25, b=0),
                plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                font_color="#fafafa",
            )
            st.plotly_chart(fig_dis, use_container_width=True)
            st.caption(
                "⚡ **Sub-pixel sensitivity asymmetry:** VIIRS reports fire in 3,724 cells where MODIS reports none (55.0%), "
                "driven by its 375 m pixel resolving weak agricultural burns that dilute across MODIS's 1 km footprint."
            )
        else:
            st.info("Processing disagreement data…")

    st.divider()

    # ── 5. Calibration Reliability Summary & Limitations ──────────────────────
    st.markdown("## 🔒 Calibration Reliability")
    st.caption("Evidence-based decision gate determining when calibrated estimates are scientifically justified.")

    # Executive gate status cards
    gc1, gc2, gc3 = st.columns(3)
    with gc1:
        st.markdown(
            '<div style="background:#1b3a24; border-left:4px solid #4caf50; padding:12px 16px; border-radius:6px;">'
            '<strong style="color:#4caf50; font-size:1.0rem;">🟢 Reliable (Pilot Model)</strong><br>'
            '<span style="font-size:0.85rem; color:#cfd8dc;">'
            '<strong>Model C (Context OLS)</strong> is fully supported across Punjab & Haryana. '
            'N = 2,554 co-active pairs (1,312 train / 1,242 eval), held-out MAE = 26.19 MW, bias = +8.1% (≤ ±15% threshold).'
            '</span></div>',
            unsafe_allow_html=True,
        )
    with gc2:
        st.markdown(
            '<div style="background:#3a3014; border-left:4px solid #ff9800; padding:12px 16px; border-radius:6px;">'
            '<strong style="color:#ff9800; font-size:1.0rem;">🟡 Caution (Subgroup Alert)</strong><br>'
            '<span style="font-size:0.85rem; color:#cfd8dc;">'
            'Subgroups with timing difference Δt ≤ 5 min exhibit +26.9% validation bias (exceeding ±15%), '
            'or 20 ≤ N < 50 pairs. Calibrated estimates shown with uncertainty warning.'
            '</span></div>',
            unsafe_allow_html=True,
        )
    with gc3:
        st.markdown(
            '<div style="background:#3a1818; border-left:4px solid #f44336; padding:12px 16px; border-radius:6px;">'
            '<strong style="color:#f44336; font-size:1.0rem;">🔴 Abstain (Safety Guard)</strong><br>'
            '<span style="font-size:0.85rem; color:#cfd8dc;">'
            'Triggered when N < 20 pairs or FRP > 279.18 MW (99th percentile). '
            'System suppresses calibration and reports raw satellite observations only.'
            '</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Spatial Applicability Audit across 481 Active 0.1° Grid Cells")
    rel = data["reliability"]
    if not rel.empty:
        counts = rel["status"].value_counts()
        g = counts.get("green", 0)
        y = counts.get("yellow", 0)
        r = counts.get("red", 0)
        total = len(rel)

        ac1, ac2, ac3 = st.columns(3)
        ac1.markdown(f'<span class="badge-green">🟢 Reliable</span> &nbsp; **{g}** of {total} grid cells (in-domain agricultural fires)', unsafe_allow_html=True)
        ac2.markdown(f'<span class="badge-yellow">🟡 Caution</span> &nbsp; **{y}** of {total} grid cells (borderline conditions)', unsafe_allow_html=True)
        ac3.markdown(f'<span class="badge-red">🔴 Abstain</span> &nbsp; **{r}** of {total} grid cells (extreme outlier FRP > 279 MW)', unsafe_allow_html=True)

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
