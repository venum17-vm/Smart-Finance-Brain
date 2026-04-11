"""
app.py — Smart Finance Brain v6.1
Dark Gold Bloomberg-inspired UI | Groq Llama-3 AI | Full Finance Suite

FIX v6.1: Corrected groq_engine import (was: from modules import groq_engine → import groq_engine)
UI v6.1: Premium HTML/CSS/JS animations, glow effects, animated cards, ticker, glassmorphism
"""
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os, sys, io

_ROOT    = os.path.dirname(os.path.abspath(__file__))
_MODULES = os.path.join(_ROOT, "modules")
for _p in [_ROOT, _MODULES]:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import database           as db
import email_service      as es
import groq_engine        as ai          # ← FIX: was "from modules import groq_engine as ai"
from modules import finance_manager    as fm
from modules import obligation_manager as om
from modules import document_manager  as dm
from modules import file_processor    as fp

st.set_page_config(page_title="Smart Finance Brain", page_icon="💎",
                   layout="wide", initial_sidebar_state="expanded")

db.init_global_database()
if st.session_state.get('logged_in') and st.session_state.get('user'):
    phone = st.session_state['user'].get('phone', '')
    if phone:
        db.set_current_user(phone)
        om.update_overdue_statuses()

CHART_COLORS = ['#FFD700','#FFA500','#00D4AA','#7C3AED','#3B82F6',
                '#EF4444','#10B981','#EC4899','#8B5CF6','#06B6D4']

CAT_ICONS = {
    "Food & Dining":"🍽️","Transportation":"🚗","Shopping":"🛍️",
    "Entertainment":"🎬","Bills & Utilities":"⚡","Health":"🏥",
    "Education":"📚","Travel":"✈️","Investment":"📈","Other":"💼"
}


# ══════════════════════════════════════════════════════════════════════════════
#  PREMIUM DARK GOLD CSS + HTML/JS ENHANCEMENTS
# ══════════════════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
  --gold:        #FFD700;
  --gold-dim:    #C9A227;
  --gold-glow:   rgba(255,215,0,0.20);
  --gold-soft:   rgba(255,215,0,0.07);
  --gold-pulse:  rgba(255,215,0,0.35);
  --teal:        #00D4AA;
  --teal-soft:   rgba(0,212,170,0.10);
  --bg-base:     #040912;
  --bg-card:     #09142A;
  --bg-panel:    #0C1830;
  --bg-hover:    #102040;
  --border:      rgba(255,215,0,0.10);
  --border-hi:   rgba(255,215,0,0.30);
  --text-primary:   #EDE8D8;
  --text-secondary: #7A8BA0;
  --text-muted:     #394556;
  --red:    #EF4444;
  --green:  #10B981;
  --blue:   #3B82F6;
  --purple: #7C3AED;
}

* { box-sizing: border-box; }
html, body, [class*="css"] {
  font-family: 'Inter', sans-serif;
  color: var(--text-primary);
}

/* ── APP BACKGROUND with subtle animated gradient ── */
.stApp {
  background: var(--bg-base);
  background-image:
    radial-gradient(ellipse 80% 60% at 10% 10%, rgba(255,215,0,0.05) 0%, transparent 60%),
    radial-gradient(ellipse 60% 50% at 90% 90%, rgba(0,212,170,0.04) 0%, transparent 60%),
    radial-gradient(ellipse 40% 40% at 50% 50%, rgba(59,130,246,0.02) 0%, transparent 60%);
  min-height: 100vh;
}

/* ── HIDE STREAMLIT CHROME ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0.5rem !important; max-width: 1400px !important; }

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #020810 0%, #050F1C 60%, #040C18 100%) !important;
  border-right: 1px solid var(--border) !important;
  box-shadow: 4px 0 32px rgba(0,0,0,0.7);
}
section[data-testid="stSidebar"] * { color: var(--text-primary) !important; }
section[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: 1px solid var(--border) !important;
  color: var(--text-secondary) !important;
  border-radius: 9px !important;
  font-size: 0.83rem !important;
  font-weight: 500 !important;
  padding: 9px 14px !important;
  text-align: left !important;
  box-shadow: none !important;
  transition: all 0.25s ease !important;
  letter-spacing: 0.01em !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--gold-soft) !important;
  border-color: rgba(255,215,0,0.25) !important;
  color: var(--gold) !important;
  box-shadow: 0 0 12px rgba(255,215,0,0.08) !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: linear-gradient(135deg, rgba(255,215,0,0.12), rgba(255,165,0,0.08)) !important;
  border-color: rgba(255,215,0,0.30) !important;
  color: var(--gold) !important;
  box-shadow: 0 0 16px rgba(255,215,0,0.10) !important;
}

/* ── METRIC CARDS ── */
[data-testid="metric-container"] {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px 22px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.3s, transform 0.25s, box-shadow 0.3s;
}
[data-testid="metric-container"]:hover {
  border-color: rgba(255,215,0,0.25);
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(255,215,0,0.08);
}
[data-testid="metric-container"]::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, var(--gold), var(--teal), transparent);
}
[data-testid="metric-container"]::after {
  content: '';
  position: absolute; top: 0; right: 0; width: 80px; height: 80px;
  background: radial-gradient(ellipse at top right, var(--gold-soft), transparent);
  pointer-events: none;
}
[data-testid="metric-container"] label {
  color: var(--text-secondary) !important;
  font-size: 0.70rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.10em !important;
  text-transform: uppercase !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
  color: var(--gold) !important;
  font-size: 1.7rem !important;
  font-weight: 800 !important;
  font-family: 'JetBrains Mono', monospace !important;
  text-shadow: 0 0 20px rgba(255,215,0,0.25) !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
  font-size: 0.76rem !important;
}

/* ── BUTTONS ── */
.stButton > button {
  background: linear-gradient(135deg, #FFD700, #F59E0B) !important;
  color: #060C1A !important;
  border: none !important;
  border-radius: 9px !important;
  font-weight: 700 !important;
  font-size: 0.84rem !important;
  padding: 10px 20px !important;
  transition: all 0.25s ease !important;
  box-shadow: 0 4px 16px rgba(255,215,0,0.22) !important;
  letter-spacing: 0.02em !important;
}
.stButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 28px rgba(255,215,0,0.40) !important;
  background: linear-gradient(135deg, #FFE033, #FBB040) !important;
}
.stButton > button:active {
  transform: translateY(0) !important;
}
.stButton > button[kind="secondary"] {
  background: var(--bg-card) !important;
  color: var(--text-secondary) !important;
  border: 1px solid var(--border) !important;
  box-shadow: none !important;
}
.stButton > button[kind="secondary"]:hover {
  background: var(--bg-hover) !important;
  border-color: rgba(255,215,0,0.25) !important;
  color: var(--gold) !important;
  box-shadow: 0 0 12px rgba(255,215,0,0.08) !important;
}

/* ── INPUTS ── */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stDateInput input, .stSelectbox > div > div {
  background: var(--bg-panel) !important;
  color: var(--text-primary) !important;
  border: 1px solid rgba(255,215,0,0.12) !important;
  border-radius: 9px !important;
  font-family: 'Inter', sans-serif !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
  border-color: rgba(255,215,0,0.40) !important;
  box-shadow: 0 0 0 3px rgba(255,215,0,0.06) !important;
  outline: none !important;
}
.stTextInput label, .stTextArea label, .stNumberInput label,
.stSelectbox label, .stDateInput label {
  color: var(--text-secondary) !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.04em !important;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--bg-card);
  border-radius: 11px;
  padding: 4px;
  gap: 3px;
  border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
  background: transparent;
  color: var(--text-secondary) !important;
  border-radius: 8px;
  padding: 8px 16px;
  font-weight: 600;
  font-size: 0.82rem;
  transition: all 0.2s;
  border: none !important;
}
.stTabs [data-baseweb="tab"]:hover {
  color: var(--gold) !important;
  background: var(--gold-soft) !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, #FFD700, #F59E0B) !important;
  color: #060C1A !important;
  box-shadow: 0 2px 10px rgba(255,215,0,0.30) !important;
}

/* ── DATAFRAME ── */
.stDataFrame, [data-testid="stDataFrame"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  overflow: hidden !important;
}

/* ── EXPANDER ── */
.stExpander {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  transition: border-color 0.2s !important;
}
.stExpander:hover {
  border-color: rgba(255,215,0,0.20) !important;
}
.stExpander summary {
  color: var(--text-primary) !important;
  font-weight: 600 !important;
}

/* ── PROGRESS BAR ── */
.stProgress > div > div {
  background: linear-gradient(90deg, var(--gold), var(--teal)) !important;
  border-radius: 4px !important;
  box-shadow: 0 0 8px rgba(255,215,0,0.3) !important;
}
.stProgress > div {
  background: rgba(255,255,255,0.05) !important;
  border-radius: 4px !important;
}

/* ── ALERTS ── */
.stSuccess { background: rgba(16,185,129,0.07) !important; border-left: 3px solid var(--green) !important; border-radius: 9px !important; }
.stWarning { background: rgba(245,158,11,0.07) !important; border-left: 3px solid #F59E0B !important; border-radius: 9px !important; }
.stError   { background: rgba(239,68,68,0.07)  !important; border-left: 3px solid var(--red) !important; border-radius: 9px !important; }
.stInfo    { background: rgba(59,130,246,0.07) !important; border-left: 3px solid var(--blue) !important; border-radius: 9px !important; }

/* ── CHAT ── */
[data-testid="stChatMessage"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  margin-bottom: 8px !important;
}
[data-testid="stChatInputTextArea"] {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: 11px !important;
  color: var(--text-primary) !important;
}

/* ── CUSTOM HTML COMPONENTS ── */
.page-header {
  background: linear-gradient(135deg, rgba(255,215,0,0.05), rgba(0,212,170,0.02));
  border: 1px solid var(--border);
  border-top: 2px solid var(--gold);
  border-radius: 18px;
  padding: 22px 30px;
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
}
.page-header::before {
  content: '';
  position: absolute; top: -50%; right: -10%; width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(255,215,0,0.04), transparent 70%);
  pointer-events: none;
}
.page-header h1 {
  color: var(--gold);
  font-size: 1.75rem;
  font-weight: 900;
  margin: 0;
  letter-spacing: -0.025em;
  text-shadow: 0 0 40px rgba(255,215,0,0.20);
}
.page-header p { color: var(--text-secondary); margin: 5px 0 0; font-size: 0.84rem; }

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 16px;
  transition: border-color 0.25s, box-shadow 0.25s;
  position: relative;
  overflow: hidden;
}
.card:hover {
  border-color: rgba(255,215,0,0.18);
  box-shadow: 0 4px 24px rgba(255,215,0,0.05);
}
.card-header {
  font-size: 0.70rem;
  font-weight: 800;
  color: var(--text-secondary);
  letter-spacing: 0.10em;
  text-transform: uppercase;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.danger-card {
  background: rgba(239,68,68,0.04);
  border: 1px solid rgba(239,68,68,0.18);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 16px;
}

/* ── LOGIN PAGE ── */
.login-wrap {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}
.login-logo { text-align: center; margin-bottom: 28px; }
.login-logo-icon {
  font-size: 3.8rem;
  display: block;
  margin-bottom: 10px;
  filter: drop-shadow(0 0 28px rgba(255,215,0,0.50));
  animation: float 3s ease-in-out infinite;
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-8px); }
}
.login-logo h1 {
  color: var(--gold);
  font-size: 2.1rem;
  font-weight: 900;
  margin: 0;
  letter-spacing: -0.035em;
  text-shadow: 0 0 40px rgba(255,215,0,0.30);
}
.login-logo p { color: var(--text-secondary); font-size: 0.88rem; margin: 6px 0 0; }
.login-box {
  background: var(--bg-card);
  border: 1px solid rgba(255,215,0,0.15);
  border-top: 2px solid var(--gold);
  border-radius: 22px;
  padding: 38px;
  width: 100%;
  max-width: 490px;
  box-shadow: 0 28px 80px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,215,0,0.04);
  backdrop-filter: blur(10px);
}
.feature-row {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  justify-content: center;
  margin-top: 14px;
}
.feature-tag {
  background: rgba(255,215,0,0.06);
  border: 1px solid rgba(255,215,0,0.15);
  border-radius: 20px;
  padding: 4px 12px;
  font-size: 0.70rem;
  color: var(--gold);
  font-weight: 600;
  transition: all 0.2s;
}
.feature-tag:hover {
  background: rgba(255,215,0,0.12);
  border-color: rgba(255,215,0,0.30);
}

/* ── STAT ROW ── */
.stat-row {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.stat-item {
  flex: 1;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
  text-align: center;
  transition: all 0.25s;
}
.stat-item:hover {
  border-color: rgba(255,215,0,0.20);
  background: var(--bg-hover);
  transform: translateY(-2px);
}
.stat-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--gold);
  text-shadow: 0 0 16px rgba(255,215,0,0.20);
}
.stat-label {
  font-size: 0.68rem;
  color: var(--text-muted);
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  margin-top: 3px;
}

/* ── TICKER BAR ── */
.ticker-bar {
  background: linear-gradient(90deg, #060E1E, #08132A, #060E1E);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 7px 20px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.73rem;
  color: var(--text-secondary);
  margin-bottom: 18px;
  white-space: nowrap;
  overflow: hidden;
  position: relative;
}
.ticker-bar::before {
  content: '';
  position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: linear-gradient(180deg, var(--gold), var(--teal));
  border-radius: 10px 0 0 10px;
}
.ticker-bar span.up   { color: var(--green); font-weight: 700; }
.ticker-bar span.down { color: var(--red); font-weight: 700; }
.ticker-bar span.gold { color: var(--gold); font-weight: 700; }

/* ── BADGES ── */
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.70rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.badge-pending  { background: rgba(245,158,11,0.14); color: #F59E0B; border: 1px solid rgba(245,158,11,0.25); }
.badge-paid     { background: rgba(16,185,129,0.14); color: var(--green); border: 1px solid rgba(16,185,129,0.25); }
.badge-overdue  { background: rgba(239,68,68,0.14);  color: var(--red); border: 1px solid rgba(239,68,68,0.25); }
.badge-info     { background: rgba(59,130,246,0.14); color: var(--blue); border: 1px solid rgba(59,130,246,0.25); }

/* ── PULSE GLOW for active elements ── */
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 8px rgba(255,215,0,0.15); }
  50%       { box-shadow: 0 0 20px rgba(255,215,0,0.35); }
}
.glow-active { animation: pulse-glow 2.5s ease-in-out infinite; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: rgba(255,215,0,0.18); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,215,0,0.36); }

/* ── PLOTLY CHART CONTAINER ── */
.js-plotly-plot {
  border-radius: 12px !important;
  overflow: hidden !important;
}

/* ── CHECKBOX RADIO ── */
.stCheckbox label, .stRadio label { color: var(--text-secondary) !important; font-size: 0.82rem !important; }
.stCheckbox [data-testid="stCheckbox"] > div { border-color: var(--border) !important; }

/* ── SLIDER ── */
.stSlider [data-testid="stSliderThumb"] {
  background: var(--gold) !important;
  box-shadow: 0 0 8px rgba(255,215,0,0.4) !important;
}
.stSlider [data-testid="stSliderTrack"] > div:first-child {
  background: linear-gradient(90deg, var(--gold), var(--teal)) !important;
}

/* ── DIVIDER ── */
hr { border-color: rgba(255,215,0,0.08) !important; }

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] {
  background: var(--bg-panel) !important;
  border: 1px dashed rgba(255,215,0,0.20) !important;
  border-radius: 12px !important;
  transition: border-color 0.2s, background 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: rgba(255,215,0,0.40) !important;
  background: rgba(255,215,0,0.03) !important;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _phone() -> str:
    return st.session_state.get('user', {}).get('phone', '')

def _user() -> dict:
    return st.session_state.get('user', {})

def dark_layout(fig, title="", height=360):
    fig.update_layout(
        title=dict(text=title, font=dict(color='#FFD700', size=13, family='Inter'), x=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(9,20,42,0.5)',
        font=dict(color='#7A8BA0', size=11, family='Inter'),
        height=height,
        margin=dict(l=10, r=10, t=44, b=10),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='#7A8BA0', size=10)),
        xaxis=dict(gridcolor='rgba(255,255,255,0.03)', color='#7A8BA0', showline=False),
        yaxis=dict(gridcolor='rgba(255,255,255,0.03)', color='#7A8BA0', showline=False),
    )
    return fig

def _cat_idx(cat):
    cats = fm.get_expense_categories()
    return cats.index(cat) if cat in cats else len(cats)-1

def _parse_date_safe(s):
    if not s:
        return None
    for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def _ticker():
    phone       = _phone()
    month_total = fm.get_current_month_total()
    prev_total  = fm.get_previous_month_total()
    budget      = db.get_monthly_budget(datetime.now().strftime('%Y-%m'), phone) or 0
    delta       = month_total - prev_total
    delta_sign  = "+" if delta >= 0 else ""
    delta_cls   = "up" if delta <= 0 else "down"
    budget_pct  = (month_total / budget * 100) if budget else 0
    obl         = om.get_obligation_summary()
    ai_dot      = "🟢" if ai.is_configured() else "🔴"

    st.markdown(f"""
    <div class='ticker-bar'>
      <span class='gold'>💎 SMART FINANCE BRAIN</span> &nbsp;│&nbsp;
      MONTH: <span class='{"down" if budget and month_total > budget else "up"}'>₹{month_total:,.0f}</span> &nbsp;│&nbsp;
      DELTA: <span class='{delta_cls}'>{delta_sign}₹{abs(delta):,.0f}</span> &nbsp;│&nbsp;
      BUDGET: <span>₹{budget:,.0f}</span> &nbsp;│&nbsp;
      USED: <span class='{"down" if budget_pct>90 else "up"}'>{budget_pct:.1f}%</span> &nbsp;│&nbsp;
      BILLS: <span class='{"down" if obl["overdue"]>0 else "gold"}'>{obl["pending"]}</span> &nbsp;│&nbsp;
      AI: {ai_dot} &nbsp;│&nbsp;
      <span class='gold'>{datetime.now().strftime("%d %b %Y  %H:%M")}</span>
    </div>
    """, unsafe_allow_html=True)


def check_and_send_email_alert(user: dict):
    if not user or not user.get('email_enabled', 1):
        return
    to_email = user.get('email', '')
    if not to_email or '@' not in to_email:
        return
    se = db.get_setting('sender_email', '')
    sp = db.get_setting('sender_password', '')
    if not es.is_configured(se, sp):
        return

    phone  = user.get('phone', '')
    name   = user.get('name', 'User')
    month  = datetime.now().strftime('%Y-%m')
    status = fm.get_budget_status(month)
    if not status:
        return

    pct = status['percentage_used']
    thresholds_str = db.get_user_setting('thresholds', '75,90,100', phone)
    try:
        thresholds = sorted([int(t) for t in thresholds_str.split(',') if t.strip()])
    except Exception:
        thresholds = [75, 90, 100]

    for level in thresholds:
        if pct >= level:
            key = f"email_sent_{level}_{month}_{phone}"
            if not st.session_state.get(key, False):
                with st.spinner(f"Sending {level}% budget alert..."):
                    ok, _ = es.send_multi_threshold_alert(
                        se, sp, to_email, name,
                        status['spent'], status['budget'], pct, level)
                if ok:
                    st.session_state[key] = True
                    st.toast(f"{'🚨' if level>=100 else '⚠️'} {level}% alert → {to_email}", icon="✅")
                break

    today = datetime.now().strftime('%Y-%m-%d')
    for obl in om.get_overdue_obligations():
        obl_key = f"obl_alert_{obl['id']}_{today}_{phone}"
        if not st.session_state.get(obl_key, False):
            es.send_obligation_reminder(se, sp, to_email, name,
                                        obl['name'], obl['amount'], obl['due_date'])
            st.session_state[obl_key] = True

    for obl in om.get_upcoming_obligations(3):
        key3 = f"obl_3day_{obl['id']}_{today}_{phone}"
        if not st.session_state.get(key3, False):
            es.send_obligation_reminder(se, sp, to_email, name,
                                        obl['name'], obl['amount'], obl['due_date'])
            st.session_state[key3] = True


# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN PAGE  — premium animated HTML
# ══════════════════════════════════════════════════════════════════════════════
def page_login():
    inject_css()

    # Animated particles background
    st.markdown("""
<style>
.sfb-bg {
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background: radial-gradient(ellipse 80% 60% at 20% 20%, rgba(255,215,0,0.06) 0%, transparent 60%),
              radial-gradient(ellipse 60% 50% at 80% 80%, rgba(0,212,170,0.04) 0%, transparent 60%);
}
.sfb-lines {
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image: linear-gradient(rgba(255,215,0,0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,215,0,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
}
</style>
<div class='sfb-bg'></div>
<div class='sfb-lines'></div>
""", unsafe_allow_html=True)

    _, col, _ = st.columns([0.7, 1.6, 0.7])
    with col:
        st.markdown("""
        <div class='login-logo'>
          <span class='login-logo-icon'>💎</span>
          <h1>Smart Finance Brain</h1>
          <p>Bloomberg-grade personal finance intelligence</p>
          <div class='feature-row'>
            <span class='feature-tag'>🤖 Groq AI</span>
            <span class='feature-tag'>📊 8 Charts</span>
            <span class='feature-tag'>🔮 Forecasting</span>
            <span class='feature-tag'>📧 Smart Alerts</span>
            <span class='feature-tag'>📄 OCR Scanner</span>
            <span class='feature-tag'>🔒 Isolated Data</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        tab_login, tab_register, tab_reset = st.tabs(["🔑 Sign In", "✨ Sign Up", "🔓 Reset PIN"])

        with tab_login:
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            method = st.radio("Login via:", ["📱 Phone + PIN", "📧 Email + PIN"],
                              horizontal=True, label_visibility="collapsed")
            with st.form("login_form"):
                identifier = st.text_input(
                    "Phone Number" if "Phone" in method else "Email Address",
                    placeholder="10-digit number" if "Phone" in method else "you@gmail.com",
                    max_chars=10 if "Phone" in method else 100
                )
                pin       = st.text_input("PIN", type="password", placeholder="4-digit PIN", max_chars=4)
                login_btn = st.form_submit_button("Sign In →", use_container_width=True)

            if login_btn:
                if not identifier.strip():
                    st.error("Enter your phone or email.")
                elif len(pin) != 4 or not pin.isdigit():
                    st.error("PIN must be exactly 4 digits.")
                else:
                    user = (db.verify_user(identifier.strip(), pin)
                            if "Phone" in method
                            else db.verify_user_by_email(identifier.strip(), pin))
                    if user:
                        db.set_current_user(user['phone'])
                        st.session_state.update({'user': user, 'logged_in': True, 'page': '🤖 AI Assistant'})
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")

        with tab_register:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            st.caption("Each account is completely isolated. Your data is private.")
            with st.form("reg_form"):
                rc1, rc2 = st.columns(2)
                with rc1:
                    r_name  = st.text_input("Full Name *", placeholder="Rahul Sharma")
                    r_phone = st.text_input("Phone *", placeholder="10 digits", max_chars=10)
                    r_pin   = st.text_input("Create PIN *", type="password", placeholder="4 digits", max_chars=4)
                with rc2:
                    r_email = st.text_input("Email *", placeholder="you@gmail.com")
                    r_alert = st.slider("Alert at (%)", 50, 95, 75, 5)
                    r_pin2  = st.text_input("Confirm PIN *", type="password", placeholder="Repeat", max_chars=4)
                r_email_on = st.checkbox("Enable Email Alerts", value=True)
                reg_btn    = st.form_submit_button("Create Account →", use_container_width=True)

            if reg_btn:
                err = None
                if not r_name.strip(): err = "Enter your name."
                elif len(r_phone) != 10 or not r_phone.isdigit(): err = "Enter a valid 10-digit phone."
                elif not r_email.strip() or '@' not in r_email: err = "Enter a valid email."
                elif len(r_pin) != 4 or not r_pin.isdigit(): err = "PIN must be 4 digits."
                elif r_pin != r_pin2: err = "PINs do not match."
                elif db.get_user_by_phone(r_phone): err = "Phone already registered."
                elif db.get_user_by_email(r_email.strip()): err = "Email already registered."

                if err:
                    st.error(err)
                else:
                    if db.create_user(r_phone, r_name.strip(), r_pin,
                                      r_email.strip().lower(), r_alert, int(r_email_on)):
                        db.set_current_user(r_phone)
                        db.set_user_setting('thresholds', '75,90,100', r_phone)
                        user = db.get_user_by_phone(r_phone)
                        st.session_state.update({'user': user, 'logged_in': True, 'page': '🤖 AI Assistant'})
                        se = db.get_setting('sender_email', '')
                        sp = db.get_setting('sender_password', '')
                        if r_email_on and es.is_configured(se, sp):
                            es.send_welcome(se, sp, r_email.strip(), r_name.strip())
                        st.success(f"Welcome, {r_name}! 🎉")
                        st.rerun()
                    else:
                        st.error("Registration failed. Try again.")

        with tab_reset:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            st.info("Enter your registered email to reset PIN.")
            with st.form("reset_form"):
                f_email = st.text_input("Registered Email")
                f_pin   = st.text_input("New PIN", type="password", max_chars=4)
                f_pin2  = st.text_input("Confirm PIN", type="password", max_chars=4)
                if st.form_submit_button("Reset →", use_container_width=True):
                    if '@' not in f_email or len(f_pin) != 4 or f_pin != f_pin2:
                        st.error("Check your inputs.")
                    else:
                        u = db.get_user_by_email(f_email.strip())
                        if u:
                            db.update_user_pin(u['phone'], f_pin)
                            st.success("PIN reset! You can now sign in.")
                        else:
                            st.error("Email not found.")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center;color:#1E2A3A;font-size:.70rem;margin-top:20px;'>
          Smart Finance Brain v6.1 &nbsp;·&nbsp; BCA Final Year Project &nbsp;·&nbsp; Groq Llama-3
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    user  = _user()
    phone = _phone()
    with st.sidebar:
        month_total = fm.get_current_month_total()
        budget      = db.get_monthly_budget(datetime.now().strftime('%Y-%m'), phone) or 0
        budget_pct  = (month_total / budget * 100) if budget else 0
        obl_s       = om.get_obligation_summary()
        ai_ok       = ai.is_configured()
        email_ok    = es.is_configured(db.get_setting('sender_email',''), db.get_setting('sender_password','')) and bool(user.get('email',''))

        st.markdown(f"""
        <div style='text-align:center;padding:18px 0 12px;'>
          <div style='font-size:2.6rem;filter:drop-shadow(0 0 20px rgba(255,215,0,0.55));animation:float 3s ease-in-out infinite;'>💎</div>
          <div style='color:#FFD700;font-size:0.88rem;font-weight:900;letter-spacing:0.06em;margin-top:6px;text-shadow:0 0 20px rgba(255,215,0,0.30);'>SMART FINANCE BRAIN</div>
          <div style='margin-top:12px;padding:10px 14px;background:rgba(255,215,0,0.04);
               border:1px solid rgba(255,215,0,0.10);border-radius:11px;'>
            <div style='color:#EDE8D8;font-weight:700;font-size:.84rem;'>👤 {user.get("name","User")}</div>
            <div style='color:#394556;font-size:.70rem;margin-top:2px;'>📱 {phone}</div>
            <div style='color:#394556;font-size:.68rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>{user.get("email","")[:28]}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        pages = ["🤖 AI Assistant", "💰 Expense Manager", "📊 Budget & Forecast", "📈 Dashboard"]
        if 'page' not in st.session_state:
            st.session_state.page = pages[0]
        for page in pages:
            active = st.session_state.page == page
            if st.sidebar.button(page, key=f"nav_{page}", use_container_width=True,
                                 type="primary" if active else "secondary"):
                st.session_state.page = page
                st.rerun()

        st.markdown("---")
        st.markdown(f"""
        <div style='padding:12px;background:rgba(255,215,0,0.03);border-radius:11px;border:1px solid rgba(255,215,0,0.09);margin-bottom:8px;'>
          <div style='color:#394556;font-size:.66rem;font-weight:800;letter-spacing:.08em;'>THIS MONTH</div>
          <div style='color:#FFD700;font-size:1.35rem;font-weight:800;font-family:"JetBrains Mono",monospace;text-shadow:0 0 12px rgba(255,215,0,0.20);'>₹{month_total:,.0f}</div>
          <div style='color:#7A8BA0;font-size:.70rem;'>Budget: {'₹'+f'{budget:,.0f}' if budget else 'Not set'}</div>
          {f'<div style="margin-top:7px;"><div style="height:3px;background:rgba(255,255,255,0.06);border-radius:2px;"><div style="height:3px;width:{min(budget_pct,100):.0f}%;background:{"#EF4444" if budget_pct>90 else "#F59E0B" if budget_pct>75 else "#10B981"};border-radius:2px;box-shadow:0 0 6px currentColor;"></div></div><div style="color:#7A8BA0;font-size:.66rem;margin-top:3px;">{budget_pct:.1f}% used</div></div>' if budget else ''}
        </div>
        """, unsafe_allow_html=True)

        if obl_s['overdue'] > 0:
            st.markdown(f"<div style='padding:7px 12px;background:rgba(239,68,68,0.07);border-radius:9px;border:1px solid rgba(239,68,68,0.18);color:#EF4444;font-size:.74rem;margin-bottom:5px;font-weight:600;'>🚨 {obl_s['overdue']} OVERDUE BILL(S)</div>", unsafe_allow_html=True)
        if obl_s['upcoming_7d'] > 0:
            st.markdown(f"<div style='padding:7px 12px;background:rgba(245,158,11,0.07);border-radius:9px;border:1px solid rgba(245,158,11,0.18);color:#F59E0B;font-size:.74rem;margin-bottom:5px;font-weight:600;'>📅 {obl_s['upcoming_7d']} DUE IN 7 DAYS</div>", unsafe_allow_html=True)

        st.markdown("---")
        se = db.get_setting('sender_email', '')
        sp = db.get_setting('sender_password', '')
        st.markdown(f"""
        <div style='font-size:.70rem;color:#394556;line-height:1.8;'>
          <span style='color:{"#10B981" if ai_ok else "#EF4444"};'>{"●" if ai_ok else "○"}</span>
          &nbsp;Groq AI {'<span style="color:#7A8BA0;">Active</span>' if ai_ok else '<span style="color:#EF4444;">Not configured</span>'}
        </div>
        <div style='font-size:.70rem;color:#394556;line-height:1.8;margin-top:2px;'>
          <span style='color:{"#10B981" if email_ok else "#394556"};'>{"●" if email_ok else "○"}</span>
          &nbsp;Email {'<span style="color:#7A8BA0;">ON</span>' if email_ok else '<span style="color:#394556;">OFF</span>'}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True, type="secondary"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        st.markdown("<div style='text-align:center;color:#1A2030;font-size:.62rem;margin-top:8px;'>v6.1 · Groq Llama-3 · Fixed</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 · AI ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════
def page_ai_assistant():
    user  = _user()
    phone = _phone()

    _ticker()
    st.markdown("""<div class='page-header'>
    <h1>🤖 AI Financial Assistant</h1>
    <p>Powered by Groq Llama-3.3-70b · Upload any file · Chat · Auto-extract expenses</p>
    </div>""", unsafe_allow_html=True)

    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = [{
            'role': 'assistant',
            'content': (
                f"Hello **{user.get('name','there')}**! I'm SmartFinance AI powered by Groq Llama-3.\n\n"
                "I can:\n"
                "- 📎 **Read any file** — PDF, images, Excel, CSV, DOCX, text\n"
                "- 💡 **Extract** amounts, dates, vendors from bills automatically\n"
                "- 📊 **Analyze** your spending patterns with AI insights\n"
                "- 💬 **Answer** any question about your finances\n\n"
                "Upload a document or type your question below!"
            )
        }]
    if 'pending_expense' not in st.session_state:
        st.session_state.pending_expense = None
    if 'camera_open' not in st.session_state:
        st.session_state.camera_open = False

    col_chat, col_right = st.columns([2, 1])

    with col_right:
        # API Key setup
        groq_key = db.get_setting('groq_api_key', '')
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        if not groq_key:
            st.markdown("<div class='card-header'>⚡ GROQ API SETUP</div>", unsafe_allow_html=True)
            st.markdown("<small style='color:#7A8BA0;'>Get free key at <b>console.groq.com</b></small>", unsafe_allow_html=True)
            with st.form("api_form"):
                new_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
                if st.form_submit_button("Save & Activate", use_container_width=True):
                    if new_key.startswith('gsk_') or len(new_key) > 30:
                        with st.spinner("Testing connection..."):
                            ok, msg = ai.test_connection(new_key)
                        if ok:
                            db.set_setting('groq_api_key', new_key)
                            st.success("✅ Groq AI activated!")
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("Key should start with 'gsk_' and be 50+ chars.")
        else:
            st.markdown("<div class='card-header'>⚡ GROQ AI STATUS</div>", unsafe_allow_html=True)
            st.markdown("<div style='color:#10B981;font-size:.80rem;font-weight:600;'>● Connected · Llama-3.3-70b-versatile</div>", unsafe_allow_html=True)
            if st.button("🔑 Change API Key", use_container_width=True, type="secondary"):
                db.set_setting('groq_api_key', '')
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # Upload
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>📎 UPLOAD DOCUMENT</div>", unsafe_allow_html=True)
        st.markdown("<small style='color:#7A8BA0;'>PDF, Images, Excel, CSV, DOCX, TXT</small>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("", label_visibility="collapsed",
            type=["pdf","png","jpg","jpeg","bmp","tiff","webp","xlsx","xls","csv","txt","docx","md"],
            key="ai_upload")
        st.markdown("</div>", unsafe_allow_html=True)

        # Camera
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>📷 CAMERA CAPTURE</div>", unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            if not st.session_state.camera_open:
                if st.button("📸 Open", use_container_width=True):
                    st.session_state.camera_open = True
                    st.rerun()
            else:
                if st.button("✕ Close", use_container_width=True, type="secondary"):
                    st.session_state.camera_open = False
                    st.rerun()
        camera_img = None
        if st.session_state.camera_open:
            st.caption("Point at receipt and capture.")
            camera_img = st.camera_input("", label_visibility="collapsed")
            if camera_img:
                st.session_state.camera_open = False
        else:
            st.caption("Camera off — click Open to scan receipts.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Pending expense
        if st.session_state.pending_expense:
            pexp = st.session_state.pending_expense
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='card-header'>✅ SAVE EXTRACTED EXPENSE</div>", unsafe_allow_html=True)
            with st.form("confirm_exp"):
                desc     = st.text_input("Description", value=str(pexp.get('vendor','') or 'Unknown'))
                amt      = st.number_input("Amount (₹)", value=float(pexp.get('total', 0) or 0), min_value=0.0)
                cat      = st.selectbox("Category", fm.get_expense_categories(), index=_cat_idx(pexp.get('category','Other')))
                pm       = st.selectbox("Payment", fm.get_payment_methods())
                exp_date = st.date_input("Date", value=_parse_date_safe(pexp.get('date')) or datetime.now())
                sc1, sc2 = st.columns(2)
                if sc1.form_submit_button("💾 Save", use_container_width=True):
                    if db.add_expense(exp_date.strftime('%Y-%m-%d'), desc, amt, cat, pm, source='ai', phone=phone):
                        st.success("Saved!")
                        check_and_send_email_alert(user)
                        st.session_state.chat_messages.append({'role':'assistant','content':f"✅ **{desc}** · ₹{amt:,.2f} · {cat} saved!"})
                    st.session_state.pending_expense = None
                    st.rerun()
                if sc2.form_submit_button("Skip", use_container_width=True):
                    st.session_state.pending_expense = None
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Quick stats
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>📊 ACCOUNT OVERVIEW</div>", unsafe_allow_html=True)
        expenses = db.get_all_expenses(phone)
        total    = sum(e['amount'] for e in expenses)
        st.markdown(f"""
        <div class='stat-row'>
          <div class='stat-item'><div class='stat-value'>₹{total/1000:.1f}K</div><div class='stat-label'>All-Time</div></div>
          <div class='stat-item'><div class='stat-value'>₹{fm.get_current_month_total():,.0f}</div><div class='stat-label'>This Month</div></div>
          <div class='stat-item'><div class='stat-value'>{len(expenses):,}</div><div class='stat-label'>Entries</div></div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🗑 Clear Chat", use_container_width=True, type="secondary"):
            st.session_state.chat_messages = [{'role':'assistant','content':"Chat cleared. How can I help?"}]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("🧠 AI: Analyze My Spending", use_container_width=True):
            with st.spinner("Groq is analyzing your financial data..."):
                insights = ai.analyze_spending_patterns(expenses)
            st.session_state.chat_messages.append({'role':'assistant','content':f"**📊 AI Spending Analysis:**\n\n{insights}"})
            st.rerun()

    with col_chat:
        # Handle upload
        if uploaded_file is not None:
            fname    = uploaded_file.name
            ext      = os.path.splitext(fname)[1].lower()
            user_msg = f"📎 Uploaded: **{fname}**"
            if not any(m['content'] == user_msg for m in st.session_state.chat_messages[-3:]):
                st.session_state.chat_messages.append({'role': 'user', 'content': user_msg})
                if ext in ['.xlsx', '.xls', '.csv']:
                    with st.spinner("Importing data..."):
                        fn = fp.process_csv_file if ext == '.csv' else fp.process_excel_file
                        ok, msg = fn(uploaded_file, phone)
                    reply = f"{'✅' if ok else '❌'} {msg}"
                    if ok:
                        check_and_send_email_alert(user)
                else:
                    with st.spinner(f"Reading {fname} with AI..."):
                        content, method = ai.read_file_content(uploaded_file)
                        fin_data        = ai.extract_financial_data(content)
                        summary         = ai.summarize_document(content)
                        doc_type        = dm._detect_doc_type(content)

                    upload_dir = db.get_upload_dir(phone)
                    os.makedirs(upload_dir, exist_ok=True)
                    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = "".join(c for c in fname if c.isalnum() or c in ('._-'))
                    fpath     = os.path.join(upload_dir, f"{ts}_{safe_name}")
                    uploaded_file.seek(0)
                    with open(fpath, 'wb') as f:
                        f.write(uploaded_file.read())
                    db.save_document(fname, fpath, content,
                                     datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                     summary, doc_type, phone)

                    reply = f"✅ **{fname}** read via {method}\n\n📄 **Summary:** {summary}\n\n"
                    if fin_data.get('total'):
                        reply += (f"💰 **Detected:** ₹{fin_data['total']:,.2f} "
                                  f"· {fin_data.get('category','Other')} "
                                  f"· {fin_data.get('date','date unknown')}\n\n"
                                  f"*Use the Save form on the right to add this expense.*")
                        st.session_state.pending_expense = fin_data
                    else:
                        reply += "No specific financial amount detected automatically."

                st.session_state.chat_messages.append({'role': 'assistant', 'content': reply})
                st.rerun()

        # Handle camera
        if camera_img is not None:
            import hashlib
            h = hashlib.md5(camera_img.getvalue()).hexdigest()[:8]
            if f"cam_{h}" not in st.session_state:
                st.session_state[f"cam_{h}"] = True
                st.session_state.chat_messages.append({'role': 'user', 'content': '📷 Captured receipt'})
                with st.spinner("Reading receipt with OCR + AI..."):
                    content, method = ai.read_file_content(camera_img)
                    fin_data        = ai.extract_financial_data(content)
                    summary         = ai.summarize_document(content)
                reply = f"📷 **Receipt scanned** ({method})\n\n{summary}\n\n"
                if fin_data.get('total'):
                    reply += f"💰 Detected: ₹{fin_data['total']:,.2f} · {fin_data.get('category','Other')}"
                    st.session_state.pending_expense = fin_data
                else:
                    reply += "No amount detected. Enter manually."
                st.session_state.chat_messages.append({'role': 'assistant', 'content': reply})
                st.rerun()

        # Display messages
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg['role'], avatar="💎" if msg['role'] == 'assistant' else "👤"):
                st.markdown(msg['content'])

        # Chat input
        if prompt := st.chat_input("Ask about your finances, upload bills, get insights..."):
            st.session_state.chat_messages.append({'role': 'user', 'content': prompt})
            expenses    = db.get_all_expenses(phone)
            month_total = fm.get_current_month_total()
            budget      = db.get_monthly_budget(datetime.now().strftime('%Y-%m'), phone)
            obl         = om.get_obligation_summary()
            cat_totals  = fm.get_category_wise_total_current_month() or {'None': 0}
            context = (
                f"User: {user.get('name')}. "
                f"This month spent: ₹{month_total:,.0f}. "
                f"Budget: {'₹'+f'{budget:,.0f}' if budget else 'not set'}. "
                f"Pending bills: {obl['pending']}. "
                f"Total expense entries: {len(expenses)}. "
                f"Top category: {max(cat_totals, key=lambda k: cat_totals.get(k,0))}."
            )
            with st.spinner("Groq thinking..."):
                reply = ai.chat_response(prompt, context)
            st.session_state.chat_messages.append({'role': 'assistant', 'content': reply})
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 · EXPENSE MANAGER
# ══════════════════════════════════════════════════════════════════════════════
def page_expense_manager():
    user  = _user()
    phone = _phone()
    _ticker()
    st.markdown("""<div class='page-header'>
    <h1>💰 Expense Manager</h1>
    <p>Add · View · Filter · Import · Manage all your expenses with full ID tracking</p>
    </div>""", unsafe_allow_html=True)

    tab_view, tab_add, tab_import, tab_files = st.tabs([
        "📋 All Expenses", "➕ Add Expense", "📂 Import Data", "🗂 Imported Files"
    ])

    with tab_view:
        df = fm.get_expenses_as_dataframe()
        if df.empty:
            st.info("No expenses yet. Add your first one in the **Add Expense** tab.")
        else:
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total All-Time",  f"₹{df['Amount'].sum():,.2f}")
            c2.metric("This Month",      f"₹{fm.get_current_month_total():,.2f}")
            c3.metric("Last Month",      f"₹{fm.get_previous_month_total():,.2f}")
            c4.metric("Avg per Entry",   f"₹{df['Amount'].mean():,.2f}")
            c5.metric("Total Entries",   f"#{len(df):,}")
            st.markdown("---")

            with st.expander("🔍 Filters", expanded=False):
                f1, f2, f3, f4, f5 = st.columns(5)
                cats   = ["All"] + sorted(df['Category'].unique().tolist())
                fcat   = f1.selectbox("Category", cats)
                pms    = ["All"] + sorted(df['Payment Method'].unique().tolist())
                fpm    = f2.selectbox("Payment", pms)
                fsrcs  = ["All"] + sorted(df['source'].unique().tolist()) if 'source' in df.columns else ["All"]
                fsrc   = f3.selectbox("Source", fsrcs)
                fsearch = f4.text_input("Search", placeholder="keyword")
                fsort   = f5.selectbox("Sort", ["Date ↓","Date ↑","Amount ↓","Amount ↑","ID ↓"])

            filtered = df.copy()
            if fcat != "All": filtered = filtered[filtered['Category'] == fcat]
            if fpm  != "All": filtered = filtered[filtered['Payment Method'] == fpm]
            if fsrc  != "All" and 'source' in filtered.columns:
                filtered = filtered[filtered['source'] == fsrc]
            if fsearch:
                filtered = filtered[filtered['Description'].str.contains(fsearch, case=False, na=False)]
            sm = {"Date ↓":('Date',False),"Date ↑":('Date',True),"Amount ↓":('Amount',False),"Amount ↑":('Amount',True),"ID ↓":('ID',False)}
            sc, sa = sm.get(fsort, ('Date', False))
            filtered = filtered.sort_values(sc, ascending=sa)

            st.markdown(f"<div style='color:#7A8BA0;font-size:.80rem;margin-bottom:6px;'>Showing <b style='color:#FFD700;'>{len(filtered):,}</b> of {len(df):,} entries</div>", unsafe_allow_html=True)

            disp = filtered[['ID','Date','Description','Amount','Category','Payment Method','Notes']].copy()
            disp['Date']     = disp['Date'].dt.strftime('%d %b %Y')
            disp['Amount']   = disp['Amount'].apply(lambda x: f"₹{x:,.2f}")
            disp['Category'] = disp['Category'].apply(lambda c: f"{CAT_ICONS.get(c,'💼')} {c}")
            disp['ID']       = disp['ID'].apply(lambda x: f"#{x}")
            st.dataframe(disp, use_container_width=True, hide_index=True)

            ec1, ec2, ec3 = st.columns([1, 1, 3])
            del_id_str = ec1.text_input("Delete by #ID", placeholder="e.g. 42")
            if ec2.button("🗑 Delete", type="primary"):
                try:
                    del_id = int(del_id_str.strip().lstrip('#'))
                    if db.delete_expense(del_id, phone):
                        st.success(f"#{del_id} deleted.")
                        st.rerun()
                    else:
                        st.error(f"#{del_id} not found.")
                except Exception:
                    st.error("Enter a valid numeric ID.")

    with tab_add:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        with st.form("add_exp_form", clear_on_submit=True):
            a1, a2 = st.columns(2)
            with a1:
                exp_date = st.date_input("📅 Date", value=datetime.now())
                desc     = st.text_input("📝 Description *", placeholder="e.g. Swiggy Dinner")
                amount   = st.number_input("💰 Amount (₹) *", min_value=0.01, step=1.0)
            with a2:
                suggested = fm.auto_categorize(desc) if desc else "Other"
                cat       = st.selectbox(f"🏷 Category (auto: {suggested})",
                                          fm.get_expense_categories(), index=_cat_idx(suggested))
                pm        = st.selectbox("💳 Payment Method", fm.get_payment_methods())
                notes     = st.text_area("📌 Notes", height=80, placeholder="Optional...")
            submitted = st.form_submit_button("💾 Save Expense", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            if not desc:
                st.error("Please enter a description.")
            elif amount <= 0:
                st.error("Please enter a valid amount.")
            else:
                if db.add_expense(exp_date.strftime('%Y-%m-%d'), desc, amount, cat, pm, notes, phone=phone):
                    st.success(f"✅ Saved: **{desc}** · ₹{amount:,.2f} · {CAT_ICONS.get(cat,'')} {cat}")
                    st.balloons()
                    check_and_send_email_alert(user)
                else:
                    st.error("Failed to save. Try again.")

    with tab_import:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>📂 IMPORT EXPENSES FROM FILE</div>", unsafe_allow_html=True)
        i1, i2, i3 = st.tabs(["Excel (.xlsx)", "CSV (.csv)", "Text (.txt)"])

        for tab_obj, key_pfx, ext_list, proc_fn in [
            (i1, "excel", ["xlsx","xls"], fp.process_excel_file),
            (i2, "csv",   ["csv"],        fp.process_csv_file),
        ]:
            with tab_obj:
                uf = st.file_uploader(f"Upload file", type=ext_list, key=f"imp_{key_pfx}")
                if uf:
                    bc1, bc2 = st.columns(2)
                    if bc1.button("👁 Preview", key=f"prev_{key_pfx}"):
                        prev = fp.get_import_preview(uf)
                        if prev is not None:
                            st.dataframe(prev, use_container_width=True)
                            st.caption(f"{len(prev)} rows shown")
                            uf.seek(0)
                    if bc2.button("📥 Import All", type="primary", key=f"do_{key_pfx}"):
                        with st.spinner("Importing..."):
                            uf.seek(0)
                            ok, msg = proc_fn(uf, phone)
                        (st.success if ok else st.error)(msg)
                        if ok:
                            check_and_send_email_alert(user)

        with i3:
            tf = st.file_uploader("Upload .txt file", type=["txt"], key="imp_txt")
            if tf:
                tc1, tc2 = st.columns(2)
                if tc1.button("👁 Preview", key="prev_txt"):
                    prev = fp.get_import_preview(tf)
                    if prev is not None:
                        st.dataframe(prev, use_container_width=True)
                    tf.seek(0)
                if tc2.button("📥 Import", type="primary", key="do_txt"):
                    tf.seek(0)
                    ok, msg = fp.process_text_file(tf, phone)
                    (st.success if ok else st.error)(msg)
                    if ok:
                        check_and_send_email_alert(user)

        st.markdown("---")
        t1, t2 = st.columns(2)
        sdf = fp.create_sample_excel()
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as w:
            sdf.to_excel(w, index=False)
        t1.download_button("📥 Excel Template", buf.getvalue(), "expense_template.xlsx", use_container_width=True)
        t2.download_button("📥 CSV Template", sdf.to_csv(index=False), "expense_template.csv", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_files:
        st.markdown("<div class='card-header'>🗂 IMPORTED FILES — Delete file + all its expenses</div>", unsafe_allow_html=True)
        imported = db.get_all_imported_files(phone)
        if not imported:
            st.info("No files imported yet.")
        else:
            for ifile in imported:
                with st.expander(f"📄 {ifile['filename']}  ·  {ifile['rows_imported']} rows  ·  {ifile['import_date'][:10]}  ·  #{ifile['id']}"):
                    fc1, fc2, fc3 = st.columns(3)
                    fc1.markdown(f"**Type:** {ifile['file_type'].upper()}")
                    fc2.markdown(f"**Rows:** {ifile['rows_imported']}")
                    fc3.markdown(f"**On disk:** {'✅' if os.path.exists(ifile.get('file_path','')) else '❌'}")
                    if st.button(f"🗑 Delete file + {ifile['rows_imported']} expenses", key=f"del_f_{ifile['id']}", type="primary"):
                        count, removed = fp.delete_imported_file(ifile, phone)
                        st.success(f"Deleted {count} expense(s). File {'removed.' if removed else 'was missing on disk.'}")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 3 · BUDGET & FORECAST
# ══════════════════════════════════════════════════════════════════════════════
def page_budget_forecast():
    user  = _user()
    phone = _phone()
    _ticker()
    st.markdown("""<div class='page-header'>
    <h1>📊 Budget, Alerts &amp; Forecast</h1>
    <p>Set budget · Multi-threshold email alerts · Bill reminders · Recurring detection · AI Forecast</p>
    </div>""", unsafe_allow_html=True)

    try:
        import plotly.graph_objects as go
        PLOTLY = True
    except ImportError:
        PLOTLY = False

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "💵 Budget", "📋 Bills & ToDo", "🔁 Recurring",
        "🔮 Forecast", "🎮 Simulate", "⚙ Settings"
    ])

    # ── BUDGET ────────────────────────────────────────────────────────────────
    with t1:
        curr_month    = datetime.now().strftime('%Y-%m')
        budget_status = fm.get_budget_status(curr_month)
        bc1, bc2      = st.columns([1, 1])

        with bc1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='card-header'>💵 SET MONTHLY BUDGET</div>", unsafe_allow_html=True)
            cv = float(budget_status['budget']) if budget_status else 10000.0
            with st.form("budget_form"):
                bamt    = st.number_input("Amount (₹)", min_value=100.0, step=500.0, value=cv)
                alert_p = st.slider("Primary alert threshold (%)", 50, 95, user.get('budget_alert', 75), 5)
                if st.form_submit_button("💾 Save Budget", type="primary", use_container_width=True):
                    if db.set_monthly_budget(curr_month, bamt, phone):
                        db.update_user(phone, user['name'], user.get('email',''), alert_p, user.get('email_enabled',1))
                        st.session_state.user['budget_alert'] = alert_p
                        st.success(f"✅ Budget set: ₹{bamt:,.0f} for {curr_month}")
                        check_and_send_email_alert(user)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            if ai.is_configured():
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("<div class='card-header'>🧠 AI BUDGET ADVISOR</div>", unsafe_allow_html=True)
                if st.button("Get AI Recommendation", use_container_width=True):
                    expenses = db.get_all_expenses(phone)
                    with st.spinner("Groq analyzing your spending..."):
                        rec = ai.get_budget_recommendation(expenses, cv)
                    st.markdown(rec)
                st.markdown("</div>", unsafe_allow_html=True)

        with bc2:
            if budget_status:
                b, s, r, pct = (budget_status['budget'], budget_status['spent'],
                                budget_status['remaining'], budget_status['percentage_used'])
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("<div class='card-header'>📊 THIS MONTH STATUS</div>", unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Budget",  f"₹{b:,.0f}")
                m2.metric("Spent",   f"₹{s:,.0f}")
                m3.metric("Left",    f"₹{r:,.0f}")
                color = "#EF4444" if pct >= 100 else "#F59E0B" if pct >= 80 else "#10B981"
                st.markdown(f"<div style='margin:8px 0 4px;font-family:JetBrains Mono,monospace;font-size:2rem;font-weight:800;color:{color};text-shadow:0 0 16px {color}40;'>{pct:.1f}%</div>", unsafe_allow_html=True)
                st.progress(min(pct / 100, 1.0))
                if pct >= 100: st.error(f"🚨 Exceeded by ₹{s-b:,.0f}!")
                elif pct >= 90: st.error(f"⚠️ Only ₹{r:,.0f} left!")
                elif pct >= 75: st.warning(f"⚠️ {pct:.0f}% used — ₹{r:,.0f} remaining.")
                else:           st.success(f"✅ On track — ₹{r:,.0f} remaining.")
                st.markdown("</div>", unsafe_allow_html=True)

                if PLOTLY:
                    import plotly.graph_objects as go
                    monthly = fm.get_monthly_summary(6)
                    if monthly:
                        vals   = list(monthly.values())
                        colors = ['#EF4444' if v > b else '#F59E0B' if v > b*0.8 else '#10B981' for v in vals]
                        fig    = go.Figure()
                        fig.add_trace(go.Bar(x=list(monthly.keys()), y=vals,
                                             marker_color=colors, name='Spent'))
                        fig.add_hline(y=b, line_dash="dash", line_color="#FFD700",
                                      line_width=1.5, annotation_text="Budget")
                        dark_layout(fig, "6-Month vs Budget", height=280)
                        st.plotly_chart(fig, use_container_width=True)

    # ── BILLS & TODO ──────────────────────────────────────────────────────────
    with t2:
        obl_s = om.get_obligation_summary()
        oc1, oc2, oc3, oc4 = st.columns(4)
        oc1.metric("Total Bills",  obl_s['total'])
        oc2.metric("⚡ Pending",   obl_s['pending'])
        oc3.metric("🚨 Overdue",   obl_s['overdue'])
        oc4.metric("✅ Paid",       obl_s['paid'])

        if obl_s['upcoming_list']:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("<div class='card-header'>⏰ DUE WITHIN 7 DAYS</div>", unsafe_allow_html=True)
            for o in obl_s['upcoming_list']:
                days_left = (datetime.strptime(o['due_date'], '%Y-%m-%d') - datetime.now()).days
                uc1, uc2, uc3, uc4 = st.columns([3, 1, 1, 1])
                uc1.markdown(f"**{o['name']}** · ₹{o['amount']:,.0f}")
                uc2.markdown(f"<span class='badge badge-pending'>{days_left}d</span>", unsafe_allow_html=True)
                if uc3.button("✅", key=f"pay_up_{o['id']}"):
                    om.mark_paid(o['id'])
                    st.rerun()
                if uc4.button("📧", key=f"em_up_{o['id']}"):
                    se = db.get_setting('sender_email', '')
                    sp = db.get_setting('sender_password', '')
                    ue = user.get('email', '')
                    if es.is_configured(se, sp) and ue:
                        ok, _ = es.send_obligation_reminder(se, sp, ue, user.get('name',''), o['name'], o['amount'], o['due_date'])
                        (st.success if ok else st.error)("Reminder sent!" if ok else "Failed.")
            st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("➕ Add New Bill / Obligation"):
            with st.form("add_obl"):
                oa1, oa2 = st.columns(2)
                with oa1:
                    oname = st.text_input("Bill Name *")
                    oamt  = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
                    odue  = st.date_input("Due Date")
                with oa2:
                    ocat   = st.selectbox("Category", fm.get_expense_categories())
                    orecur = st.checkbox("Recurring?")
                    orper  = st.selectbox("Period", ["monthly","quarterly","annually"], disabled=not orecur)
                onotes = st.text_input("Notes")
                if st.form_submit_button("Add Bill", type="primary", use_container_width=True):
                    if oname:
                        om.add_obligation(oname, oamt, odue.strftime('%Y-%m-%d'), ocat, int(orecur), orper, onotes)
                        st.success(f"Added: {oname}")
                        check_and_send_email_alert(user)
                        st.rerun()

        st.markdown("#### All Bills")
        for obl in om.get_all_obligations():
            s    = obl['status']
            icon = {'overdue':'🔴','pending':'🟡','paid':'🟢'}.get(s, '⚪')
            amt  = f"₹{obl['amount']:,.0f}" if obl['amount'] else "—"
            due  = obl['due_date'] or "No date"
            with st.expander(f"{icon} #{obl['id']}  {obl['name']}  ·  {amt}  ·  {due}"):
                bc1, bc2, bc3, bc4 = st.columns(4)
                bc1.markdown(f"**Cat:** {obl['category']}")
                bc2.markdown(f"**Recur:** {'Yes' if obl['is_recurring'] else 'No'}")
                if s != 'paid' and bc3.button("✅ Paid", key=f"pay_{obl['id']}"):
                    om.mark_paid(obl['id'])
                    st.rerun()
                if bc4.button("🗑 Delete", key=f"delobl_{obl['id']}"):
                    om.delete_obligation(obl['id'])
                    st.rerun()
                if st.button("📧 Send Reminder Email", key=f"rem_{obl['id']}"):
                    se = db.get_setting('sender_email', '')
                    sp = db.get_setting('sender_password', '')
                    ue = user.get('email', '')
                    if es.is_configured(se, sp) and ue:
                        ok, info = es.send_obligation_reminder(se, sp, ue, user.get('name',''), obl['name'], obl['amount'], due)
                        (st.success if ok else st.error)(f"{'Sent to '+ue if ok else info}")
                    else:
                        st.warning("Configure Gmail in Settings tab first.")

    # ── RECURRING ─────────────────────────────────────────────────────────────
    with t3:
        recurring = fm.detect_recurring_expenses()
        if recurring:
            st.success(f"Found **{len(recurring)}** recurring patterns")
            for item in recurring:
                with st.expander(f"🔄 {item['description'].title()} · {item['occurrences']} months · avg ₹{item['avg_amount']:,.0f}"):
                    ec = st.columns(min(len(item['expenses']), 4))
                    for i, exp in enumerate(item['expenses'][:4]):
                        ec[i].metric(f"#{exp['id']} {exp['date']}", f"₹{exp['amount']:,.0f}")
                    if st.button("✅ Mark All Recurring", key=f"mk_{item['description']}", type="primary"):
                        for exp in item['expenses']:
                            db.update_recurring_status(exp['id'], 1, phone)
                        st.success("Marked recurring!")
                        st.rerun()
        else:
            st.info("No recurring patterns detected. Add expenses across multiple months.")
        st.markdown("---")
        rec = fm.get_recurring_expenses()
        if rec:
            st.markdown(f"**{len(rec)} manually-marked recurring expenses:**")
            for e in rec[:10]:
                c1, c2, c3 = st.columns([3,1,1])
                c1.markdown(f"**{e['description']}** · ₹{e['amount']:,.0f}")
                c2.markdown(f"<span class='badge badge-info'>RECUR</span>", unsafe_allow_html=True)
                if c3.button("↩️ Unmark", key=f"unrk_{e['id']}"):
                    db.update_recurring_status(e['id'], 0, phone)
                    st.rerun()

    # ── FORECAST ──────────────────────────────────────────────────────────────
    with t4:
        if PLOTLY:
            import plotly.graph_objects as go
            monthly = fm.get_monthly_summary(12)
            if len(monthly) >= 2:
                fore  = fm.forecast_multi_month(3)
                hm    = list(monthly.keys())
                ha    = list(monthly.values())
                fm_   = [f['month'] for f in fore]
                fa    = [f['predicted'] for f in fore]
                fig   = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hm, y=ha, mode='lines+markers', name='Actual',
                    line=dict(color='#00D4AA', width=2.5),
                    fill='tozeroy', fillcolor='rgba(0,212,170,0.04)',
                    marker=dict(size=7, color='#00D4AA')
                ))
                if hm and fm_:
                    fig.add_trace(go.Scatter(
                        x=[hm[-1]] + fm_, y=[ha[-1]] + fa,
                        mode='lines+markers', name='🔮 Forecast',
                        line=dict(color='#FFD700', width=2.2, dash='dash'),
                        marker=dict(size=10, symbol='diamond', color='#FFD700')
                    ))
                budget = db.get_monthly_budget(datetime.now().strftime('%Y-%m'), phone)
                if budget:
                    fig.add_hline(y=budget, line_dash='dot', line_color='#EF4444', annotation_text="Budget")
                dark_layout(fig, "🔮 Spending Forecast — Linear Regression", height=400)
                st.plotly_chart(fig, use_container_width=True)
                f1, f2, f3 = st.columns(3)
                for i, f in enumerate(fore[:3]):
                    [f1,f2,f3][i].metric(f['month'], f"₹{f['predicted']:,.0f}")
            else:
                st.warning("Need at least 2 months of data for forecasting.")
        else:
            st.error("pip install plotly")

    # ── SIMULATE ──────────────────────────────────────────────────────────────
    with t5:
        cat_totals = fm.get_category_wise_total_current_month()
        if cat_totals:
            s1, s2 = st.columns(2)
            sel = s1.selectbox("Category", list(cat_totals.keys()))
            pct = s2.slider("Increase (%)", 0, 300, 20, 5)
            if st.button("▶ Simulate Impact", type="primary"):
                result = fm.simulate_category_increase(sel, pct)
                if result:
                    r1, r2 = st.columns(2)
                    r1.metric(f"Current {sel}",    f"₹{result['current_amount']:,.0f}")
                    r1.metric("Current Monthly",   f"₹{result['current_total']:,.0f}")
                    r2.metric(f"After +{pct}%",    f"₹{result['increased_amount']:,.0f}", delta=f"+₹{result['difference']:,.0f}")
                    r2.metric("New Monthly Total", f"₹{result['new_total']:,.0f}", delta=f"+₹{result['difference']:,.0f}")
                    if PLOTLY:
                        import plotly.graph_objects as go
                        fig = go.Figure(data=[
                            go.Bar(name='Current',   x=[sel,'Total'], y=[result['current_amount'], result['current_total']], marker_color='#00D4AA'),
                            go.Bar(name='Simulated', x=[sel,'Total'], y=[result['increased_amount'], result['new_total']], marker_color='#FFD700'),
                        ])
                        fig.update_layout(barmode='group')
                        dark_layout(fig, f"Impact of +{pct}% on {sel}")
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add some expenses this month first.")

    # ── SETTINGS ──────────────────────────────────────────────────────────────
    with t6:
        se = db.get_setting('sender_email', '')
        sp = db.get_setting('sender_password', '')

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>📧 GMAIL SENDER CONFIG</div>", unsafe_allow_html=True)
        st.caption("This Gmail **sends** all alerts. Users receive alerts at their own email.")
        with st.form("gmail_form"):
            new_se = st.text_input("Gmail Address", value=se, placeholder="yourapp@gmail.com")
            new_sp = st.text_input("App Password (16 chars)", value=sp, type="password")
            gc1, gc2 = st.columns(2)
            save_g = gc1.form_submit_button("💾 Save", use_container_width=True)
            test_g = gc2.form_submit_button("🔌 Test", use_container_width=True)
        if save_g:
            if new_se and '@' in new_se and new_sp and len(new_sp.replace(' ','')) >= 8:
                db.set_setting('sender_email', new_se.strip())
                db.set_setting('sender_password', new_sp.strip())
                st.success("Gmail saved!")
                st.rerun()
            else:
                st.error("Enter valid Gmail and App Password.")
        if test_g:
            with st.spinner("Testing Gmail..."):
                ok, info = es.test_connection(new_se, new_sp)
            (st.success if ok else st.error)(info)

        ue = user.get('email', '')
        if es.is_configured(se, sp) and ue:
            if st.button("📨 Send Test Email to My Account", use_container_width=True):
                with st.spinner("Sending..."):
                    ok, info = es.send_test_email(se, sp, ue, user.get('name','User'))
                (st.success if ok else st.error)(f"{'Test email sent to '+ue if ok else info}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>📊 ALERT THRESHOLDS</div>", unsafe_allow_html=True)
        st.caption("Email sent once per month when spending crosses each selected level.")
        thresholds_str = db.get_user_setting('thresholds', '75,90,100', phone)
        try:
            cur_t = [int(t) for t in thresholds_str.split(',') if t.strip()]
        except Exception:
            cur_t = [75, 90, 100]
        all_t = [50, 60, 70, 75, 80, 90, 100]
        sel_t = []
        tc = st.columns(7)
        for i, lvl in enumerate(all_t):
            with tc[i]:
                if st.checkbox(f"{lvl}%", value=(lvl in cur_t), key=f"thr_{lvl}"):
                    sel_t.append(lvl)
        if sorted(sel_t) != sorted(cur_t) and sel_t:
            db.set_user_setting('thresholds', ','.join(map(str, sorted(sel_t))), phone)
            m_ = datetime.now().strftime('%Y-%m')
            for lvl in all_t:
                st.session_state.pop(f"email_sent_{lvl}_{m_}_{phone}", None)
            st.success("Thresholds updated!")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='danger-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header' style='color:#EF4444;'>🗑 DELETE ACCOUNT</div>", unsafe_allow_html=True)
        st.caption("Permanently removes all your data, expenses, documents, and uploaded files.")
        with st.expander("Delete my account permanently"):
            del_pin = st.text_input("Enter your PIN to confirm:", type="password", max_chars=4)
            if st.button("🗑 Delete Everything Permanently", type="primary"):
                if del_pin != user.get('pin', ''):
                    st.error("Wrong PIN.")
                else:
                    if es.is_configured(se, sp) and ue:
                        es.send_account_deleted(se, sp, ue, user.get('name',''))
                    ok2, file_paths = db.delete_user_account(phone)
                    if ok2:
                        for fp_path in file_paths:
                            if fp_path and os.path.exists(fp_path):
                                try:
                                    os.remove(fp_path)
                                except Exception:
                                    pass
                        for k in list(st.session_state.keys()):
                            del st.session_state[k]
                        st.success("Account deleted.")
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 4 · DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def page_dashboard():
    phone = _phone()
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("pip install plotly")
        return

    _ticker()
    st.markdown("""<div class='page-header'>
    <h1>📈 Financial Dashboard</h1>
    <p>8 interactive Plotly charts · Real-time analytics · Bloomberg-grade data view</p>
    </div>""", unsafe_allow_html=True)

    expenses = db.get_all_expenses(phone)
    if not expenses:
        st.info("No data yet. Import the sample CSV or add some expenses first.")
        return

    df_all = pd.DataFrame(expenses)
    df_all['date_parsed'] = pd.to_datetime(df_all['date'])
    total    = df_all['amount'].sum()
    now      = datetime.now()
    budget   = db.get_monthly_budget(now.strftime('%Y-%m'), phone)
    curr_m   = fm.get_current_month_total()
    prev_m   = fm.get_previous_month_total()
    avg_m    = df_all.groupby(df_all['date_parsed'].dt.to_period('M'))['amount'].sum().mean()
    pred     = fm.forecast_next_month_spending() or 0
    obl_s    = om.get_obligation_summary()
    budget_pct = (curr_m / budget * 100) if budget else 0

    # KPI row
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("This Month",  f"₹{curr_m:,.0f}", delta=f"₹{curr_m-prev_m:,.0f}")
    k2.metric("Last Month",  f"₹{prev_m:,.0f}")
    k3.metric("All-Time",    f"₹{total:,.0f}")
    k4.metric("Avg/Month",   f"₹{avg_m:,.0f}")
    k5.metric("🔮 Forecast", f"₹{pred:,.0f}")
    k6.metric("Bills Due",   f"{obl_s['pending']}", delta=f"-{obl_s['overdue']} overdue")
    st.markdown("---")

    # CHART 1 & 2
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        monthly = fm.get_monthly_summary(12)
        if monthly:
            vals   = list(monthly.values())
            b_line = budget or max(vals) * 1.2
            colors = ['#EF4444' if v > b_line else '#F59E0B' if v > b_line*0.8 else '#FFD700' for v in vals]
            fig    = go.Figure()
            fig.add_trace(go.Bar(x=list(monthly.keys()), y=vals, marker_color=colors,
                                 name='Monthly Spend', opacity=0.85))
            fig.add_trace(go.Scatter(x=list(monthly.keys()), y=vals,
                                     mode='lines+markers', name='Trend',
                                     line=dict(color='#00D4AA', width=1.5),
                                     marker=dict(size=5)))
            if budget:
                fig.add_hline(y=budget, line_dash='dot', line_color='#FFD700',
                              line_width=1.5, annotation_text="Budget")
            dark_layout(fig, "📉 Monthly Spending Trend (12 Months)")
            st.plotly_chart(fig, use_container_width=True)

    with r1c2:
        cat_tot = fm.get_category_wise_total()
        if cat_tot:
            fig = go.Figure(data=[go.Pie(
                labels=[f"{CAT_ICONS.get(k,'💼')} {k}" for k in cat_tot.keys()],
                values=list(cat_tot.values()),
                hole=0.6,
                marker=dict(colors=CHART_COLORS, line=dict(color='#040912', width=2)),
                textinfo='label+percent',
                textfont=dict(color='#7A8BA0', size=10),
                hovertemplate='<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}<extra></extra>'
            )])
            fig.update_layout(
                title=dict(text="🍕 Spending by Category (All-Time)", font=dict(color='#FFD700', size=13), x=0),
                paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#7A8BA0'), height=360,
                showlegend=False,
                annotations=[dict(text=f'₹{total/1000:.1f}K', x=0.5, y=0.5,
                                  font=dict(size=18, color='#FFD700', family='JetBrains Mono'),
                                  showarrow=False)]
            )
            st.plotly_chart(fig, use_container_width=True)

    # CHART 3 & 4
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        pm_tot = fm.get_payment_method_totals()
        if pm_tot:
            spm = dict(sorted(pm_tot.items(), key=lambda x: x[1], reverse=True))
            fig = go.Figure(go.Bar(
                x=list(spm.values()), y=list(spm.keys()), orientation='h',
                marker=dict(color=CHART_COLORS[:len(spm)], line=dict(color='#040912', width=1)),
                text=[f"₹{v:,.0f}" for v in spm.values()],
                textposition='outside', textfont=dict(color='#7A8BA0', size=10),
            ))
            dark_layout(fig, "💳 Spending by Payment Method", height=320)
            st.plotly_chart(fig, use_container_width=True)

    with r2c2:
        dates_, amts_ = fm.get_daily_spending_trend(30)
        if dates_:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=dates_, y=amts_, marker_color='#3B82F6', opacity=0.7, name='Daily'))
            fig.add_trace(go.Scatter(x=dates_, y=pd.Series(amts_).rolling(7).mean().tolist(),
                                     mode='lines', name='7-day avg',
                                     line=dict(color='#FFD700', width=2)))
            dark_layout(fig, "📅 Daily Spending — Last 30 Days", height=320)
            fig.update_xaxes(tickangle=-45, nticks=8)
            st.plotly_chart(fig, use_container_width=True)

    # CHART 5 & 6
    r3c1, r3c2 = st.columns(2)
    with r3c1:
        top10 = fm.get_top_expenses(10)
        if top10:
            labels  = [f"#{e['id']} {e['description'][:18]}" for e in top10][::-1]
            amounts = [e['amount'] for e in top10][::-1]
            fig     = go.Figure(go.Bar(
                x=amounts, y=labels, orientation='h',
                marker=dict(color='#7C3AED', line=dict(color='#040912', width=1)),
                text=[f"₹{a:,.0f}" for a in amounts],
                textposition='outside', textfont=dict(color='#7A8BA0', size=10),
            ))
            dark_layout(fig, "🏆 Top 10 Largest Expenses", height=380)
            st.plotly_chart(fig, use_container_width=True)

    with r3c2:
        df_r  = df_all[df_all['is_recurring'] == 1]
        df_nr = df_all[df_all['is_recurring'] == 0]
        def msum(d):
            if d.empty:
                return {}
            return d.set_index('date_parsed').resample('ME')['amount'].sum().tail(6).to_dict()
        rm  = msum(df_r)
        nrm = msum(df_nr)
        all_m = sorted(set(list(rm.keys()) + list(nrm.keys())))
        if all_m:
            ml  = [str(m)[:7] for m in all_m]
            fig = go.Figure(data=[
                go.Bar(name='🔁 Recurring', x=ml, y=[rm.get(m, 0) for m in all_m], marker_color='#7C3AED'),
                go.Bar(name='One-Time',     x=ml, y=[nrm.get(m, 0) for m in all_m], marker_color='#00D4AA'),
            ])
            fig.update_layout(barmode='stack')
            dark_layout(fig, "🔁 Recurring vs One-Time (6 Months)", height=380)
            st.plotly_chart(fig, use_container_width=True)

    # CHART 7 & 8
    r4c1, r4c2 = st.columns(2)
    with r4c1:
        wd   = fm.get_weekday_spending()
        days = list(wd['totals'].keys())
        vals = list(wd['totals'].values())
        avgs = [wd['totals'][d] / max(wd['counts'][d], 1) for d in days]
        fig  = go.Figure()
        fig.add_trace(go.Bar(x=days, y=vals, name='Total',
                             marker_color=[CHART_COLORS[i % len(CHART_COLORS)] for i in range(7)],
                             opacity=0.85))
        fig.add_trace(go.Scatter(x=days, y=avgs, mode='lines+markers',
                                 name='Avg/transaction',
                                 line=dict(color='#FFD700', width=2),
                                 marker=dict(size=7), yaxis='y2'))
        fig.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False, color='#7A8BA0'))
        dark_layout(fig, "📆 Spending by Day of Week", height=320)
        st.plotly_chart(fig, use_container_width=True)

    with r4c2:
        hist = fm.get_monthly_summary(6)
        fore = fm.forecast_multi_month(3)
        hm   = list(hist.keys())
        ha   = list(hist.values())
        fm_  = [f['month'] for f in fore]
        fa   = [f['predicted'] for f in fore]
        fig  = go.Figure()
        fig.add_trace(go.Scatter(x=hm, y=ha, mode='lines+markers', name='Actual',
                                 line=dict(color='#00D4AA', width=2.5),
                                 fill='tozeroy', fillcolor='rgba(0,212,170,0.04)',
                                 marker=dict(size=8, color='#00D4AA')))
        if hm and fm_:
            fig.add_trace(go.Scatter(x=[hm[-1]] + fm_, y=[ha[-1]] + fa,
                                     mode='lines+markers', name='🔮 Forecast',
                                     line=dict(color='#FFD700', width=2, dash='dash'),
                                     marker=dict(size=10, symbol='diamond', color='#FFD700')))
        if budget:
            fig.add_hline(y=budget, line_dash='dot', line_color='#EF4444', annotation_text="Budget")
        dark_layout(fig, "🔮 Actual vs AI Forecast", height=320)
        st.plotly_chart(fig, use_container_width=True)

    # Category Summary Table
    st.markdown("---")
    st.markdown("#### 📋 Category Summary Table")
    cat_all  = fm.get_category_wise_total()
    curr_mo  = fm.get_category_wise_total_current_month()
    rows = [{
        'Category':      f"{CAT_ICONS.get(c,'💼')} {c}",
        'All-Time (₹)':  f"₹{cat_all.get(c,0):,.2f}",
        'This Month (₹)':f"₹{curr_mo.get(c,0):,.2f}",
        'Share':         f"{cat_all.get(c,0)/total*100:.1f}%" if total else "0%",
    } for c in fm.get_expense_categories() if c in cat_all or c in curr_mo]
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    inject_css()
    if not st.session_state.get('logged_in', False):
        page_login()
        return
    render_sidebar()
    page = st.session_state.get('page', '🤖 AI Assistant')
    if   page == "🤖 AI Assistant":     page_ai_assistant()
    elif page == "💰 Expense Manager":   page_expense_manager()
    elif page == "📊 Budget & Forecast": page_budget_forecast()
    elif page == "📈 Dashboard":         page_dashboard()


if __name__ == "__main__":
    main()
