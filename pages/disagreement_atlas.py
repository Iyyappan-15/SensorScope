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
        map_data = disagree.groupby(["grid_lat", "grid_lon"]).agg(
            mean_d_count=("d_count", "mean"),
            n_days=("d_count", "count"),
        ).reset_index()

        fig = px.scatter_mapbox(
            map_data,
            lat="grid_lat", lon="grid_lon",
            color="mean_d_count",
            size="n_days",
            color_continuous_scale="RdBu",
            color_continuous_midpoint=0,
            range_color=[-5, 5],
            mapbox_style="carto-darkmatter",
            zoom=6, opacity=0.8,
            hover_data={"mean_d_count": ":.2f", "n_days": True},
            labels={"mean_d_count": "Mean Δ count (VIIRS−MODIS)", "n_days": "Active days"},
        )
        fig.update_layout(height=430, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Blue = VIIRS sees more | Red = MODIS sees more | White = agreement")

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
                height=200,
                margin=dict(l=0, r=0, t=40, b=0),
                plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#fafafa",
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
                height=200, showlegend=False,
                margin=dict(l=0, r=0, t=40, b=0),
                plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#fafafa",
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
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#fafafa",
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
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#fafafa",
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
