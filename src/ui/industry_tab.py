"""
Industry tab renderer.
"""
import streamlit as st

from src.ui.common import (
    _section_header, _section_gap,
    _period_pills, _filter_history,
    _ret_metric,
    _key_point_card, _key_point_card_with_image,
    find_best_news_image,
)
from src.charts.charts import create_peer_bar_chart, create_sector_etf_chart


# ─────────────────────────────────────────
# Chart fragment
# ─────────────────────────────────────────
@st.fragment
def _etf_chart_fragment(etf):
    etf_period = _period_pills("etf_period")
    st.plotly_chart(create_sector_etf_chart(_filter_history(etf["history"], etf_period), etf.get("name", "")), width='stretch')


# ─────────────────────────────────────────
# Tab renderer
# ─────────────────────────────────────────
def render_industry_tab(industry_data: dict, analysis: dict):
    ticker   = industry_data.get("ticker", "")
    company  = industry_data.get("company_name", ticker)
    sector   = industry_data.get("sector", "–")
    industry = industry_data.get("industry", "–")
    etf      = industry_data.get("sector_etf", {})
    target   = industry_data.get("target", {})
    peers    = industry_data.get("peers", [])

    # ── Sector ETF chart ──
    if etf.get("history") is not None and not etf["history"].empty:
        _etf_chart_fragment(etf)

    # ── Row 1: Sector basic info ──
    _section_header("🏭", "Sector Info")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Sector", sector)
    with c2:
        st.metric("Industry", industry)
    with c3:
        etf_ret1m = etf.get("ret_1m")
        st.metric(
            f"Sector ETF ({etf.get('ticker', '–')})",
            f"${etf.get('latest_price', '–'):,.2f}" if etf.get("latest_price") else "–",
            f"{etf_ret1m:+.2f}% (1M)" if etf_ret1m is not None else None,
        )

    _section_gap()

    # ── Row 2: Target stock vs sector performance ──
    _section_header("📊", f"{ticker} vs Sector Performance")
    c1, c2, c3, c4 = st.columns(4)
    for col, label, val in [
        (c1, f"{ticker} 1D",      target.get("ret_1d")),
        (c2, f"{ticker} 1M",      target.get("ret_1m")),
        (c3, f"Sector ETF 1D",    etf.get("ret_1d")),
        (c4, f"Sector ETF 1M",    etf.get("ret_1m")),
    ]:
        with col:
            _ret_metric(label, val)

    _section_gap()

    # ── Row 3: Peer comparison ──
    if peers:
        _section_header("🔄", "Peer Comparison")
        c_chart, c_table = st.columns([3, 2])
        with c_chart:
            st.plotly_chart(create_peer_bar_chart(target, peers, ticker), width='stretch', key="peer_bar_main")
        with c_table:
            st.markdown("**Returns**")
            import pandas as pd

            ret_cols = ["1D", "1M", "3M"]
            rows = [{"Ticker": ticker, "Company": company,
                     "Price": f"${target['latest_price']:,.2f}" if target.get("latest_price") else "–",
                     "1D": target.get("ret_1d"),
                     "1M": target.get("ret_1m"),
                     "3M": target.get("ret_3m")}] + [
                    {"Ticker": p["ticker"], "Company": p.get("name", ""),
                     "Price": f"${p['latest_price']:,.2f}" if p.get("latest_price") else "–",
                     "1D": p.get("ret_1d"),
                     "1M": p.get("ret_1m"),
                     "3M": p.get("ret_3m")}
                    for p in peers]
            df_peers = pd.DataFrame(rows).set_index("Ticker")

            def _ret_color(val):
                if not isinstance(val, (int, float)) or pd.isna(val):
                    return ""
                intensity = min(abs(val) / 15, 1.0)
                if val > 0:
                    g = int(120 + 135 * intensity)
                    return f"color: rgb(40, {g}, 80); font-weight: 600"
                elif val < 0:
                    r = int(120 + 135 * intensity)
                    return f"color: rgb({r}, 50, 50); font-weight: 600"
                return ""

            styled = (df_peers.style
                .format({c: (lambda x: f"{x:+.2f}%" if isinstance(x, float) and not pd.isna(x) else "–")
                         for c in ret_cols})
                .map(_ret_color, subset=ret_cols))
            st.dataframe(styled, width='stretch')
        _section_gap()

    # ── AI analysis: momentum badge + summary ──
    momentum = analysis.get("momentum", "neutral")
    momentum_style = {
        "bullish": ("🟢", "#28a745", "BULLISH"),
        "neutral": ("🟡", "#ffc107", "NEUTRAL"),
        "bearish": ("🔴", "#dc3545", "BEARISH"),
    }
    icon, color, label = momentum_style.get(momentum, ("🟡", "#ffc107", "NEUTRAL"))
    st.markdown(
        f'<div style="background:{color}18; border:1px solid {color}40; border-left:3px solid {color}; '
        f'border-radius:0 10px 10px 0; padding:12px 18px; margin-bottom:16px;">'
        f'<span style="background:{color}; color:#000; font-size:0.7em; font-weight:800; '
        f'padding:2px 8px; border-radius:4px; letter-spacing:1px; margin-right:8px;">{label.upper()}</span>'
        f'<strong style="color:#e0e0e0;">Industry Momentum</strong><br>'
        f'<span style="font-size:0.92em; color:#bbb; line-height:1.65;">{analysis.get("industry_summary", "")}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── AI key points ──
    _section_header("🔍", "Key Points")
    for point in analysis.get("key_points", []):
        importance = point.get("importance", "medium")
        viz_type   = point.get("viz_type", "none")

        if viz_type == "image":
            keywords = point.get("image_keywords", "")
            thumb_url, thumb_title, thumb_link = find_best_news_image(
                industry_data.get("news", []), keywords
            )
            _key_point_card_with_image(point["title"], point["analysis"], importance,
                                       thumb_url or "", thumb_title or "", thumb_link or "")
        else:
            _key_point_card(point["title"], point["analysis"], importance)
