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

    total_cells = len(disagree)
    both   = int(disagree["has_both"].sum())
    m_only = int(disagree["modis_only"].sum())
    v_only = int(disagree["viirs_only"].sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total grid-cell-days", f"{total_cells:,}")
    col2.metric("Both sensors active", f"{both:,}", f"{both/total_cells*100:.1f}%")
    col3.metric("MODIS only", f"{m_only:,}", f"{m_only/total_cells*100:.1f}%")
    col4.metric("VIIRS only", f"{v_only:,}", f"{v_only/total_cells*100:.1f}%")

    st.info(
        "⚠️ **Interpretation note:** 'MODIS only' or 'VIIRS only' does NOT necessarily mean "
        "the other sensor missed a real fire. It may mean the sensor did not have "
        "a valid observation opportunity for that cell on that day.",
        icon=None,
    )

    st.divider()

    # ── Spatial disagreement map ───────────────────────────────────────────────
    left, right = st.columns([1.3, 1])

    with left:
        st.subheader("🗺️ Spatial disagreement (Δ detection count)")
        
        c_map1, c_map2 = st.columns([1.3, 1])
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
                "Min Active Days per Cell",
                min_value=1,
                max_value=15,
                value=1,
                help="Filter out cells with very few active fire days to reduce clutter.",
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

        if "Satellite" in basemap_choice:
            map_style = "white-bg"
            map_layers = [esri_layer]
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
            labels={"mean_d_count": "Mean Δ count (VIIRS−MODIS)", "n_days": "Active days"},
            **style_kw,
        )
        fig.update_traces(
            hovertemplate=(
                "<b>0.1° Grid Cell</b><br>"
                "<b>Coordinates:</b> %{lat:.2f}°N, %{lon:.2f}°E<br>"
                "<b>Mean Δ count (VIIRS−MODIS):</b> %{customdata[0]:+.2f}<br>"
                "<b>Active Days:</b> %{customdata[1]}<extra></extra>"
            ),
            marker=dict(opacity=0.8),
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
        st.caption("🔵 Blue = VIIRS detects more | 🔴 Red = MODIS detects more | ⚪ White = balanced")

    with right:
        st.subheader("📊 Disagreement by Day / Night")
        dn_stats = disagreement_by_daynight(disagree)
        if not dn_stats.empty:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=dn_stats["daynight"], y=dn_stats["mean_d_count"],
                name="Δ count", marker_color=["#1E90FF", "#FF6B35"],
                text=dn_stats["mean_d_count"].round(2), textposition="auto",
            ))
            fig2.update_layout(
                title="Mean (VIIRS − MODIS) detection count",
                yaxis_title="Mean Δ count",
                xaxis=dict(tickvals=["D", "N"], ticktext=["☀️ Day", "🌙 Night"]),
                height=220,
                margin=dict(l=0, r=0, t=40, b=0),
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
                title="Mean disagreement by season",
            )
            fig3.update_layout(
                height=220, showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ── FRP distribution comparison ────────────────────────────────────────────
    st.subheader("🔥 Fire Radiative Power (FRP) distribution")
    combined = data["combined"]
    if not combined.empty:
        fig4 = px.histogram(
            combined[combined["frp_mw"] <= 500],
            x="frp_mw", color="sensor",
            nbins=60, barmode="overlay",
            color_discrete_map={"MODIS": "#FF6B35", "VIIRS": "#1E90FF"},
            opacity=0.7,
            labels={"frp_mw": "FRP (MW)", "sensor": "Sensor"},
            title="FRP distribution — MODIS vs VIIRS (≤ 500 MW shown)",
        )
        fig4.update_layout(
            height=320,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig4, use_container_width=True)
        st.caption(
            "VIIRS detects more weak fires (low FRP) due to its finer 375 m resolution. "
            "MODIS pixels aggregate multiple fires, producing higher per-pixel FRP values. "
            "This resolution difference is a primary source of sensor disagreement."
        )

    # ── Association status breakdown ───────────────────────────────────────────
    if not combined_assoc.empty and "match_status" in combined_assoc.columns:
        st.divider()
        st.subheader("🔗 Candidate association status")
        status_counts = combined_assoc.groupby(["sensor", "match_status"]).size().reset_index(name="count")
        fig5 = px.bar(
            status_counts, x="sensor", y="count", color="match_status",
            barmode="stack",
            color_discrete_map={
                "matched": "#4caf50",
                "unmatched": "#f44336",
                "ambiguous": "#ff9800",
            },
            labels={"count": "Records", "match_status": "Status"},
            title="Cross-sensor candidate association status",
        )
        fig5.update_layout(
            height=300,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig5, use_container_width=True)
        st.caption(
            "⚠️ **Methodological Boundary:** These are *exploratory candidate associations*, "
            "not confirmed ground-truth fire identity matches. Orbital overpass time differences vary continuously."
        )

        # 9-cell sensitivity matrix
        sens_file = Path(__file__).parent.parent / "docs" / "sensitivity_scan_results.csv"
        if sens_file.exists():
            with st.expander("🔬 View 9-Cell Spatial & Temporal Sensitivity Matrix"):
                st.markdown(
                    "Sensitivity of cross-sensor candidate matching across 3 temporal windows "
                    "($\\Delta t \\in \\{5, 15, 30\\}\\text{ min}$) and 3 spatial radii "
                    "($\\Delta r \\in \\{5, 11, 20\\}\\text{ km}$):"
                )
                df_sens = pd.read_csv(sens_file)
                st.dataframe(df_sens, use_container_width=True, hide_index=True)
                st.caption(
                    "**Key Finding on Ambiguity:** At strict thresholds (5 min, 5 km), only 6.6% of MODIS records find a candidate match. "
                    "At liberal thresholds (30 min, 20 km), 51.2% of MODIS records find a candidate match, but **91.5% of those candidate associations (475/519) are ambiguous** "
                    "(1 MODIS detection matched to multiple VIIRS clusters). Empirical mean observed time offsets range from 1.5 to 13.4 minutes."
                )
