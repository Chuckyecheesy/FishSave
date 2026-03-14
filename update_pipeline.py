"""
Update & Test Overfishing ML Pipeline
Merges forecast 2019-2025, recomputes OFR_change year-on-year, updates PriceIndex with beta,
splits train/val/test (1950-2000, 2001-2010, 2011-2025), sanity checks and saves report.
"""
import os
import pandas as pd
import numpy as np
import warnings
os.environ.setdefault('MPLCONFIGDIR', os.path.join(os.path.dirname(__file__) or '.', '.mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", message=".*fragmented.*")
beta = 0.5
future_years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
example_countries = ['Japan', 'United States of America', 'Norway']

# 1. Load data
df_main = pd.read_csv('country_features.csv')
df_forecast = pd.read_csv('forecast_2019_2025.csv')

# Normalize column names to string years
def norm_year_cols(df):
    for c in list(df.columns):
        if isinstance(c, (int, float)) and 1950 <= int(c) <= 2025:
            df = df.rename(columns={c: str(int(c))})
    return df
df_main = norm_year_cols(df_main)

# 2. Pivot forecast to wide and merge OFR for 2019-2025
df_forecast_ofr = df_forecast.pivot(index='Country', columns='Year', values='OFR_forecast').reset_index()
df_forecast_ofr = df_forecast_ofr.rename(columns={y: str(y) for y in future_years if y in df_forecast_ofr.columns})
# Merge forecast years 2019-2025 into main
merge_cols = [c for c in df_forecast_ofr.columns if c == 'Country' or str(c).isdigit()]
df_main = df_main.merge(df_forecast_ofr[merge_cols], on='Country', how='left', suffixes=('', '_f'))
# Drop any duplicate columns from merge (keep original)
dup = [c for c in df_main.columns if c.endswith('_f')]
df_main = df_main.drop(columns=dup, errors='ignore')

# Ensure we have 1950-2025 year columns
year_columns = [str(y) for y in range(1950, 2026)]
for y in year_columns:
    if y not in df_main.columns:
        df_main[y] = np.nan

# Coerce year columns to numeric, fill missing with median per column
for y in year_columns:
    df_main[y] = pd.to_numeric(df_main[y], errors='coerce')
for y in year_columns:
    med = df_main[y].median()
    df_main[y] = df_main[y].fillna(med)

# 3. Recompute OFR_change year-on-year (1951 through 2025)
for i in range(1, len(year_columns)):
    prev_y = year_columns[i - 1]
    curr_y = year_columns[i]
    if prev_y in df_main.columns and curr_y in df_main.columns:
        df_main[f'OFR_change_{curr_y}'] = df_main[curr_y] - df_main[prev_y]

# Keep a single OFR_change for compatibility (last year's change: 2025 - 2024)
if '2025' in df_main.columns and '2024' in df_main.columns:
    df_main['OFR_change'] = df_main['2025'] - df_main['2024']
else:
    df_main['OFR_change'] = df_main.get('OFR_change', np.nan)

# 4. Update PriceIndex for 2019-2025 using beta formula
# PriceIndex_t = PriceIndex_2018 * (1 + beta * (OFR_t - OFR_2018) / OFR_2018)
price_2018 = df_main['PriceIndex'].copy()
price_2018 = pd.to_numeric(price_2018, errors='coerce').replace([np.inf, -np.inf], np.nan)
price_2018 = price_2018.fillna(price_2018.median())
ofr_2018 = df_main['OFR'].copy()
ofr_2018 = pd.to_numeric(ofr_2018, errors='coerce').replace([np.inf, -np.inf], np.nan)
ofr_2018 = ofr_2018.fillna(ofr_2018.median()).replace(0, np.nan)

for year in future_years:
    y = str(year)
    if y not in df_main.columns:
        continue
    ofr_t = pd.to_numeric(df_main[y], errors='coerce')
    # avoid div by zero
    ratio = (ofr_t - ofr_2018) / ofr_2018
    ratio = ratio.fillna(0)
    df_main[f'PriceIndex_{y}'] = price_2018 * (1 + beta * ratio)
# Keep main PriceIndex as 2025 value for downstream
if 'PriceIndex_2025' in df_main.columns:
    df_main['PriceIndex'] = df_main['PriceIndex_2025']

# Fill OFR/PriceIndex missing
df_main['OFR'] = pd.to_numeric(df_main['OFR'], errors='coerce').fillna(df_main['OFR'].median())
df_main['PriceIndex'] = pd.to_numeric(df_main['PriceIndex'], errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(df_main['PriceIndex'].median())

# 5. Split train / validation / test
train_years = [str(y) for y in range(1950, 2001)]
val_years = [str(y) for y in range(2001, 2011)]
test_years = [str(y) for y in range(2011, 2026)]

def select_cols(df, years):
    cand = ['Country'] + years + ['OFR', 'OFR_change', 'PriceIndex']
    return df[[c for c in cand if c in df.columns]]

train_df = select_cols(df_main, train_years)
val_df = select_cols(df_main, val_years)
test_df = select_cols(df_main, test_years)

# 6. Save updated CSVs
train_df.to_csv('train_features_updated.csv', index=False)
val_df.to_csv('val_features_updated.csv', index=False)
test_df.to_csv('test_features_updated.csv', index=False)
print("Saved: train_features_updated.csv, val_features_updated.csv, test_features_updated.csv")

# 7. Sanity check and trend plots
report_rows = []
for df, name in zip([train_df, val_df, test_df], ['Train', 'Validation', 'Test']):
    print(f"\n{name} set shape: {df.shape}")
    print("Columns:", df.columns.tolist())
    print(df.head(3))
    missing = df.isna().sum().sum()
    report_rows.append({'set': name, 'rows': df.shape[0], 'cols': df.shape[1], 'missing': missing})

    # Plot OFR (year columns) and PriceIndex for example countries
    plot_years = [c for c in df.columns if c.isdigit()]
    plot_years = sorted(plot_years, key=int)
    if not plot_years:
        continue
    for country in example_countries:
        if country not in df['Country'].values:
            continue
        subset = df[df['Country'] == country][plot_years]
        if subset.empty:
            continue
        fig, ax = plt.subplots(figsize=(10, 4))
        vals = subset.values.flatten()
        ax.plot([int(y) for y in plot_years], vals, 'o-', label='OFR (catch) trend', markersize=3)
        if 'PriceIndex' in df.columns:
            pi = df.loc[df['Country'] == country, 'PriceIndex'].values
            if len(pi):
                ax.axhline(pi[0], color='C1', linestyle='--', label=f'PriceIndex ({pi[0]:.0f})')
        ax.set_xlabel('Year')
        ax.set_ylabel('Value')
        ax.set_title(f'{country} — {name}')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        safe_name = name.replace(' ', '_').lower()
        safe_country = country.replace(' ', '_').replace('/', '_')[:25]
        plt.savefig(f'pipeline_{safe_name}_{safe_country}.png', dpi=100)
        plt.close()
        print(f"  Saved: pipeline_{safe_name}_{safe_country}.png")

# 8. Save report CSV
report_df = pd.DataFrame(report_rows)
report_df.to_csv('update_pipeline_report.csv', index=False)
print("\nPipeline update report saved as 'update_pipeline_report.csv'")
print(report_df.to_string(index=False))
