"""Page 3 — Calibration Lab: model comparison + reliability gate."""

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


BADGE_HTML = {
    "green":  '<span class="badge-green">🟢 Reliable</span>',
    "yellow": '<span class="badge-yellow">🟡 Use with caution</span>',
    "red":    '<span class="badge-red">🔴 Calibration unavailable</span>',
}


def _metrics_row(result, split: str):
    metrics_obj = getattr(result, f"{split}_metrics", None)
    if metrics_obj is None:
        return None
    return {
        "Model": result.model_name,
        "Split": split.capitalize(),
        "N pairs": metrics_obj.n_pairs,
        "MAE (MW)": round(metrics_obj.mae, 2) if not np.isnan(metrics_obj.mae) else "—",
        "RMSE (MW)": round(metrics_obj.rmse, 2) if not np.isnan(metrics_obj.rmse) else "—",
        "Mean bias (MW)": round(metrics_obj.mean_bias, 2) if not np.isnan(metrics_obj.mean_bias) else "—",
        "Bias %": f"{metrics_obj.mean_bias_pct:+.1f}%" if not np.isnan(metrics_obj.mean_bias_pct) else "—",
        "Spearman r": round(metrics_obj.spearman_r, 3) if not np.isnan(metrics_obj.spearman_r) else "—",
    }


def render() -> None:
    st.title("🔬 Calibration Lab")
    st.caption("Comparing calibration models — with an evidence-based reliability gate")

    data = load_data()
    data_source_banner(data["using_real_data"])

    pairs = data.get("pairs_strict", data["pairs"])
    cal_results = data["cal_results"]

    if pairs.empty:
        st.warning(
            "No paired MODIS+VIIRS observations found for this region and period. "
            "Calibration requires grid cells where BOTH sensors reported activity."
        )
        return

    st.success(
        f"**{len(pairs):,}** strictly selected co-active grid-cell observations evaluated for calibration "
        f"(1,312 Training pairs [Nov 1–10, 2022] · 1,242 Held-out Evaluation pairs [Nov 1–10, 2023])."
    )
    st.caption(
        "ℹ️ **Population Identification:** Displayed calibration models are evaluated strictly on the 2,554 co-active cell-day "
        "observations from the primary November Kharif burning peak. The broader exploratory archive contains 2,560 co-active observations "
        "(including exploratory API test probe dates)."
    )

    # ── Scatter: raw relationship ──────────────────────────────────────────────
    st.subheader("🔍 Raw MODIS vs VIIRS FRP relationship")
    col_sc, col_inf = st.columns([1.5, 1])

    with col_sc:
        sample_pairs = pairs.sample(min(2000, len(pairs)), random_state=1)
        fig = px.scatter(
            sample_pairs, x="frp_viirs", y="frp_modis",
            color="daynight",
            color_discrete_map={"D": "#FF9A3C", "N": "#6B8CFF"},
            opacity=0.5, size_max=4,
            labels={"frp_viirs": "VIIRS FRP (MW)", "frp_modis": "MODIS FRP (MW)",
                    "daynight": "Day/Night"},
            title="Paired observations — VIIRS FRP vs MODIS FRP",
        )
        # Add 1:1 reference line
        max_frp = min(float(sample_pairs[["frp_viirs", "frp_modis"]].max().max()), 500)
        fig.add_trace(go.Scatter(
            x=[0, max_frp], y=[0, max_frp],
            mode="lines", line=dict(dash="dash", color="grey", width=1),
            name="1:1 line",
        ))
        fig.update_layout(
            height=380,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_inf:
        st.markdown("**What this scatter shows:**")
        st.markdown("""
- Points above the 1:1 line → MODIS reports higher FRP than VIIRS
- Points below → VIIRS reports higher FRP
- Day (orange) vs Night (blue) may show different offsets
- The spread indicates measurement uncertainty

A calibration model learns the systematic relationship between these measurements.

**Key scientific note (Li et al. 2018):**
> The MODIS–VIIRS FRP relationship varies with spatial scale, ecosystem and
> viewing angle. A single global correction may not be appropriate for all conditions.
        """)

    st.divider()

    # ── Model comparison table ─────────────────────────────────────────────────
    st.subheader("📊 Model performance comparison")

    if not cal_results:
        st.info("No calibration models available.")
        return

    rows = []
    for key in ["identity", "global", "context"]:
        if key not in cal_results:
            continue
        r = cal_results[key]
        for split in ["train", "val", "test"]:
            m = _metrics_row(r, split)
            if m:
                rows.append(m)

    if rows:
        df_metrics = pd.DataFrame(rows)
        # Highlight val rows
        st.dataframe(
            df_metrics,
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "• **Train:** November 2022 model fitting ($n=1,312$ co-active pairs).<br>"
            "• **Val:** November 2023 held-out comparative evaluation ($n=1,242$ co-active pairs).<br>"
            "• *Note:* No independent final test period is available in this pilot; November 2023 served as the comparative evaluation period.",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Reliability gate — the key feature ────────────────────────────────────
    st.subheader("🔒 Calibration Reliability Gate")
    st.markdown(
        "The reliability gate determines whether a calibrated estimate is "
        "**justified** for each model, based on evidence — not just whether a model ran."
    )

    for key, label in [
        ("context", "Model C — Context-aware"),
        ("global", "Model B — Global RMA"),
        ("identity", "Model A — Identity (no correction)"),
    ]:
        if key not in cal_results:
            continue
        r = cal_results[key]
        status = r.reliability_status
        badge = BADGE_HTML.get(status, status)

        with st.expander(f"{label}  &nbsp; {badge}", expanded=(key == "context")):
            st.markdown(f"**Status:** {badge}", unsafe_allow_html=True)
            st.markdown(f"**Reason:** {r.reliability_reason}")
            st.markdown(f"**Trained:** {'Yes' if r.trained else 'No'}")

            if r.trained:
                if hasattr(r, "model_obj") and r.model_obj is not None:
                    coefs = r.model_obj.coef_
                    inter = r.model_obj.intercept_
                    st.markdown(
                        f"**Equation:** `FRP_MODIS_ref = {inter:.2f} + {coefs[0]:.3f} × FRP_VIIRS + "
                        f"{coefs[1]:.3f} × Count_VIIRS + {coefs[2]:.3f} × Is_Night`"
                    )
                elif key == "identity":
                    st.markdown("**Equation:** `FRP_MODIS_ref = FRP_VIIRS` (Identity / Baseline)")
                else:
                    st.markdown(f"**Equation:** `FRP_MODIS_ref = {r.intercept:.2f} + {r.slope:.3f} × FRP_VIIRS`")

            if status == "green":
                st.success("✅ Calibrated estimates shown in the Fire Activity Calendar.")
            elif status == "yellow":
                st.warning("⚠️ Calibrated estimates shown with caution warning.")
            else:
                st.error(
                    "🚫 Calibrated estimates NOT shown. "
                    "Raw sensor measurements are displayed instead."
                )

    st.divider()

    # ── Calibration effect visualization ──────────────────────────────────────
    st.subheader("📈 Before / after calibration")
    best_key = None
    for k in ["context", "global"]:
        if k in cal_results and cal_results[k].trained:
            best_key = k
            break

    if best_key:
        r = cal_results[best_key]
        sample = pairs.sample(min(1500, len(pairs)), random_state=2)
        if hasattr(r, "model_obj") and r.model_obj is not None:
            frp = sample["frp_viirs"].values.reshape(-1, 1)
            count = sample["count_viirs"].values.reshape(-1, 1) if "count_viirs" in sample.columns else np.ones_like(frp)
            is_night = (sample["daynight"].values == "N").astype(float).reshape(-1, 1)
            X_sample = np.hstack([frp, count, is_night])
            predicted = np.maximum(0.0, r.model_obj.predict(X_sample))
        else:
            predicted = np.maximum(0.0, r.slope * sample["frp_viirs"].values + r.intercept)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=sample["frp_modis"], y=sample["frp_viirs"],
            mode="markers", name="Raw VIIRS",
            marker=dict(color="#1E90FF", opacity=0.4, size=4),
        ))
        fig2.add_trace(go.Scatter(
            x=sample["frp_modis"], y=predicted,
            mode="markers", name="Calibrated VIIRS",
            marker=dict(color="#4caf50", opacity=0.5, size=4, symbol="diamond"),
        ))
        max_v = min(float(sample[["frp_modis", "frp_viirs"]].max().max()), 500)
        fig2.add_trace(go.Scatter(
            x=[0, max_v], y=[0, max_v],
            mode="lines", name="1:1",
            line=dict(dash="dash", color="grey", width=1),
        ))
        fig2.update_layout(
            title=f"Effect of {r.model_name}",
            xaxis_title="MODIS FRP (MW) — reference",
            yaxis_title="VIIRS FRP (MW) — raw vs calibrated",
            height=380,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "Green diamonds (calibrated) should lie closer to the 1:1 line than blue circles (raw). "
            "If they don't, the model is not improving comparability and should not be used."
        )
    else:
        st.info("No trained calibration model available to visualize.")
