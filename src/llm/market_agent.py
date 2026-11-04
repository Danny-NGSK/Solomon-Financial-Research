"""
Dynamic market analysis AI agent

Autonomously identifies the most important market factors based on current data
and determines point-by-point analysis + visualization types.
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from src.config.settings import LLM_MODEL_DEFAULT

load_dotenv()


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a professional investment research analyst.
Based on current market data and news, you dynamically identify and analyze the key market factors that investors must know at this point in time.
Without a fixed template, you select only the factors that truly stand out in the current data.
Your response must be in English and in valid JSON format."""


def _build_data_summary(market_data: dict) -> str:
    lines = []

    # SPY performance
    spy = market_data.get("spy", {})
    if spy:
        lines.append("## S&P 500 (SPY)")
        lines.append(f"- Current Price: ${spy.get('latest_price', 'N/A')}")
        if spy.get("ret_1m") is not None:
            lines.append(f"- 1-Month Return: {spy['ret_1m']:+.2f}%")
        if spy.get("ret_3m") is not None:
            lines.append(f"- 3-Month Return: {spy['ret_3m']:+.2f}%")

    if market_data.get("vix"):
        lines.append(f"- VIX (Fear Index): {market_data['vix']}")

    # Macro indicators
    macro = market_data.get("macro", {})
    if macro:
        lines.append("\n## Key Macro Indicators")
        for sid, data in macro.items():
            val = f"{data['latest']}{data['unit']}"
            chg = ""
            if data.get("change_1y") is not None:
                chg = f" (vs. 1Y ago: {data['change_1y']:+.2f}{data['unit']})"
            lines.append(f"- {data['name']}: {val}{chg}  [as of: {data.get('as_of', '')}]")
        # 10Y-2Y yield spread
        d10 = macro.get("DGS10")
        d2  = macro.get("DGS2")
        if d10 and d2:
            spread = round(d10["latest"] - d2["latest"], 2)
            status = "INVERTED (recession warning)" if spread < 0 else ("Flat" if spread < 0.5 else "Normal")
            lines.append(f"- 10Y-2Y Yield Spread: {spread:+.2f}% → {status}")

    # Recent news headlines
    news = market_data.get("news", [])
    if news:
        lines.append("\n## Recent Market News Headlines")
        for i, item in enumerate(news[:8], 1):
            title = "".join(c for c in item.get("title", "") if c.isprintable()).strip()
            if title:
                lines.append(f"{i}. {title}")

    return "\n".join(lines)


def analyze_market(market_data: dict) -> dict:
    """
    Dynamically identify the key market points at the current moment by analyzing market data.

    Returns:
        {
          "market_summary": str,
          "risk_level": "low" | "medium" | "high" | "extreme",
          "key_points": [
            {
              "title": str,
              "analysis": str,
              "importance": "critical" | "high" | "medium",
              "viz_type": "chart" | "image" | "none",
              "chart_series_id": str | null,
              "image_keywords": str | null,
            }
          ]
        }
    """
    data_summary = _build_data_summary(market_data)

    user_prompt = f"""The following is current market data:

{data_summary}

Based on this data, identify and analyze 3–5 key market factors that investors must know right now.

Response format (JSON):
{{
  "market_summary": "Overall market situation summary (2-3 sentences, include specific figures)",
  "risk_level": "low|medium|high|extreme",
  "key_points": [
    {{
      "title": "Point title (concise)",
      "analysis": "Current situation + specific figures + investment implications (2-3 sentences)",
      "importance": "critical|high|medium",
      "viz_type": "chart|image|none",
      "chart_series_id": "FRED series ID or null",
      "image_keywords": "relevant image search keywords (English) or null"
    }}
  ]
}}

viz_type selection:
- chart: indicators where time-series trend is key (rates/CPI/unemployment etc.) → use FEDFUNDS/CPIAUCSL/UNRATE/DGS10/T10YIE/DEXUSEU/VIXCLS for chart_series_id
- image: geopolitical issues, policy events, specific news events → English keywords for image_keywords
- none: when figures/text alone are sufficient

Return only valid JSON."""

    response = _get_client().chat.completions.create(
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
