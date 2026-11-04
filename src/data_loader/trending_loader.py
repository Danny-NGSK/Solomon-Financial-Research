"""
Yahoo Finance top-volume tickers loader for the current trading day
"""
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

FALLBACK = [
    {"ticker": "AAPL",  "name": "Apple"},
    {"ticker": "NVDA",  "name": "NVIDIA"},
    {"ticker": "TSLA",  "name": "Tesla"},
    {"ticker": "MSFT",  "name": "Microsoft"},
    {"ticker": "AMZN",  "name": "Amazon"},
    {"ticker": "GOOGL", "name": "Alphabet"},
    {"ticker": "META",  "name": "Meta"},
]


def load_trending_tickers(count: int = 7) -> list[dict]:
    """
    Fetch the top-volume tickers of the day from the Yahoo Finance most_actives screener.

    Returns:
        [{"ticker": "AAPL", "name": "Apple Inc.", "price": 189.3,
          "change_pct": +1.23, "volume": 98_000_000}, ...]
    """
    try:
        resp = requests.get(
            "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved",
            params={"scrIds": "most_actives", "count": count, "region": "US", "lang": "en-US"},
            headers=HEADERS,
            timeout=6,
        )
        resp.raise_for_status()
        quotes = resp.json()["finance"]["result"][0]["quotes"]

        result = []
        for q in quotes:
            ticker = q.get("symbol", "")
            name   = q.get("shortName") or q.get("longName") or ticker
            price  = q.get("regularMarketPrice")
            vol    = q.get("regularMarketVolume")

            # Change %: use provided value first; compute from change/prevClose if absent
            chg        = q.get("regularMarketChangePercent")
            change     = q.get("regularMarketChange")
            prev_close = q.get("regularMarketPreviousClose")

            if chg == 0 and (not change or change == 0):
                # API returns 0 when data is unavailable → do not display
                chg = None
            elif chg is None and change and prev_close:
                chg = (change / prev_close) * 100

            result.append({
                "ticker":     ticker,
                "name":       name,
                "price":      round(price, 2)  if price is not None else None,
                "change_pct": round(chg, 2)    if chg   is not None else None,
                "volume":     vol,
                "sector":     q.get("sector", ""),
            })
        return result if result else FALLBACK

    except Exception as e:
        print(f"[Trending] Load failed: {e}")
        return FALLBACK
