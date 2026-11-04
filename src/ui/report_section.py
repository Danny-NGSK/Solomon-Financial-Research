"""
Final investment report renderer and Ask Solomon chat section.
"""
import streamlit as st

from src.ui.common import _section_header, _section_gap


def render_final_report(report: dict, ticker: str, company_name: str, report_time: str = ""):
    verdict       = report.get("verdict", "HOLD").upper()
    conviction    = report.get("conviction", "medium")
    target        = report.get("target_price")
    target_basis  = report.get("target_price_basis", "")
    summary       = report.get("summary", "")
    thesis        = report.get("investment_thesis", [])
    risks         = report.get("key_risks", [])
    conclusion    = report.get("conclusion", "")

    verdict_style = {
        "BUY":  ("#28a745", "💚"),
        "HOLD": ("#ffc107", "💛"),
        "SELL": ("#dc3545", "❤️"),
    }
    conviction_kr = {"high": "Strong", "medium": "Medium", "low": "Low"}
    color, emoji = verdict_style.get(verdict, ("#ffc107", "💛"))

    # ── Price/upside calculation ──
    cur_price_ctx = st.session_state.get("chat_context", {}).get("current_price")
    upside_str = ""
    if target and isinstance(cur_price_ctx, (int, float)) and cur_price_ctx > 0:
        upside = (target / cur_price_ctx - 1) * 100
        upside_str = f'<span style="font-size:0.9em; color:{color}; margin-left:12px;">Upside {upside:+.1f}%</span>'
    target_str    = f'<span style="color:{color}; font-weight:700;">${target:,.2f}</span>{upside_str}' if target else "–"
    conviction_str = conviction_kr.get(conviction, conviction)

    basis_html = (
        f'<div style="margin-top:12px; font-size:0.78em; color:#888; '
        f'max-width:500px; margin-left:auto; margin-right:auto; line-height:1.5;">'
        f'<span style="color:#a080e0; letter-spacing:0.5px;">📐 VALUATION BASIS</span><br>{target_basis}</div>'
    ) if target_basis and target else ""

    # ── Thesis / risks HTML ──
    thesis_items = "".join(
        f'<div style="display:flex; gap:10px; padding:8px 0; border-bottom:1px solid #1a3d24;">'
        f'<span style="color:#34d368; font-weight:800; min-width:18px; flex-shrink:0;">{i+1}</span>'
        f'<span style="font-size:0.87em; color:#c0ddc8; line-height:1.65;">{item}</span>'
        f'</div>'
        for i, item in enumerate(thesis)
    )
    risks_items = "".join(
        f'<div style="display:flex; gap:10px; padding:8px 0; border-bottom:1px solid #3d1a1a;">'
        f'<span style="color:#e05555; font-weight:800; min-width:18px; flex-shrink:0;">{i+1}</span>'
        f'<span style="font-size:0.87em; color:#ddb8b8; line-height:1.65;">{item}</span>'
        f'</div>'
        for i, item in enumerate(risks)
    )

    _section_gap()
    st.markdown(f"""
<div style="
    background: linear-gradient(160deg, #1c1c2e 0%, #1a1a28 100%);
    border: 1px solid #2e2e4e;
    border-radius: 20px;
    padding: 36px 40px 28px;
    box-shadow: 0 8px 48px rgba(0,0,0,0.6), 0 1px 0 rgba(255,255,255,0.04) inset;
    position: relative;
    overflow: hidden;
    margin-bottom: 8px;
">
  <!-- Top-left gloss effect -->
  <div style="position:absolute; top:-60px; left:-60px; width:200px; height:200px;
              background:radial-gradient(circle, rgba(124,92,191,0.12) 0%, transparent 70%);
              pointer-events:none;"></div>

  <!-- Title -->
  <div style="font-size:1.25em; font-weight:800; color:#e0e0f0; margin-bottom:24px;
              display:flex; align-items:center; gap:10px;">
    <span style="font-size:0.85em;">📋</span>
    {company_name} ({ticker}) Investment Report
    <span style="flex:1; height:1px; background:linear-gradient(90deg,#3a3a5a,transparent); margin-left:8px;"></span>
  </div>

  <!-- Verdict banner -->
  <div style="background:{color}18; border:1px solid {color}55; border-radius:14px;
              padding:24px 32px; text-align:center; margin-bottom:24px;">
    <div style="font-size:2.8em; font-weight:900; color:{color}; letter-spacing:6px; line-height:1;">{emoji} {verdict}</div>
    <div style="display:flex; justify-content:center; gap:32px; margin-top:14px; flex-wrap:wrap;">
      <div>
        <div style="font-size:0.7em; color:#888; margin-bottom:3px; letter-spacing:1px;">CONVICTION</div>
        <div style="font-size:0.95em; font-weight:700; color:{color};">{conviction_str}</div>
      </div>
      <div>
        <div style="font-size:0.7em; color:#888; margin-bottom:3px; letter-spacing:1px;">TARGET PRICE</div>
        <div style="font-size:0.95em; font-weight:700; color:#e0e0f0;">{target_str}</div>
      </div>
    </div>
    {basis_html}
  </div>

  <!-- Summary -->
  <div style="background:rgba(255,255,255,0.04); border:1px solid #2e2e4e; border-radius:10px;
              padding:16px 20px; margin-bottom:20px; font-size:0.94em; color:#c8c8e0; line-height:1.8;">
    {summary}
  </div>

  <!-- Investment thesis & risks (flex 2-column) -->
  <div style="display:flex; gap:14px; margin-bottom:20px;">
    <div style="flex:1; background:#0d2010; border:1px solid #1a3d24; border-radius:10px; padding:16px 18px;">
      <div style="color:#34d368; font-weight:800; font-size:0.88em; margin-bottom:10px; letter-spacing:0.5px;">📈 Investment Thesis</div>
      {thesis_items}
    </div>
    <div style="flex:1; background:#200d0d; border:1px solid #3d1a1a; border-radius:10px; padding:16px 18px;">
      <div style="color:#e05555; font-weight:800; font-size:0.88em; margin-bottom:10px; letter-spacing:0.5px;">⚠️ Key Risks</div>
      {risks_items}
    </div>
  </div>

  <!-- Conclusion -->
  <div style="background:linear-gradient(135deg, #1a1230, #1e1540);
              border:1px solid #4a3088; border-left:4px solid #7c5cbf;
              border-radius:12px; padding:22px 26px; box-shadow:0 0 24px rgba(124,92,191,0.15);">
    <div style="font-size:0.68em; font-weight:800; letter-spacing:3px; color:#a080e0; margin-bottom:10px;">✦ CONCLUSION</div>
    <div style="font-size:1.02em; line-height:1.9; color:#d0cce8;">{conclusion}</div>
  </div>

</div>
""", unsafe_allow_html=True)

    _model = __import__('src.config.settings', fromlist=['LLM_MODEL_REPORT']).LLM_MODEL_REPORT
    _time_str = f" · Generated {report_time}" if report_time else ""
    st.caption(f"Generated by AI ({_model}) for informational purposes only. The investor bears sole responsibility for any investment decisions.{_time_str}")


def _build_chat_system_prompt(report: dict, ctx: dict) -> str:
    ticker       = ctx.get("ticker", "")
    company_name = ctx.get("company_name", ticker)
    cur_price    = ctx.get("current_price")
    verdict      = report.get("verdict", "HOLD")
    conviction   = report.get("conviction", "medium")
    target       = report.get("target_price")
    summary      = report.get("summary", "")
    thesis       = report.get("investment_thesis", [])
    risks        = report.get("key_risks", [])
    conclusion   = report.get("conclusion", "")

    price_str = f"${cur_price:,.2f}" if isinstance(cur_price, (int, float)) else str(cur_price or "N/A")
    target_str = ""
    if target and isinstance(cur_price, (int, float)) and cur_price > 0:
        upside = (target / cur_price - 1) * 100
        target_str = f"${target:,.2f} ({upside:+.1f}% vs current)"
    elif target:
        target_str = f"${target:,.2f}"

    lines = [
        f"You are a senior investment analyst who has just completed an analysis of {company_name} ({ticker}).",
        "Answer the user's follow-up questions specifically and clearly, grounded in the analysis data below.",
        "For questions requiring specific numbers (stop-loss, price targets, etc.), always provide a concrete price and rationale.",
        "Respond in English.",
        "",
        "## Completed Analysis Report",
        f"- Ticker: {company_name} ({ticker})",
        f"- Current Price: {price_str}",
        f"- Rating: {verdict}  |  Conviction: {conviction}",
    ]
    if target_str:
        lines.append(f"- Price Target: {target_str}")
    lines += [
        f"- Summary: {summary}",
        "",
        "### Investment Thesis",
        *[f"- {t}" for t in thesis],
        "",
        "### Key Risks",
        *[f"- {r}" for r in risks],
        "",
        "### Conclusion",
        conclusion,
        "",
        "### Market Conditions",
        f"- Risk Level: {ctx.get('market_risk', '–')}",
        f"- {ctx.get('market_summary', '')}",
        "",
        "### Industry Conditions",
        f"- Momentum: {ctx.get('industry_momentum', '–')}",
        f"- {ctx.get('industry_summary', '')}",
        "",
        "### Company Analysis",
        f"- Stance: {ctx.get('company_stance', '–')}",
        f"- {ctx.get('company_summary', '')}",
    ]
    return "\n".join(lines)


def render_chat_section():
    report = st.session_state.get("final_report")
    ctx    = st.session_state.get("chat_context", {})
    if not report or not ctx:
        return

    # Reset chat history when ticker changes
    if st.session_state.get("chat_ticker") != ctx.get("ticker"):
        st.session_state["chat_history"] = []
        st.session_state["chat_ticker"]  = ctx.get("ticker")

    _section_gap()
    _section_header("💬", "Ask Solomon")
    st.caption("Ask anything based on the report.  e.g. *Where's the stop-loss?* / *Is now a good entry?* / *What's the target price rationale?*")

    history: list = st.session_state.setdefault("chat_history", [])

    # ── Declare message container before input box → messages stack above the input (ChatGPT pattern)
    msg_container = st.container()

    # ── Input box (code order: below = lower on page)
    question = st.chat_input("Ask Solomon anything...")

    if question:
        history.append({"role": "user", "content": question})

        system_prompt = _build_chat_system_prompt(report, ctx)
        messages = [{"role": "system", "content": system_prompt}]
        for m in history[-10:]:
            messages.append({"role": m["role"], "content": m["content"]})

        import os
        from openai import OpenAI as _OAI
        _client = _OAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Render existing history + new question + streaming response in container (above)
        with msg_container:
            for msg in history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            with st.chat_message("assistant"):
                stream = _client.chat.completions.create(
                    model=__import__("src.config.settings", fromlist=["LLM_MODEL_REPORT"]).LLM_MODEL_REPORT,
                    messages=messages,
                    temperature=0.4,
                    max_completion_tokens=600,
                    stream=True,
                )
                response_text = st.write_stream(
                    chunk.choices[0].delta.content or ""
                    for chunk in stream
                    if chunk.choices[0].delta.content
                )

        history.append({"role": "assistant", "content": response_text})

    else:
        # Render existing chat history in container (above input box)
        with msg_container:
            for msg in history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
