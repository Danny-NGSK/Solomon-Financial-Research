"""
Shared news loader with fallbacks.

Since mid-October 2026, Yahoo's endpoint behind yfinance `Ticker.news` returns 404,
so `Ticker.news` comes back empty for every symbol. This module tries, in order:
  1. yf.Ticker(symbol).news            (original source; kept in case Yahoo restores it)
  2. yf.Search(symbol, news_count=n)   (different Yahoo endpoint, still working)
  3. Yahoo Finance RSS headline feed   (last resort, no thumbnails)
and normalizes everything to:
  { title, url, publisher, thumbnail, summary, publish_time }
"""
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import requests
import yfinance as yf

RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline"


def _normalize(item: dict) -> dict | None:
    content = item.get("content") or {}
    title = item.get("title") or content.get("title", "")
    if not title:
        return None
    url = (item.get("link")
           or (content.get("clickThroughUrl") or {}).get("url", "")
           or (content.get("canonicalUrl") or {}).get("url", ""))
    publisher = item.get("publisher") or (content.get("provider") or {}).get("displayName", "")

    thumbnail = None
    thumb_data = content.get("thumbnail") or item.get("thumbnail")
    if isinstance(thumb_data, dict):
        resolutions = thumb_data.get("resolutions") or []
        if resolutions:
            thumbnail = resolutions[0].get("url")

    return {
        "title": title,
        "url": url,
        "publisher": publisher,
        "thumbnail": thumbnail,
        "summary": content.get("summary", "") or item.get("summary", ""),
        "publish_time": item.get("providerPublishTime") or content.get("pubDate"),
    }


def _from_ticker(symbol: str) -> list:
    return yf.Ticker(symbol).news or []


def _from_search(symbol: str, n: int) -> list:
    return yf.Search(symbol, news_count=n).news or []


def _from_rss(symbol: str, n: int) -> list:
    resp = requests.get(
        RSS_URL,
        params={"s": symbol, "region": "US", "lang": "en-US"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items = []
    for it in root.iter("item"):
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate")
        ts = None
        if pub:
            try:
                ts = int(parsedate_to_datetime(pub).timestamp())
            except Exception:
                pass
        items.append({
            "title": (it.findtext("title") or "").strip(),
            "link": link,
            "publisher": urlparse(link).netloc.replace("www.", "") if link else "",
            "summary": (it.findtext("description") or "").strip(),
            "providerPublishTime": ts,
        })
    items.sort(key=lambda x: x.get("providerPublishTime") or 0, reverse=True)
    return items[:n]


def fetch_news(symbol: str, n: int = 10, tag: str = "News") -> list:
    """Return up to n normalized news items for symbol, trying each source until one works."""
    sources = [
        ("Ticker.news", lambda: _from_ticker(symbol)),
        ("Search",      lambda: _from_search(symbol, n)),
        ("RSS",         lambda: _from_rss(symbol, n)),
    ]
    for name, fn in sources:
        try:
            items = [x for x in (_normalize(i) for i in fn()[:n]) if x]
            if items:
                return items
            print(f"[{tag}] {symbol}: {name} returned no news, trying next source")
        except Exception as e:
            print(f"[{tag}] {symbol}: {name} failed ({e}), trying next source")
    return []
