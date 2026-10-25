"""
fetch_fred.py
-------------
Downloads real U.S. price index data from FRED (Federal Reserve Bank of St. Louis)
and saves it to data/external/price_indices.csv.

These indices drive how prices move in the synthetic GulfChem data, and they are the
leading indicators we will use for price forecasting in Phase 6.

Run from the project root:
    python src/fetch_fred.py

Requires a free FRED API key stored in a .env file:
    FRED_API_KEY=your_key_here
"""

import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = ROOT / "data" / "external" / "price_indices.csv"

# Each key is the short name the generator uses; each value is the FRED series.
# WHY these series: they match the biggest cost drivers in maintenance spend.
SERIES = {
    "STEEL": ("WPU1017", "PPI: Steel Mill Products"),                  # pipe, flanges, fittings
    "VALVES": ("WPU114902", "PPI: Metal Valves, Except Fluid Power"),  # valves and actuators
    "PUMPS": ("WPU1141", "PPI: Pumps, Compressors, and Equipment"),    # pump repair, MRO parts
    "LABOR": ("CES2000000003", "Avg Hourly Earnings: Construction"),   # contractor labor rates
}

START_DATE = "2018-01-01"  # extra history gives the forecasting models more to learn from
API_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch_series(series_id: str, api_key: str) -> pd.DataFrame:
    """Download one FRED series and return a DataFrame with date and value columns."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": START_DATE,
    }
    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    observations = response.json()["observations"]

    df = pd.DataFrame(observations)[["date", "value"]]
    # FRED marks missing values with "." so we convert them to NaN and drop them.
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    return df.dropna()


def main():
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        sys.exit("FRED_API_KEY not found. Add it to the .env file in your project root.")

    frames = []
    for short_name, (series_id, description) in SERIES.items():
        try:
            df = fetch_series(series_id, api_key)
            df["index_name"] = short_name
            df["series_id"] = series_id
            df["description"] = description
            frames.append(df)
            print(f"OK   {short_name:<6} {series_id:<15} {len(df)} months, "
                  f"latest {df['date'].max():%Y-%m} = {df['value'].iloc[-1]:.1f}")
        except Exception as error:  # keep going if one series fails
            print(f"FAIL {short_name:<6} {series_id:<15} {error}")

    if not frames:
        sys.exit("No series downloaded. Check your API key and internet connection.")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result = pd.concat(frames, ignore_index=True)
    result = result[["date", "index_name", "series_id", "description", "value"]]
    result.to_csv(OUT_FILE, index=False)
    print(f"\nSaved {len(result)} rows to {OUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
