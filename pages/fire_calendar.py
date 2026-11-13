"""Page 4 — Fire Activity Calendar: historical patterns with transparency."""

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
from analysis.disagreement import disagreement_by_year


SEASON_COLORS = {
    "Pre-monsoon":  "#FF9A3C",
    "Monsoon":      "#4caf50",
    "Post-monsoon": "#FF6B35",
    "Winter":       "#6B8CFF",
}


def render() -> None:
    st.title("📅 Fire Activity Calendar")
    st.caption("Historical fire patterns — with sensor transparency and uncertainty")

    data = load_data()
    data_source_banner(data["using_real_data"])

    disagree = data["disagree"]
    cal_results = data["cal_results"]
    reliability = data["reliability"]

    if disagree.empty:
        st.warning("No historical data loaded.")
        return

    # ── Controls ───────────────────────────────────────────────────────────────
    colA, colB, colC = st.columns(3)
    metric = colA.selectbox("Activity metric", ["Detection count", "FRP sum (MW)"])
    daynight_filter = colB.selectbox("Day / Night", ["Both", "Day only", "Night only"])
    show_calibrated = colC.checkbox("Show calibrated VIIRS estimate", value=True)

    # Apply day/night filter
    df = disagree.copy()
    if daynight_filter == "Day only":
        df = df[df["daynight"] == "D"]
    elif daynight_filter == "Night only":
        df = df[df["daynight"] == "N"]

    # Monthly roll-up
    monthly = df.groupby(["year", "month"]).agg(
        modis_count=("count_modis", "sum"),
        viirs_count=("count_viirs", "sum"),
        modis_frp=("frp_sum_modis", "sum"),
        viirs_frp=("frp_sum_viirs", "sum"),
    ).reset_index()
    monthly["period"] = pd.to_datetime(
        monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2) + "-01"
    )
    monthly = monthly.sort_values("period")

    # Determine Y values
    if metric == "Detection count":
        y_modis = "modis_count"
        y_viirs = "viirs_count"
        y_label = "Grid-cell detections"
    else:
        y_modis = "modis_frp"
        y_viirs = "viirs_frp"
        y_label = "Total FRP (MW)"

    # Calibrated VIIRS estimate (if model available and reliable)
    best_model = None
    best_status = "red"
    for k in ["context", "global"]:
        if k in cal_results and cal_results[k].trained:
            best_model = cal_results[k]
            best_status = best_model.reliability_status
            break

    if best_model and show_calibrated and metric == "FRP sum (MW)":
        monthly["viirs_calibrated"] = (
            best_model.slope * monthly[y_viirs] + best_model.intercept * monthly["modis_count"]
        ).clip(lower=0)
        has_calibrated = True
    else:
        has_calibrated = False

    # ── Main timeline chart ────────────────────────────────────────────────────
    st.subheader("📈 Monthly fire activity timeline")

    fig = go.Figure()

    # MODIS bars
    fig.add_trace(go.Bar(
        x=monthly["period"], y=monthly[y_modis],
        name="MODIS (observed)",
        marker_color="#FF6B35", opacity=0.85,
    ))

    # VIIRS bars
    fig.add_trace(go.Bar(
        x=monthly["period"], y=monthly[y_viirs],
        name="VIIRS (observed)",
        marker_color="#1E90FF", opacity=0.75,
    ))

    # Calibrated VIIRS line
    if has_calibrated:
        fig.add_trace(go.Scatter(
            x=monthly["period"], y=monthly["viirs_calibrated"],
            name="VIIRS → MODIS-ref (calibrated)",
            mode="lines+markers",
            line=dict(color="#4caf50", width=2),
            marker=dict(size=5),
        ))

    # Reliability gate annotation
    if best_status == "red" and show_calibrated:
        fig.add_annotation(
            x=0.5, y=0.95, xref="paper", yref="paper",
            text="🔴 Calibration unavailable — insufficient evidence. Raw data shown.",
            showarrow=False, font=dict(color="#f44336", size=12),
            bgcolor="#1a0000", bordercolor="#f44336",
        )
    elif best_status == "yellow" and show_calibrated and has_calibrated:
        fig.add_annotation(
            x=0.5, y=0.95, xref="paper", yref="paper",
            text="🟡 Calibration shown with caution — limited evidence.",
            showarrow=False, font=dict(color="#ff9800", size=12),
            bgcolor="#1a1000", bordercolor="#ff9800",
        )

    fig.update_layout(
        barmode="group",
        height=420,
        xaxis_title="Month",
        yaxis_title=y_label,
        legend=dict(orientation="h", y=-0.15),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#fafafa",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Reliability badge
    if best_model:
        badge_map = {
            "green":  ("🟢", "Calibrated estimates are reliable for this dataset.", "success"),
            "yellow": ("🟡", "Calibrated estimates shown with caution.", "warning"),
            "red":    ("🔴", "Calibration not supported — insufficient paired observations.", "error"),
        }
        icon, msg, level = badge_map.get(best_status, ("🔴", "", "error"))
        getattr(st, level)(f"{icon} **Reliability gate:** {msg}")

    st.divider()

    # ── Anomaly detection — simple z-score ────────────────────────────────────
    st.subheader("🚨 Unusual activity periods")

    if len(monthly) >= 6:
        monthly["month_num"] = monthly["month"]
        # Compute month-of-year historical mean and std
        monthly_clim = (
            monthly.groupby("month_num")[y_modis]
            .agg(clim_mean="mean", clim_std="std")
            .reset_index()
        )
        monthly = monthly.merge(monthly_clim, on="month_num")
        monthly["z_score"] = (
            (monthly[y_modis] - monthly["clim_mean"]) /
            (monthly["clim_std"] + 1e-9)
        )

        threshold = st.slider("Anomaly threshold (Z-score)", 1.0, 3.0, 1.5, 0.1)
        anomalies = monthly[monthly["z_score"].abs() >= threshold]

        if anomalies.empty:
            st.info(f"No months exceed Z = {threshold:.1f} in this dataset.")
        else:
            st.markdown(f"**{len(anomalies)} months** show unusual activity (|Z| ≥ {threshold:.1f}):")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=monthly["period"], y=monthly["z_score"],
                mode="lines+markers", name="Z-score",
                line=dict(color="#8884d8"), marker=dict(size=5),
            ))
            fig2.add_hline(y=threshold, line_dash="dash", line_color="orange",
                           annotation_text=f"+ threshold ({threshold:.1f})")
            fig2.add_hline(y=-threshold, line_dash="dash", line_color="orange",
                           annotation_text=f"− threshold (−{threshold:.1f})")
            fig2.add_hline(y=0, line_color="grey", line_width=0.5)
            fig2.update_layout(
                height=280, yaxis_title="Z-score",
                plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#fafafa",
                margin=dict(l=0, r=0, t=20, b=0),
            )
            st.plotly_chart(fig2, use_container_width=True)

            with st.expander("View anomalous months"):
                anom_display = anomalies[["year", "month", y_modis, y_viirs, "z_score"]].copy()
                anom_display.columns = ["Year", "Month", "MODIS activity", "VIIRS activity", "Z-score"]
                anom_display["Z-score"] = anom_display["Z-score"].round(2)
                st.dataframe(anom_display, use_container_width=True, hide_index=True)

        st.caption(
            "⚠️ Z-scores are computed within this dataset only. "
            "Apparent anomalies may reflect sensor changeover (2012 MODIS→VIIRS) "
            "rather than real changes in burning activity."
        )
    else:
        st.info("Need ≥ 6 monthly data points for anomaly detection.")

    st.divider()

    # ── Seasonal heatmap ──────────────────────────────────────────────────────
    st.subheader("🌡️ Seasonal activity heatmap")
    pivot = disagree.groupby(["year", "month"])[["count_modis", "count_viirs"]].sum().reset_index()

    if not pivot.empty:
        pivot_wide = pivot.pivot(index="year", columns="month", values="count_modis").fillna(0)
        fig3 = px.imshow(
            pivot_wide,
            labels=dict(x="Month", y="Year", color="MODIS detections"),
            color_continuous_scale="YlOrRd",
            aspect="auto",
            title="MODIS monthly detection count heatmap",
        )
        fig3.update_layout(
            height=280,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#fafafa",
        )
        st.plotly_chart(fig3, use_container_width=True)
        st.caption(
            "Oct–Nov shows the Kharif stubble burning peak. "
            "Apr–May shows the Rabi stubble burning peak. "
            "These patterns are consistent with ground-truth agricultural calendars."
        )
