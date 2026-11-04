"""
Ticker search and resolution utilities for the searchbox.
"""
import yfinance as yf


def search_ticker(query: str) -> list[str]:
    """
    Search for matching tickers/companies for autocomplete.
    Returns a list of 'SYMBOL — Company Name' strings.
    """
    if not query or len(query.strip()) < 1:
        return []
    try:
        results = yf.Search(query, max_results=8).quotes
        suggestions = []
        for r in results:
            symbol = r.get("symbol", "")
            name = r.get("shortname") or r.get("longname", "")
            exchange = r.get("exchange", "")
            # Filter out non-equity types and non-US exchanges to reduce noise
            quote_type = r.get("quoteType", "")
            if not symbol:
                continue
            if quote_type not in ("EQUITY", "ETF", ""):
                continue
            label = f"{symbol} — {name}" if name else symbol
            suggestions.append(label)
        return suggestions
    except Exception:
        q = query.strip().upper()
        return [q] if q else []


def resolve_ticker(raw: str) -> str:
    """
    Extract a clean ticker symbol from a selected searchbox value.
    Handles formats like 'AAPL — Apple Inc.' or plain 'AAPL' or 'Apple'.
    """
    if not raw:
        return ""
    # Format: "SYMBOL — Company Name"
    ticker = raw.split("—")[0].strip().upper()
    # Remove any trailing punctuation
    ticker = ticker.rstrip(" .-")
    return ticker
