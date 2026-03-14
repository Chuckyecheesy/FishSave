"""
Sanity Check Agent for Overfishing ML Pipeline
Loads train/val/test CSVs, checks shapes and missing values, fills OFR/OFR_change/PriceIndex,
plots catch trends for sample countries, saves a summary report.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

csv_files = ['train_features.csv', 'val_features.csv', 'test_features.csv']
# Use exact country names from the CSVs
example_countries = ['Japan', 'United States of America', 'Norway', 'China', 'Indonesia']
feature_cols = ['OFR', 'OFR_change', 'PriceIndex']

report_rows = []

for file in csv_files:
    if not os.path.exists(file):
        print(f"Skip (not found): {file}")
        continue

    print(f"\n{'='*60}\nSanity Check: {file}\n{'='*60}")
    df = pd.read_csv(file)

    # Detect year columns (numeric strings in 1950-2018 range)
    year_columns = [c for c in df.columns if isinstance(c, str) and c.isdigit() and 1950 <= int(c) <= 2018]
    if not year_columns:
        year_columns = [c for c in df.columns if str(c).isdigit()]
    year_columns = sorted(year_columns, key=int)

    # Ensure year columns are numeric
    for col in year_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Count missing BEFORE fill for report
    missing_before = df[feature_cols].isna().sum().to_dict() if all(c in df.columns for c in feature_cols) else {}
    total_missing_before = df.isna().sum().sum()

    # Fill missing and inf in OFR, OFR_change, PriceIndex
    for col in feature_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)
            med = df[col].median()
            df[col] = df[col].fillna(med)

    # Print basic info
    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())
    print("Missing values per column:")
    missing_per_col = df.isna().sum()
    print(missing_per_col[missing_per_col > 0] if (missing_per_col > 0).any() else "0 (all filled)")
    print("First 3 rows:")
    print(df.head(3))

    # Report row (missing counts before fill)
    row = {'file': file, 'rows': df.shape[0], 'cols': df.shape[1],
           'total_missing_before_fill': total_missing_before,
           'year_columns_count': len(year_columns)}
    for col in feature_cols:
        row[f'missing_{col}'] = missing_before.get(col, 0)
    report_rows.append(row)

    # Plot catch (year columns) trends for example countries
    if year_columns:
        fig, ax = plt.subplots(figsize=(10, 4))
        years = [int(y) for y in year_columns]
        for country in example_countries:
            mask = df['Country'] == country
            if mask.any():
                vals = df.loc[mask, year_columns].values.flatten()
                ax.plot(years, vals, label=country, marker='o', markersize=2)
        ax.set_xlabel('Year')
        ax.set_ylabel('Catch (OFR proxy)')
        ax.set_title(f'Catch by year — {file}')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plot_path = file.replace('.csv', '_trends.png')
        plt.savefig(plot_path, dpi=100)
        plt.close()
        print(f"Saved plot: {plot_path}")

# Save report CSV
report_df = pd.DataFrame(report_rows)
report_df.to_csv('sanity_check_report.csv', index=False)
print("\n" + "="*60)
print("Sanity check report saved as 'sanity_check_report.csv'")
print(report_df.to_string(index=False))
