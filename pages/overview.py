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
from config import REGIONAL_KEY_CITIES


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

    # ── 2. Headline Scientific KPI Cards (Strict November 1–10 Cohort) ────────
    st.markdown("### 🔬 Audited Pilot Harmonization Population *(Strict Nov 1–10 Window)*")
    st.caption(
        "Audited pilot dataset for Reduced Major Axis (RMA) calibration, date-grouped cross-validation, and Model C evaluation."
    )

    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    sc1.metric("2022 Training Observations", "1,312", "Nov 1–10, 2022")
    sc2.metric("2023 Evaluation Observations", "1,242", "Nov 1–10, 2023")
    sc3.metric("Co-active cell-day observations", "2,554", "Total Population")
    sc4.metric("Active Study Dates", "10 + 9", "19 Active Study Dates")
    sc5.metric("Model C Nov 2023 Evaluation MAE", "26.19 MW", "+8.1% Bias (Aggregate Pilot Gate: Green)")

    st.caption(
        "ℹ️ **Gate Scope:** *Aggregate Pilot Gate is GREEN across the regional evaluation dataset (+8.1% bias, MAE = 26.19 MW). "
        "Individual temporal subgroups (e.g., Δt ≤ 5 min) receive CAUTION or ABSTAIN statuses due to elevated subgroup validation bias or localized sample size limitations.*"
    )

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
        ctrl1, ctrl2, ctrl3, ctrl4, ctrl5 = st.columns([1.1, 1.0, 1.1, 0.9, 0.9])

        with ctrl1:
            basemap_choice = st.selectbox(
                "Map View / Basemap",
                options=["🛰️ Satellite (ESRI)", "☀️ Light (OSM)", "🗺️ Positron (Light)", "🌑 Dark Matter"],
                index=0,
                help="Toggle between high-resolution ESRI satellite imagery, OpenStreetMap light, Positron, or Dark Matter.",
            )

        with ctrl2:
            sensor_selection = st.multiselect(
                "Sensors Visible",
                options=["MODIS", "VIIRS"],
                default=["MODIS", "VIIRS"],
                help="Toggle visibility of individual sensor detection layers.",
            )

        with ctrl3:
            period_selection = st.selectbox(
                "Observation Window",
                options=["Strict November 1–10 Cohort", "All Pilot Records (2022–2023)"],
                index=0,
                help="Filters to the audited November 1–10 calibration cohort (2,554 strict co-active observations).",
            )

        with ctrl4:
            daynight_selection = st.selectbox(
                "Day / Night Pass",
                options=["All Passes", "Day only (☀️ D)", "Night only (🌙 N)"],
                index=0,
                help="Filter by solar illumination at time of satellite overpass.",
            )

        with ctrl5:
            show_grid_overlay = st.checkbox(
                "0.1° Grid Overlay",
                value=False,
                help="Display bounding lines of the 0.1° (~11 km) spatial analysis cells.",
            )
            density_view = st.checkbox(
                "Density Heatmap View",
                value=False,
                help="Render a continuous thermal kernel density surface instead of discrete point centroids.",
            )
            show_city_labels = st.checkbox(
                "Show City Labels",
                value=True,
                help="Display major regional city names (Ludhiana, Amritsar, Bathinda, etc.) for geographic orientation.",
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
        if period_selection == "Strict November 1–10 Cohort":
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

        # Prepare rich, human-readable hover information
        sample = sample.copy()

        def _fmt_conf(row):
            s = row["sensor"]
            raw = str(row["confidence_raw"]).strip()
            if s == "VIIRS":
                mapping = {"n": "Nominal (N)", "h": "High (H)", "l": "Low (L)"}
                return mapping.get(raw.lower(), f"{raw.upper()}")
            else:
                try:
                    val = int(float(raw))
                    cat = "High" if val >= 80 else ("Nominal" if val >= 30 else "Low")
                    return f"{val}% ({cat})"
                except Exception:
                    return raw

        def _fmt_date(d):
            try:
                return pd.to_datetime(d).strftime("%d %b %Y")
            except Exception:
                return str(d)

        def _fmt_time(t):
            s = str(t).zfill(4)
            return f"{s[:2]}:{s[2:]} UTC"

        sample["date_disp"] = sample["acq_date"].apply(_fmt_date)
        sample["time_disp"] = sample["acq_time"].apply(_fmt_time)
        sample["conf_disp"] = sample.apply(_fmt_conf, axis=1)
        sample["dn_disp"] = sample["daynight"].map({"D": "Day (☀️)", "N": "Night (🌙)"}).fillna("Unknown")
        sample["coord_disp"] = sample.apply(lambda r: f"{r['latitude']:.4f}°N, {r['longitude']:.4f}°E", axis=1)

        # Basemap configuration
        esri_layer = {
            "below": "traces",
            "sourcetype": "raster",
            "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
        }
        esri_labels_layer = {
            "below": "traces",
            "sourcetype": "raster",
            "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"],
        }

        if "Satellite" in basemap_choice:
            map_style = "white-bg"
            map_layers = [esri_layer, esri_labels_layer]
        elif "OSM" in basemap_choice:
            map_style = "open-street-map"
            map_layers = []
        elif "Positron" in basemap_choice:
            map_style = "carto-positron"
            map_layers = []
        else:
            map_style = "carto-darkmatter"
            map_layers = []

        scatter_fn = getattr(px, "scatter_map", None) or px.scatter_mapbox
        map_kw = {"map_style": map_style} if hasattr(px, "scatter_map") else {"mapbox_style": map_style}

        target_center = dict(lat=30.8, lon=76.0)
        target_zoom = 6.8

        if density_view:
            density_fn = getattr(px, "density_map", None) or px.density_mapbox
            fig_map = density_fn(
                sample,
                lat="latitude",
                lon="longitude",
                z="frp_mw",
                radius=14,
                center=target_center,
                zoom=target_zoom,
                opacity=0.8,
                color_continuous_scale="Viridis",
                labels={"frp_mw": "FRP (MW)"},
                **map_kw,
            )
        else:
            fig_map = scatter_fn(
                sample,
                lat="latitude",
                lon="longitude",
                color="sensor",
                color_discrete_map={"MODIS": "#FF6B35", "VIIRS": "#1E90FF"},
                center=target_center,
                zoom=target_zoom,
                opacity=0.8,
                hover_name="sensor",
                custom_data=["sensor", "date_disp", "time_disp", "frp_mw", "conf_disp", "dn_disp", "coord_disp"],
                **map_kw,
            )
            fig_map.update_traces(
                hovertemplate=(
                    "<b>%{customdata[0]} Active Hotspot</b><br><br>"
                    "<b>Observation details</b><br>"
                    "• <b>Date:</b> %{customdata[1]}<br>"
                    "• <b>Acquisition time:</b> %{customdata[2]}<br>"
                    "• <b>FRP:</b> %{customdata[3]:.1f} MW<br>"
                    "• <b>Confidence:</b> %{customdata[4]}<br>"
                    "• <b>Day/Night:</b> %{customdata[5]}<br>"
                    "• <b>Coordinates:</b> %{customdata[6]}"
                    "<extra></extra>"
                ),
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
                    line=dict(color="#fbc02d", width=2.5, dash="dash"),
                    name="0.1° Grid AOI Bounding Box",
                    hoverinfo="text",
                    text="Punjab & Haryana Study AOI Boundary [29.5°–32.5°N, 73.8°–77.5°E]",
                )
            )

        # Optional Major City Landmark Labels
        if show_city_labels:
            city_trace_type = go.Scattermap if hasattr(px, "scatter_map") else go.Scattermapbox
            fig_map.add_trace(
                city_trace_type(
                    lat=[c["lat"] for c in REGIONAL_KEY_CITIES],
                    lon=[c["lon"] for c in REGIONAL_KEY_CITIES],
                    mode="markers+text",
                    text=[c["name"] for c in REGIONAL_KEY_CITIES],
                    textposition="top center",
                    textfont=dict(size=11, color="#FFFFFF", family="Arial Black"),
                    marker=dict(size=8, color="#FFD700", symbol="circle"),
                    name="Major Cities",
                    hovertext=[f"<b>📍 {c['name']}</b> ({c['state']})<br>Coordinates: {c['lat']:.4f}°N, {c['lon']:.4f}°E" for c in REGIONAL_KEY_CITIES],
                    hoverinfo="text",
                )
            )

        # Explicit layout configuration with fixed center, desktop height ~560px, and dynamic basemap
        layout_dict = dict(
            center=target_center,
            zoom=target_zoom,
            style=map_style,
            layers=map_layers,
        )
        if hasattr(px, "scatter_map"):
            fig_map.update_layout(
                map=layout_dict,
                height=560,
                margin=dict(l=0, r=0, t=30, b=0),
                uirevision=f"sensorscope_explorer_{basemap_choice}_{density_view}",
                legend=dict(
                    orientation="h",
                    y=1.03,
                    x=0.0,
                    bgcolor="rgba(0, 0, 0, 0.4)",
                    font=dict(color="#ffffff"),
                    bordercolor="#444",
                    borderwidth=1,
                ),
            )
        else:
            fig_map.update_layout(
                mapbox=layout_dict,
                height=560,
                margin=dict(l=0, r=0, t=30, b=0),
                uirevision=f"sensorscope_explorer_{basemap_choice}_{density_view}",
                legend=dict(
                    orientation="h",
                    y=1.03,
                    x=0.0,
                    bgcolor="rgba(0, 0, 0, 0.4)",
                    font=dict(color="#ffffff"),
                    bordercolor="#444",
                    borderwidth=1,
                ),
            )

        st.plotly_chart(fig_map, use_container_width=True)

        # Basemap provider attribution
        st.caption(
            "🛰️ **Basemap Attribution:** Imagery © ESRI, Maxar, Earthstar Geographics, and the GIS User Community. "
            "Vector tiles © OpenStreetMap contributors, CartoDB."
        )

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
                yaxis_title="Raw hotspot records",
                legend=dict(orientation="h", y=1.05, x=0.0),
                margin=dict(l=0, r=0, t=25, b=0),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
            st.caption(
                "🔥 **Seasonal Activity Patterns:** The observed seasonal pattern coincides with reported regional agricultural burning periods "
                "(post-monsoon paddy stubble in Oct–Nov; minor Rabi wheat residue in Apr–May). "
                "FIRMS hotspot detections do not independently establish the fuel type or cause of each fire. "
                "Scientific calibration is evaluated strictly on the November peak."
            )
        else:
            st.info("Processing disagreement data…")

    with col_hist_right:
        st.subheader("🗺️ Sensor Disagreement Breakdown")
        st.caption("Cross-sensor detection patterns across 6,772 diurnal cell observations (6,751 unique calendar cell-dates).")
        if not disagree.empty:
            total_cells = len(disagree)
            both_count = int(disagree["has_both"].sum())
            m_only_count = int(disagree["modis_only"].sum())
            v_only_count = int(disagree["viirs_only"].sum())

            # Horizontal bar comparison
            dis_df = pd.DataFrame({
                "Category": ["Both Sensors Detected", "VIIRS-only observations", "MODIS-only observations"],
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
                xaxis_title="Diurnal Cell Observations",
                yaxis=dict(autorange="reversed"),
                margin=dict(l=0, r=0, t=25, b=0),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_dis, use_container_width=True)
            st.caption(
                "⚡ **Observation Asymmetry:** VIIRS reports fire in 3,724 cells where MODIS reports none (55.0%), "
                "while MODIS reports fire in 488 cells where VIIRS reports none (7.2%). "
                "VIIRS-only observations may reflect differences in spatial resolution, observation timing, viewing geometry, "
                "atmospheric conditions and sensor detection characteristics. The current analysis does not isolate the cause of individual disagreements."
            )
        else:
            st.info("Processing disagreement data…")

    st.divider()

    # ── 5. Calibration Reliability Summary & Limitations ──────────────────────
    st.markdown("## 🔒 Calibration Reliability")
    st.caption("Evidence-based decision gate determining when calibrated estimates are scientifically justified.")

    # Executive gate status cards - Theme-adaptive high contrast
    gc1, gc2, gc3 = st.columns(3)
    with gc1:
        st.markdown(
            '<div class="gate-card-green">'
            '<strong style="color:#2e7d32; font-size:1.0rem;">🟢 Reliable (Aggregate Pilot Model)</strong><br>'
            '<span style="font-size:0.88rem; color:inherit; line-height:1.45; display:inline-block; margin-top:4px;">'
            '<strong>Model C (Context OLS)</strong> meets the aggregate evaluation criteria for the November Punjab–Haryana pilot dataset '
            '(held-out MAE = 26.19 MW, bias = +8.1% across N = 2,554 co-active pairs). '
            'This does not establish independent reliability for every individual grid cell, season or fire condition.'
            '</span></div>',
            unsafe_allow_html=True,
        )
    with gc2:
        st.markdown(
            '<div class="gate-card-yellow">'
            '<strong style="color:#e65100; font-size:1.0rem;">🟡 Caution (Subgroup Alert)</strong><br>'
            '<span style="font-size:0.88rem; color:inherit; line-height:1.45; display:inline-block; margin-top:4px;">'
            'Subgroups with timing difference Δt ≤ 5 min exhibit +26.9% validation bias (exceeding ±15%), '
            'or 20 ≤ N < 50 pairs. Calibrated estimates shown with uncertainty warning.'
            '</span></div>',
            unsafe_allow_html=True,
        )
    with gc3:
        st.markdown(
            '<div class="gate-card-red">'
            '<strong style="color:#c62828; font-size:1.0rem;">🔴 Abstain (Safety Guard)</strong><br>'
            '<span style="font-size:0.88rem; color:inherit; line-height:1.45; display:inline-block; margin-top:4px;">'
            'Triggered when N < 20 pairs or FRP > 279.18 MW (99th percentile). '
            'System suppresses calibration and reports raw satellite observations only.'
            '</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Spatial Applicability of the Regional Calibration Model (481 Active 0.1° Grid Cells)")
    st.info(
        "ℹ️ **Evaluation Scope Clarification:** "
        "The metrics below (**Regional Evaluation MAE = 26.19 MW**, **Regional Evaluation Bias = +8.1%**) "
        "reflect the *aggregate performance of the regional Model C on the held-out November 2023 evaluation sample*. "
        "They are **NOT independent per-cell validation metrics**, as individual 0.1° grid cells possess only 1 to 28 local co-active observations "
        "(statistically insufficient for standalone local regression). "
        "The status indicates whether each cell's local mean FRP falls within the regional model's evaluated input domain (Q01–Q99).",
        icon=None,
    )
    rel = data["reliability"]
    if not rel.empty:
        counts = rel["status"].value_counts()
        g = counts.get("green", 0)
        y = counts.get("yellow", 0)
        r = counts.get("red", 0)
        total = len(rel)

        ac1, ac2, ac3 = st.columns(3)
        ac1.markdown(f'<span class="badge-green">🟢 In-domain</span> &nbsp; **{g}** of {total} grid cells (cell mean FRP within Q01–Q99 bounds)', unsafe_allow_html=True)
        ac2.markdown(f'<span class="badge-yellow">🟡 Caution</span> &nbsp; **{y}** of {total} grid cells (borderline conditions)', unsafe_allow_html=True)
        ac3.markdown(f'<span class="badge-red">🔴 Out-of-domain</span> &nbsp; **{r}** of {total} grid cells (outlier mean FRP > 279.18 MW)', unsafe_allow_html=True)

        with st.expander("View full per-cell domain applicability table"):
            display = rel[["grid_lat", "grid_lon", "n_paired_obs", "status_label",
                           "val_mae", "val_bias_pct", "reason"]].copy()
            display.columns = ["Grid Lat", "Grid Lon", "Local co-active observations", "Regional Domain Status",
                               "Regional evaluation MAE (MW)", "Regional evaluation bias %", "Domain Applicability Rationale"]
            st.dataframe(display, use_container_width=True)
    else:
        st.info("Reliability analysis not yet available — requires paired MODIS+VIIRS observations.")

    # ── About box ─────────────────────────────────────────────────────────────
    st.divider()
    with st.expander("ℹ️ About SensorScope"):
        st.markdown("""
**About SensorScope**

SensorScope investigates differences between MODIS and VIIRS active-fire observations over Punjab and Haryana, India.

It compares sensor-specific detections, aggregates observations into geographic grid-cell and diurnal periods, and evaluates an empirical MODIS-referenced FRP harmonization model where sufficient evidence exists.

**Key principle:** A missing FIRMS detection does not mean zero fire activity. It may mean the location was not observed or the thermal anomaly was not detected (e.g. cloud obscuration, orbital gap).

**Data:** NASA FIRMS Standard Processing products — Aqua MODIS Collection 6.1 and Suomi-NPP VIIRS Collection 2.

**Scientific scope:** The current calibration is evaluated on jointly active cell-day observations during the November agricultural burning pilot. It is an empirical MODIS-referenced FRP harmonization for jointly active cell-day observations, not a universal sensor correction or an individual fire-event matching system.
        """)
