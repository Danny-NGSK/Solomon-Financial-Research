"""
Shared UI utility functions used across multiple tab modules.
"""
import streamlit as st
import plotly.graph_objects as go

# ─────────────────────────────────────────
# Period selector
# ─────────────────────────────────────────
_PERIOD_OPTIONS = ["1M", "3M", "6M", "YTD", "1Y", "5Y", "All"]


def _filter_history(hist, label: str):
    """Slice the history DataFrame to match the selected period."""
    import pandas as pd
    if hist is None or hist.empty or label == "All":
        return hist
    end = hist.index[-1]
    tz = end.tzinfo  # preserve index timezone
    if label == "YTD":
        start = pd.Timestamp(end.year, 1, 1, tz=tz)
    else:
        offsets = {
            "1M": pd.DateOffset(months=1),
            "3M": pd.DateOffset(months=3),
            "6M": pd.DateOffset(months=6),
            "1Y": pd.DateOffset(years=1),
            "5Y": pd.DateOffset(years=5),
        }
        start = end - offsets[label]
    return hist[hist.index >= start]


def _period_pills(key: str, default: str = "1Y") -> str:
    """Period selection pills. Returns the selected label."""
    return st.pills("Period", _PERIOD_OPTIONS, default=default, key=key, label_visibility="collapsed")


# ─────────────────────────────────────────
# Sector / exchange constants
# ─────────────────────────────────────────
_SECTOR_COLORS = {
    "Technology":             "#4C9BE8",
    "Healthcare":             "#28a745",
    "Financials":             "#F59E0B",
    "Consumer Discretionary": "#e91e63",
    "Consumer Staples":       "#9c27b0",
    "Energy":                 "#ff5722",
    "Industrials":            "#607d8b",
    "Materials":              "#795548",
    "Real Estate":            "#00bcd4",
    "Communication Services": "#3f51b5",
    "Utilities":              "#8bc34a",
}

_EXCHANGE_LABELS = {
    "NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ",
    "NYQ": "NYSE",   "ASE": "AMEX",
    "PCX": "NYSE",   "BTS": "OTC",
}


# ─────────────────────────────────────────
# Pill / badge helpers
# ─────────────────────────────────────────
def _pill(text: str, color: str, text_color: str = "#fff") -> str:
    return (
        f'<span style="display:inline-block; padding:3px 10px; border-radius:20px; '
        f'font-size:0.75em; font-weight:600; letter-spacing:0.4px; '
        f'background:{color}22; border:1px solid {color}66; color:{color}; '
        f'margin-right:6px; white-space:nowrap;">{text}</span>'
    )


def _company_pills(sector: str, industry: str, market_cap, exchange: str) -> str:
    parts = []

    # Sector pill
    if sector and sector != "–":
        color = _SECTOR_COLORS.get(sector, "#888888")
        parts.append(_pill(sector, color))

    # Market cap tier
    if market_cap:
        if market_cap >= 200e9:
            parts.append(_pill("Mega Cap", "#6f42c1"))
        elif market_cap >= 10e9:
            parts.append(_pill("Large Cap", "#4C9BE8"))
        elif market_cap >= 2e9:
            parts.append(_pill("Mid Cap", "#28a745"))
        else:
            parts.append(_pill("Small Cap", "#888888"))

    # Exchange
    exch_label = _EXCHANGE_LABELS.get(exchange, exchange)
    if exch_label:
        parts.append(_pill(exch_label, "#aaaaaa"))

    return '<div style="margin:6px 0 4px;">' + "".join(parts) + "</div>"


def _company_returns(price: dict) -> str:
    """Inline display of 1D / 1M / 3M / 1Y returns."""
    items = [
        ("1D",  price.get("ret_1d")),
        ("1M",  price.get("ret_1m")),
        ("3M",  price.get("ret_3m")),
        ("1Y",  price.get("ret_1y")),
    ]
    parts = []
    for label, val in items:
        if val is None:
            continue
        color = "#26a69a" if val >= 0 else "#ef5350"
        sign  = "+" if val >= 0 else ""
        parts.append(
            f'<span style="font-size:0.78em; color:#666; margin-right:4px;">{label}</span>'
            f'<span style="font-size:0.82em; font-weight:600; color:{color}; margin-right:12px;">{sign}{val:.2f}%</span>'
        )
    if not parts:
        return ""
    return '<div style="margin-bottom:10px; display:flex; flex-wrap:wrap; align-items:center;">' + "".join(parts) + "</div>"


# ─────────────────────────────────────────
# Section layout helpers
# ─────────────────────────────────────────
def _section_gap(size: int = 20):
    """Spacing between sections (replaces ---)"""
    st.markdown(f'<div style="margin:{size}px 0; border-top:1px solid #1e1e2a;"></div>', unsafe_allow_html=True)


def _section_header(icon: str, title: str):
    """Section header - consistent style"""
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:8px; margin:20px 0 12px;">'
        f'<span style="font-size:1.1em;">{icon}</span>'
        f'<span style="font-size:1.05em; font-weight:700; color:#e0e0e0; letter-spacing:0.3px;">{title}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────
# Key point cards
# ─────────────────────────────────────────
def _key_point_card_with_image(title: str, analysis: str, importance: str,
                               thumb_url: str, thumb_title: str, thumb_link: str):
    """Render a text card + image in a single flex container (auto height matching)."""
    color_map = {
        "critical": ("#ef4444", "#ef444420", "CRITICAL"),
        "high":     ("#f97316", "#f9731620", "HIGH"),
        "medium":   ("#4C9BE8", "#4C9BE820", "MEDIUM"),
    }
    color, bg, badge = color_map.get(importance, ("#4C9BE8", "#4C9BE820", "MEDIUM"))

    img_block = (
        f'<a href="{thumb_link}" target="_blank" style="text-decoration:none; display:block; '
        f'width:25%; flex-shrink:0; border-radius:0 10px 10px 0; overflow:hidden;">'
        f'<img src="{thumb_url}" style="width:100%; height:100%; object-fit:cover; display:block;">'
        f'</a>'
    ) if thumb_url else ""

    st.markdown(
        f'<div style="display:flex; align-items:stretch; background:{bg}; '
        f'border:1px solid {color}40; border-left:3px solid {color}; '
        f'border-radius:0 10px 10px 0; margin-bottom:10px; overflow:hidden;">'
        f'<div style="flex:1; padding:14px 18px;">'
        f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">'
        f'<span style="background:{color}; color:#fff; font-size:0.65em; font-weight:800; '
        f'padding:2px 7px; border-radius:4px; letter-spacing:1px;">{badge}</span>'
        f'<span style="font-weight:700; font-size:0.97em; color:#e8e8e8;">{title}</span>'
        f'</div>'
        f'<div style="font-size:0.92em; color:#bbb; line-height:1.65;">{analysis}</div>'
        f'</div>'
        f'{img_block}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _key_point_card(title: str, analysis: str, importance: str):
    """AI key point card"""
    color_map = {
        "critical": ("#ef4444", "#ef444420", "CRITICAL"),
        "high":     ("#f97316", "#f9731620", "HIGH"),
        "medium":   ("#4C9BE8", "#4C9BE820", "MEDIUM"),
    }
    color, bg, badge = color_map.get(importance, ("#4C9BE8", "#4C9BE820", "MEDIUM"))
    st.markdown(
        f'<div style="background:{bg}; border:1px solid {color}40; border-left:3px solid {color}; '
        f'border-radius:0 10px 10px 0; padding:14px 18px; margin-bottom:10px;">'
        f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">'
        f'<span style="background:{color}; color:#fff; font-size:0.65em; font-weight:800; '
        f'padding:2px 7px; border-radius:4px; letter-spacing:1px;">{badge}</span>'
        f'<span style="font-weight:700; font-size:0.97em; color:#e8e8e8;">{title}</span>'
        f'</div>'
        f'<div style="font-size:0.92em; color:#bbb; line-height:1.65;">{analysis}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────
# Return metric component
# ─────────────────────────────────────────
def _ret_metric(label: str, val, note: str = ""):
    """Metric replacement component that renders return values in color based on positive/negative intensity."""
    if val is None or (isinstance(val, float) and __import__("math").isnan(val)):
        value_html = '<span style="font-size:1.6em; font-weight:700; color:#888;">–</span>'
    else:
        intensity = min(abs(val) / 15, 1.0)
        if val > 0:
            g = int(120 + 135 * intensity)
            color = f"rgb(40, {g}, 80)"
        elif val < 0:
            r = int(120 + 135 * intensity)
            color = f"rgb({r}, 50, 50)"
        else:
            color = "#888"
        sign = "+" if val > 0 else ""
        value_html = f'<span style="font-size:1.6em; font-weight:700; color:{color};">{sign}{val:.2f}%</span>'
    note_html = f'<div style="font-size:0.75em; color:#666; margin-top:2px;">{note}</div>' if note else ""
    st.markdown(
        f'<div style="padding:4px 0 8px;">'
        f'<div style="font-size:0.82em; color:#aaa; margin-bottom:4px;">{label}</div>'
        f'{value_html}{note_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────
# Color utility
# ─────────────────────────────────────────
def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return ", ".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


# ─────────────────────────────────────────
# News image search utility
# ─────────────────────────────────────────
def find_best_news_image(news_items: list, keywords: str):
    """Search for news thumbnails based on keywords"""
    if not keywords or not news_items:
        return None, None, None

    kw = keywords.lower().split()

    def score(item):
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()
        return sum(1 for k in kw if k in text)

    ranked = sorted(news_items, key=score, reverse=True)
    for item in ranked[:5]:
        if item.get("thumbnail"):
            return item["thumbnail"], item.get("title", ""), item.get("url", "")

    return None, None, None
