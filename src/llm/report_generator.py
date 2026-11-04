"""
Comprehensive investment report generator

Synthesizes the 3-stage analysis (Market/Macro → Industry → Company)
to produce a final investment opinion powered by gpt-5.4.
"""
import os
import json
import statistics
from openai import OpenAI
from dotenv import load_dotenv
from src.config.settings import LLM_MODEL_REPORT

load_dotenv()

SYSTEM_PROMPT = """You are a senior investment analyst at an institutional investor level.
You synthesize macro, industry, and company analysis to deliver a clear, evidence-based final investment opinion.
Your judgments are grounded in numbers and concrete rationale, avoiding vague language.
Your response must be in English and in valid JSON format."""


def _build_synthesis_prompt(
    ticker: str,
    company_name: str,
    market_analysis: dict,
    industry_analysis: dict,
    company_analysis: dict,
    company_data: dict,
    industry_data: dict = None,
) -> str:
    price    = company_data.get("price", {})
    val      = company_data.get("valuation", {})
    analyst  = company_data.get("analyst", {})

    fin = company_data.get("financials", {})

    def _fmt_cap(v):
        if v is None: return "N/A"
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9:  return f"${v/1e9:.1f}B"
        return f"${v/1e6:.0f}M"

    def _pct(v):
        return f"{v*100:+.1f}%" if v is not None else "N/A"

    def _fmt_pe(v):
        if v is None: return "N/A"
        if v < 0:     return "N/M"
        return f"{v:.1f}x"

    def _fmt_mult(v, decimals=2):
        return f"{v:.{decimals}f}x" if v is not None else "N/A"

    lines = []
    lines.append(f"# Analysis Subject: {company_name} ({ticker})")
    lines.append(f"- Current Price: ${price.get('latest', 'N/A')}")
    lines.append(f"- 52-Week Range: ${price.get('week_52_low', '–')} – ${price.get('week_52_high', '–')}")
    lines.append(f"- Market Cap: {_fmt_cap(val.get('market_cap'))}")
    lines.append(f"- Trailing P/E: {_fmt_pe(val.get('pe_ratio'))}")
    lines.append(f"- Forward P/E:  {_fmt_pe(val.get('forward_pe'))}")
    lines.append(f"- P/B: {_fmt_mult(val.get('pb_ratio'))}")
    lines.append(f"- EPS (TTM): ${fin.get('eps_ttm', 'N/A')}")
    lines.append(f"- Revenue Growth (YoY): {_pct(fin.get('revenue_growth_yoy'))}")
    lines.append(f"- Gross Margin: {_pct(fin.get('gross_margin'))}")
    lines.append(f"- Operating Margin: {_pct(fin.get('operating_margin'))}")
    lines.append(f"- Net Margin: {_pct(fin.get('net_margin'))}")
    lines.append(f"- ROE: {_pct(fin.get('roe'))}")
    lines.append(f"- Debt/Equity: {fin.get('debt_to_equity', 'N/A')}")
    lines.append(f"- Analyst Consensus: {analyst.get('recommendation', '–').upper()} / Mean Target ${analyst.get('target_price', '–')} / {analyst.get('num_analysts', '–')} analysts")

    # ── Short Interest ──
    si = company_data.get("short_interest", {})
    if si.get("short_float") is not None:
        lines.append(f"- Short Interest: {si['short_float']:.2f}% of float"
                     + (f" / {si['short_ratio']:.1f} days to cover" if si.get("short_ratio") else ""))

    # ── EPS Surprise (summary of most recent 2 quarters) ──
    eps_surp = company_data.get("eps_surprise", [])
    if eps_surp:
        surp_lines = []
        for q in eps_surp[:2]:
            sp = q.get("surprise_pct")
            if sp is not None:
                beat = "BEAT" if sp >= 0 else "MISS"
                surp_lines.append(f"{q['date']} {beat} {sp:+.1f}%")
        if surp_lines:
            lines.append(f"- Recent EPS Surprises: {' | '.join(surp_lines)}")

    # ── Peer Valuation averages (for relative valuation assessment) ──
    if industry_data:
        peers = industry_data.get("peers", [])
        if peers:
            peer_pes  = [p["pe_ratio"]  for p in peers if p.get("pe_ratio")  and p["pe_ratio"] > 0]
            peer_fpes = [p["forward_pe"] for p in peers if p.get("forward_pe") and p["forward_pe"] > 0]
            peer_ops  = [p["op_margin"] for p in peers if p.get("op_margin")]
            if peer_pes:
                med_pe  = round(statistics.median(peer_pes), 1)
                pe_own  = val.get("pe_ratio")
                rel     = f" → {'PREMIUM' if pe_own and pe_own > 0 and pe_own > med_pe else 'DISCOUNT'} vs peers" if pe_own and pe_own > 0 else ""
                lines.append(f"- Peer Median P/E (TTM): {med_pe}x{rel}")
            if peer_fpes:
                med_fpe = round(statistics.median(peer_fpes), 1)
                lines.append(f"- Peer Median Forward P/E: {med_fpe}x")
            if peer_ops:
                med_op = round(statistics.median(peer_ops) * 100, 1)
                lines.append(f"- Peer Median Op. Margin: {med_op}%")

    lines.append("\n## [Stage 1] Macro Analysis")
    lines.append(f"- Market Risk: {market_analysis.get('risk_level', '–').upper()}")
    lines.append(f"- Summary: {market_analysis.get('market_summary', '–')}")
    for p in market_analysis.get("key_points", [])[:3]:
        lines.append(f"  • [{p.get('importance','').upper()}] {p['title']}: {p['analysis']}")

    lines.append("\n## [Stage 2] Industry Analysis")
    lines.append(f"- Industry Momentum: {industry_analysis.get('momentum', '–').upper()}")
    lines.append(f"- Summary: {industry_analysis.get('industry_summary', '–')}")
    for p in industry_analysis.get("key_points", [])[:3]:
        lines.append(f"  • [{p.get('importance','').upper()}] {p['title']}: {p['analysis']}")

    lines.append("\n## [Stage 3] Company Analysis")
    lines.append(f"- AI Investment Stance: {company_analysis.get('investment_stance', '–').upper()}")
    lines.append(f"- Summary: {company_analysis.get('company_summary', '–')}")
    for p in company_analysis.get("key_points", [])[:3]:
        lines.append(f"  • [{p.get('importance','').upper()}] {p['title']}: {p['analysis']}")

    prompt = "\n".join(lines)
    prompt += f"""

Based on the 3-stage analysis above, write a final investment report for {company_name} ({ticker}).

Response format (JSON):
{{
  "verdict": "BUY|HOLD|SELL",
  "conviction": "high|medium|low",
  "target_price": number or null,
  "target_price_basis": "Valuation methodology used (e.g. '28x Forward P/E on FY2025E EPS of $X.XX, in line with sector peers at X% premium/discount'). Required if target_price is set.",
  "summary": "Synthesis of 3-stage analysis (3-4 sentences, include key figures)",
  "investment_thesis": [
    "BUY/HOLD/SELL rationale 1 (include specific figures)",
    "BUY/HOLD/SELL rationale 2 (include specific figures)",
    "BUY/HOLD/SELL rationale 3 (include specific figures)"
  ],
  "key_risks": [
    "Key risk 1",
    "Key risk 2"
  ],
  "conclusion": "Final investment conclusion (1-2 sentences, include a clear action)"
}}

Return only valid JSON."""

    return prompt


def generate_final_report(
    ticker: str,
    market_analysis: dict,
    industry_analysis: dict,
    company_analysis: dict,
    company_data: dict,
    industry_data: dict = None,
) -> dict:
    """
    Generate a final investment report by synthesizing the 3-stage analysis.

    Returns:
        {
          "verdict": "BUY" | "HOLD" | "SELL",
          "conviction": "high" | "medium" | "low",
          "target_price": float | None,
          "summary": str,
          "investment_thesis": [str, str, str],
          "key_risks": [str, str],
          "conclusion": str,
        }
    """
    company_name = company_data.get("company_name", ticker)

    prompt = _build_synthesis_prompt(
        ticker, company_name,
        market_analysis, industry_analysis, company_analysis,
        company_data, industry_data,
    )

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=LLM_MODEL_REPORT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_completion_tokens=2000,
    )

    return json.loads(response.choices[0].message.content)
