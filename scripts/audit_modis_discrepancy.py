"""
audit_modis_discrepancy.py — Authoritative audit of the 14-record MODIS difference
Exploratory Archive (8,472 records) vs Strict November 1–10 Cohort (8,458 records).
"""
import sys
from pathlib import Path
import pandas as pd

RAW_MODIS = Path("data/raw/modis")

def main():
    all_files = sorted(list(RAW_MODIS.glob("*.csv")))
    print(f"Total MODIS CSV files in {RAW_MODIS}: {len(all_files)}")

    # Classify files
    strict_files = []
    exploratory_files = []

    for f in all_files:
        # Strict files are Nov 1-10 in 2022 and 2023
        name = f.stem
        # e.g., MODIS_SP_2022-11-01_d10, MODIS_SP_2022-11-01_d1, etc.
        # Check date
        parts = name.split("_")
        date_str = parts[2] if len(parts) >= 3 else ""
        if date_str in ["2022-05-31", "2022-11-30", "2023-05-31", "2023-11-30"]:
            exploratory_files.append(f)
        else:
            strict_files.append(f)

    print(f"Strict Nov 1-10 files: {len(strict_files)}")
    print(f"Exploratory single-day probe files: {len(exploratory_files)}")

    strict_dfs = []
    for f in strict_files:
        df = pd.read_csv(f)
        df["source_file"] = f.name
        strict_dfs.append(df)
    strict_df = pd.concat(strict_dfs, ignore_index=True) if strict_dfs else pd.DataFrame()

    probe_dfs = []
    for f in exploratory_files:
        df = pd.read_csv(f)
        df["source_file"] = f.name
        probe_dfs.append(df)
    probe_df = pd.concat(probe_dfs, ignore_index=True) if probe_dfs else pd.DataFrame()

    total_df = pd.concat([strict_df, probe_df], ignore_index=True)

    print("\n=== TOTAL MODIS ARCHIVE ===")
    print(f"Total records: {len(total_df)}")
    print(f"By satellite:\n{total_df['satellite'].value_counts()}")

    print("\n=== STRICT NOV 1-10 FILES ===")
    print(f"Strict records: {len(strict_df)}")
    print(f"By satellite:\n{strict_df['satellite'].value_counts()}")

    print("\n=== THE 14 EXCLUDED EXPLORATORY RECORDS ===")
    print(f"Total probe records: {len(probe_df)}")
    print(f"By satellite:\n{probe_df['satellite'].value_counts()}")
    print("\nFile-by-file breakdown of excluded probe files:")
    for f in exploratory_files:
        sub = probe_df[probe_df["source_file"] == f.name]
        sat_counts = dict(sub["satellite"].value_counts())
        print(f"  {f.name}: {len(sub)} rows, satellites: {sat_counts}")

    print("\nListing all 14 records:")
    cols = ["source_file", "acq_date", "acq_time", "latitude", "longitude", "satellite", "frp", "daynight"]
    print(probe_df[cols].to_string(index=False))

if __name__ == "__main__":
    main()
