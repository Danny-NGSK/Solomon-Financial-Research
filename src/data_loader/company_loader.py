"""
Company data loader
- Basic info (name, sector, description): yfinance
- Stock performance + history: yfinance
- Valuation metrics (P/E, P/B, etc.): yfinance
- Financial metrics (revenue, margins, ROE, etc.): yfinance
- Analyst consensus: yfinance
- News: yfinance
"""
import yfinance as yf
from src.data_loader.news_loader import fetch_news
from src.data_loader.info_loader import fetch_info


def _safe(info: dict, key: str, default=None):
    val = info.get(key)
    return val if val is not None else default


def load_company_data(ticker: str) -> dict:
    """
    Load all company data.

    Returns:
        {
            "ticker":       str,
            "company_name": str,
            "sector":       str,
            "industry":     str,
            "description":  str,
            "price": {
                "latest", "ret_1d", "ret_1m", "ret_3m", "ret_1y",
                "week_52_high", "week_52_low", "history"
            },
            "valuation": {
                "market_cap", "pe_ratio", "forward_pe",
                "pb_ratio", "ps_ratio", "dividend_yield"
            },
            "financials": {
                "revenue_ttm", "revenue_growth_yoy",
                "gross_margin", "operating_margin", "net_margin",
                "eps_ttm", "earnings_growth_yoy", "roe", "debt_to_equity"
            },
            "analyst": {
                "recommendation", "target_price", "num_analysts", "upside_pct"
            },
            "news": [ { title, url, publisher, thumbnail } ],
        }
    """
    ticker = ticker.upper()
    t = yf.Ticker(ticker)

    # ── Basic info ──
    info = fetch_info(ticker)   # Yahoo with retry + Alpha Vantage fallback for missing fields

    result = {
        "ticker":       ticker,
        "company_name": _safe(info, "longName") or _safe(info, "shortName") or ticker,
        "sector":       _safe(info, "sector", "–"),
        "industry":     _safe(info, "industry", "–"),
        "description":  _safe(info, "longBusinessSummary", ""),
        "exchange":     _safe(info, "exchange", ""),
        "website":      _safe(info, "website", ""),
    }

    # ── Stock performance ──
    price = {}
    try:
        hist = t.history(period="max")
        if not hist.empty:
            close = hist["Close"].dropna()
            if not close.empty:
                import pandas as pd
                latest_date = close.index[-1]
                price["latest"] = round(float(close.iloc[-1]), 2)
                price["ret_1d"] = round((close.iloc[-1] / close.iloc[-2]  - 1) * 100, 2) if len(close) >= 2  else None
                price["ret_1m"] = round((close.iloc[-1] / close.iloc[-21] - 1) * 100, 2) if len(close) >= 21 else None
                price["ret_3m"] = round((close.iloc[-1] / close.iloc[-63] - 1) * 100, 2) if len(close) >= 63 else None
                _1y_ago = close[close.index <= latest_date - pd.DateOffset(years=1)]
                price["ret_1y"] = round((close.iloc[-1] / _1y_ago.iloc[-1] - 1) * 100, 2) if not _1y_ago.empty else None
            price["history"]      = hist
        price["week_52_high"] = _safe(info, "fiftyTwoWeekHigh")
        price["week_52_low"]  = _safe(info, "fiftyTwoWeekLow")
    except Exception as e:
        print(f"[Company] {ticker} price load failed: {e}")

    result["price"] = price

    # ── Valuation ──
    market_cap = _safe(info, "marketCap")

    # trailingPE fallback: price ÷ EPS (yfinance omits it when EPS ≤ 0)
    pe_ratio = _safe(info, "trailingPE")
    if pe_ratio is None:
        eps_ttm   = _safe(info, "trailingEps")
        cur_price = price.get("latest")
        if eps_ttm and eps_ttm != 0 and cur_price:
            pe_ratio = round(cur_price / eps_ttm, 1)

    result["valuation"] = {
        "market_cap":     market_cap,
        "pe_ratio":       pe_ratio,
        "forward_pe":     _safe(info, "forwardPE"),
        "pb_ratio":       _safe(info, "priceToBook"),
        "ps_ratio":       _safe(info, "priceToSalesTrailing12Months"),
        "dividend_yield": _safe(info, "dividendYield"),
    }

    # ── Short interest ──
    short_float = _safe(info, "shortPercentOfFloat")   # 0.023 = 2.3%
    short_ratio = _safe(info, "shortRatio")             # days to cover
    shares_short = _safe(info, "sharesShort")
    date_si_raw  = _safe(info, "dateShortInterest")    # unix timestamp

    short_date_str = ""
    if date_si_raw:
        try:
            from datetime import datetime as _dt
            short_date_str = _dt.fromtimestamp(date_si_raw).strftime("%b %Y")
        except Exception:
            pass

    result["short_interest"] = {
        "short_float":   round(short_float * 100, 2) if short_float is not None else None,  # Convert to %
        "short_ratio":   round(short_ratio, 1) if short_ratio is not None else None,
        "shares_short":  shares_short,
        "as_of":         short_date_str,
    }

    # ── Financial metrics ──
    # profitMargins: yfinance may return 0.0 instead of None for small-cap/loss-making stocks
    # → If EPS < 0 but margin = 0, it's a data error → recalculate from netIncomeToCommon/totalRevenue
    raw_margin = _safe(info, "profitMargins")
    if raw_margin == 0:
        net_inc = _safe(info, "netIncomeToCommon")
        rev     = _safe(info, "totalRevenue")
        if net_inc is not None and rev and rev > 0:
            raw_margin = round(net_inc / rev, 6)
        else:
            raw_margin = None

    result["financials"] = {
        "revenue_ttm":          _safe(info, "totalRevenue") or None,
        "revenue_growth_yoy":   _safe(info, "revenueGrowth"),
        "gross_margin":         _safe(info, "grossMargins") or None,
        "operating_margin":     _safe(info, "operatingMargins"),
        "net_margin":           raw_margin,
        "eps_ttm":              _safe(info, "trailingEps"),
        "earnings_growth_yoy":  _safe(info, "earningsGrowth"),
        "roe":                  _safe(info, "returnOnEquity") or None,
        "debt_to_equity":       _safe(info, "debtToEquity"),
    }

    # ── Analyst consensus ──
    target_price  = _safe(info, "targetMeanPrice")
    target_high   = _safe(info, "targetHighPrice")
    target_low    = _safe(info, "targetLowPrice")
    target_median = _safe(info, "targetMedianPrice")
    current_price = price.get("latest")
    upside = round((target_price / current_price - 1) * 100, 1) if (target_price and current_price) else None

    # recommendations_summary: Number of analysts per rating (Strong Buy / Buy / Hold / Sell / Strong Sell)
    ratings = {}
    try:
        rec_summary = t.recommendations_summary
        if rec_summary is not None and not rec_summary.empty:
            # Use the most recent period row
            row = rec_summary.iloc[0]
            for col in ["strongBuy", "buy", "hold", "sell", "strongSell"]:
                if col in row:
                    ratings[col] = int(row[col])
    except Exception as e:
        print(f"[Company] {ticker} recommendations_summary failed: {e}")
    if not ratings and info.get("_av_ratings"):
        ratings = info["_av_ratings"]

    result["analyst"] = {
        "recommendation": _safe(info, "recommendationKey", "–"),
        "target_price":   target_price,
        "target_high":    target_high,
        "target_low":     target_low,
        "target_median":  target_median,
        "num_analysts":   _safe(info, "numberOfAnalystOpinions"),
        "upside_pct":     upside,
        "ratings":        ratings,
    }

    # ── News ──
    news_items = fetch_news(ticker, n=10, tag="Company")

    result["news"] = news_items

    # ── Quarterly financials — Alpha Vantage INCOME_STATEMENT (up to 5 years) ──
    quarterly = {}
    try:
        import os, requests, pandas as pd
        from src.config.settings import ALPHA_VANTAGE_API_KEY as av_key
        if av_key:
            url = (
                f"https://www.alphavantage.co/query"
                f"?function=INCOME_STATEMENT&symbol={ticker}&apikey={av_key}"
            )
            resp = requests.get(url, timeout=10)
            data = resp.json()
            reports = data.get("quarterlyReports", [])
            if reports:
                # Sort ascending, most recent 12 quarters
                reports = sorted(reports, key=lambda r: r["fiscalDateEnding"])[-12:]
                quarters, revenue, gross_profit, op_income = [], [], [], []
                for r in reports:
                    date = r["fiscalDateEnding"]  # "2024-09-30"
                    yr   = int(date[2:4])
                    mo   = int(date[5:7])
                    q    = (mo - 1) // 3 + 1
                    quarters.append(f"Q{q}'{yr:02d}")

                    def _av(key, rec=r):
                        v = rec.get(key, "None")
                        try:
                            return round(float(v) / 1e9, 2)
                        except (ValueError, TypeError):
                            return None

                    rev_val = _av("totalRevenue")
                    gp_val  = _av("grossProfit")
                    op_val  = _av("operatingIncome")
                    revenue.append(rev_val)
                    gross_profit.append(gp_val)
                    op_income.append(op_val)

                if any(v is not None for v in revenue):
                    quarterly = {
                        "quarters":      quarters,
                        "revenue_b":     revenue,
                        "gross_profit_b": gross_profit,
                        "op_income_b":   op_income,
                    }
    except Exception as e:
        print(f"[Company] {ticker} AV quarterly financials load failed: {e}")

    # Fall back to yfinance if AV fails
    if not quarterly:
        try:
            import pandas as pd
            qf = t.quarterly_financials
            if qf is not None and not qf.empty:
                rev_key = next((k for k in ["Total Revenue", "Revenue", "Operating Revenue"] if k in qf.index), None)
                gp_key  = next((k for k in ["Gross Profit"] if k in qf.index), None)
                op_key  = next((k for k in ["Operating Income", "EBIT", "Total Operating Income As Reported"] if k in qf.index), None)
                cols = sorted(qf.columns)[-8:]
                quarters, revenue, gross_profit, op_income = [], [], [], []
                for col in cols:
                    q_num = (col.month - 1) // 3 + 1
                    quarters.append(f"Q{q_num}'{col.year % 100:02d}" if hasattr(col, "year") else str(col)[:7])
                    def _val(key, c=col):
                        if key is None: return None
                        v = qf.loc[key, c]
                        return round(float(v) / 1e9, 2) if not pd.isna(v) else None
                    revenue.append(_val(rev_key))
                    gross_profit.append(_val(gp_key))
                    op_income.append(_val(op_key))
                if any(v is not None for v in revenue):
                    quarterly = {
                        "quarters":       quarters,
                        "revenue_b":      revenue,
                        "gross_profit_b": gross_profit,
                        "op_income_b":    op_income,
                    }
        except Exception as e:
            print(f"[Company] {ticker} yf quarterly financials load failed: {e}")

    result["quarterly"] = quarterly

    # ── Cash flow statement (annual, most recent 4 years) ──
    cashflow = {}
    try:
        import pandas as pd
        cf = t.cashflow
        if cf is not None and not cf.empty:
            cf_keys = {
                "operating":  ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
                "investing":  ["Investing Cash Flow", "Cash Flow From Continuing Investing Activities"],
                "financing":  ["Financing Cash Flow", "Cash Flow From Continuing Financing Activities"],
                "capex":      ["Capital Expenditure", "Purchase Of PPE"],
                "free_cf":    ["Free Cash Flow"],
            }
            cols = sorted(cf.columns)[-4:]  # Most recent 4 years

            def _cf_val(key_candidates, col):
                for k in key_candidates:
                    if k in cf.index:
                        v = cf.loc[k, col]
                        return round(float(v) / 1e9, 2) if not pd.isna(v) else None
                return None

            years, operating, investing, financing, capex, free_cf = [], [], [], [], [], []
            for col in cols:
                years.append(str(col.year) if hasattr(col, "year") else str(col)[:4])
                operating.append(_cf_val(cf_keys["operating"], col))
                investing.append(_cf_val(cf_keys["investing"], col))
                financing.append(_cf_val(cf_keys["financing"], col))
                capex.append(_cf_val(cf_keys["capex"], col))
                free_cf.append(_cf_val(cf_keys["free_cf"], col))

            if any(v is not None for v in operating):
                cashflow = {
                    "years":     years,
                    "operating": operating,
                    "investing": investing,
                    "financing": financing,
                    "capex":     capex,
                    "free_cf":   free_cf,
                }
    except Exception as e:
        print(f"[Company] {ticker} cash flow load failed: {e}")

    result["cashflow"] = cashflow

    # ── EPS Surprise (most recent 4 quarters) ──
    eps_surprise = []
    try:
        import pandas as pd
        ed = t.earnings_dates
        if ed is not None and not ed.empty:
            # Normalize column names (handle differences across yfinance versions)
            col_map = {}
            for c in ed.columns:
                cl = c.lower().replace(" ", "").replace("(", "").replace(")", "")
                if "estimate" in cl:
                    col_map["estimate"] = c
                elif "reported" in cl or "actual" in cl:
                    col_map["actual"] = c
                elif "surprise" in cl and "%" in c:
                    col_map["surprise_pct"] = c

            # Only quarters with actual reported EPS
            actual_col = col_map.get("actual")
            if actual_col:
                past = ed.dropna(subset=[actual_col])
                past = past.sort_index(ascending=False).head(4)  # Most recent 4 quarters

                for date, row in past.iterrows():
                    est = row.get(col_map.get("estimate", ""))
                    act = row.get(actual_col)
                    surp = row.get(col_map.get("surprise_pct", ""))

                    # Date format
                    try:
                        date_str = date.strftime("%b %Y")
                    except Exception:
                        date_str = str(date)[:7]

                    def _safe_float(v):
                        try:
                            f = float(v)
                            return None if pd.isna(f) else f
                        except (TypeError, ValueError):
                            return None

                    act_f  = _safe_float(act)
                    est_f  = _safe_float(est)
                    surp_f = _safe_float(surp)

                    # Calculate surprise_pct manually if not provided
                    if surp_f is None and act_f is not None and est_f is not None and est_f != 0:
                        surp_f = round((act_f - est_f) / abs(est_f) * 100, 1)

                    if act_f is not None:
                        eps_surprise.append({
                            "date":         date_str,
                            "estimate":     round(est_f, 2) if est_f is not None else None,
                            "actual":       round(act_f, 2),
                            "surprise_pct": round(surp_f, 1) if surp_f is not None else None,
                        })
    except Exception as e:
        print(f"[Company] {ticker} EPS surprise load failed: {e}")

    result["eps_surprise"] = eps_surprise
    return result
