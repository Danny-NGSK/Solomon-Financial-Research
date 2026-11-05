"""
FRED (Federal Reserve Economic Data) macroeconomic indicator loader
Free API: https://fred.stlouisfed.org/docs/api/api_key.html
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from fredapi import Fred

# Define macroeconomic indicators to load
MACRO_SERIES = {
    "FEDFUNDS": {"name": "Fed Funds Rate",        "unit": "%"},
    "DGS2":     {"name": "2Y Treasury",           "unit": "%"},
    "DGS5":     {"name": "5Y Treasury",           "unit": "%"},
    "DGS10":    {"name": "10Y Treasury Yield",     "unit": "%"},
    "CPIAUCSL": {"name": "CPI YoY",               "unit": "%"},   # Convert to YoY % change after loading
    "UNRATE":   {"name": "Unemployment Rate",     "unit": "%"},
    "T10YIE":   {"name": "10Y Breakeven Inflation","unit": "%"},
    "DEXUSEU":  {"name": "USD/EUR",               "unit": ""},
}


def _get_fred() -> Fred:
    from src.config.settings import FRED_API_KEY as api_key
    if not api_key:
        raise ValueError(
            "FRED_API_KEY is not set in .env.\n"
            "Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    return Fred(api_key=api_key)


def fetch_series(series_id: str, years: int = 2) -> pd.Series:
    fred = _get_fred()
    start = (datetime.today() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
    for attempt in range(3):
        try:
            return fred.get_series(series_id, observation_start=start).dropna()
        except Exception as e:
            if attempt == 2:
                raise
            import time; time.sleep(1.5)
    return pd.Series(dtype=float)


def fetch_macro_snapshot() -> dict:
    """
    Load key macroeconomic indicators.

    Returns:
        {
            "FEDFUNDS": {
                "name": "Fed Funds Rate",
                "unit": "%",
                "latest": 5.33,
                "prev_1y": 5.5,
                "change_1y": -0.17,
                "series": pd.Series,   # Time series for charting (2 years)
                "as_of": "2024-03-01"
            },
            ...
        }
    """
    snapshot = {}

    for sid, meta in MACRO_SERIES.items():
        try:
            series = fetch_series(sid, years=10)
            if series.empty:
                continue

            # Convert CPI to YoY % change rate
            if sid == "CPIAUCSL":
                series = (series.pct_change(12) * 100).dropna()

            latest = round(float(series.iloc[-1]), 3)

            # Value from 1 year ago
            cutoff = series.index[-1] - pd.DateOffset(years=1)
            prev_series = series[series.index <= cutoff]
            prev = round(float(prev_series.iloc[-1]), 3) if not prev_series.empty else None

            # as_of: date of the last data point. Falls back to isoformat if strftime fails
            try:
                as_of_str = series.index[-1].strftime("%Y-%m-%d")
            except Exception:
                as_of_str = str(series.index[-1])[:10]

            snapshot[sid] = {
                "name": meta["name"],
                "unit": meta["unit"],
                "latest": latest,
                "prev_1y": prev,
                "change_1y": round(latest - prev, 3) if prev is not None else None,
                "series": series,
                "as_of": as_of_str,
            }

        except Exception as e:
            print(f"[FRED] {sid} load failed: {e}")

    return snapshot
