import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str) -> str | None:
    """Read a secret from the environment (.env locally), falling back to
    Streamlit's secrets store (used on Streamlit Community Cloud, where
    .env is not uploaded and secrets are configured via the dashboard)."""
    value = os.getenv(key)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception:
        return None


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR        = BASE_DIR / "data"
RAW_DIR         = DATA_DIR / "raw"
PROCESSED_DIR   = DATA_DIR / "processed"
CACHE_DIR       = DATA_DIR / "cache"

RAW_COMPANY_DIR     = RAW_DIR / "company"
RAW_INDUSTRY_DIR    = RAW_DIR / "industry"
RAW_MARKET_DIR      = RAW_DIR / "market"

PROCESSED_COMPANY_DIR   = PROCESSED_DIR / "company"
PROCESSED_INDUSTRY_DIR  = PROCESSED_DIR / "industry"
PROCESSED_MARKET_DIR    = PROCESSED_DIR / "market"

OUTPUT_DIR  = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
LOGS_DIR    = OUTPUT_DIR / "logs"
REPORTS_DIR = OUTPUT_DIR / "reports"

DEFAULT_START_DATE = "2025-01-01"
DEFAULT_END_DATE   = None

ALPHA_VANTAGE_API_KEY = _get_secret("ALPHA_VANTAGE_API_KEY")
OPENAI_API_KEY        = _get_secret("OPENAI_API_KEY")
FRED_API_KEY          = _get_secret("FRED_API_KEY")

# OpenAI model configuration
LLM_MODEL_DEFAULT = "gpt-5.4-mini"   # General requests
LLM_MODEL_REPORT  = "gpt-5.4"        # Final investment report generation

if not OPENAI_API_KEY:
    print("⚠️  OPENAI_API_KEY is not set in .env.")
if not FRED_API_KEY:
    print("⚠️  FRED_API_KEY is not set in .env. Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html")
