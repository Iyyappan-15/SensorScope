"""Page 2 — Disagreement Atlas: where and why sensors differ."""

import sys
from pathlib import Path
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pages.data_loader import load_data, data_source_banner
from analysis.disagreement import disagreement_by_daynight, disagreement_by_season
from config import REGIONAL_KEY_CITIES


def render() -> None:
    st.title("🗺️ Disagreement Atlas")
    st.caption("Where do MODIS and VIIRS report different fire activity — and why?")

    data = load_data()
    data_source_banner(data["using_real_data"])

    disagree = data["disagree"]
    combined_assoc = data["combined_assoc"]

    if disagree.empty:
        st.warning("No disagreement data available. Load satellite data first.")
        return

    # ── Overall match breakdown ────────────────────────────────────────────────
    st.subheader("📊 Cross-sensor observation breakdown")
    st.caption("Exploratory archive: 6,772 diurnal cell observations, representing 6,751 unique calendar cell-dates.")

    total_cells = len(disagree)
    both   = int(disagree["has_both"].sum())
    m_only = int(disagree["modis_only"].sum())
    v_only = int(disagree["viirs_only"].sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Diurnal Cell Obs", f"{total_cells:,}")
    col2.metric("Both sensors detected", f"{both:,}", f"{both/total_cells*100:.1f}%")
    col3.metric("MODIS only", f"{m_only:,}", f"{m_only/total_cells*100:.1f}%")
    col4.metric("VIIRS only", f"{v_only:,}", f"{v_only/total_cells*100:.1f}%")

    st.info(
        "⚠️ **Interpretation note:** 'MODIS only' or 'VIIRS only' indicates observations reported by one sensor where the other sensor recorded no active fire hotspots in that grid cell during that pass. It does **not** prove the other sensor missed a real fire, as overpass timing, cloud cover, satellite viewing geometry, and sub-pixel detection limits differ.\n\n"
        "ℹ️ **Population Distinction:** The 2,560 'Both sensors detected' observations belong to the broader exploratory archive (6,772 diurnal observations across 6,751 unique cell-dates). The strict calibration evaluation specifically evaluates 2,554 co-active cell-day observations (1,312 training + 1,242 evaluation) from November 1–10, 2022 and November 1–10, 2023.",
        icon=None,
    )

    st.divider()

    # ── Spatial disagreement map ───────────────────────────────────────────────
    left, right = st.columns([1.3, 1])

    with left:
        st.subheader("🗺️ Spatial reporting asymmetry (VIIRS − MODIS)")
        
        c_map1, c_map2, c_map3 = st.columns([1.1, 1.1, 0.8])
        with c_map1:
            basemap_choice = st.selectbox(
                "Map View / Basemap",
                options=["🛰️ Satellite (ESRI)", "☀️ Light (OSM)", "🗺️ Positron (Light)", "🌑 Dark Matter"],
                index=0,
                help="Choose background basemap: real satellite imagery, bright OpenStreetMap, Positron, or Dark Matter.",
                key="atlas_basemap",
            )
        with c_map2:
            min_days = st.slider(
                "Min Diurnal Passes per Cell",
                min_value=1,
                max_value=15,
                value=1,
                help="Filter to cells observed across at least N diurnal passes to suppress transient single-pass noise.",
            )
        with c_map3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            show_city_labels = st.checkbox(
                "Show City Labels",
                value=True,
                help="Display major regional city names (Ludhiana, Amritsar, Bathinda, etc.) for geographic orientation.",
                key="atlas_cities",
            )

        map_data = disagree.groupby(["grid_lat", "grid_lon"]).agg(
            mean_d_count=("d_count", "mean"),
            n_days=("d_count", "count"),
        ).reset_index()

        if min_days > 1:
            map_data = map_data[map_data["n_days"] >= min_days]

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
        style_kw = {"map_style": map_style} if hasattr(px, "scatter_map") else {"mapbox_style": map_style}

        target_center = dict(lat=30.8, lon=76.0)

        fig = scatter_fn(
            map_data,
            lat="grid_lat", lon="grid_lon",
            color="mean_d_count",
            size="n_days",
            size_max=8,
            color_continuous_scale="RdBu",
            color_continuous_midpoint=0,
            range_color=[-5, 5],
            center=target_center,
            zoom=6.6,
            opacity=0.75,
            custom_data=["mean_d_count", "n_days"],
            labels={"mean_d_count": "Mean Δ count (VIIRS−MODIS)", "n_days": "Observation passes"},
            **style_kw,
        )
        fig.update_traces(
            hovertemplate=(
                "<b>0.1° Grid Cell</b><br>"
                "<b>Coordinates:</b> %{lat:.2f}°N, %{lon:.2f}°E<br>"
                "<b>Mean Δ count (VIIRS−MODIS):</b> %{customdata[0]:+.2f}<br>"
                "<b>Observation Passes:</b> %{customdata[1]}<extra></extra>"
            ),
            marker=dict(opacity=0.8),
        )

        # Optional Major City Landmark Labels
        if show_city_labels:
            city_trace_type = go.Scattermap if hasattr(px, "scatter_map") else go.Scattermapbox
            fig.add_trace(
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

        layout_dict = dict(
            center=target_center,
            zoom=6.6,
            style=map_style,
            layers=map_layers,
        )
        if hasattr(px, "scatter_map"):
            fig.update_layout(
                map=layout_dict,
                height=480, margin=dict(l=0, r=0, t=10, b=0),
                uirevision=f"sensorscope_atlas_{basemap_choice}",
                coloraxis_colorbar=dict(
                    title="Mean Δ count",
                    orientation="h",
                    y=-0.18,
                    x=0.5,
                    xanchor="center",
                    len=0.85,
                ),
            )
        else:
            fig.update_layout(
                mapbox=layout_dict,
                height=480, margin=dict(l=0, r=0, t=10, b=0),
                uirevision=f"sensorscope_atlas_{basemap_choice}",
                coloraxis_colorbar=dict(
                    title="Mean Δ count",
                    orientation="h",
                    y=-0.18,
                    x=0.5,
                    xanchor="center",
                    len=0.85,
                ),
            )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "🔵 Blue = More VIIRS-reported records | 🔴 Red = More MODIS-reported records | ⚪ White = Similar reported counts<br>"
            "Aggregation: $\\Delta C = \\text{Mean}(C_{\\text{VIIRS}} - C_{\\text{MODIS}})$ per $0.1^\\circ$ grid cell across all diurnal observation passes.",
            unsafe_allow_html=True,
        )

    with right:
        st.subheader("📊 Disagreement by Day / Night")
        st.caption("Mean difference in reported hotspot counts per diurnal cell observation (VIIRS − MODIS)")
        dn_stats = disagreement_by_daynight(disagree)
        if not dn_stats.empty:
            day_row = dn_stats[dn_stats["daynight"] == "D"]
            night_row = dn_stats[dn_stats["daynight"] == "N"]
            day_n = int(day_row["n_cells"].values[0]) if not day_row.empty else 0
            night_n = int(night_row["n_cells"].values[0]) if not night_row.empty else 0

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=dn_stats["daynight"], y=dn_stats["mean_d_count"],
                name="Δ count", marker_color=["#1E90FF", "#FF6B35"],
                text=dn_stats["mean_d_count"].round(2), textposition="auto",
            ))
            fig2.update_layout(
                yaxis_title="Mean Δ count",
                xaxis=dict(
                    tickvals=["D", "N"],
                    ticktext=[f"☀️ Day (n={day_n:,})", f"🌙 Night (n={night_n:,})"],
                ),
                height=220,
                margin=dict(l=0, r=0, t=20, b=0),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📊 Disagreement by Season")
        season_stats = disagreement_by_season(disagree)
        if not season_stats.empty:
            season_order = ["Pre-monsoon", "Monsoon", "Post-monsoon", "Winter"]
            season_stats["season"] = pd.Categorical(
                season_stats["season"], categories=season_order, ordered=True
            )
            season_stats = season_stats.sort_values("season")
            fig3 = px.bar(
                season_stats, x="season", y="mean_d_count",
                color="mean_d_count",
                color_continuous_scale="RdBu",
                color_continuous_midpoint=0,
                labels={"mean_d_count": "Mean Δ count", "season": "Season"},
            )
            fig3.update_layout(
                height=220, showlegend=False,
                yaxis_title="Mean Δ count",
                margin=dict(l=0, r=0, t=20, b=0),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig3, use_container_width=True)
            st.caption(
                "• **Post-monsoon** (Oct–Nov, n=6,731): Post-monsoon agricultural burning peak (mean Δ count = +3.76).<br>"
                "• **Pre-monsoon** (Mar–May, n=41): Rabi harvest burning (mean Δ count = +1.12).<br>"
                "*Note: Observational archive data, not a controlled seasonal experiment. Monsoon and winter passes are unrepresented in this pilot archive.*",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── FRP distribution comparison ────────────────────────────────────────────
    st.subheader("🔥 Fire Radiative Power (FRP) distribution")
    combined = data["combined"]
    if not combined.empty:
        fig4 = px.histogram(
            combined,
            x="frp_mw", color="sensor",
            nbins=60, barmode="overlay",
            color_discrete_map={"MODIS": "#FF6B35", "VIIRS": "#1E90FF"},
            opacity=0.7,
            labels={"frp_mw": "FRP (MW)", "sensor": "Sensor"},
            title="Descriptive Raw FRP Distribution — MODIS vs VIIRS (0 – 158 MW)",
        )
        fig4.update_layout(
            height=320,
            yaxis_title="Number of hotspot records",
            xaxis_title="FRP (MW)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig4, use_container_width=True)
        st.caption(
            "Full exploratory archive range (0.0 to 158.0 MW; 95th percentile is 24.1 MW). "
            "VIIRS detects a substantially higher volume of lower-FRP hotspots, reflecting its finer 375 m nadir footprint resolving smaller agricultural burns. "
            "Rather than a single cause, observed FRP discrepancies arise from a combination of pixel footprint scaling, "
            "sub-pixel fire fractional area, overpass time offsets (fires rapidly igniting or extinguishing), and atmospheric transmission."
        )

    # ── Association status breakdown ───────────────────────────────────────────
    if not combined_assoc.empty and "match_status" in combined_assoc.columns:
        st.divider()
        st.subheader("🔗 Candidate association status")

        # Map to rigorous labels
        status_label_map = {
            "matched": "Unambiguous candidate",
            "ambiguous": "Multiple candidate associations",
            "unmatched": "No candidate within selected thresholds",
        }
        assoc_df = combined_assoc.copy()
        assoc_df["status_label"] = assoc_df["match_status"].map(status_label_map).fillna(assoc_df["match_status"])

        status_counts = assoc_df.groupby(["sensor", "status_label"]).size().reset_index(name="count")
        
        n_tot = len(assoc_df)
        n_m = len(assoc_df[assoc_df["sensor"] == "MODIS"])
        n_v = len(assoc_df[assoc_df["sensor"] == "VIIRS"])

        fig5 = px.bar(
            status_counts, x="sensor", y="count", color="status_label",
            barmode="stack",
            color_discrete_map={
                "Unambiguous candidate": "#4caf50",
                "Multiple candidate associations": "#ff9800",
                "No candidate within selected thresholds": "#f44336",
            },
            labels={"count": "Records", "status_label": "Candidate Status"},
            title=f"Cross-sensor candidate association status (Sample of {n_tot:,} records)",
        )
        fig5.update_layout(
            height=300,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig5, use_container_width=True)
        st.caption(
            f"Based on a representative sample of {n_tot:,} hotspot records ({n_m:,} MODIS, {n_v:,} VIIRS) "
            "evaluated against nominal spatial-temporal thresholds (15 min, 11 km).<br>"
            "⚠️ **Methodological Boundary:** These represent *exploratory candidate spatial-temporal associations*, "
            "NOT verified physical fire identities or ground truth. In fast-moving agricultural burning, fires can ignite or extinguish "
            "within minutes, and differing orbital viewing geometries cause parallax and footprint distortions.",
            unsafe_allow_html=True,
        )

        # 9-cell sensitivity matrix
        sens_file = Path(__file__).parent.parent / "docs" / "sensitivity_scan_results.csv"
        if sens_file.exists():
            with st.expander("🔬 View 9-Cell Spatial & Temporal Sensitivity Matrix"):
                st.markdown(
                    "Sensitivity of cross-sensor candidate matching across 3 temporal windows "
                    "($\\Delta t \\in \\{5, 15, 30\\}\\text{ min}$) and 3 spatial radii "
                    "($\\Delta r \\in \\{5, 11, 20\\}\\text{ km}$) across 5,000 scanned detections (1,013 MODIS, 3,987 VIIRS):"
                )
                df_sens = pd.read_csv(sens_file)

                # Formatted summary view for users
                summary_df = df_sens[[
                    "time_window_min",
                    "spatial_tol_km",
                    "modis_candidate_assoc_pct",
                    "modis_ambig_of_assoc_pct",
                    "viirs_candidate_assoc_pct",
                    "viirs_ambig_of_assoc_pct",
                    "mean_observed_dt_min",
                ]].copy()
                summary_df.columns = [
                    "Time Window (min)",
                    "Spatial Radius (km)",
                    "MODIS Associated (%)",
                    "MODIS Ambiguous (%)",
                    "VIIRS Associated (%)",
                    "VIIRS Ambiguous (%)",
                    "Mean Overpass Δt (min)",
                ]
                st.dataframe(summary_df, use_container_width=True, hide_index=True)

                with st.expander("Detailed Technical Counts & Sub-metrics"):
                    st.dataframe(df_sens, use_container_width=True, hide_index=True)

                st.caption(
                    "**Key Finding on Ambiguity Escalation:** At strict thresholds (5 min, 5 km), only 6.6% of MODIS records find a candidate match. "
                    "At liberal thresholds (30 min, 20 km), 51.2% of MODIS records find a candidate match, but **91.5% of those candidate associations (475/519) are ambiguous** "
                    "(multiple VIIRS detections within the configured search neighbourhood). Empirical mean observed time offsets range from 1.5 to 13.4 minutes. "
                    "This explosive escalation in ambiguity illustrates why point-to-point 1:1 matching is scientifically inappropriate for disparate-resolution sensors."
                )
