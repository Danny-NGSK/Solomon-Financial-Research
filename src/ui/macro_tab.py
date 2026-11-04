"""
Macro (Market Overview) tab renderer.
"""
import streamlit as st
import plotly.graph_objects as go

from src.ui.common import (
    _section_header, _section_gap,
    _period_pills, _filter_history,
    _key_point_card, _key_point_card_with_image,
    _hex_to_rgb, find_best_news_image,
)
from src.charts.charts import (
    create_spy_chart, create_fear_greed_gauge, create_macro_chart,
    create_sector_treemap, create_sector_heatmap,
)


# ─────────────────────────────────────────
# Fear & Greed helpers
# ─────────────────────────────────────────
def _fg_color(score: int) -> str:
    if score <= 25:   return "#dc3545"   # Extreme Fear → red
    if score <= 45:   return "#fd7e14"   # Fear → orange
    if score <= 55:   return "#ffc107"   # Neutral → yellow
    if score <= 75:   return "#20c997"   # Greed → teal
    return "#28a745"                     # Extreme Greed → green


def _fg_label_kr(rating: str) -> str:
    mapping = {
        "extreme fear": "Extreme Fear",
        "fear": "Fear",
        "neutral": "Neutral",
        "greed": "Greed",
        "extreme greed": "Extreme Greed",
    }
    return mapping.get(rating.lower(), rating.title())


# ─────────────────────────────────────────
# Chart fragments (avoid re-render on interaction)
# ─────────────────────────────────────────
@st.fragment
def _spy_chart_fragment(spy):
    spy_period = _period_pills("spy_period")
    st.plotly_chart(create_spy_chart(_filter_history(spy["history"], spy_period)), width='stretch')


# ─────────────────────────────────────────
# Tab renderer
# ─────────────────────────────────────────
def render_macro_tab(market_data: dict, analysis: dict):
    spy    = market_data.get("spy", {})
    nasdaq = market_data.get("nasdaq", {})
    dow    = market_data.get("dow", {})
    macro  = market_data.get("macro", {})
    vix    = market_data.get("vix")
    fg     = market_data.get("fear_greed")

    # ── SPY chart (top full width) ──
    if spy.get("history") is not None and not spy["history"].empty:
        _spy_chart_fragment(spy)

    # ── Row 1: Major Indices ──
    _section_header("📈", "Major Indices")

    def _sparkline(history, color: str) -> go.Figure:
        """1-month sparkline (compact, no axes or labels)"""
        if history is None or history.empty:
            return None
        close = history["Close"].dropna().iloc[-21:]
        if len(close) < 2:
            return None
        y_min = float(close.min())
        y_max = float(close.max())
        pad   = (y_max - y_min) * 0.02 or y_max * 0.005
        # Minimize padding to 2% → data variation occupies 96% of chart height, making fluctuations clearly visible
        # fill="tozeroy" + yaxis range starting near y_min means
        # y=0 is off screen below, so the entire area under the line is filled → clean sparkline
        fig = go.Figure(go.Scatter(
            x=list(range(len(close))), y=close.values,
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=f"rgba({_hex_to_rgb(color)}, 0.15)",
        ))
        fig.update_layout(
            height=68, margin=dict(l=0, r=0, t=2, b=2),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False, range=[y_min - pad, y_max + pad]),
        )
        return fig

    c1, c2, c3 = st.columns(3)
    for col, label, data, spark_color in [
        (c1, "S&P 500",   spy,    "#00CC96"),
        (c2, "NASDAQ",    nasdaq, "#4C9BE8"),
        (c3, "Dow Jones", dow,    "#F59E0B"),
    ]:
        with col:
            if data:
                price_val = data.get("latest_price", "-")
                d1    = data.get("ret_1d")
                d1m   = data.get("ret_1m")
                delta_str = f"{d1:+.2f}% (1D)" if d1 is not None else ""
                st.metric(label, f"{price_val:,.2f}", delta_str)
                if d1m is not None:
                    st.caption(f"1M: {d1m:+.2f}%")
                hist = data.get("history")
                if hist is not None and not hist.empty:
                    spark = _sparkline(hist, spark_color)
                    if spark:
                        st.plotly_chart(spark, width='stretch', key=f"spark_{label.replace(' ','_')}", config={"displayModeBar": False})
            else:
                st.metric(label, "–")

    _section_gap()

    # ── Row 2: Market Sentiment ──
    _section_header("😨", "Market Sentiment")
    c1, c2 = st.columns([1, 2])

    with c1:
        vix_val = vix if vix else 0
        if vix_val <= 15:   vix_label, vix_color = "Stable", "#28a745"
        elif vix_val <= 20: vix_label, vix_color = "Caution", "#ffc107"
        elif vix_val <= 30: vix_label, vix_color = "Fear", "#fd7e14"
        else:               vix_label, vix_color = "Extreme Fear", "#dc3545"

        st.markdown(
            f'<div style="padding:16px 12px;">'
            f'<div style="font-size:0.85em; color:#aaa; margin-bottom:4px;">VIX (Volatility Index)</div>'
            f'<div style="font-size:2.4em; font-weight:bold; color:{vix_color};">{vix_val}</div>'
            f'<div style="font-size:0.9em; color:{vix_color}; margin-top:4px;">{vix_label}</div>'
            f'<div style="font-size:0.75em; color:#666; margin-top:8px;">≤15 Stable · ≤20 Caution · ≤30 Fear · 30+ Extreme Fear</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with c2:
        if fg:
            gauge_fig = create_fear_greed_gauge(fg["score"], fg["rating"], fg.get("source", "vix_proxy"))
            st.plotly_chart(gauge_fig, width='stretch')
        else:
            st.metric("Fear & Greed", "–")

    _section_gap()

    # ── Row 3: Interest Rates ──
    def _fmt_as_of(as_of_str: str) -> str:
        """'2024-03-01' -> 'Mar 2024'"""
        try:
            from datetime import datetime as _dt
            return _dt.strptime(as_of_str[:10], "%Y-%m-%d").strftime("%b %Y")
        except Exception:
            return as_of_str[:7] if as_of_str else ""

    _section_header("💰", "Interest Rates")
    rate_ids = ["FEDFUNDS", "DGS2", "DGS5", "DGS10"]
    cols = st.columns(len(rate_ids) + 1)
    for col, sid in zip(cols, rate_ids):
        with col:
            d = macro.get(sid)
            if d:
                delta = f"{d['change_1y']:+.2f} pp" if d.get("change_1y") is not None else None
                st.metric(d["name"], f"{d['latest']:.2f}%", delta)
                # Guard against edge case where as_of is missing — always attempt to display
                as_of_raw = d.get("as_of") or ""
                if as_of_raw:
                    st.caption(f"As of {_fmt_as_of(as_of_raw)}")
                else:
                    st.caption("As of (unavailable)")
            else:
                st.metric(sid, "–")

    # 10Y-2Y spread
    with cols[-1]:
        d10 = macro.get("DGS10")
        d2  = macro.get("DGS2")
        if d10 and d2:
            spread = round(d10["latest"] - d2["latest"], 2)
            spread_str = f"{spread:+.2f}%"
            if spread < 0:
                spread_label = "⚠️ Inverted"
                spread_color = "#ef5350"
            elif spread < 0.5:
                spread_label = "Flat"
                spread_color = "#ffc107"
            else:
                spread_label = "Normal"
                spread_color = "#26a69a"
            st.markdown(
                f'<div style="background:#13131a; border:1px solid #22222e; border-radius:10px; padding:14px 16px 12px;">'
                f'<div style="font-size:0.78em; color:#888; margin-bottom:4px;">10Y–2Y Spread</div>'
                f'<div style="font-size:1.45em; font-weight:700; color:{spread_color};">{spread_str}</div>'
                f'<div style="font-size:0.78em; color:{spread_color}; margin-top:4px;">{spread_label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.metric("10Y–2Y Spread", "–")

    _section_gap()

    # ── Row 4: Economic Indicators ──
    _section_header("📊", "Economic Indicators")
    c1, c2 = st.columns(2)
    for col, sid in [(c1, "CPIAUCSL"), (c2, "UNRATE")]:
        with col:
            d = macro.get(sid)
            if d:
                delta = f"{d['change_1y']:+.2f}{d['unit']}" if d.get("change_1y") is not None else None
                st.metric(d["name"], f"{d['latest']}{d['unit']}", delta)
                if d.get("as_of"):
                    st.caption(f"As of {_fmt_as_of(d['as_of'])} · FRED data may lag 1–2 months")
            else:
                st.metric(sid, "–")

    _section_gap()

    # ── Sector heatmap ──
    sector_returns = market_data.get("sector_returns", {})
    if sector_returns:
        _section_header("🗺️", "Sector Map")

        @st.fragment
        def _sector_map_fragment(sr: dict):
            period = st.pills(
                "Period", ["1D", "1W", "1M"], default="1D",
                key="sector_map_period", label_visibility="collapsed",
            )
            tab_tree, tab_heat = st.tabs(["🟩 Treemap", "🔲 Heatmap"])
            with tab_tree:
                st.plotly_chart(create_sector_treemap(sr, period), width='stretch', key="sector_treemap")
            with tab_heat:
                st.plotly_chart(create_sector_heatmap(sr), width='stretch', key="sector_heatmap")

        _sector_map_fragment(sector_returns)
        _section_gap()

    # ── AI analysis: risk badge + summary ──
    risk = analysis.get("risk_level", "medium")
    risk_style = {
        "low":     ("🟢", "#28a745"),
        "medium":  ("🟡", "#ffc107"),
        "high":    ("🔴", "#dc3545"),
        "extreme": ("⛔", "#6f42c1"),
    }
    icon, color = risk_style.get(risk, ("🟡", "#ffc107"))
    st.markdown(
        f'<div style="background:{color}18; border:1px solid {color}40; border-left:3px solid {color}; '
        f'border-radius:0 10px 10px 0; padding:12px 18px; margin-bottom:16px;">'
        f'<span style="background:{color}; color:#000; font-size:0.7em; font-weight:800; '
        f'padding:2px 8px; border-radius:4px; letter-spacing:1px; margin-right:8px;">{risk.upper()}</span>'
        f'<strong style="color:#e0e0e0;">Market Risk</strong><br>'
        f'<span style="font-size:0.92em; color:#bbb; line-height:1.65;">{analysis.get("market_summary", "")}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── AI key points ──
    _section_header("🔍", "Key Points")
    for i, point in enumerate(analysis.get("key_points", [])):
        importance = point.get("importance", "medium")
        viz_type   = point.get("viz_type", "none")

        if viz_type == "chart":
            sid = point.get("chart_series_id")
            if sid and sid in macro:
                col_text, col_viz = st.columns([3, 2], vertical_alignment="top")
                with col_text:
                    _key_point_card(point["title"], point["analysis"], importance)
                with col_viz:
                    st.plotly_chart(create_macro_chart(macro[sid]), width='stretch', key=f"macro_chart_{sid}_{i}")
            else:
                _key_point_card(point["title"], point["analysis"], importance)
        elif viz_type == "image":
            keywords = point.get("image_keywords", "")
            thumb_url, thumb_title, thumb_link = find_best_news_image(
                market_data.get("news", []), keywords
            )
            _key_point_card_with_image(point["title"], point["analysis"], importance,
                                       thumb_url or "", thumb_title or "", thumb_link or "")
        else:
            _key_point_card(point["title"], point["analysis"], importance)
