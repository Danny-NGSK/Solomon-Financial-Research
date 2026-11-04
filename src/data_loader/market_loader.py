"""
Market data loader
- Major indices (SPY/NASDAQ/Dow): yfinance
- VIX + CNN Fear & Greed Index: yfinance / CNN API
- Market news (with thumbnails): yfinance
- Macroeconomic indicators: FRED API
"""
import requests
import yfinance as yf
from src.data_loader.fred_loader import fetch_macro_snapshot


def _fetch_index(ticker: str, fallback: str = None, period: str = "6mo") -> dict:
    """Return single index data (price + returns). Tries fallback ticker on failure."""
    tickers = [ticker] + ([fallback] if fallback else [])
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period=period)
            if hist.empty:
                continue
            close = hist["Close"].dropna()
            if close.empty:
                continue
            import pandas as pd
            latest_date = close.index[-1]
            latest = round(float(close.iloc[-1]), 2)
            ret_1d = round((close.iloc[-1] / close.iloc[-2]  - 1) * 100, 2) if len(close) >= 2  else None
            ret_1m = round((close.iloc[-1] / close.iloc[-21] - 1) * 100, 2) if len(close) >= 21 else None
            ret_3m = round((close.iloc[-1] / close.iloc[-63] - 1) * 100, 2) if len(close) >= 63 else None
            return {
                "latest_price": latest,
                "ret_1d": ret_1d,
                "ret_1m": ret_1m,
                "ret_3m": ret_3m,
                "history": hist,
            }
        except Exception as e:
            print(f"[Market] {t} load failed: {e}")
    return {}


def _fetch_cnn_fear_greed() -> dict | None:
    """Fetch CNN Fear & Greed Index directly (using browser headers)"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://edition.cnn.com/markets/fear-and-greed",
        "Origin": "https://edition.cnn.com",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }
    endpoints = [
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/",
    ]
    for url in endpoints:
        try:
            resp = requests.get(url, headers=headers, timeout=6)
            if resp.status_code == 200 and resp.text.strip():
                data = resp.json()
                fg = data.get("fear_and_greed") or {}
                score  = fg.get("score")
                rating = fg.get("rating", "")
                if score is not None:
                    print(f"[Market] CNN Fear & Greed Index fetched successfully: {score} ({rating})")
                    return {"score": round(float(score)), "rating": rating, "source": "cnn"}
        except Exception as e:
            print(f"[Market] CNN F&G endpoint failed ({url}): {e}")
    return None


def _calc_fear_greed_from_vix(vix: float) -> dict:
    """Calculate market sentiment index based on VIX (fallback when CNN fails)"""
    if vix <= 12:
        score, rating = min(100, int(100 - vix * 0.5)), "Extreme Greed"
    elif vix <= 17:
        score, rating = int(90 - (vix - 12) * 5), "Greed"
    elif vix <= 22:
        score, rating = int(65 - (vix - 17) * 3), "Neutral"
    elif vix <= 30:
        score, rating = int(50 - (vix - 22) * 3.1), "Fear"
    else:
        score, rating = max(0, int(25 - (vix - 30))), "Extreme Fear"
    return {"score": max(0, min(100, score)), "rating": rating, "source": "vix_proxy"}


def load_market_data() -> dict:
    """
    Load all market data.

    Returns:
        {
            "spy":    { latest_price, ret_1d, ret_1m, ret_3m, history },
            "nasdaq": { latest_price, ret_1d, ret_1m, ret_3m, history },
            "dow":    { latest_price, ret_1d, ret_1m, ret_3m, history },
            "vix":    float,
            "fear_greed": { score: int, rating: str } | None,
            "news":   [ { title, url, publisher, thumbnail, summary } ],
            "macro":  { ... }  # Result from fred_loader.fetch_macro_snapshot()
        }
    """
    result = {}

    # --- Major indices (fallback to ETF substitute tickers on failure) ---
    result["spy"]    = _fetch_index("SPY",   period="max")
    result["nasdaq"] = _fetch_index("^IXIC", fallback="QQQ", period="max")
    result["dow"]    = _fetch_index("^DJI",  fallback="DIA", period="max")

    # --- VIX ---
    try:
        vix_hist = yf.Ticker("^VIX").history(period="5d")
        if not vix_hist.empty:
            vix_close = vix_hist["Close"].dropna()
            if not vix_close.empty:
                result["vix"] = round(float(vix_close.iloc[-1]), 2)
    except Exception as e:
        print(f"[Market] VIX load failed: {e}")

    # --- Fear & Greed Index (CNN preferred, falls back to VIX-based calculation) ---
    result["fear_greed"] = _fetch_cnn_fear_greed()
    if result["fear_greed"] is None and result.get("vix"):
        result["fear_greed"] = _calc_fear_greed_from_vix(result["vix"])

    # --- Market news (with thumbnails) ---
    news_items = []
    try:
        raw_news = yf.Ticker("SPY").news[:12]
        for item in raw_news:
            content = item.get("content") or {}

            thumbnail = None
            thumb_data = content.get("thumbnail")
            if thumb_data:
                resolutions = thumb_data.get("resolutions", [])
                if resolutions:
                    thumbnail = resolutions[0].get("url")

            title     = item.get("title") or content.get("title", "")
            url       = item.get("link") or (content.get("clickThroughUrl") or {}).get("url", "")
            publisher = item.get("publisher") or (content.get("provider") or {}).get("displayName", "")
            summary   = content.get("summary", "")

            if title:
                news_items.append({
                    "title": title,
                    "url": url,
                    "publisher": publisher,
                    "thumbnail": thumbnail,
                    "summary": summary,
                })
    except Exception as e:
        print(f"[Market] News load failed: {e}")

    result["news"] = news_items

    # --- FRED macroeconomic indicators ---
    try:
        result["macro"] = fetch_macro_snapshot()
    except Exception as e:
        print(f"[Market] FRED data load failed: {e}")
        result["macro"] = {}

    # --- Sector ETF returns (for heatmap) ---
    sector_etfs = {
        "Technology":       "XLK",
        "Healthcare":       "XLV",
        "Financials":       "XLF",
        "Consumer Disc.":   "XLY",
        "Consumer Stpl.":   "XLP",
        "Energy":           "XLE",
        "Utilities":        "XLU",
        "Real Estate":      "XLRE",
        "Materials":        "XLB",
        "Industrials":      "XLI",
        "Comm. Services":   "XLC",
    }
    sector_returns = {}
    for sector_name, etf_ticker in sector_etfs.items():
        try:
            hist = yf.Ticker(etf_ticker).history(period="3mo")
            if hist.empty:
                continue
            close = hist["Close"].dropna()
            if close.empty:
                continue
            ret_1d = round((close.iloc[-1] / close.iloc[-2]  - 1) * 100, 2) if len(close) >= 2  else None
            ret_1w = round((close.iloc[-1] / close.iloc[-5]  - 1) * 100, 2) if len(close) >= 5  else None
            ret_1m = round((close.iloc[-1] / close.iloc[-21] - 1) * 100, 2) if len(close) >= 21 else None
            sector_returns[sector_name] = {"ticker": etf_ticker, "ret_1d": ret_1d, "ret_1w": ret_1w, "ret_1m": ret_1m}
        except Exception as e:
            print(f"[Market] Sector {etf_ticker} load failed: {e}")
    result["sector_returns"] = sector_returns

    return result
