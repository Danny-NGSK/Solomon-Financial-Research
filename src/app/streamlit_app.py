import sys
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go

project_root = str(Path(__file__).resolve().parents[2])
if project_root not in sys.path:
    sys.path.append(project_root)

LOGO_PATH  = Path(project_root) / "assets" / "logo_transparent.png"
CROWN_PATH = Path(project_root) / "assets" / "crown.png"


def _img_b64(path: Path) -> str:
    import base64
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


@st.cache_data(show_spinner=False)
def _cached_logo_b64() -> str:
    return _img_b64(LOGO_PATH)


@st.cache_data(show_spinner=False)
def _cached_crown_b64() -> str:
    return _img_b64(CROWN_PATH)

from src.data_loader.market_loader import load_market_data
from src.data_loader.industry_loader import load_industry_data
from src.data_loader.company_loader import load_company_data
from src.llm.market_agent import analyze_market
from src.llm.industry_agent import analyze_industry
from src.llm.company_agent import analyze_company
from src.llm.report_generator import generate_final_report
from src.data_loader.trending_loader import load_trending_tickers

from src.ui.common import _SECTOR_COLORS
from src.ui.macro_tab import render_macro_tab
from src.ui.industry_tab import render_industry_tab
from src.ui.company_tab import render_company_tab
from src.ui.news_tab import render_news_tab
from src.ui.report_section import render_final_report, render_chat_section


def inject_global_css():
    st.markdown("""
<style>
/* ── Global font / background ── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Pretendard', -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
}

/* ── Tab styles ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #2a2a3a;
    width: 100%;
}
.stTabs [data-baseweb="tab"] {
    flex: 1;
    justify-content: center;
    padding: 10px 8px;
    border-radius: 8px 8px 0 0;
    font-weight: 600;
    font-size: 0.9em;
    color: #888;
    background: transparent;
    border: none;
}
.stTabs [aria-selected="true"] {
    color: #f5c518 !important;
    background: rgba(245,197,24,0.08) !important;
    border-bottom: 2px solid #f5c518 !important;
}

/* ── st.metric card ── */
[data-testid="stMetric"] {
    background: #13131a;
    border: 1px solid #22222e;
    border-radius: 10px;
    padding: 14px 16px 12px !important;
}
[data-testid="stMetricLabel"] { font-size: 0.78em !important; color: #888 !important; }
[data-testid="stMetricValue"] { font-size: 1.45em !important; font-weight: 700 !important; color: #f0f0f0 !important; }
[data-testid="stMetricDelta"] { font-size: 0.82em !important; }

/* ── DataFrame ── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

/* ── expander ── */
[data-testid="stExpander"] {
    border: 1px solid #22222e !important;
    border-radius: 10px !important;
    background: #13131a !important;
}

/* ── Chat message ── */
[data-testid="stChatMessage"] {
    background: #13131a !important;
    border: 1px solid #22222e !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
}

/* ── Search box ── */
[data-testid="stTextInput"] input {
    border-radius: 8px !important;
}

/* ── Button ── */
[data-testid="stBaseButton-primary"] {
    border-radius: 8px !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px;
}

/* ── Quick Pick card buttons (key="qp_*") ── */
[class*="st-key-qp_"] button {
    background: #13131a !important;
    border: 1px solid #22222e !important;
    border-radius: 10px !important;
    color: #e0e0e0 !important;
    font-weight: 700 !important;
    font-size: 0.88em !important;
    padding: 10px 8px !important;
    height: auto !important;
    min-height: 44px !important;
    line-height: 1.5 !important;
    transition: border-color 0.15s, background 0.15s, color 0.15s !important;
}
[class*="st-key-qp_"] button:hover {
    border-color: #f5c518 !important;
    background: #1a1a24 !important;
    color: #f5c518 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0e0e14; }
::-webkit-scrollbar-thumb { background: #2a2a3a; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3a3a4a; }

/* ── Hide sticky JS iframe ── */
iframe[height="1"] {
    display: block;
    height: 1px !important;
    min-height: 1px !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    overflow: hidden;
}

/* ── Sticky tab header ── */
#solomon-sticky-bar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 99999;
    background: rgba(14,14,22,0.92);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-bottom: 1px solid #2a2a3a;
    padding: 8px 28px;
    display: none;
    align-items: center;
    gap: 10px;
    font-size: 0.9em;
}
</style>
""", unsafe_allow_html=True)

    # ── Sticky tab header JS (injected directly into parent document) ──
    st.iframe("""
<script>
(function() {
  var pd = window.parent.document;
  if (pd.getElementById('solomon-sticky-bar')) return;
  var bar = pd.createElement('div');
  bar.id = 'solomon-sticky-bar';
  bar.style.cssText = [
    'position:fixed','top:0','left:0','right:0','z-index:99999',
    'background:rgba(14,14,22,0.95)','backdrop-filter:blur(10px)',
    '-webkit-backdrop-filter:blur(10px)','border-bottom:1px solid #2a2a3a',
    'padding:9px 28px','display:none','align-items:center','gap:10px',
    'font-size:0.88em','font-family:Inter,sans-serif'
  ].join(';');
  bar.innerHTML =
    '<span style="font-weight:800;letter-spacing:1px;background:linear-gradient(90deg,#f5c518,#c8960c);' +
    '-webkit-background-clip:text;-webkit-text-fill-color:transparent;">Solomon</span>' +
    '<span style="color:#3a3a4a;font-size:1.3em;line-height:1;">|</span>' +
    '<span id="solomon-sticky-label" style="color:#e0e0e0;font-weight:600;"></span>';
  pd.body.appendChild(bar);
  function getActiveTab() {
    var tab = pd.querySelector('.stTabs [role="tab"][aria-selected="true"]');
    return tab ? tab.innerText.trim() : '';
  }
  function update() {
    var scroller = pd.querySelector('[data-testid="stAppViewContainer"] > section.main')
                || pd.querySelector('section.main')
                || pd.querySelector('.main');
    var scrollY = scroller ? scroller.scrollTop : pd.documentElement.scrollTop;
    var label = getActiveTab();
    if (scrollY > 150 && label) {
      bar.style.display = 'flex';
      pd.getElementById('solomon-sticky-label').innerText = label;
    } else {
      bar.style.display = 'none';
    }
  }
  [pd.querySelector('[data-testid="stAppViewContainer"] > section.main'),
   pd.querySelector('section.main'), pd.querySelector('.main'),
   pd.documentElement, window.parent].filter(Boolean).forEach(function(el) {
    try { el.addEventListener('scroll', update, {passive:true}); } catch(e) {}
  });
  pd.addEventListener('click', function() { setTimeout(update, 150); }, true);
})();
</script>
""", height=1)


# ─────────────────────────────────────────
# Cached data loaders
# ─────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def cached_market_data():
    return load_market_data()


@st.cache_data(ttl=900, show_spinner=False)
def cached_trending():
    return load_trending_tickers(count=7)


@st.cache_data(ttl=600, show_spinner=False)
def cached_industry_data(ticker: str):
    return load_industry_data(ticker)


@st.cache_data(ttl=600, show_spinner=False)
def cached_company_data(ticker: str):
    return load_company_data(ticker)


def main():
    st.set_page_config(
        page_title="Solomon Financial Research",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    inject_global_css()

    # ── Header ──
    if CROWN_PATH.exists():
        crown_b64 = _cached_crown_b64()
        st.markdown(f"""
<div style="display:flex; align-items:center; padding: 12px 0 0; gap: 20px;">
  <img src="data:image/png;base64,{crown_b64}"
       style="height:80px; object-fit:contain; flex-shrink:0;">
  <div style="flex:1; line-height:1.15;">
    <div style="font-size:3.4em; font-weight:800; letter-spacing:2px;
                background: linear-gradient(90deg, #f5c518, #c8960c);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
      Solomon
    </div>
    <div style="font-size:1.05em; letter-spacing:7px; color:#888; font-weight:400; margin-top:2px;">
      FINANCIAL RESEARCH
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.title("📈 Solomon Financial Research")
    st.markdown("<hr style='margin: 14px 0 20px; border-color:#2a2a3a;'>", unsafe_allow_html=True)

    from streamlit_searchbox import st_searchbox
    from src.config.company_search import search_ticker, resolve_ticker

    def _on_searchbox_submit(value):
        if value:
            st.session_state["_submitted_query"] = str(value)
        st.session_state["_analyze_trigger"] = True

    col_search, col_btn = st.columns([3, 1], vertical_alignment="top")
    with col_search:
        selected = st_searchbox(
            search_ticker,
            placeholder="Enter ticker or company name (e.g. NVDA, Apple, Tesla...)",
            label="",
            key="company_searchbox",
            clear_on_submit=False,
            default_use_searchterm=True,
            submit_function=_on_searchbox_submit,
        )
    with col_btn:
        start_btn = st.button("🚀 Analyze", width='stretch', type="primary")

    # Enter or button click triggers analysis
    enter_trigger  = st.session_state.pop("_analyze_trigger", False)
    submitted_query = st.session_state.pop("_submitted_query", "")
    quick_pick     = st.session_state.pop("_quick_pick", "")
    do_analyze = start_btn or enter_trigger or bool(quick_pick)

    # selected can be None on Enter (timing issue) — fall back to submitted_query / quick_pick
    raw = quick_pick or selected or submitted_query
    search_query = resolve_ticker(raw) if raw else ""

    if do_analyze and not search_query:
        st.warning("Please enter a ticker or company name.")

    # Store data and analysis results in session_state on Analyze button click or Enter
    if do_analyze and search_query:
        import random, time

        QUOTES = [
            # Warren Buffett
            ("The stock market is a device for transferring money\nfrom the impatient to the patient.", "Warren Buffett"),
            ("Risk comes from not knowing what you're doing.", "Warren Buffett"),
            ("It's far better to buy a wonderful company at a fair price\nthan a fair company at a wonderful price.", "Warren Buffett"),
            ("The most important quality for an investor is temperament,\nnot intellect.", "Warren Buffett"),
            ("Be fearful when others are greedy,\nand greedy when others are fearful.", "Warren Buffett"),
            ("Diversification is protection against ignorance.\nIt makes little sense if you know what you are doing.", "Warren Buffett"),
            ("Price is what you pay. Value is what you get.", "Warren Buffett"),
            ("Our favorite holding period is forever.", "Warren Buffett"),
            ("Never invest in a business you can't understand.", "Warren Buffett"),
            ("It's only when the tide goes out that you learn\nwho has been swimming naked.", "Warren Buffett"),
            # Benjamin Graham
            ("In the short run, the market is a voting machine.\nIn the long run, it is a weighing machine.", "Benjamin Graham"),
            ("Mr. Market knocks on your door every morning\noffering to buy or sell.", "Benjamin Graham"),
            ("The investor's chief problem — even his worst enemy —\nis likely to be himself.", "Benjamin Graham"),
            ("Successful investing is about managing risk,\nnot avoiding it.", "Benjamin Graham"),
            # Peter Lynch
            ("Don't try to predict the market — react to it.", "Peter Lynch"),
            ("If you can't explain why you own a stock,\nyou have no business owning it.", "Peter Lynch"),
            ("Know what you own, and know why you own it.", "Peter Lynch"),
            ("The real key to making money in stocks\nis not to get scared out of them.", "Peter Lynch"),
            ("Behind every stock is a company.\nFind out what it's doing.", "Peter Lynch"),
            # Charlie Munger
            ("Invert, always invert.", "Charlie Munger"),
            ("All I want to know is where I'm going to die,\nso I'll never go there.", "Charlie Munger"),
            ("The best thing a human being can do\nis to help another human being know more.", "Charlie Munger"),
            ("Show me the incentive and I'll show you the outcome.", "Charlie Munger"),
            # Others
            ("Compound interest is the eighth wonder of the world.\nHe who understands it, earns it; he who doesn't, pays it.", "Albert Einstein"),
            ("The four most dangerous words in investing are:\n'This time it's different.'", "John Templeton"),
            ("The stock market is filled with individuals who know\nthe price of everything, but the value of nothing.", "Philip Fisher"),
            ("An investment in knowledge pays the best interest.", "Benjamin Franklin"),
            ("The individual investor should act consistently\nas an investor and not as a speculator.", "Benjamin Graham"),
            ("Wide diversification is only required when investors\ndo not understand what they are doing.", "Warren Buffett"),
            ("You get recessions, you have stock market declines.\nIf you don't understand that's going to happen,\nthen you're not ready.", "Peter Lynch"),
            ("The market is a pendulum that forever swings\nbetween unsustainable optimism and unjustified pessimism.", "Benjamin Graham"),
            ("In investing, what is comfortable is rarely profitable.", "Robert Arnott"),
            ("The secret to investing is to figure out the value\nof something — and then pay a lot less.", "Joel Greenblatt"),
        ]

        quote_text, quote_author = random.choice(QUOTES)

        loading_placeholder = st.empty()

        def _show_loading(stage: str, step: int):
            steps = ["📡 Fetching data (parallel)", "🤖 Running AI analysis", "✅ Complete"]
            bar_filled = "█" * step
            bar_empty  = "░" * (3 - step)
            loading_placeholder.markdown(f"""
<style>
@keyframes pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.5; }}
}}
.loading-card {{
  background: #16161e;
  border: 1px solid #2a2a3a;
  border-radius: 14px;
  padding: 40px 48px;
  text-align: center;
  max-width: 600px;
  margin: 40px auto;
}}
.loading-quote {{
  font-size: 1.15em;
  color: #e0e0e0;
  line-height: 1.7;
  font-style: italic;
  white-space: pre-line;
  margin-bottom: 10px;
}}
.loading-author {{
  font-size: 0.85em;
  color: #4C9BE8;
  margin-bottom: 32px;
}}
.loading-stage {{
  font-size: 0.9em;
  color: #aaa;
  animation: pulse 1.5s ease-in-out infinite;
  margin-bottom: 12px;
}}
.loading-bar {{
  font-size: 1.1em;
  letter-spacing: 3px;
  color: #4C9BE8;
}}
</style>
<div class="loading-card">
  <div style="font-size:2.4em; margin-bottom:20px;">📊</div>
  <div class="loading-quote">"{quote_text}"</div>
  <div class="loading-author">— {quote_author}</div>
  <div class="loading-stage">{stage}</div>
  <div class="loading-bar">{bar_filled}{bar_empty}</div>
</div>
""", unsafe_allow_html=True)

        _show_loading("📡 Step 1/3 · Fetching market, industry, company data...", 1)
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=3) as executor:
            fut_market   = executor.submit(cached_market_data)
            fut_industry = executor.submit(cached_industry_data, search_query)
            fut_company  = executor.submit(cached_company_data,  search_query)
            market_data   = fut_market.result()
            industry_data = fut_industry.result()
            company_data  = fut_company.result()

        # ── Validation: if no price data and name not found, mark as invalid ──
        _price_check = company_data.get("price", {})
        _name_check  = company_data.get("company_name", search_query)
        _not_found   = _price_check.get("latest") is None and _name_check == search_query

        if _not_found:
            loading_placeholder.empty()
            st.session_state["analyzed"]     = False
            st.session_state["search_error"] = search_query
            st.rerun()

        st.session_state.pop("search_error", None)
        _show_loading("🤖 Step 2/3 · Running AI analysis (Macro → Industry → Company)...", 2)
        try:
            market_analysis = analyze_market(market_data)
        except Exception as e:
            st.error(f"[Macro] AI analysis failed: {e}")
            market_analysis = {"market_summary": "Analysis failed", "risk_level": "medium", "key_points": []}

        try:
            industry_analysis = analyze_industry(industry_data, market_analysis)
        except Exception as e:
            st.error(f"[Industry] AI analysis failed: {e}")
            industry_analysis = {"industry_summary": "Analysis failed", "momentum": "neutral", "key_points": []}

        try:
            company_analysis = analyze_company(company_data, market_analysis)
        except Exception as e:
            st.error(f"[Company] AI analysis failed: {e}")
            company_analysis = {"company_summary": "Analysis failed", "investment_stance": "neutral", "key_points": []}

        _show_loading("✅ Step 3/3 · Rendering results...", 3)
        time.sleep(0.3)
        loading_placeholder.empty()

        st.session_state["analyzed"]          = True
        st.session_state["ticker"]            = search_query
        st.session_state["market_data"]       = market_data
        st.session_state["industry_data"]     = industry_data
        st.session_state["company_data"]      = company_data
        st.session_state["market_analysis"]   = market_analysis
        st.session_state["industry_analysis"] = industry_analysis
        st.session_state["company_analysis"]  = company_analysis
        st.session_state["final_report"]      = None   # Reset the report

    # Show landing page if no analysis results
    if not st.session_state.get("analyzed"):
        # ── Search failure error UI ──
        search_error = st.session_state.pop("search_error", None)
        if search_error:
            st.markdown(
                f'<div style="max-width:520px; margin:24px auto; background:#1a1014; '
                f'border:1px solid #ef444440; border-left:4px solid #ef4444; '
                f'border-radius:12px; padding:24px 28px; text-align:center;">'
                f'<div style="font-size:2em; margin-bottom:12px;">🔍</div>'
                f'<div style="font-size:1.05em; font-weight:700; color:#ef4444; margin-bottom:8px;">'
                f'No results found for "{search_error}"</div>'
                f'<div style="font-size:0.9em; color:#aaa; line-height:1.7;">'
                f'Please enter a valid ticker symbol or company name.<br>'
                f'<span style="color:#555;">e.g. AAPL · NVDA · TSLA · Apple · Tesla</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        # ── Subtitle ──
        st.markdown(
            '<p style="text-align:center; color:#aaa; font-size:1.05em; '
            'max-width:560px; margin: 4px auto 36px;">'
            'Macro · Industry · Company — 3-stage AI research in seconds.</p>',
            unsafe_allow_html=True,
        )

        # ── 3-stage flow visualization ──
        st.markdown("""
<style>
@keyframes flow-right {
  0%   { opacity: 0.25; transform: translateX(-8px); }
  55%  { opacity: 1;    transform: translateX(4px);  }
  100% { opacity: 0.25; transform: translateX(-8px); }
}
@keyframes flow-head {
  0%   { opacity: 0.25; transform: translateX(-6px); }
  55%  { opacity: 1;    transform: translateX(5px);  }
  100% { opacity: 0.25; transform: translateX(-6px); }
}
.flow-arrow { flex-shrink:0; display:flex; align-items:center; }
.flow-arrow-line {
  width:52px; height:3px; border-radius:2px;
  animation: flow-right 1.6s ease-in-out infinite;
}
.flow-arrow-head {
  width:0; height:0;
  border-top:7px solid transparent;
  border-bottom:7px solid transparent;
  margin-left:-1px;
  animation: flow-head 1.6s ease-in-out infinite;
}
</style>
<div style="display:flex; align-items:center; gap:8px; max-width:860px; margin:0 auto 40px;">

  <!-- Stage 1 -->
  <div style="flex:1; background:#16161e; border:1px solid #2a2a3a; border-radius:14px;
              padding:28px 20px; text-align:center;">
    <div style="font-size:2em; margin-bottom:10px;">🌍</div>
    <div style="font-size:0.68em; font-weight:800; letter-spacing:2px; color:#f5c518; margin-bottom:6px;">STAGE 1</div>
    <div style="font-weight:700; font-size:0.97em; color:#e0e0e0; margin-bottom:10px;">Macro & Market</div>
    <div style="font-size:0.81em; color:#666; line-height:1.65;">
      Interest rates · CPI<br>VIX · Fear &amp; Greed<br>Sector performance
    </div>
  </div>

  <!-- Arrow 1 -->
  <div class="flow-arrow">
    <div class="flow-arrow-line" style="background:linear-gradient(90deg,#f5c518,#818CF8);"></div>
    <div class="flow-arrow-head" style="border-left:11px solid #818CF8;"></div>
  </div>

  <!-- Stage 2 -->
  <div style="flex:1; background:#16161e; border:1px solid #2a2a3a; border-radius:14px;
              padding:28px 20px; text-align:center;">
    <div style="font-size:2em; margin-bottom:10px;">🏭</div>
    <div style="font-size:0.68em; font-weight:800; letter-spacing:2px; color:#818CF8; margin-bottom:6px;">STAGE 2</div>
    <div style="font-weight:700; font-size:0.97em; color:#e0e0e0; margin-bottom:10px;">Industry</div>
    <div style="font-size:0.81em; color:#666; line-height:1.65;">
      Sector ETF trend<br>Peer comparison<br>Industry momentum
    </div>
  </div>

  <!-- Arrow 2 -->
  <div class="flow-arrow">
    <div class="flow-arrow-line" style="background:linear-gradient(90deg,#818CF8,#00CC96);"></div>
    <div class="flow-arrow-head" style="border-left:11px solid #00CC96;"></div>
  </div>

  <!-- Stage 3 -->
  <div style="flex:1; background:#16161e; border:1px solid #2a2a3a; border-radius:14px;
              padding:28px 20px; text-align:center;">
    <div style="font-size:2em; margin-bottom:10px;">🏢</div>
    <div style="font-size:0.68em; font-weight:800; letter-spacing:2px; color:#00CC96; margin-bottom:6px;">STAGE 3</div>
    <div style="font-weight:700; font-size:0.97em; color:#e0e0e0; margin-bottom:10px;">Company</div>
    <div style="font-size:0.81em; color:#666; line-height:1.65;">
      Valuation · Financials<br>Analyst consensus<br>AI investment thesis
    </div>
  </div>

</div>
""", unsafe_allow_html=True)

        # ── Quick Pick (today's top volume) ──
        trending = cached_trending()
        st.markdown(
            '<div style="text-align:center; font-size:0.75em; color:#555; '
            'letter-spacing:1.5px; font-weight:700; margin-bottom:12px;">'
            '🔥 TODAY\'S MOST ACTIVE</div>',
            unsafe_allow_html=True,
        )
        qcols = st.columns(len(trending))
        for col, item in zip(qcols, trending):
            ticker_q   = item["ticker"]
            chg        = item.get("change_pct")
            chg_str    = f"{chg:+.2f}%" if chg is not None else "–"
            sector_q   = item.get("sector", "")
            dot_color  = _SECTOR_COLORS.get(sector_q, "")
            dot        = f"🔵" if not dot_color else ""   # fallback: no dot if no color mapping
            # Display sector color dot on button label as unicode circle
            # Since CSS applies a single text color inside buttons, the dot is handled as a separate label prefix
            chg_color_val = "#26a69a" if chg is not None and chg >= 0 else "#ef5350"
            label = ticker_q
            with col:
                # Sector color dot (overlaid above button via CSS)
                if dot_color:
                    st.markdown(
                        f'<div style="text-align:right; margin-bottom:-22px; padding-right:6px; '
                        f'position:relative; z-index:1; pointer-events:none;">'
                        f'<span style="display:inline-block; width:8px; height:8px; border-radius:50%; '
                        f'background:{dot_color}; opacity:0.85;"></span></div>',
                        unsafe_allow_html=True,
                    )
                if st.button(label, key=f"qp_{ticker_q}", width='stretch'):
                    st.session_state["_quick_pick"] = ticker_q
                    st.rerun()
                # Return rate — displayed cleanly just below button (no overlap)
                st.markdown(
                    f'<div style="text-align:center; margin-top:3px; margin-bottom:2px; '
                    f'font-size:0.78em; font-weight:700; color:{chg_color_val}; line-height:1;">'
                    f'{chg_str}</div>',
                    unsafe_allow_html=True,
                )
        st.stop()

    # Render tabs if analysis results are in session_state
    if st.session_state.get("analyzed"):
        ticker            = st.session_state["ticker"]
        market_data       = st.session_state["market_data"]
        industry_data     = st.session_state["industry_data"]
        company_data      = st.session_state["company_data"]
        market_analysis   = st.session_state["market_analysis"]
        industry_analysis = st.session_state["industry_analysis"]
        company_analysis  = st.session_state["company_analysis"]

        from src.config.settings import LLM_MODEL_REPORT

        @st.fragment
        def _report_section():
            already_reported = bool(st.session_state.get("final_report"))

            if not already_reported:
                col_banner, col_btn = st.columns([3, 1], vertical_alignment="center")
                with col_banner:
                    st.markdown(
                        f'<div style="background:linear-gradient(90deg,#1c1a2e,#16161e); '
                        f'border:1px solid #6f42c150; border-left:4px solid #a78bfa; '
                        f'border-radius:10px; padding:12px 18px;">'
                        f'<div style="font-size:0.72em; font-weight:800; letter-spacing:2px; color:#a78bfa; margin-bottom:4px;">✦ AI INVESTMENT REPORT</div>'
                        f'<div style="font-size:0.85em; color:#888;">Synthesizes Macro → Industry → Company 3-stage analysis into a final investment opinion. &nbsp;<span style="color:#555; font-size:0.9em;">Model: {LLM_MODEL_REPORT}</span></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    report_btn = st.button("📋 Generate Report", width='stretch')

                if report_btn:
                    with st.spinner("Generating investment report..."):
                        try:
                            from datetime import datetime
                            st.session_state["final_report"] = generate_final_report(
                                ticker=ticker,
                                market_analysis=market_analysis,
                                industry_analysis=industry_analysis,
                                company_analysis=company_analysis,
                                company_data=company_data,
                                industry_data=industry_data,
                            )
                            st.session_state["report_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                            price_data = company_data.get("price", {})
                            st.session_state["chat_context"] = {
                                "ticker":            ticker,
                                "company_name":      company_data.get("company_name", ticker),
                                "current_price":     price_data.get("latest"),
                                "market_risk":       market_analysis.get("risk_level", "–"),
                                "market_summary":    market_analysis.get("market_summary", ""),
                                "industry_momentum": industry_analysis.get("momentum", "–"),
                                "industry_summary":  industry_analysis.get("industry_summary", ""),
                                "company_stance":    company_analysis.get("investment_stance", "–"),
                                "company_summary":   company_analysis.get("company_summary", ""),
                            }
                            st.session_state["chat_history"] = []
                            st.session_state["chat_ticker"]  = ticker
                        except Exception as e:
                            st.error(f"Report generation failed: {e}")

            if st.session_state.get("final_report"):
                render_final_report(
                    st.session_state["final_report"],
                    ticker=ticker,
                    company_name=company_data.get("company_name", ticker),
                    report_time=st.session_state.get("report_timestamp", ""),
                )
                render_chat_section()

        _report_section()
        st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

        tab1, tab2, tab3, tab4 = st.tabs(
            ["🌍 Macro & Market", "🏭 Industry", "🏢 Company", "📰 Recent News"]
        )

        with tab1:
            render_macro_tab(market_data, market_analysis)

        with tab2:
            render_industry_tab(industry_data, industry_analysis)

        with tab3:
            render_company_tab(company_data, company_analysis, industry_data)

        with tab4:
            render_news_tab(
                company_data.get("news", []),
                ticker=ticker,
                company_name=company_data.get("company_name", ticker),
            )


if __name__ == "__main__":
    main()
