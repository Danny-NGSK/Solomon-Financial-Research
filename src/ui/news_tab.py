"""
News tab renderer.
"""
import streamlit as st

from src.ui.common import _section_header, _section_gap


def _relative_time(publish_time) -> str:
    """unix timestamp → relative time in '3h ago' format"""
    if not publish_time:
        return ""
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        # If publish_time is a string (ISO), parse it; if numeric, use fromtimestamp
        if isinstance(publish_time, str):
            from datetime import datetime as _dt
            pt = _dt.fromisoformat(publish_time.replace("Z", "+00:00"))
        else:
            pt = datetime.fromtimestamp(int(publish_time), tz=timezone.utc)
        diff = int((now - pt).total_seconds())
        if diff < 60:       return "just now"
        if diff < 3600:     return f"{diff // 60}m ago"
        if diff < 86400:    return f"{diff // 3600}h ago"
        if diff < 604800:   return f"{diff // 86400}d ago"
        return pt.strftime("%b %d")
    except Exception:
        return ""


def _news_card(title: str, url: str, publisher: str, thumbnail: str | None, summary: str, publish_time=None) -> str:
    short_title = (title[:80] + "…") if len(title) > 80 else title
    rel_time    = _relative_time(publish_time)
    time_html   = f' · <span style="color:#555;">{rel_time}</span>' if rel_time else ""
    meta_html   = f'📌 {publisher}{time_html}' if publisher else rel_time

    if thumbnail:
        card_inner = (
            f'<div style="width:100%; padding-top:52%; position:relative; overflow:hidden; border-radius:8px;">'
            f'<img src="{thumbnail}" style="position:absolute; top:0; left:0; width:100%; height:100%; object-fit:cover;">'
            f'<div style="position:absolute; inset:0; background:linear-gradient(to top, rgba(0,0,0,0.92) 55%, rgba(0,0,0,0.05) 100%); border-radius:8px;"></div>'
            f'<div style="position:absolute; bottom:0; left:0; right:0; padding:12px 14px;">'
            f'<p style="font-size:1.0em; font-weight:700; color:#f0f0f0; margin:0 0 6px; line-height:1.4;">{short_title}</p>'
            f'<p style="font-size:0.75em; color:#bbb; margin:0;">{meta_html}</p>'
            f'</div></div>'
        )
    else:
        initial = (publisher[0].upper()) if publisher else "N"
        card_inner = (
            f'<div style="width:100%; padding-top:52%; position:relative; background:linear-gradient(135deg, #16161e, #1e1e2e); border-radius:8px; overflow:hidden;">'
            f'<div style="position:absolute; inset:0;">'
            f'  <div style="position:absolute; right:-10px; top:50%; transform:translateY(-50%); '
            f'font-size:9em; font-weight:900; color:rgba(255,255,255,0.04); line-height:1; user-select:none;">{initial}</div>'
            f'  <div style="position:absolute; inset:0; background:linear-gradient(to top, rgba(0,0,0,0.85) 55%, transparent 100%);"></div>'
            f'  <div style="position:absolute; bottom:0; left:0; right:0; padding:12px 14px;">'
            f'    <p style="font-size:1.0em; font-weight:700; color:#f0f0f0; margin:0 0 6px; line-height:1.4;">{short_title}</p>'
            f'    <p style="font-size:0.75em; color:#bbb; margin:0;">{meta_html}</p>'
            f'  </div>'
            f'</div></div>'
        )

    return (
        f'<a href="{url}" target="_blank" style="text-decoration:none; color:inherit;">'
        f'<div style="border:1px solid #2a2a3a; border-radius:8px; overflow:hidden; margin-bottom:4px;">'
        f'{card_inner}'
        f'</div></a>'
    )


def _render_news_grid(items: list):
    """Render a 2-column news card grid."""
    cols = st.columns(2)
    for i, item in enumerate(items):
        with cols[i % 2]:
            st.markdown(
                _news_card(
                    title=item.get("title", "No title"),
                    url=item.get("url", "#"),
                    publisher=item.get("publisher", ""),
                    thumbnail=item.get("thumbnail"),
                    summary=item.get("summary", ""),
                    publish_time=item.get("publish_time"),
                ),
                unsafe_allow_html=True,
            )
            st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)


def render_news_tab(news_items: list, ticker: str = "", company_name: str = ""):
    if not news_items:
        st.info("No news data available.")
        return

    # Build keyword set for matching (ticker + significant words from company name)
    keywords = set()
    if ticker:
        keywords.add(ticker.lower())
    if company_name:
        # Add each word ≥4 chars from company name (skip "Inc", "Corp", etc.)
        for word in company_name.lower().split():
            if len(word) >= 4 and word not in {"inc.", "inc", "corp", "corp.", "group", "holdings", "limited", "ltd"}:
                keywords.add(word)

    def _is_relevant(item: dict) -> bool:
        if not keywords:
            return False
        text = (item.get("title", "") + " " + item.get("publisher", "")).lower()
        return any(kw in text for kw in keywords)

    company_news = [n for n in news_items if _is_relevant(n)]
    market_news  = [n for n in news_items if not _is_relevant(n)]

    if company_news:
        _section_header("🏢", f"{ticker} News" if ticker else "Company News")
        _render_news_grid(company_news[:10])

    if market_news:
        _section_gap(8)
        _section_header("🌍", "Related Market News")
        st.caption("General market & financial news from Yahoo Finance")
        _render_news_grid(market_news[:10])
