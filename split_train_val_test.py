"""
Time-Series Train/Validation/Test Split
Splits country_features.csv into train (1950-2000), val (2001-2010), test (2011-2018).
"""
import pandas as pd
import numpy as np

# Load CSV
df = pd.read_csv('country_features.csv')

# Ensure year columns are strings (CSV headers may be read as int or str)
all_cols = list(df.columns)
year_cols_raw = [c for c in all_cols if isinstance(c, (int, float)) or (isinstance(c, str) and c.isdigit())]
year_columns = [str(int(y)) for y in range(1950, 2019)]
# Rename year columns to string if needed
rename = {c: str(int(c)) for c in year_cols_raw if str(int(c)) in year_columns}
if rename:
    df = df.rename(columns=rename)

# Handle missing values: replace inf in numeric columns, optional fill/drop for OFR, OFR_change, PriceIndex
feature_cols = ['OFR', 'OFR_change', 'PriceIndex']
for col in feature_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df[col] = df[col].replace([np.inf, -np.inf], np.nan)
# Drop rows where all three features are missing (optional: or fill with median)
for col in feature_cols:
    if col in df.columns and df[col].isna().any():
        df[col] = df[col].fillna(df[col].median())

# Define year column lists (as strings)
train_years = [str(y) for y in range(1950, 2001)]
val_years = [str(y) for y in range(2001, 2011)]
test_years = [str(y) for y in range(2011, 2019)]

# Select only columns that exist
def select_cols(df, years, extra):
    cand = ['Country'] + years + extra
    return df[[c for c in cand if c in df.columns]]

train_df = select_cols(df, train_years, ['OFR', 'OFR_change', 'PriceIndex'])
val_df   = select_cols(df, val_years,   ['OFR', 'OFR_change', 'PriceIndex'])
test_df  = select_cols(df, test_years,  ['OFR', 'OFR_change', 'PriceIndex'])

# Save CSVs
train_df.to_csv('train_features.csv', index=False)
val_df.to_csv('val_features.csv', index=False)
test_df.to_csv('test_features.csv', index=False)

# Verification
print("Train set:", train_df.shape)
print(train_df.head(3))
print("\nValidation set:", val_df.shape)
print(val_df.head(3))
print("\nTest set:", test_df.shape)
print(test_df.head(3))
