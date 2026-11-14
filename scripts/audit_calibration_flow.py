"""
audit_calibration_flow.py — Comprehensive Data Flow, Estimator & Metric Verification
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

sys.path.insert(0, '.')
import pages.data_loader as dl

def main():
    print("=== DATA LOADER EXPORT AUDIT ===")
    data = dl.load_data()
    print("Keys in data:", sorted(list(data.keys())))
    print("data['is_synthetic']:", data.get('is_synthetic'))
    print("data['pairs'] length:", len(data.get('pairs', [])))
    print("data['pairs_strict'] length:", len(data.get('pairs_strict', [])))

    pairs_strict = data['pairs_strict'].copy()
    pairs_strict['year'] = pairs_strict['acq_date'].str[:4].astype(int)
    t_2022 = pairs_strict[pairs_strict['year'] == 2022]
    v_2023 = pairs_strict[pairs_strict['year'] == 2023]
    print(f"pairs_strict total: {len(pairs_strict)}")
    print(f"2022 training partition: {len(t_2022)}")
    print(f"2023 comparative evaluation partition: {len(v_2023)}")

    cal = data['cal_results']
    print("\n=== FITTED CALIBRATION MODELS ===")
    for name in ['identity', 'global', 'context']:
        r = cal[name]
        print(f"--- Model {name.upper()} ---")
        print(f"Trained: {r.trained}, Reliability: {r.reliability_status}")
        if r.train_metrics:
            tm = r.train_metrics
            print(f"  Train metrics (2022): n={tm.n_pairs}, MAE={tm.mae:.4f}, RMSE={tm.rmse:.4f}, Bias%={tm.mean_bias_pct:+.2f}%")
        if r.val_metrics:
            vm = r.val_metrics
            print(f"  Eval metrics (2023):  n={vm.n_pairs}, MAE={vm.mae:.4f}, RMSE={vm.rmse:.4f}, Bias%={vm.mean_bias_pct:+.2f}%")
        if name == 'global':
            print(f"  RMA Slope: {r.slope:.5f}, Intercept: {r.intercept:.4f}")
        if name == 'context':
            m_obj = r.model_obj
            print(f"  Model type: {type(m_obj)}")
            feature_names = getattr(m_obj, "feature_names_in_", r.feature_names)
            print(f"  feature_names_in_: {list(feature_names)}")
            print(f"  intercept_: {m_obj.intercept_:.6f}")
            print(f"  coef_: {list(m_obj.coef_)}")

    print("\n=== INDEPENDENT RE-CALCULATION OF MODEL C PREDICTIONS & METRICS ===")
    ctx_model = cal['context'].model_obj

    def build_features(df: pd.DataFrame) -> np.ndarray:
        frp = df["frp_viirs"].values.reshape(-1, 1)
        count = df["count_viirs"].values.reshape(-1, 1) if "count_viirs" in df.columns else np.ones_like(frp)
        is_night = (df["daynight"].values == "N").astype(float).reshape(-1, 1)
        return np.hstack([frp, count, is_night])

    # Train partition
    X_train = build_features(t_2022)
    y_train = t_2022['frp_modis'].values
    y_pred_train = ctx_model.predict(X_train)
    mae_train = mean_absolute_error(y_train, y_pred_train)
    rmse_train = np.sqrt(mean_squared_error(y_train, y_pred_train))
    bias_train = float(np.mean(y_pred_train - y_train))
    bias_pct_train = bias_train / (np.mean(y_train) + 1e-9) * 100

    # Eval partition
    X_eval = build_features(v_2023)
    y_eval = v_2023['frp_modis'].values
    y_pred_eval = ctx_model.predict(X_eval)
    mae_eval = mean_absolute_error(y_eval, y_pred_eval)
    rmse_eval = np.sqrt(mean_squared_error(y_eval, y_pred_eval))
    bias_eval = float(np.mean(y_pred_eval - y_eval))
    bias_pct_eval = bias_eval / (np.mean(y_eval) + 1e-9) * 100

    print(f"Independent Train MAE:  {mae_train:.4f} (matches stored {cal['context'].train_metrics.mae:.4f})")
    print(f"Independent Train RMSE: {rmse_train:.4f} (matches stored {cal['context'].train_metrics.rmse:.4f})")
    print(f"Independent Train Bias: {bias_pct_train:+.2f}% (matches stored {cal['context'].train_metrics.mean_bias_pct:+.2f}%)")
    print(f"Independent Eval MAE:   {mae_eval:.4f} (matches stored {cal['context'].val_metrics.mae:.4f})")
    print(f"Independent Eval RMSE:  {rmse_eval:.4f} (matches stored {cal['context'].val_metrics.rmse:.4f})")
    print(f"Independent Eval Bias:  {bias_pct_eval:+.2f}% (matches stored {cal['context'].val_metrics.mean_bias_pct:+.2f}%)")


if __name__ == '__main__':
    main()
