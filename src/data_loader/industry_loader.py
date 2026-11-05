"""
Industry data loader
- Sector/industry info for the given ticker: yfinance
- Sector ETF performance: yfinance
- Peer comparison: yfinance (predefined peer map → dynamic industry fallback)
- Industry-related news: yfinance
"""
import yfinance as yf
from src.data_loader.news_loader import fetch_news
from src.data_loader.info_loader import fetch_info

# ─────────────────────────────────────────
# Sector → ETF mapping (SPDR-based)
# ─────────────────────────────────────────
SECTOR_ETF_MAP = {
    "Technology":             ("XLK",  "Technology Select Sector SPDR"),
    "Healthcare":             ("XLV",  "Health Care Select Sector SPDR"),
    "Financial Services":     ("XLF",  "Financial Select Sector SPDR"),
    "Consumer Cyclical":      ("XLY",  "Consumer Discretionary Select Sector SPDR"),
    "Consumer Defensive":     ("XLP",  "Consumer Staples Select Sector SPDR"),
    "Energy":                 ("XLE",  "Energy Select Sector SPDR"),
    "Utilities":              ("XLU",  "Utilities Select Sector SPDR"),
    "Real Estate":            ("XLRE", "Real Estate Select Sector SPDR"),
    "Basic Materials":        ("XLB",  "Materials Select Sector SPDR"),
    "Industrials":            ("XLI",  "Industrial Select Sector SPDR"),
    "Communication Services": ("XLC",  "Communication Services Select Sector SPDR"),
}

# ─────────────────────────────────────────
# Ticker → peer company mapping
# ─────────────────────────────────────────
PEER_MAP = {
    # Semiconductors
    "NVDA": ["AMD", "INTC", "TSM", "ASML", "QCOM", "AVGO"],
    "AMD":  ["NVDA", "INTC", "QCOM", "AVGO", "TSM"],
    "INTC": ["NVDA", "AMD", "QCOM", "TSM", "AVGO"],
    "TSM":  ["NVDA", "ASML", "INTC", "AMD", "AMAT"],
    "ASML": ["TSM", "AMAT", "LRCX", "KLAC", "NVDA"],
    "QCOM": ["NVDA", "AMD", "AVGO", "MRVL", "INTC"],
    "AVGO": ["QCOM", "NVDA", "AMD", "MRVL", "TXN"],
    # Big Tech
    "AAPL": ["MSFT", "GOOGL", "META", "AMZN", "NVDA"],
    "MSFT": ["AAPL", "GOOGL", "META", "AMZN", "CRM"],
    "GOOGL":["MSFT", "META", "AMZN", "AAPL", "NFLX"],
    "GOOG": ["MSFT", "META", "AMZN", "AAPL", "NFLX"],
    "META": ["GOOGL", "SNAP", "PINS", "NFLX", "MSFT"],
    "AMZN": ["MSFT", "GOOGL", "AAPL", "WMT", "SHOP"],
    # Electric Vehicles
    "TSLA": ["GM", "F", "RIVN", "NIO", "LI"],
    "RIVN": ["TSLA", "GM", "F", "NIO", "LCID"],
    # Enterprise Software
    "PLTR": ["CRM", "SNOW", "DDOG", "MDB", "NOW"],
    "CRM":  ["MSFT", "SAP", "NOW", "ORCL", "PLTR"],
    "SNOW": ["PLTR", "DDOG", "MDB", "ESTC", "NET"],
    # Financials
    "JPM":  ["BAC", "WFC", "GS", "MS", "C"],
    "BAC":  ["JPM", "WFC", "C", "GS", "USB"],
    "GS":   ["MS", "JPM", "BAC", "WFC", "BLK"],
    # Healthcare
    "JNJ":  ["PFE", "MRK", "ABBV", "LLY", "BMY"],
    "PFE":  ["JNJ", "MRK", "ABBV", "LLY", "BMY"],
    "LLY":  ["PFE", "JNJ", "MRK", "ABBV", "NVO"],
}


def _fetch_ticker(ticker: str, period: str = "6mo") -> dict:
    """Return price + returns for a single ticker"""
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty:
            return {}
        close = hist["Close"].dropna()
        if close.empty:
            return {}
        latest  = round(float(close.iloc[-1]), 2)
        ret_1d  = round((close.iloc[-1] / close.iloc[-2]  - 1) * 100, 2) if len(close) >= 2  else None
        ret_1m  = round((close.iloc[-1] / close.iloc[-21] - 1) * 100, 2) if len(close) >= 21 else None
        ret_3m  = round((close.iloc[-1] / close.iloc[-63] - 1) * 100, 2) if len(close) >= 63 else None
        return {
            "latest_price": latest,
            "ret_1d": ret_1d,
            "ret_1m": ret_1m,
            "ret_3m": ret_3m,
            "history": hist,
        }
    except Exception as e:
        print(f"[Industry] {ticker} load failed: {e}")
        return {}


def _fetch_info(ticker: str) -> dict:
    """Peer / sector lookups only need Yahoo fields; skip Alpha Vantage to save its daily quota."""
    return fetch_info(ticker, use_av_fallback=False)


def load_industry_data(ticker: str) -> dict:
    """
    Load all industry data.

    Returns:
        {
            "ticker":       str,
            "company_name": str,
            "sector":       str,
            "industry":     str,
            "sector_etf":   { ticker, name, ret_1d, ret_1m, ret_3m, history },
            "target":       { latest_price, ret_1d, ret_1m, ret_3m, history },
            "peers":        [ { ticker, name, latest_price, ret_1d, ret_1m, ret_3m } ],
            "news":         [ { title, url, publisher, thumbnail } ],
        }
    """
    ticker = ticker.upper()
    result = {"ticker": ticker}

    # ── Company basic info ──
    info = _fetch_info(ticker)

    result["company_name"] = info.get("longName") or info.get("shortName") or ticker
    result["sector"]       = info.get("sector", "Unknown")
    result["industry"]     = info.get("industry", "Unknown")

    # ── Sector ETF ──
    etf_ticker, etf_name = SECTOR_ETF_MAP.get(result["sector"], ("SPY", "S&P 500 ETF"))
    etf_data = _fetch_ticker(etf_ticker, period="max")
    result["sector_etf"] = {"ticker": etf_ticker, "name": etf_name, **etf_data}

    # ── Target ticker performance ──
    result["target"] = _fetch_ticker(ticker, period="max")

    # ── Industry peers ──
    peer_tickers = PEER_MAP.get(ticker, [])

    # PEER_MAP에 없으면 yf.Industry로 동적 조회
    if not peer_tickers:
        industry_key = info.get("industryKey", "")
        if industry_key:
            try:
                ind = yf.Industry(industry_key)
                top_df = ind.top_performing_companies
                if top_df is not None and not top_df.empty:
                    peer_tickers = [s for s in top_df.index.tolist() if s != ticker][:5]
            except Exception as e:
                print(f"[Industry] dynamic peer lookup failed: {e}")

    peers = []
    for pt in [t for t in peer_tickers if t != ticker][:5]:
        data    = _fetch_ticker(pt, period="6mo")
        pt_info = _fetch_info(pt)
        # Keep the peer if EITHER price history or fundamentals loaded —
        # previously a failed price fetch dropped the peer even when its valuation data was fine.
        if not data and not pt_info:
            print(f"[Industry] peer {pt}: no price or info data, skipped")
            continue
        peers.append({
            "ticker":     pt,
            "name":       pt_info.get("shortName") or pt,
            "pe_ratio":   pt_info.get("trailingPE"),
            "forward_pe": pt_info.get("forwardPE"),
            "pb_ratio":   pt_info.get("priceToBook"),
            "ps_ratio":   pt_info.get("priceToSalesTrailing12Months"),
            "op_margin":  pt_info.get("operatingMargins"),
            **{k: v for k, v in data.items() if k != "history"},
        })
    result["peers"] = peers

    # ── Industry-related news ──
    news_items = fetch_news(ticker, n=10, tag="Industry")

    result["news"] = news_items
    return result
