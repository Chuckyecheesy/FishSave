"""
Forecast missing OFR % and PriceIndex for 2019–2025 based on past trends.
Updates country_features by adding year columns 2019–2025 and saving
country_features_extended.csv (keeps original country_features.csv intact).
"""
import pandas as pd
import numpy as np

# Load existing features (1950–2018)
df = pd.read_csv('country_features.csv')

# Ensure year columns are strings for consistent access
year_cols = [c for c in df.columns if str(c).isdigit() and 1950 <= int(c) <= 2018]
year_cols = sorted(year_cols, key=lambda x: int(x))
y_1950 = '1950'
y_2018 = '2018'
if y_1950 not in df.columns:
    y_1950 = year_cols[0]
if y_2018 not in df.columns:
    y_2018 = year_cols[-1]

future_years = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
beta = 0.5  # PriceIndex sensitivity

# Coerce OFR/PriceIndex to numeric, replace inf
df['OFR'] = pd.to_numeric(df['OFR'], errors='coerce')
df['PriceIndex'] = pd.to_numeric(df['PriceIndex'], errors='coerce')
df['PriceIndex'] = df['PriceIndex'].replace([np.inf, -np.inf], np.nan)
df['PriceIndex'] = df['PriceIndex'].fillna(df['PriceIndex'].median())

forecast_rows = []

for idx, row in df.iterrows():
    last_ofr = float(row['OFR'])
    last_price = float(row['PriceIndex'])
    # Slope from catch trend 1950 -> 2018 (so OFR extrapolation is non-zero)
    catch_1950 = pd.to_numeric(row[y_1950], errors='coerce')
    catch_2018 = pd.to_numeric(row[y_2018], errors='coerce')
    if pd.isna(catch_1950):
        catch_1950 = 0.0
    if pd.isna(catch_2018):
        catch_2018 = last_ofr
    span = 2018 - 1950
    slope = (catch_2018 - catch_1950) / span if span else 0.0
    # Optional: scale slope to OFR magnitude so we extrapolate OFR in same direction as catch
    if catch_2018 != 0 and last_ofr != 0:
        ofr_slope = last_ofr * (slope / catch_2018)
    else:
        ofr_slope = slope

    for t in future_years:
        ofr_forecast = last_ofr + ofr_slope * (t - 2018)
        ofr_forecast = max(0.0, ofr_forecast)  # avoid negative
        if last_ofr != 0:
            price_forecast = last_price * (1 + beta * (ofr_forecast - last_ofr) / last_ofr)
        else:
            price_forecast = last_price
        price_forecast = max(0.0, price_forecast)
        forecast_rows.append({
            'Country': row['Country'],
            'Year': t,
            'OFR_forecast': ofr_forecast,
            'PriceIndex_forecast': price_forecast,
        })

forecast_df = pd.DataFrame(forecast_rows)
forecast_df.to_csv('forecast_2019_2025.csv', index=False)
print("Forecast for 2019–2025 saved to forecast_2019_2025.csv")

# --- Update country_features: add 2019–2025 and save extended CSV ---
# Extrapolate catch for 2019–2025 using same slope (catch_2018 + slope*(t-2018))
extended = df.copy()
for t in future_years:
    col = str(t)
    extended[col] = np.nan
    for idx, row in extended.iterrows():
        c2018 = pd.to_numeric(row[y_2018], errors='coerce')
        if pd.isna(c2018):
            c2018 = 0.0
        catch_1950 = pd.to_numeric(row[y_1950], errors='coerce')
        if pd.isna(catch_1950):
            catch_1950 = 0.0
        slope = (c2018 - catch_1950) / (2018 - 1950) if 2018 != 1950 else 0.0
        val = c2018 + slope * (t - 2018)
        extended.at[idx, col] = max(0.0, val)

# Reorder columns: Country, 1950..2025, OFR, OFR_change, PriceIndex
all_year_cols = sorted([c for c in extended.columns if str(c).isdigit()], key=lambda x: int(x))
other_cols = [c for c in extended.columns if c not in all_year_cols and c != 'Country']
extended = extended[['Country'] + all_year_cols + other_cols]

# Set OFR and PriceIndex to 2025 forecast (one value per country for extended file)
forecast_2025 = forecast_df[forecast_df['Year'] == 2025].drop_duplicates(subset='Country')
ofr_lookup = forecast_2025.set_index('Country')['OFR_forecast']
price_lookup = forecast_2025.set_index('Country')['PriceIndex_forecast']
extended = extended.set_index('Country')
extended['OFR'] = ofr_lookup.reindex(extended.index).fillna(extended['OFR'])
extended['PriceIndex'] = price_lookup.reindex(extended.index).fillna(extended['PriceIndex'])
extended = extended.reset_index()
# OFR_change from 2018 to 2025 (fractional change)
ofr_2018 = df.set_index('Country')['OFR']
def ofr_change_2025(row):
    c = row['Country']
    o18 = ofr_2018.get(c, 0) or np.nan
    if pd.isna(o18) or o18 == 0:
        return 0.0
    return (row['OFR'] - o18) / o18
extended['OFR_change'] = extended.apply(ofr_change_2025, axis=1)

extended.to_csv('country_features_extended.csv', index=False)
print("Extended features (1950–2025) saved to country_features_extended.csv")

# Optional: overwrite original (uncomment if you want to replace country_features.csv)
# extended.to_csv('country_features.csv', index=False)
# print("country_features.csv updated with 2019–2025.")
