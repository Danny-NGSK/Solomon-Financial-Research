"""
Shared company-fundamentals loader: yfinance `.info` with retry, cache and an Alpha Vantage fallback.

Why: on Streamlit Cloud, Yahoo often rate-limits bursts of requests. When that happens
`.info` can come back partially filled — quote fields (price, market cap, P/E) are present,
but the detailed-statistics fields (margins, ROE, revenue growth, analyst targets) are missing.
That showed up as blanks in the Company tab's Valuation / Financials / Analyst sections.

Strategy:
  1. Call yf.Ticker(t).info, retrying with backoff while the detailed fields are missing.
  2. Fill any still-missing fields from Alpha Vantage OVERVIEW (different provider, so it
     isn't affected by Yahoo's limits). Only called when something is missing, because the
     free AV tier allows ~25 requests/day.
  3. Cache results in-process so repeat lookups don't hit either API.

The returned dict uses yfinance key names, so callers don't need to change how they read it.
"""
import time

import requests
import yfinance as yf

from src.config.settings import ALPHA_VANTAGE_API_KEY

_CACHE: dict = {}
_TTL = 6 * 3600

# Fields that only come from Yahoo's detailed-statistics modules; if all are missing,
# the response was most likely cut short by rate limiting.
_DETAIL_KEYS = ["operatingMargins", "returnOnEquity", "grossMargins", "totalRevenue", "revenueGrowth"]

# Alpha Vantage OVERVIEW field -> yfinance .info field
_AV_MAP = {
    "MarketCapitalization":        "marketCap",
    "PERatio":                     "trailingPE",
    "ForwardPE":                   "forwardPE",
    "PriceToBookRatio":            "priceToBook",
    "PriceToSalesRatioTTM":        "priceToSalesTrailing12Months",
    "ProfitMargin":                "profitMargins",
    "OperatingMarginTTM":          "operatingMargins",
    "ReturnOnEquityTTM":           "returnOnEquity",
    "RevenueTTM":                  "totalRevenue",
    "EPS":                         "trailingEps",
    "QuarterlyRevenueGrowthYOY":   "revenueGrowth",
    "QuarterlyEarningsGrowthYOY":  "earningsGrowth",
    "AnalystTargetPrice":          "targetMeanPrice",
    "52WeekHigh":                  "fiftyTwoWeekHigh",
    "52WeekLow":                   "fiftyTwoWeekLow",
    "Name":                        "longName",
    "Sector":                      "sector",
    "Industry":                    "industry",
    "Description":                 "longBusinessSummary",
}
_AV_RATINGS = {
    "AnalystRatingStrongBuy":  "strongBuy",
    "AnalystRatingBuy":        "buy",
    "AnalystRatingHold":       "hold",
    "AnalystRatingSell":       "sell",
    "AnalystRatingStrongSell": "strongSell",
}
_TEXT_FIELDS = {"Name", "Sector", "Industry", "Description"}


def _has_detail(info: dict) -> bool:
    return any(info.get(k) is not None for k in _DETAIL_KEYS)


def _yahoo_info(ticker: str, retries: int) -> dict:
    best: dict = {}
    for attempt in range(retries + 1):
        try:
            info = yf.Ticker(ticker).info or {}
            if len(info) > len(best):
                best = info
            if _has_detail(info):
                return info
            print(f"[Info] {ticker}: Yahoo returned partial info ({len(info)} fields), attempt {attempt + 1}")
        except Exception as e:
            print(f"[Info] {ticker}: Yahoo info attempt {attempt + 1} failed: {e}")
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    return best


def _av_overview(ticker: str) -> dict:
    if not ALPHA_VANTAGE_API_KEY:
        return {}
    try:
        resp = requests.get(
            "https://www.alphavantage.co/query",
            params={"function": "OVERVIEW", "symbol": ticker, "apikey": ALPHA_VANTAGE_API_KEY},
            timeout=10,
        )
        data = resp.json() or {}
        if "Symbol" not in data:   # rate-limit / error responses have a "Note" or "Information" key instead
            msg = data.get("Note") or data.get("Information") or "no data"
            print(f"[Info] {ticker}: Alpha Vantage OVERVIEW unavailable ({str(msg)[:80]})")
            return {}
        return data
    except Exception as e:
        print(f"[Info] {ticker}: Alpha Vantage OVERVIEW failed: {e}")
        return {}


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None   # AV uses "None" / "-" for missing values


def _fill_from_av(info: dict, av: dict) -> list:
    """Fill missing yfinance keys from an AV OVERVIEW payload. Returns the keys that were filled."""
    filled = []
    for av_key, yf_key in _AV_MAP.items():
        if info.get(yf_key) is not None:
            continue
        raw = av.get(av_key)
        val = (raw if raw not in (None, "None", "-", "") else None) if av_key in _TEXT_FIELDS else _num(raw)
        if val is not None:
            info[yf_key] = val
            filled.append(yf_key)

    if info.get("grossMargins") is None:
        gp, rev = _num(av.get("GrossProfitTTM")), _num(av.get("RevenueTTM"))
        if gp is not None and rev:
            info["grossMargins"] = gp / rev
            filled.append("grossMargins")

    ratings = {yk: int(_num(av.get(ak)) or 0) for ak, yk in _AV_RATINGS.items()}
    total = sum(ratings.values())
    if total:
        info["_av_ratings"] = ratings
        if info.get("numberOfAnalystOpinions") is None:
            info["numberOfAnalystOpinions"] = total
            filled.append("numberOfAnalystOpinions")
        if info.get("recommendationKey") in (None, "none", "–"):
            score = (1 * ratings["strongBuy"] + 2 * ratings["buy"] + 3 * ratings["hold"]
                     + 4 * ratings["sell"] + 5 * ratings["strongSell"]) / total
            info["recommendationKey"] = ("strong_buy" if score <= 1.5 else "buy" if score <= 2.5
                                         else "hold" if score <= 3.5 else "sell" if score <= 4.5
                                         else "strong_sell")
            filled.append("recommendationKey")
    return filled


def _cached(key, fn):
    now = time.time()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < _TTL:
        return hit[1]
    val = fn()
    if val:
        _CACHE[key] = (now, val)
    return val


def fetch_info(ticker: str, retries: int = 2, use_av_fallback: bool = True) -> dict:
    """yfinance-style info dict for ticker, as complete as Yahoo + Alpha Vantage allow.

    Yahoo and Alpha Vantage results are cached separately, so the industry loader (Yahoo only)
    and the company loader (Yahoo + AV) share one Yahoo call per ticker.
    """
    ticker = ticker.upper()
    info = dict(_cached(("yahoo", ticker), lambda: _yahoo_info(ticker, retries)) or {})

    if use_av_fallback and (not _has_detail(info) or info.get("targetMeanPrice") is None):
        av = _cached(("av", ticker), lambda: _av_overview(ticker)) or {}
        if av:
            filled = _fill_from_av(info, av)
            if filled:
                print(f"[Info] {ticker}: filled {len(filled)} fields from Alpha Vantage: {', '.join(filled)}")
    return info
