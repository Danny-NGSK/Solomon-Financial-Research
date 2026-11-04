import math
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return ", ".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def _line_chart(x, y, color: str, title: str, unit: str = "", height: int = 260) -> go.Figure:
    import pandas as pd
    y_clean = pd.Series(y).dropna()
    if not y_clean.empty:
        y_min, y_max = float(y_clean.min()), float(y_clean.max())
        padding = (y_max - y_min) * 0.05 or y_max * 0.01
        y_range = [y_min - padding, y_max + padding]
    else:
        y_range = None

    # Remove weekends + holidays only for daily (trading day) data — keep monthly/weekly data as-is
    x_idx = pd.DatetimeIndex(x)
    _rangebreaks = []
    if len(x_idx) >= 2:
        median_gap = pd.Series(x_idx).diff().dropna().median()
        if median_gap.days <= 4:  # daily trading data
            _rangebreaks = [dict(bounds=["sat", "mon"])]
            # Auto-detect weekday trading holidays (Christmas, Thanksgiving, etc.)
            all_bdays = pd.bdate_range(x_idx.min(), x_idx.max())
            missing = all_bdays.difference(x_idx.normalize())
            if len(missing) > 0:
                _rangebreaks.append(dict(values=missing.strftime("%Y-%m-%d").tolist()))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y,
        mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=f"rgba({_hex_to_rgb(color)}, 0.08)",
        hovertemplate=f"%{{x|%Y-%m-%d}}<br>{title}: %{{y:.2f}}{unit}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=12)),
        yaxis_title=unit or None,
        height=height,
        margin=dict(l=8, r=8, t=30, b=8),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, type="date", rangebreaks=_rangebreaks),
        yaxis=dict(gridcolor="rgba(200,200,200,0.15)", range=y_range),
    )
    return fig


def create_spy_chart(history) -> go.Figure:
    return _line_chart(history.index, history["Close"], "#00CC96", "S&P 500 (SPY)", "$", height=260)


def create_fear_greed_gauge(score: int, rating: str, source: str = "cnn") -> go.Figure:
    """CNN-style Fear & Greed semicircle gauge"""
    zone_colors = ["#d63031", "#e17055", "#f5c518", "#55efc4", "#00b894"]
    zone_ranges = [(0, 25), (25, 45), (45, 55), (55, 75), (75, 100)]
    zone_labels = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]

    def score_color(s):
        if s < 25:  return zone_colors[0]
        if s < 45:  return zone_colors[1]
        if s < 55:  return zone_colors[2]
        if s < 75:  return zone_colors[3]
        return zone_colors[4]

    needle_color = score_color(score)
    source_note  = "" if source == "cnn" else "<br><span style='font-size:10px;color:#555'>(VIX proxy)</span>"

    # Zone label positions (angle-based x,y)
    label_annotations = []
    label_map = {12.5: "Extreme\nFear", 35: "Fear", 50: "Neutral", 65: "Greed", 87.5: "Extreme\nGreed"}
    for mid, lbl in label_map.items():
        angle = math.pi * (1 - mid / 100)
        r = 0.82
        cx, cy = 0.5 + r * 0.5 * math.cos(angle), 0.18 + r * 0.5 * math.sin(angle)
        label_annotations.append(dict(
            text=lbl.replace("\n", "<br>"),
            x=cx, y=cy, showarrow=False,
            xref="paper", yref="paper",
            font=dict(size=9, color="#666"),
            align="center",
        ))

    fig = go.Figure(go.Indicator(
        mode="gauge",
        value=score,
        domain={"x": [0.05, 0.95], "y": [0.15, 1.0]},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickvals": [0, 25, 45, 55, 75, 100],
                "ticktext": ["0", "25", "45", "55", "75", "100"],
                "tickwidth": 1,
                "tickcolor": "#444",
                "tickfont": {"size": 9, "color": "#555"},
            },
            "bar": {"color": needle_color, "thickness": 0.06},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": r, "color": f"rgba({int(c[1:3],16)},{int(c[3:5],16)},{int(c[5:7],16)},0.28)"}
                for r, c in zip(zone_ranges, zone_colors)
            ],
            "threshold": {
                "line": {"color": needle_color, "width": 5},
                "thickness": 0.9,
                "value": score,
            },
        },
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=16, r=16, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#ccc"},
        annotations=[
            # Large score number
            dict(
                text=f'<b>{score}</b>',
                x=0.5, y=0.28, showarrow=False,
                xref="paper", yref="paper",
                font=dict(size=52, color=needle_color),
            ),
            # Status label
            dict(
                text=f'<b>{rating.upper()}</b>{source_note}',
                x=0.5, y=0.10, showarrow=False,
                xref="paper", yref="paper",
                font=dict(size=15, color=needle_color),
            ),
            # Bottom title
            dict(
                text="Fear & Greed Index",
                x=0.5, y=-0.04, showarrow=False,
                xref="paper", yref="paper",
                font=dict(size=10, color="#444"),
            ),
        ],
    )
    return fig


def create_macro_chart(series_data: dict) -> go.Figure:
    return _line_chart(
        series_data["series"].index,
        series_data["series"].values,
        "#4C9BE8",
        series_data["name"],
        series_data["unit"],
        height=220,
    )


def create_peer_bar_chart(target: dict, peers: list, ticker: str) -> go.Figure:
    """Horizontal bar chart for 1-month peer returns"""
    all_data = [{"ticker": ticker, "ret_1m": target.get("ret_1m")}] + [
        {"ticker": p["ticker"], "ret_1m": p.get("ret_1m")} for p in peers
    ]
    all_data = [d for d in all_data if d["ret_1m"] is not None]
    all_data.sort(key=lambda x: x["ret_1m"])

    labels = [d["ticker"] for d in all_data]
    values = [d["ret_1m"] for d in all_data]
    colors = [
        "#00CC96" if v >= 0 else "#EF553B"
        for v in values
    ]
    # Highlight the target ticker
    bar_colors = [
        "#FFD700" if l == ticker else c
        for l, c in zip(labels, colors)
    ]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=bar_colors,
        text=[f"{v:+.1f}%" for v in values],
        textposition="outside",
        hovertemplate="%{y}: %{x:+.2f}%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="1-Month Return Comparison", font=dict(size=12)),
        height=max(200, len(all_data) * 40 + 60),
        margin=dict(l=8, r=60, t=30, b=8),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(200,200,200,0.15)", zeroline=True, zerolinecolor="#555"),
        yaxis=dict(showgrid=False),
    )
    return fig


def create_sector_etf_chart(history, etf_name: str) -> go.Figure:
    return _line_chart(history.index, history["Close"], "#818CF8", etf_name, "$", height=260)


def create_candlestick_chart(history, ticker: str) -> go.Figure:
    """Candlestick + MA20/50 + Volume"""
    ma20  = history["Close"].rolling(20).mean()
    ma50  = history["Close"].rolling(50).mean()
    ma200 = history["Close"].rolling(200).mean()

    vol_colors = [
        "#26a69a" if c >= o else "#ef5350"
        for c, o in zip(history["Close"], history["Open"])
    ]

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
    )

    # ── Candlestick ──
    fig.add_trace(go.Candlestick(
        x=history.index,
        open=history["Open"], high=history["High"],
        low=history["Low"],  close=history["Close"],
        name=ticker,
        increasing_line_color="#26a69a", increasing_fillcolor="#26a69a",
        decreasing_line_color="#ef5350", decreasing_fillcolor="#ef5350",
    ), row=1, col=1)

    # Show moving averages only when data is sufficient (handles cases shortened by period filter)
    if len(history) >= 20:
        fig.add_trace(go.Scatter(
            x=history.index, y=ma20, name="MA20",
            line=dict(color="#FFA726", width=1.5),
            hovertemplate="MA20: %{y:.2f}<extra></extra>",
        ), row=1, col=1)

    if len(history) >= 50:
        fig.add_trace(go.Scatter(
            x=history.index, y=ma50, name="MA50",
            line=dict(color="#AB47BC", width=1.5),
            hovertemplate="MA50: %{y:.2f}<extra></extra>",
        ), row=1, col=1)

    if len(history) >= 200:
        fig.add_trace(go.Scatter(
            x=history.index, y=ma200, name="MA200",
            line=dict(color="#64B5F6", width=1.5, dash="dot"),
            hovertemplate="MA200: %{y:.2f}<extra></extra>",
        ), row=1, col=1)

    # ── Volume ──
    fig.add_trace(go.Bar(
        x=history.index,
        y=history["Volume"],
        name="Volume",
        marker_color=vol_colors,
        marker_line_width=0,
        opacity=0.7,
        hovertemplate="Vol: %{y:,.0f}<extra></extra>",
        showlegend=False,
    ), row=2, col=1)

    # Auto-detect weekends + holidays (missing weekday dates)
    import pandas as _pd
    _x_idx = _pd.DatetimeIndex(history.index).normalize()
    _all_bdays = _pd.bdate_range(_x_idx.min(), _x_idx.max())
    _missing = _all_bdays.difference(_x_idx)
    _rangebreaks = [dict(bounds=["sat", "mon"])]
    if len(_missing) > 0:
        _rangebreaks.append(dict(values=_missing.strftime("%Y-%m-%d").tolist()))

    fig.update_layout(
        title=dict(text=f"{ticker} Price & Volume", font=dict(size=12)),
        height=460,
        xaxis_rangeslider_visible=False,
        margin=dict(l=8, r=8, t=30, b=8),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        xaxis2=dict(showgrid=False, type="date", rangebreaks=_rangebreaks),
        xaxis=dict(showgrid=False, type="date", rangebreaks=_rangebreaks),
        yaxis=dict(gridcolor="rgba(200,200,200,0.15)"),
        yaxis2=dict(gridcolor="rgba(200,200,200,0.1)", tickformat=".2s", title=dict(text="Vol", font=dict(size=10))),
        hovermode="x unified",
    )
    return fig


def create_financials_bar(quarterly: dict) -> go.Figure:
    """Quarterly revenue + operating income bar chart + Gross Margin % line"""
    quarters     = quarterly.get("quarters", [])
    revenue      = quarterly.get("revenue_b", [])
    gross_profit = quarterly.get("gross_profit_b", [])
    op_income    = quarterly.get("op_income_b", [])

    # Calculate Gross Margin %
    gross_margin_pct = []
    for rev, gp in zip(revenue, gross_profit):
        if rev and gp and rev > 0:
            gross_margin_pct.append(round(gp / rev * 100, 1))
        else:
            gross_margin_pct.append(None)

    has_gross = any(v is not None for v in gross_margin_pct)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=quarters, y=revenue, name="Revenue",
        marker_color="#4C9BE8",
        hovertemplate="%{x}<br>Revenue: $%{y:.2f}B<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        x=quarters, y=op_income, name="Op. Income",
        marker_color="#00CC96",
        hovertemplate="%{x}<br>Op. Income: $%{y:.2f}B<extra></extra>",
    ), secondary_y=False)

    if has_gross:
        fig.add_trace(go.Scatter(
            x=quarters, y=gross_margin_pct, name="Gross Margin %",
            mode="lines+markers",
            line=dict(color="#F59E0B", width=2, dash="dot"),
            marker=dict(size=5),
            hovertemplate="%{x}<br>Gross Margin: %{y:.1f}%<extra></extra>",
        ), secondary_y=True)

    fig.update_layout(
        title=dict(text="Quarterly Financials", font=dict(size=12)),
        barmode="group",
        height=300,
        margin=dict(l=8, r=8, t=30, b=8),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(200,200,200,0.15)", tickprefix="$", ticksuffix="B"),
        hovermode="x unified",
    )
    if has_gross:
        fig.update_yaxes(
            title_text="Gross Margin %",
            ticksuffix="%",
            gridcolor="rgba(0,0,0,0)",
            secondary_y=True,
        )
    return fig


def create_sector_heatmap(sector_returns: dict) -> go.Figure:
    """Sector ETF returns heatmap (rows=sectors, cols=periods)"""
    periods  = ["1D", "1W", "1M"]
    keys     = ["ret_1d", "ret_1w", "ret_1m"]
    sectors  = list(sector_returns.keys())

    z, text = [], []
    for s in sectors:
        row, trow = [], []
        for k in keys:
            v = sector_returns[s].get(k)
            row.append(v if v is not None else 0)
            trow.append(f"{v:+.2f}%" if v is not None else "N/A")
        z.append(row)
        text.append(trow)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=periods,
        y=sectors,
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=11),
        colorscale=[
            [0.0,  "#7f1d1d"], [0.35, "#dc2626"],
            [0.45, "#f87171"], [0.5,  "#374151"],
            [0.55, "#4ade80"], [0.65, "#16a34a"],
            [1.0,  "#14532d"],
        ],
        zmid=0,
        showscale=False,
        hovertemplate="%{y} %{x}: %{text}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Sector Returns Heatmap", font=dict(size=12)),
        height=360,
        margin=dict(l=8, r=8, t=30, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(side="top"),
    )
    return fig


def create_cashflow_chart(cashflow: dict) -> go.Figure:
    """Annual cash flow bar chart (operating/free/investing/financing)"""
    years     = cashflow.get("years", [])
    operating = cashflow.get("operating", [])
    free_cf   = cashflow.get("free_cf", [])
    investing = cashflow.get("investing", [])
    financing = cashflow.get("financing", [])

    fig = go.Figure()
    traces = [
        ("Operating CF",  operating, "#26a69a"),
        ("Free CF",       free_cf,   "#66bb6a"),
        ("Investing CF",  investing, "#ff7043"),
        ("Financing CF",  financing, "#ab47bc"),
    ]
    for name, vals, color in traces:
        if any(v is not None for v in vals):
            fig.add_trace(go.Bar(
                x=years, y=vals, name=name,
                marker_color=color,
                hovertemplate=f"%{{x}}<br>{name}: $%{{y:.2f}}B<extra></extra>",
            ))
    fig.update_layout(
        title=dict(text="Annual Cash Flow (B$)", font=dict(size=12)),
        barmode="group",
        height=280,
        margin=dict(l=8, r=8, t=30, b=8),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(200,200,200,0.15)", tickprefix="$", ticksuffix="B"),
    )
    return fig


def create_sector_treemap(sector_returns: dict, period: str = "1D") -> go.Figure:
    """Sector returns treemap (selectable period: 1D / 1W / 1M)"""
    ret_key_map = {"1D": "ret_1d", "1W": "ret_1w", "1M": "ret_1m"}
    ret_key = ret_key_map.get(period, "ret_1d")

    sector_weights = {
        "Technology": 32, "Healthcare": 13, "Financials": 13,
        "Consumer Discretionary": 11, "Communication Services": 9,
        "Industrials": 9, "Consumer Staples": 6, "Energy": 4,
        "Utilities": 3, "Real Estate": 2, "Materials": 3,
    }
    labels, parents, values, colors, texts = [], [], [], [], []
    labels.append("S&P 500")
    parents.append("")
    values.append(0)
    colors.append(0)
    texts.append("")

    colorscale = [
        [0.0,  "#7f1d1d"], [0.3, "#dc2626"],
        [0.45, "#4b5563"], [0.5, "#374151"],
        [0.55, "#4b5563"], [0.7, "#16a34a"],
        [1.0,  "#14532d"],
    ]

    ret_vals = []
    for sector, data in sector_returns.items():
        v = data.get(ret_key)
        ret_vals.append(v if v is not None else 0)

    min_r = min(ret_vals) if ret_vals else -2
    max_r = max(ret_vals) if ret_vals else 2
    span  = max(abs(min_r), abs(max_r)) or 1

    for sector, data in sector_returns.items():
        v   = data.get(ret_key)
        val = v if v is not None else 0
        w   = sector_weights.get(sector, 5)
        labels.append(sector)
        parents.append("S&P 500")
        values.append(w)
        colors.append(val)
        sign = "+" if val >= 0 else ""
        texts.append(f"{sector}<br><b>{sign}{val:.2f}%</b>")

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        customdata=colors,
        text=texts,
        textinfo="text",
        hovertemplate="%{text}<extra></extra>",
        marker=dict(
            colors=colors,
            colorscale=colorscale,
            cmid=0,
            cmin=-span,
            cmax=span,
            showscale=False,
            line=dict(width=1.5, color="#0e0e16"),
        ),
        pathbar=dict(visible=False),
        tiling=dict(pad=3),
        root_color="#0e0e16",
    ))
    fig.update_layout(
        height=380,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_company_price_chart(history, ticker: str) -> go.Figure:
    return _line_chart(history.index, history["Close"], "#F59E0B", f"{ticker} Price", "$", height=260)
