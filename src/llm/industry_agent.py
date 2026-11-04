"""
Dynamic industry analysis AI agent

Autonomously identifies and analyzes the key industry factors at the current moment
based on current sector data and peer performance.
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from src.config.settings import LLM_MODEL_DEFAULT

load_dotenv()


SYSTEM_PROMPT = """You are a professional investment research analyst.
Based on current industry and sector data, you dynamically identify and analyze the key industry factors that investors must know at this point in time.
Without a fixed template, you select only the factors that truly stand out in the current data.
Your response must be in English and in valid JSON format."""


def _build_data_summary(industry_data: dict) -> str:
    lines = []

    ticker  = industry_data.get("ticker", "")
    company = industry_data.get("company_name", "")
    sector  = industry_data.get("sector", "")
    industry= industry_data.get("industry", "")

    lines.append(f"## Subject: {company} ({ticker})")
    lines.append(f"- Sector: {sector}")
    lines.append(f"- Industry: {industry}")

    # Target ticker performance
    target = industry_data.get("target", {})
    if target:
        lines.append(f"\n## {ticker} Price Performance")
        lines.append(f"- Current Price: ${target.get('latest_price', 'N/A')}")
        if target.get("ret_1d") is not None:
            lines.append(f"- 1-Day Return: {target['ret_1d']:+.2f}%")
        if target.get("ret_1m") is not None:
            lines.append(f"- 1-Month Return: {target['ret_1m']:+.2f}%")
        if target.get("ret_3m") is not None:
            lines.append(f"- 3-Month Return: {target['ret_3m']:+.2f}%")

    # Sector ETF performance
    etf = industry_data.get("sector_etf", {})
    if etf:
        lines.append(f"\n## Sector ETF ({etf.get('ticker')} - {etf.get('name')})")
        if etf.get("ret_1d") is not None:
            lines.append(f"- 1-Day Return: {etf['ret_1d']:+.2f}%")
        if etf.get("ret_1m") is not None:
            lines.append(f"- 1-Month Return: {etf['ret_1m']:+.2f}%")
        if etf.get("ret_3m") is not None:
            lines.append(f"- 3-Month Return: {etf['ret_3m']:+.2f}%")

    # Peer comparison
    peers = industry_data.get("peers", [])
    if peers:
        lines.append("\n## Peer Performance Comparison")
        for p in peers:
            ret_1m = f"{p['ret_1m']:+.2f}%" if p.get("ret_1m") is not None else "N/A"
            ret_3m = f"{p['ret_3m']:+.2f}%" if p.get("ret_3m") is not None else "N/A"
            lines.append(f"- {p['ticker']} ({p.get('name', '')}): 1M {ret_1m} / 3M {ret_3m}")

    # Recent news
    news = industry_data.get("news", [])
    if news:
        lines.append("\n## Recent News Headlines")
        for i, item in enumerate(news[:8], 1):
            title = "".join(c for c in item.get("title", "") if c.isprintable()).strip()
            if title:
                lines.append(f"{i}. {title}")

    return "\n".join(lines)


def _macro_context_block(market_analysis: dict) -> str:
    """Build a macro context summary string from the market_analysis result."""
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


def analyze_industry(industry_data: dict, market_analysis: dict = None) -> dict:
    """
    Dynamically identify the key points at the current moment by analyzing industry data.

    Returns:
        {
          "industry_summary": str,
          "momentum": "bullish" | "neutral" | "bearish",
          "key_points": [
            {
              "title": str,
              "analysis": str,
              "importance": "critical" | "high" | "medium",
              "viz_type": "peer_chart" | "image" | "none",
              "image_keywords": str | null,
            }
          ]
        }
    """
    data_summary = _build_data_summary(industry_data)
    macro_block  = _macro_context_block(market_analysis)
    ticker = industry_data.get("ticker", "")
    sector = industry_data.get("sector", "")

    user_prompt = f"""The following is industry data for {ticker} ({sector} sector):

{data_summary}{macro_block}

Based on this data, identify and analyze 3–5 key factors that investors must know about this sector/industry right now.
Take the macro market context into account when assessing sector-level risks and opportunities.

Response format (JSON):
{{
  "industry_summary": "Current industry situation summary (2-3 sentences, include specific figures)",
  "momentum": "bullish|neutral|bearish",
  "key_points": [
    {{
      "title": "Point title (concise)",
      "analysis": "Current situation + specific figures + investment implications (2-3 sentences)",
      "importance": "critical|high|medium",
      "viz_type": "peer_chart|image|none",
      "image_keywords": "relevant image search keywords (English) or null"
    }}
  ]
}}

viz_type selection:
- peer_chart: when relative peer performance comparison is the key point (competitive dynamics, market share shifts, etc.)
- image: geopolitical issues, policy events, specific news events → English keywords for image_keywords
- none: when figures/text alone are sufficient

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
