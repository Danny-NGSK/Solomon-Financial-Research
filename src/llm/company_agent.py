"""
Dynamic company analysis AI agent

Autonomously identifies and analyzes key company investment points at the current moment
based on stock price, valuation, financial, and analyst data.
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from src.config.settings import LLM_MODEL_DEFAULT

load_dotenv()


SYSTEM_PROMPT = """You are a professional investment research analyst.
Based on a company's price, valuation, and financial data, you dynamically identify and analyze the key investment points that investors must know at this point in time.
Without a fixed template, you select only the factors that truly stand out in the current data.
Your response must be in English and in valid JSON format."""


def _fmt_market_cap(val) -> str:
    if val is None:
        return "N/A"
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    return f"${val/1e6:.0f}M"


def _fmt_pct(val, digits=1) -> str:
    if val is None:
        return "N/A"
    return f"{val*100:+.{digits}f}%"


def _build_data_summary(company_data: dict) -> str:
    lines = []

    ticker  = company_data.get("ticker", "")
    company = company_data.get("company_name", "")
    sector  = company_data.get("sector", "")
    industry= company_data.get("industry", "")

    lines.append(f"## Subject: {company} ({ticker})")
    lines.append(f"- Sector: {sector} / Industry: {industry}")

    # Price performance
    price = company_data.get("price", {})
    if price:
        lines.append(f"\n## Price Performance")
        lines.append(f"- Current Price: ${price.get('latest', 'N/A')}")
        if price.get("ret_1d")  is not None: lines.append(f"- 1-Day Return: {price['ret_1d']:+.2f}%")
        if price.get("ret_1m")  is not None: lines.append(f"- 1-Month Return: {price['ret_1m']:+.2f}%")
        if price.get("ret_3m")  is not None: lines.append(f"- 3-Month Return: {price['ret_3m']:+.2f}%")
        if price.get("ret_1y")  is not None: lines.append(f"- 1-Year Return: {price['ret_1y']:+.2f}%")
        if price.get("week_52_high") and price.get("week_52_low"):
            lines.append(f"- 52-Week Range: ${price['week_52_low']} – ${price['week_52_high']}")

    # Valuation
    val = company_data.get("valuation", {})
    if val:
        lines.append(f"\n## Valuation")
        lines.append(f"- Market Cap: {_fmt_market_cap(val.get('market_cap'))}")
        pe = val.get("pe_ratio")
        if pe is not None:
            lines.append(f"- Trailing P/E: {'N/M (negative earnings)' if pe < 0 else f'{pe:.1f}x'}")
        fpe = val.get("forward_pe")
        if fpe is not None:
            lines.append(f"- Forward P/E: {'N/M (negative earnings)' if fpe < 0 else f'{fpe:.1f}x'}")
        if val.get("pb_ratio"):      lines.append(f"- P/B: {val['pb_ratio']:.2f}x")
        if val.get("ps_ratio"):      lines.append(f"- P/S: {val['ps_ratio']:.2f}x")
        if val.get("dividend_yield"): lines.append(f"- Dividend Yield: {val['dividend_yield']*100:.2f}%")

    # Financials
    fin = company_data.get("financials", {})
    if fin:
        lines.append(f"\n## Financials (TTM)")
        if fin.get("revenue_ttm"):          lines.append(f"- Revenue: {_fmt_market_cap(fin['revenue_ttm'])}")
        if fin.get("revenue_growth_yoy"):   lines.append(f"- Revenue Growth (YoY): {_fmt_pct(fin['revenue_growth_yoy'])}")
        if fin.get("gross_margin"):         lines.append(f"- Gross Margin: {_fmt_pct(fin['gross_margin'])}")
        if fin.get("operating_margin"):     lines.append(f"- Operating Margin: {_fmt_pct(fin['operating_margin'])}")
        if fin.get("net_margin"):           lines.append(f"- Net Margin: {_fmt_pct(fin['net_margin'])}")
        if fin.get("eps_ttm"):              lines.append(f"- EPS: ${fin['eps_ttm']:.2f}")
        if fin.get("earnings_growth_yoy"):  lines.append(f"- EPS Growth (YoY): {_fmt_pct(fin['earnings_growth_yoy'])}")
        if fin.get("roe"):                  lines.append(f"- ROE: {_fmt_pct(fin['roe'])}")
        if fin.get("debt_to_equity"):       lines.append(f"- Debt/Equity: {fin['debt_to_equity']:.2f}")

    # Analyst consensus
    analyst = company_data.get("analyst", {})
    if analyst:
        lines.append(f"\n## Analyst Consensus")
        lines.append(f"- Recommendation: {analyst.get('recommendation', '–').upper()}")
        if analyst.get("target_price"):  lines.append(f"- Price Target: ${analyst['target_price']:.2f}")
        if analyst.get("upside_pct") is not None: lines.append(f"- Upside Potential: {analyst['upside_pct']:+.1f}%")
        if analyst.get("num_analysts"): lines.append(f"- Number of Analysts: {analyst['num_analysts']}")

    # Recent news
    news = company_data.get("news", [])
    if news:
        lines.append(f"\n## Recent News Headlines")
        for i, item in enumerate(news[:8], 1):
            title = "".join(c for c in item.get("title", "") if c.isprintable()).strip()
            if title:
                lines.append(f"{i}. {title}")

    return "\n".join(lines)


def _macro_context_block(market_analysis: dict) -> str:
    if not market_analysis:
        return ""
    lines = ["\n## Macro Market Context (for reference)"]
    risk = market_analysis.get("risk_level", "")
    summary = market_analysis.get("market_summary", "")
    if risk:
        lines.append(f"- Overall Market Risk: {risk.upper()}")
    if summary:
        lines.append(f"- Market Overview: {summary}")
    kps = market_analysis.get("key_points", [])
    for kp in kps[:3]:
        title = kp.get("title", "")
        imp   = kp.get("importance", "")
        if title:
            lines.append(f"- [{imp.upper()}] {title}")
    return "\n".join(lines)


def analyze_company(company_data: dict, market_analysis: dict = None) -> dict:
    """
    Dynamically identify the key investment points at the current moment by analyzing company data.

    Returns:
        {
          "company_summary": str,
          "investment_stance": "bullish" | "neutral" | "bearish",
          "key_points": [
            {
              "title": str,
              "analysis": str,
              "importance": "critical" | "high" | "medium",
              "viz_type": "image" | "none",
              "image_keywords": str | null,
            }
          ]
        }
    """
    data_summary = _build_data_summary(company_data)
    macro_block  = _macro_context_block(market_analysis)
    ticker  = company_data.get("ticker", "")
    company = company_data.get("company_name", ticker)

    user_prompt = f"""The following is company data for {company} ({ticker}):

{data_summary}{macro_block}

Based on this data, identify and analyze 3–5 key investment points that investors must know about this company right now.
Take the macro market context into account when assessing company-level risks and the broader investment environment.

Response format (JSON):
{{
  "company_summary": "Current company situation summary (2-3 sentences, include specific figures)",
  "investment_stance": "bullish|neutral|bearish",
  "key_points": [
    {{
      "title": "Point title (concise)",
      "analysis": "Current situation + specific figures + investment implications (2-3 sentences)",
      "importance": "critical|high|medium",
      "viz_type": "image|none",
      "image_keywords": "relevant image search keywords (English) or null"
    }}
  ]
}}

viz_type selection:
- image: when visual aids help (product launches, CEO issues, M&A, geopolitical risks, etc.) → English keywords for image_keywords
- none: when figures/financial data alone are sufficient

Return only valid JSON."""

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=LLM_MODEL_DEFAULT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_completion_tokens=2000,
    )

    return json.loads(response.choices[0].message.content)
