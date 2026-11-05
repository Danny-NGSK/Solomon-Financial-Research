"""
Company tab renderer.
"""
import streamlit as st
import plotly.graph_objects as go

from src.ui.common import (
    _section_header, _section_gap,
    _period_pills, _filter_history,
    _ret_metric,
    _key_point_card, _key_point_card_with_image,
    _company_pills,
    find_best_news_image,
)
from src.charts.charts import (
    create_candlestick_chart,
    create_financials_bar,
    create_cashflow_chart,
)


# ─────────────────────────────────────────
# Logo fetcher (cached)
# ─────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_logo_url(website: str) -> str:
    """Try Clearbit → Google Favicon in order, validate in Python, then return."""
    if not website:
        return ""
    try:
        import requests
        from urllib.parse import urlparse
        parsed = urlparse(website)
        domain = (parsed.netloc or parsed.path).replace("www.", "")
        if not domain:
            return ""

        candidates = [
            f"https://logo.clearbit.com/{domain}",
            f"https://www.google.com/s2/favicons?domain={domain}&sz=128",
        ]
        for url in candidates:
            try:
                r = requests.head(url, timeout=3, allow_redirects=True)
                if r.status_code == 200:
                    return url
            except Exception:
                continue
    except Exception:
        pass
    return ""


# ─────────────────────────────────────────
# Formatting helper
# ─────────────────────────────────────────
def _fmt_large(val) -> str:
    if val is None:
        return "–"
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    return f"${val/1e6:.0f}M"


# ─────────────────────────────────────────
# Chart fragment
# ─────────────────────────────────────────
@st.fragment
def _candle_chart_fragment(history, ticker):
    candle_period = _period_pills("candle_period")
    st.plotly_chart(create_candlestick_chart(_filter_history(history, candle_period), ticker), width='stretch')


# ─────────────────────────────────────────
# Tab renderer
# ─────────────────────────────────────────
def render_company_tab(company_data: dict, analysis: dict, industry_data: dict | None = None):
    ticker  = company_data.get("ticker", "")
    company = company_data.get("company_name", ticker)
    sector  = company_data.get("sector", "–")
    industry= company_data.get("industry", "–")
    desc    = company_data.get("description", "")
    price   = company_data.get("price", {})
    val     = company_data.get("valuation", {})
    fin     = company_data.get("financials", {})
    analyst = company_data.get("analyst", {})

    # ── Company header ──
    logo_url = _fetch_logo_url(company_data.get("website", ""))
    if logo_url:
        logo_html = (
            f'<img src="{logo_url}" '
            f'style="width:48px; height:48px; object-fit:contain; border-radius:10px; '
            f'background:#1e1e2a; padding:4px; margin-right:14px; flex-shrink:0;">'
        )
    else:
        initial = ticker[0] if ticker else "?"
        logo_html = (
            f'<div style="width:48px; height:48px; border-radius:10px; background:#2a2a3a; '
            f'display:flex; align-items:center; justify-content:center; '
            f'font-size:1.3em; font-weight:700; color:#888; margin-right:14px; flex-shrink:0;">'
            f'{initial}</div>'
        )
    pills_html = _company_pills(sector, industry, val.get("market_cap"), company_data.get("exchange", ""))

    # Current price + change HTML
    cur_price = price.get("latest")
    ret_1d    = price.get("ret_1d")
    if cur_price is not None:
        price_color = "#26a69a" if (ret_1d or 0) >= 0 else "#ef5350"
        sign        = "+" if (ret_1d or 0) >= 0 else ""
        abs_change  = cur_price * (ret_1d / 100) / (1 + ret_1d / 100) if ret_1d else None
        change_str  = (
            f'<span style="font-size:0.95em; font-weight:600; color:{price_color}; margin-left:10px;">'
            f'{sign}${abs_change:,.2f} ({sign}{ret_1d:.2f}%)</span>'
        ) if abs_change is not None else ""
        price_html = (
            f'<div style="display:flex; align-items:baseline; margin-top:4px; flex-wrap:wrap;">'
            f'<span style="font-size:1.85em; font-weight:800; color:#f0f0f0; letter-spacing:-0.5px;">'
            f'${cur_price:,.2f}</span>'
            f'{change_str}'
            f'</div>'
        )
    else:
        price_html = ""

    st.markdown(
        f'<div style="display:flex; align-items:center; margin-bottom:4px;">'
        f'  {logo_html}'
        f'  <div style="flex:1;">'
        f'    <div style="font-size:1.4em; font-weight:700; color:#e0e0e0;">{company} '
        f'      <span style="font-size:0.7em; color:#888; font-weight:400;">({ticker})</span>'
        f'    </div>'
        f'    {pills_html}'
        f'    {price_html}'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if desc:
        short = desc[:300] + "..." if len(desc) > 300 else desc
        st.markdown(short)
        if len(desc) > 300:
            with st.expander("Show full description"):
                st.write(desc)

    _section_gap(12)

    # ── Price chart (candlestick + MA20/50) ──
    if price.get("history") is not None and not price["history"].empty:
        _candle_chart_fragment(price["history"], ticker)

    # ── Row 1: Price returns ──
    _section_header("📈", "Price Performance")
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, v in [
        (c1, "1D",  price.get("ret_1d")),
        (c2, "1M",  price.get("ret_1m")),
        (c3, "3M",  price.get("ret_3m")),
        (c4, "1Y",  price.get("ret_1y")),
    ]:
        with col:
            _ret_metric(label, v)
    with c5:
        hi  = price.get("week_52_high")
        cur = price.get("latest")
        if hi and cur:
            from_high = (cur / hi - 1) * 100
            _ret_metric("From 52W High", from_high, f"52W High ${hi:,.2f}")
        else:
            _ret_metric("From 52W High", None)

    # 52-week range
    lo, hi, cur = price.get("week_52_low"), price.get("week_52_high"), price.get("latest")
    if lo and hi and cur:
        pct_in_range = (cur - lo) / (hi - lo) * 100
        st.markdown(
            f'<div style="margin:8px 0 4px; font-size:0.85em; color:#aaa;">52-Week Range</div>'
            f'<div style="display:flex; align-items:center; gap:8px; font-size:0.9em;">'
            f'<span style="color:#888;">${lo:,.2f}</span>'
            f'<div style="flex:1; background:#333; border-radius:4px; height:6px; position:relative;">'
            f'<div style="width:{pct_in_range:.0f}%; background:#F59E0B; height:100%; border-radius:4px;"></div>'
            f'</div>'
            f'<span style="color:#888;">${hi:,.2f}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _section_gap()

    # ── Row 2: Valuation ──
    _section_header("💰", "Valuation")
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, v, fmt in [
        (c1, "Market Cap",    val.get("market_cap"),     _fmt_large),
        (c2, "PER (TTM)",    val.get("pe_ratio"),        lambda x: "N/M" if x < 0 else f"{x:.1f}x"),
        (c3, "PER (Forward)",val.get("forward_pe"),      lambda x: "N/M" if x < 0 else f"{x:.1f}x"),
        (c4, "PBR",          val.get("pb_ratio"),        lambda x: f"{x:.2f}x"),
        (c5, "PSR",          val.get("ps_ratio"),        lambda x: f"{x:.2f}x"),
    ]:
        with col:
            st.metric(label, fmt(v) if v is not None else "–")

    # ── Peer valuation comparison ──
    peers = (industry_data or {}).get("peers", [])
    if not peers:
        with st.expander("📊 Peer Valuation Comparison", expanded=False):
            st.info("Couldn't load peer companies for this ticker right now. Try again in a few minutes.")
    if peers:
        import pandas as pd, numpy as np

        VAL_COLS = [
            ("P/E (TTM)",    "pe_ratio",   lambda x: "N/M" if x < 0 else f"{x:.1f}x"),
            ("Forward P/E",  "forward_pe", lambda x: "N/M" if x < 0 else f"{x:.1f}x"),
            ("P/B",          "pb_ratio",   lambda x: f"{x:.2f}x"),
            ("P/S",          "ps_ratio",   lambda x: f"{x:.2f}x"),
            ("Op. Margin",   "op_margin",  lambda x: f"{x*100:.1f}%"),
        ]

        # Target row
        rows = [{
            "Ticker":    ticker,
            "Company":   company,
            "pe_ratio":  val.get("pe_ratio"),
            "forward_pe":val.get("forward_pe"),
            "pb_ratio":  val.get("pb_ratio"),
            "ps_ratio":  val.get("ps_ratio"),
            "op_margin": company_data.get("financials", {}).get("operating_margin"),
            "_is_target": True,
        }]
        for p in peers:
            rows.append({
                "Ticker":     p["ticker"],
                "Company":    p.get("name", p["ticker"]),
                "pe_ratio":   p.get("pe_ratio"),
                "forward_pe": p.get("forward_pe"),
                "pb_ratio":   p.get("pb_ratio"),
                "ps_ratio":   p.get("ps_ratio"),
                "op_margin":  p.get("op_margin"),
                "_is_target": False,
            })

        df_raw = pd.DataFrame(rows).set_index("Ticker")

        # Median row
        numeric_keys = [k for _, k, _ in VAL_COLS]
        peer_only = df_raw[~df_raw["_is_target"].astype(bool)]   # median of peers only, excluding the target
        medians = {k: pd.to_numeric(peer_only[k], errors="coerce").median() for k in numeric_keys}
        median_row = {"Company": "── Peer Median ──", "_is_target": False}
        for k in numeric_keys:
            median_row[k] = medians[k]
        df_raw.loc["(Median)"] = median_row

        # Display df
        display_cols = {lbl: k for lbl, k, _ in VAL_COLS}
        fmt_map      = {lbl: fn for lbl, _, fn in VAL_COLS}
        df_disp = pd.DataFrame(index=df_raw.index)
        df_disp["Company"] = df_raw["Company"]
        for lbl, key, fn in VAL_COLS:
            df_disp[lbl] = df_raw[key].apply(lambda x: fn(x) if pd.notna(x) and x is not None else "–")

        def _val_color(val, col_lbl, idx):
            key = display_cols.get(col_lbl)
            if key is None or idx == "(Median)":
                return ""
            raw_val = df_raw.loc[idx, key]
            med = medians.get(key)
            if pd.isna(raw_val) or raw_val is None or med is None or pd.isna(med):
                return ""
            higher_is_better = (key == "op_margin")
            if higher_is_better:
                is_good = raw_val >= med
            else:
                is_good = raw_val <= med
            return "color: #4ade80; font-weight:600" if is_good else "color: #f87171; font-weight:600"

        def _style_row(row):
            return ["font-weight:900; color:#F59E0B" if row.name == ticker
                    else ("color:#888; font-style:italic" if row.name == "(Median)" else "")
                    for _ in row]

        styled = df_disp.style.apply(_style_row, axis=1)
        for lbl in [l for l, _, _ in VAL_COLS]:
            styled = styled.apply(
                lambda col: [_val_color(col[idx], col.name, idx) for idx in col.index],
                subset=[lbl]
            )

        with st.expander("📊 Peer Valuation Comparison", expanded=True):
            st.caption("Green: below peer median (undervalued or margin advantage) · Red: above median (overvalued or margin disadvantage) · Yellow: target")
            st.dataframe(styled, width='stretch')
            _peer_vals = [p.get(k) for p in peers for k in numeric_keys]
            if all(v is None for v in _peer_vals):
                st.info("Peer valuation data is temporarily unavailable from Yahoo Finance. Try again in a few minutes.")

    # ── Short Interest ──
    si = company_data.get("short_interest", {})
    sf = si.get("short_float")
    sr = si.get("short_ratio")
    if sf is not None or sr is not None:
        _section_gap(12)
        _section_header("🩳", "Short Interest")

        def _si_card(label: str, value_html: str, note: str = "", note_color: str = "#888") -> str:
            return (
                f'<div style="background:#13131a; border:1px solid #22222e; border-radius:10px; padding:14px 16px 12px;">'
                f'<div style="font-size:0.78em; color:#888; margin-bottom:6px;">{label}</div>'
                f'<div style="font-size:1.45em; font-weight:700; color:#e0e0e0;">{value_html}</div>'
                f'{"<div style=" + chr(39) + "font-size:0.75em; color:" + note_color + "; margin-top:4px;" + chr(39) + ">" + note + "</div>" if note else ""}'
                f'</div>'
            )

        if sf >= 20:
            sf_color, sf_note = "#ef5350", "High — squeeze risk"
        elif sf >= 10:
            sf_color, sf_note = "#ffc107", "Elevated"
        else:
            sf_color, sf_note = "#26a69a", "Normal"

        si_c1, si_c2, si_c3 = st.columns(3)
        with si_c1:
            if sf is not None:
                st.markdown(
                    f'<div style="background:#13131a; border:1px solid #22222e; border-radius:10px; padding:14px 16px 12px;">'
                    f'<div style="font-size:0.78em; color:#888; margin-bottom:6px;">Short Float %</div>'
                    f'<div style="font-size:1.45em; font-weight:700; color:{sf_color};">{sf:.2f}%</div>'
                    f'<div style="font-size:0.75em; color:{sf_color}; margin-top:4px;">{sf_note}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with si_c2:
            if sr is not None:
                st.markdown(
                    f'<div style="background:#13131a; border:1px solid #22222e; border-radius:10px; padding:14px 16px 12px;">'
                    f'<div style="font-size:0.78em; color:#888; margin-bottom:6px;">Days to Cover</div>'
                    f'<div style="font-size:1.45em; font-weight:700; color:#e0e0e0;">{sr:.1f}</div>'
                    f'<div style="font-size:0.75em; color:#555; margin-top:4px;">days at avg daily volume</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with si_c3:
            as_of = si.get("as_of", "")
            st.markdown(
                f'<div style="background:#13131a; border:1px solid #22222e; border-radius:10px; padding:14px 16px 12px;">'
                f'<div style="font-size:0.78em; color:#888; margin-bottom:6px;">Data As Of</div>'
                f'<div style="font-size:1.45em; font-weight:700; color:#e0e0e0;">{as_of if as_of else "–"}</div>'
                f'<div style="font-size:0.75em; color:#555; margin-top:4px;">Short interest report date</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    _section_gap()

    # ── Row 3: Financial metrics ──
    quarterly_for_date = company_data.get("quarterly", {})
    ttm_date_note = ""
    if quarterly_for_date.get("quarters"):
        ttm_date_note = f" · Latest quarter: {quarterly_for_date['quarters'][-1]}"
    _section_header("📊", f"Financials (TTM{ttm_date_note})")
    c1, c2, c3, c4 = st.columns(4)
    for col, label, v, fmt in [
        (c1, "Revenue",       fin.get("revenue_ttm"),         _fmt_large),
        (c2, "Rev. Growth",   fin.get("revenue_growth_yoy"),  lambda x: f"{x*100:+.1f}%"),
        (c3, "Op. Margin",    fin.get("operating_margin"),    lambda x: f"{x*100:.2f}%" if abs(x * 100) < 1 else f"{x*100:.1f}%"),
        (c4, "Net Margin",    fin.get("net_margin"),          lambda x: f"{x*100:.2f}%" if abs(x * 100) < 1 else f"{x*100:.1f}%"),
    ]:
        with col:
            st.metric(label, fmt(v) if v is not None else "–")

    # EPS Growth fallback: calculate from quarterly data if yfinance omits it
    eps_growth = fin.get("earnings_growth_yoy")
    if eps_growth is None:
        eps_surp = company_data.get("eps_surprise", [])
        if len(eps_surp) >= 2:
            latest_act = eps_surp[0].get("actual")
            prev_act   = eps_surp[-1].get("actual")
            if latest_act is not None and prev_act is not None and prev_act != 0:
                eps_growth = round((latest_act - prev_act) / abs(prev_act), 4)

    c1, c2, c3, c4 = st.columns(4)
    for col, label, v, fmt in [
        (c1, "EPS",           fin.get("eps_ttm"),             lambda x: f"${x:.2f}"),
        (c2, "EPS Growth",    eps_growth,                     lambda x: f"{x*100:+.1f}%"),
        (c3, "ROE",           fin.get("roe"),                 lambda x: f"{x*100:.1f}%"),
        (c4, "Debt/Equity",   fin.get("debt_to_equity"),      lambda x: f"{x:.2f}"),
    ]:
        with col:
            st.metric(label, fmt(v) if v is not None else "–")

    _section_gap()

    # ── Row 4: Analyst consensus ──
    if any(analyst.get(k) for k in ["recommendation", "target_price", "num_analysts"]):
        _section_header("🎯", "Analyst Consensus")
        st.caption("Source: Yahoo Finance · Price target is the **mean** 12-month target from covering analysts")

        ratings = analyst.get("ratings", {})
        has_ratings = any(ratings.get(k, 0) > 0 for k in ["strongBuy", "buy", "hold", "sell", "strongSell"])

        # Pre-calculate ratings total outside columns → keeps donut center number and Coverage metric in sync
        _keys_order = ["strongBuy", "buy", "hold", "sell", "strongSell"]
        _ratings_total = sum(ratings.get(k, 0) for k in _keys_order)

        col_donut, col_targets = st.columns([1, 1])

        with col_donut:
            if has_ratings:
                labels = ["Strong Buy", "Buy",    "Hold",    "Sell",    "Strong Sell"]
                keys   = ["strongBuy",  "buy",    "hold",    "sell",    "strongSell"]
                colors = ["#26a69a",    "#66bb6a", "#ffc107", "#ff7043", "#ef5350"]
                values = [ratings.get(k, 0) for k in keys]
                total  = _ratings_total

                rec = analyst.get("recommendation", "–").upper()
                rec_color = {"STRONG BUY": "#26a69a", "BUY": "#66bb6a",
                             "HOLD": "#ffc107", "UNDERPERFORM": "#ff7043", "SELL": "#ef5350"}.get(rec, "#aaa")

                donut = go.Figure(go.Pie(
                    labels=labels, values=values,
                    hole=0.62,
                    marker=dict(colors=colors, line=dict(color="#0e0e16", width=2)),
                    textinfo="label+value",
                    textposition="inside",
                    insidetextfont=dict(size=11, color="#111111"),
                    insidetextorientation="horizontal",
                    hovertemplate="%{label}: %{value} analysts<extra></extra>",
                    direction="clockwise",
                    sort=False,
                    automargin=False,
                ))
                donut.update_layout(
                    height=240,
                    margin=dict(l=0, r=0, t=0, b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    uniformtext=dict(minsize=11, mode="hide"),
                    annotations=[dict(
                        text=f'<b>{rec}</b><br><span style="font-size:11px; color:#888;">{total} analysts</span>',
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=13, color=rec_color),
                        xref="paper", yref="paper",
                    )],
                )
                st.plotly_chart(donut, width='stretch', key="analyst_donut")
            else:
                rec = analyst.get("recommendation", "–").upper()
                rec_color = {"STRONG BUY": "#26a69a", "BUY": "#66bb6a",
                             "HOLD": "#ffc107", "UNDERPERFORM": "#ff7043", "SELL": "#ef5350"}.get(rec, "#aaa")
                st.markdown(
                    f'<div style="text-align:center; padding:40px 12px;">'
                    f'<div style="font-size:0.8em; color:#aaa; margin-bottom:6px;">Recommendation</div>'
                    f'<div style="font-size:2em; font-weight:800; color:{rec_color};">{rec}</div>'
                    f'</div>', unsafe_allow_html=True,
                )

        with col_targets:
            tp   = analyst.get("target_price")
            up   = analyst.get("upside_pct")
            t_lo = analyst.get("target_low")
            t_hi = analyst.get("target_high")
            t_med = analyst.get("target_median")
            n    = analyst.get("num_analysts")
            st.metric("Price Target (Mean)", f"${tp:,.2f}" if tp else "–",
                      f"{up:+.1f}% upside" if up is not None else None)
            if t_lo and t_hi:
                c_lo, c_hi = st.columns(2)
                with c_lo:
                    st.metric("Target Low", f"${t_lo:,.2f}")
                with c_hi:
                    st.metric("Target High", f"${t_hi:,.2f}")
            n_display = _ratings_total if has_ratings and _ratings_total > 0 else n
            c_cov, c_med = st.columns(2)
            with c_cov:
                st.metric("Coverage", f"{n_display} analysts" if n_display else "–")
            with c_med:
                st.metric("Target Median", f"${t_med:,.2f}" if t_med else "–")

        _section_gap()

    # ── Quarterly financials chart ──
    quarterly    = company_data.get("quarterly", {})
    cashflow     = company_data.get("cashflow", {})
    eps_surprise = company_data.get("eps_surprise", [])

    if quarterly.get("quarters") or cashflow.get("years") or eps_surprise:
        _section_header("📉", "Financials")
        tab_earn, tab_eps, tab_cf = st.tabs(["📊 Quarterly Earnings", "🎯 EPS Surprise", "💵 Cash Flow"])

        with tab_earn:
            if quarterly.get("quarters"):
                st.plotly_chart(create_financials_bar(quarterly), width='stretch', key="financials_bar")
            else:
                st.caption("No quarterly data available.")

        with tab_eps:
            if eps_surprise:
                st.caption("Actual EPS vs. analyst estimate · Beat = green · Miss = red")
                cols_eps = st.columns(len(eps_surprise))
                for col_e, q in zip(cols_eps, eps_surprise):
                    surp = q.get("surprise_pct")
                    act  = q.get("actual")
                    est  = q.get("estimate")
                    if surp is not None:
                        beat    = surp >= 0
                        s_color = "#26a69a" if beat else "#ef5350"
                        s_label = f"+{surp:.1f}% BEAT" if beat else f"{surp:.1f}% MISS"
                    else:
                        s_color = "#888"
                        s_label = "N/A"
                    est_html = f"Est. ${est:.2f}" if est is not None else "Est. –"
                    with col_e:
                        st.markdown(
                            f'<div style="background:#13131a; border:1px solid #22222e; '
                            f'border-top:3px solid {s_color}; border-radius:10px; '
                            f'padding:14px 12px; text-align:center;">'
                            f'<div style="font-size:0.72em; color:#666; margin-bottom:8px; '
                            f'letter-spacing:0.5px;">{q["date"]}</div>'
                            f'<div style="font-size:1.4em; font-weight:800; color:#f0f0f0; '
                            f'margin-bottom:6px;">${act:.2f}</div>'
                            f'<div style="font-size:0.78em; color:#666; margin-bottom:8px;">{est_html}</div>'
                            f'<div style="font-size:0.82em; font-weight:700; color:{s_color};">{s_label}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
            else:
                st.caption("No EPS surprise data available.")

        with tab_cf:
            if cashflow.get("years"):
                st.plotly_chart(create_cashflow_chart(cashflow), width='stretch', key="cashflow_bar")
            else:
                st.caption("No cash flow data available.")
        _section_gap()

    # ── AI analysis: investment stance badge + summary ──
    stance = analysis.get("investment_stance", "neutral")
    stance_style = {
        "bullish": ("🟢", "#28a745", "BULLISH"),
        "neutral": ("🟡", "#ffc107", "NEUTRAL"),
        "bearish": ("🔴", "#dc3545", "BEARISH"),
    }
    icon, color, label = stance_style.get(stance, ("🟡", "#ffc107", "NEUTRAL"))
    st.markdown(
        f'<div style="background:{color}18; border:1px solid {color}40; border-left:3px solid {color}; '
        f'border-radius:0 10px 10px 0; padding:12px 18px; margin-bottom:16px;">'
        f'<span style="background:{color}; color:#000; font-size:0.7em; font-weight:800; '
        f'padding:2px 8px; border-radius:4px; letter-spacing:1px; margin-right:8px;">{label}</span>'
        f'<strong style="color:#e0e0e0;">AI Investment Stance</strong><br>'
        f'<span style="font-size:0.92em; color:#bbb; line-height:1.65;">{analysis.get("company_summary", "")}</span>'
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
                company_data.get("news", []), keywords
            )
            _key_point_card_with_image(point["title"], point["analysis"], importance,
                                       thumb_url or "", thumb_title or "", thumb_link or "")
        else:
            _key_point_card(point["title"], point["analysis"], importance)
