#!/usr/bin/env python3
"""Data Agent for Overfishing Hackathon Project

Tasks:
1. Load Kaggle worldwide fishing catch dataset (CSV).
2. Clean missing values and standardize country names.
3. Aggregate total catch per country per year.
4. Add latitude and longitude for each country for Google Maps.
5. Save output as JSON and CSV for downstream Feature and Visualization agents.

Output JSON schema:
[
  {
    "country": "Country Name",
    "year": 2018,
    "total_catch": 12345.0,
    "lat": 12.34,
    "lon": 56.78
  },
  ...
]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


# -------------------------------
# Configuration
# -------------------------------

# Minimal mappings for known country name variants (add as needed)
COUNTRY_NAME_MAP = {
    "United States of America": "United States",
    "USA": "United States",
    "US": "United States",
    "Republic of Korea": "South Korea",
    "Korea, Republic of": "South Korea",
    "Korea, Democratic People\'s Republic of": "North Korea",
    "Russian Federation": "Russia",
    "Viet Nam": "Vietnam",
    "Czechia": "Czech Republic",
}

# Geocode cache filename (stored next to output files)
GEOCODE_CACHE_FILENAME = "country_geocode_cache.json"


# -------------------------------
# Helpers
# -------------------------------

def _standardize_country_name(country: str) -> str:
    country = str(country).strip()
    if not country:
        return country

    # Normalize whitespace and casing
    country_norm = " ".join(country.split())
    country_norm = country_norm.title()

    # Apply known mapping overrides
    mapped = COUNTRY_NAME_MAP.get(country_norm) or COUNTRY_NAME_MAP.get(country)
    return mapped or country_norm


def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    required_cols = ["Country", "Year", "Catch"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in source CSV: {missing_cols}")

    df = df.copy()

    # Drop rows with missing country/year/catch
    df = df.dropna(subset=["Country", "Year", "Catch"])

    # Standardize country names
    df["Country"] = df["Country"].astype(str).map(_standardize_country_name)

    # Ensure Year is integer and Catch is numeric
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(pd.Int64Dtype())
    df["Catch"] = pd.to_numeric(df["Catch"], errors="coerce")

    df = df.dropna(subset=["Year", "Catch"])

    return df


def aggregate_catch(df: pd.DataFrame) -> pd.DataFrame:
    # Aggregate total catch per country per year
    agg = (
        df.groupby(["Country", "Year"], dropna=False)["Catch"]
        .sum()
        .reset_index()
        .rename(columns={"Catch": "total_catch"})
    )

    # Ensure consistent ordering
    agg = agg.sort_values(["Country", "Year"]).reset_index(drop=True)
    return agg


def _load_geocode_cache(cache_path: Path) -> Dict[str, Tuple[Optional[float], Optional[float]]]:
    if not cache_path.exists():
        return {}

    try:
        with cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_geocode_cache(cache_path: Path, cache: Dict[str, Tuple[Optional[float], Optional[float]]]) -> None:
    with cache_path.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def geocode_countries(
    countries: List[str],
    cache_path: Path,
    user_agent: str = "overfishing-data-agent",
    timeout: int = 10,
    pause_seconds: float = 1.0,
) -> Dict[str, Dict[str, Optional[float]]]:
    """Return mapping: country -> {lat, lon}."""

    cache = _load_geocode_cache(cache_path)

    # Already have results for a country if in cache and lat/lon are not None
    to_lookup = [c for c in countries if c not in cache or cache[c] in (None, {}, [])]
    if not to_lookup:
        return {c: cache[c] for c in countries}

    geolocator = Nominatim(user_agent=user_agent, timeout=timeout)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=pause_seconds)

    for country in to_lookup:
        try:
            location = geocode(country)
            if location and location.latitude is not None and location.longitude is not None:
                cache[country] = {"lat": float(location.latitude), "lon": float(location.longitude)}
            else:
                cache[country] = {"lat": None, "lon": None}
                logging.warning("Geocode returned no location for country: %s", country)
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            logging.warning("Geocoding %s failed (%s); saving empty result and continuing", country, e)
            cache[country] = {"lat": None, "lon": None}
        except Exception as e:
            logging.warning("Unexpected geocoding error for %s: %s", country, e)
            cache[country] = {"lat": None, "lon": None}

    _save_geocode_cache(cache_path, cache)

    return {c: cache.get(c, {"lat": None, "lon": None}) for c in countries}


def save_outputs(
    df: pd.DataFrame,
    out_dir: str,
    json_name: str = "data_agent_output.json",
    csv_name: str = "data_agent_output.csv",
) -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    json_path = out_path / json_name
    csv_path = out_path / csv_name

    # For JSON, we want an array of objects
    records = df.to_dict(orient="records")

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    df.to_csv(csv_path, index=False)

    logging.info("Saved JSON output to %s", json_path)
    logging.info("Saved CSV output to %s", csv_path)


def build_dataset(
    input_csv: str,
    output_dir: str,
    geocode_cache_dir: Optional[str] = None,
    force_regeocode: bool = False,
) -> pd.DataFrame:
    df = load_data(input_csv)
    df = clean_data(df)
    df = aggregate_catch(df)

    cache_dir = Path(geocode_cache_dir or output_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / GEOCODE_CACHE_FILENAME

    countries = sorted(df["Country"].dropna().unique().tolist())

    if force_regeocode and cache_path.exists():
        cache_path.unlink()

    geo = geocode_countries(countries, cache_path)

    # Attach lat/lon to aggregated dataframe
    df["lat"] = df["Country"].map(lambda c: geo.get(c, {}).get("lat"))
    df["lon"] = df["Country"].map(lambda c: geo.get(c, {}).get("lon"))

    save_outputs(df, output_dir)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Data Agent for Overfishing Hackathon Project")
    parser.add_argument(
        "--input-csv",
        required=True,
        help="Path to the Kaggle fishing catch CSV (e.g., worldwide_fishing_catch.csv).",
    )
    parser.add_argument(
        "--output-dir",
        default="./output",
        help="Directory to write JSON/CSV outputs (default: ./output).",
    )
    parser.add_argument(
        "--geocode-cache-dir",
        default=None,
        help="Directory to store geocode cache (default: same as output_dir).",
    )
    parser.add_argument(
        "--force-regeocode",
        action="store_true",
        help="Ignore existing geocode cache and re-query all countries.",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    build_dataset(
        input_csv=args.input_csv,
        output_dir=args.output_dir,
        geocode_cache_dir=args.geocode_cache_dir,
        force_regeocode=args.force_regeocode,
    )


if __name__ == "__main__":
    main()
