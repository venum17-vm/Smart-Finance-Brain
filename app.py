"""
app.py — Smart Finance Brain v7.0
Redesigned UI — sidebar-first layout, card-based pages, fintech aesthetic
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
from modules import finance_manager    as fm
from modules import obligation_manager as om
from modules import document_manager  as dm
from modules import automation_engine as ae
from modules import file_processor    as fp

st.set_page_config(
    page_title="SmartFinance Brain",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_global_database()
ae.set_api_key(db.get_setting("groq_api_key", ""))

if st.session_state.get('logged_in') and st.session_state.get('user'):
    phone = st.session_state['user'].get('phone', '')
    if phone:
        db.set_current_user(phone)
        om.update_overdue_statuses()

CHART_COLORS = ['#4F46E5','#0EA5E9','#10B981','#F59E0B','#EF4444',
                '#8B5CF6','#EC4899','#14B8A6','#F97316','#84CC16']


# ══════════════════════════════════════════════════════════════════════════════
#  CSS — Complete fintech redesign
# ══════════════════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700&family=DM+Mono:wght@400;500&display=swap');

/* ── BASE ─────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
  font-family: 'DM Sans', sans-serif !important;
  font-size: 14px;
}
.stApp {
  background: #0D0F14 !important;
  min-height: 100vh;
}
#MainMenu, footer, header { visibility: hidden; }

/* ── SIDEBAR ──────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: #13161E !important;
  border-right: 1px solid #1E2330 !important;
  width: 240px !important;
  padding: 0 !important;
}
section[data-testid="stSidebar"] > div:first-child {
  padding: 0 16px 24px !important;
}
section[data-testid="stSidebar"] * { color: #9BA3B4 !important; }

/* Sidebar brand header */
.sb-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 4px 18px;
  border-bottom: 1px solid #1E2330;
  margin-bottom: 10px;
}
.sb-brand-icon {
  width: 36px; height: 36px;
  background: #4F46E5;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}
.sb-brand-name {
  font-size: 0.95rem;
  font-weight: 700;
  color: #F1F3F7 !important;
  line-height: 1.2;
}
.sb-brand-sub {
  font-size: 0.68rem;
  color: #4B5262 !important;
}

/* Sidebar section label */
.sb-section {
  font-size: 0.65rem;
  font-weight: 600;
  color: #3D4454 !important;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 14px 4px 6px;
}

/* Sidebar nav items — override Streamlit buttons */
section[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  color: #6B7384 !important;
  border: none !important;
  border-radius: 8px !important;
  padding: 9px 12px !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  text-align: left !important;
  width: 100% !important;
  margin-bottom: 2px !important;
  transition: all 0.18s ease !important;
  box-shadow: none !important;
  letter-spacing: 0 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: #1A1F2C !important;
  color: #D4D8E2 !important;
  transform: none !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: #1C2035 !important;
  color: #818CF8 !important;
  border-left: 3px solid #4F46E5 !important;
  border-radius: 0 8px 8px 0 !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}

/* Sidebar user card */
.sb-user {
  background: #1A1F2C;
  border-radius: 10px;
  padding: 12px;
  margin: 8px 0 4px;
  border: 1px solid #1E2330;
}
.sb-user-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #E2E6EF !important;
}
.sb-user-sub {
  font-size: 0.71rem;
  color: #4B5262 !important;
  margin-top: 2px;
}

/* Sidebar stat mini card */
.sb-stat {
  background: #1A1F2C;
  border: 1px solid #1E2330;
  border-radius: 10px;
  padding: 12px 14px;
  margin: 6px 0;
}
.sb-stat-label {
  font-size: 0.65rem;
  color: #4B5262 !important;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
}
.sb-stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #E2E6EF !important;
  font-family: 'DM Mono', monospace !important;
  letter-spacing: -0.02em;
  margin-top: 2px;
}
.sb-stat-sub {
  font-size: 0.7rem;
  color: #4B5262 !important;
  margin-top: 2px;
}

/* Status dots */
.sb-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 4px;
  font-size: 0.75rem;
}
.dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-green  { background: #10B981; box-shadow: 0 0 6px #10B981; }
.dot-yellow { background: #F59E0B; box-shadow: 0 0 6px #F59E0B; }
.dot-red    { background: #EF4444; box-shadow: 0 0 6px #EF4444; }
.dot-gray   { background: #3D4454; }

/* ── MAIN AREA ────────────────────────────────────────────────── */
.block-container {
  padding: 28px 32px 40px !important;
  max-width: none !important;
}

/* ── PAGE HEADER ─────────────────────────────────────────────── */
.ph {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid #1E2330;
}
.ph-left {}
.ph-title {
  font-size: 1.55rem;
  font-weight: 700;
  color: #F1F3F7;
  letter-spacing: -0.025em;
  line-height: 1.2;
  margin: 0;
}
.ph-title span { color: #818CF8; }
.ph-sub {
  font-size: 0.8rem;
  color: #4B5262;
  margin-top: 4px;
}
.ph-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 0.73rem;
  font-weight: 600;
  margin-left: 8px;
  vertical-align: middle;
}
.ph-badge-green  { background: rgba(16,185,129,0.12); color: #34D399; border: 1px solid rgba(16,185,129,0.2); }
.ph-badge-yellow { background: rgba(245,158,11,0.12); color: #FBBF24; border: 1px solid rgba(245,158,11,0.2); }
.ph-badge-blue   { background: rgba(79,70,229,0.12);  color: #818CF8; border: 1px solid rgba(79,70,229,0.2); }

/* ── METRIC CARDS ─────────────────────────────────────────────── */
[data-testid="metric-container"] {
  background: #13161E !important;
  border: 1px solid #1E2330 !important;
  border-radius: 14px !important;
  padding: 20px 22px !important;
  box-shadow: none !important;
  transition: border-color 0.2s ease, transform 0.2s ease !important;
  position: relative;
  overflow: hidden;
}
[data-testid="metric-container"]:hover {
  border-color: #2D3348 !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3) !important;
}
[data-testid="metric-container"] label {
  font-size: 0.7rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: #4B5262 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
  font-size: 1.7rem !important;
  font-weight: 700 !important;
  color: #F1F3F7 !important;
  font-family: 'DM Mono', monospace !important;
  letter-spacing: -0.03em !important;
}
[data-testid="stMetricDelta"] { font-size: 0.76rem !important; }

/* ── CONTENT CARDS ──────────────────────────────────────────────*/
.card {
  background: #13161E;
  border: 1px solid #1E2330;
  border-radius: 14px;
  padding: 22px 24px;
  margin-bottom: 18px;
  transition: border-color 0.2s ease;
}
.card:hover { border-color: #2D3348; }
.card-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: #4B5262;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 7px;
}
.card-title::before {
  content: '';
  display: inline-block;
  width: 3px; height: 14px;
  background: #4F46E5;
  border-radius: 2px;
}
.danger-card {
  background: #13161E;
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 14px;
  padding: 22px 24px;
  margin-bottom: 18px;
}

/* ── BUTTONS ──────────────────────────────────────────────────── */
.stButton > button {
  background: #4F46E5 !important;
  color: #fff !important;
  border: none !important;
  border-radius: 9px !important;
  font-weight: 600 !important;
  font-size: 0.84rem !important;
  padding: 10px 22px !important;
  transition: all 0.18s ease !important;
  box-shadow: none !important;
  letter-spacing: 0.01em !important;
}
.stButton > button:hover {
  background: #4338CA !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 16px rgba(79,70,229,0.35) !important;
}
.stButton > button:active {
  transform: translateY(0) !important;
}
.stButton > button[kind="secondary"] {
  background: #1A1F2C !important;
  color: #6B7384 !important;
  border: 1px solid #1E2330 !important;
  box-shadow: none !important;
}
.stButton > button[kind="secondary"]:hover {
  background: #1E2330 !important;
  color: #9BA3B4 !important;
  border-color: #2D3348 !important;
  box-shadow: none !important;
  transform: none !important;
}
[data-testid="stFormSubmitButton"] > button {
  background: #4F46E5 !important;
  color: white !important;
  border: none !important;
}
[data-testid="stFormSubmitButton"] > button:hover {
  background: #4338CA !important;
  box-shadow: 0 4px 16px rgba(79,70,229,0.35) !important;
}

/* ── INPUTS ───────────────────────────────────────────────────── */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stDateInput input {
  background: #1A1F2C !important;
  color: #D4D8E2 !important;
  border: 1px solid #2D3348 !important;
  border-radius: 9px !important;
  padding: 9px 13px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.87rem !important;
  transition: border-color 0.2s !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {
  border-color: #4F46E5 !important;
  box-shadow: 0 0 0 3px rgba(79,70,229,0.15) !important;
  background: #1E2437 !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder { color: #3D4454 !important; }

.stTextInput label, .stTextArea label, .stNumberInput label,
.stDateInput label, .stSelectbox label, .stSlider label,
.stCheckbox label span, .stRadio label span {
  color: #6B7384 !important;
  font-size: 0.8rem !important;
  font-weight: 500 !important;
}
.stSelectbox > div > div {
  background: #1A1F2C !important;
  border: 1px solid #2D3348 !important;
  border-radius: 9px !important;
  color: #D4D8E2 !important;
}

/* ── TABS ─────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid #1E2330 !important;
  border-radius: 0 !important;
  padding: 0 !important;
  gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: #4B5262 !important;
  border-radius: 0 !important;
  padding: 10px 18px !important;
  font-weight: 500 !important;
  font-size: 0.84rem !important;
  border-bottom: 2px solid transparent !important;
  margin-bottom: -1px !important;
  transition: all 0.18s ease !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #9BA3B4 !important; }
.stTabs [aria-selected="true"] {
  color: #818CF8 !important;
  background: transparent !important;
  border-bottom: 2px solid #4F46E5 !important;
  box-shadow: none !important;
  font-weight: 600 !important;
}

/* ── PROGRESS ─────────────────────────────────────────────────── */
.stProgress > div {
  background: #1A1F2C !important;
  border-radius: 4px !important;
  height: 6px !important;
}
.stProgress > div > div {
  background: #4F46E5 !important;
  border-radius: 4px !important;
}

/* ── ALERTS ───────────────────────────────────────────────────── */
div[data-testid="stAlert"] {
  border-radius: 10px !important;
  border-width: 1px !important;
  font-size: 0.85rem !important;
}

/* ── DATAFRAME ────────────────────────────────────────────────── */
.stDataFrame {
  background: #13161E !important;
  border: 1px solid #1E2330 !important;
  border-radius: 12px !important;
  overflow: hidden !important;
}
.stDataFrame thead tr th {
  background: #1A1F2C !important;
  color: #4B5262 !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.07em !important;
  text-transform: uppercase !important;
  border-bottom: 1px solid #1E2330 !important;
  padding: 10px 14px !important;
}
.stDataFrame tbody tr td {
  color: #9BA3B4 !important;
  font-size: 0.84rem !important;
  border-bottom: 1px solid #1A1F2C !important;
  padding: 9px 14px !important;
}
.stDataFrame tbody tr:hover td {
  background: #1A1F2C !important;
  color: #D4D8E2 !important;
}

/* ── EXPANDER ─────────────────────────────────────────────────── */
.stExpander {
  background: #13161E !important;
  border: 1px solid #1E2330 !important;
  border-radius: 12px !important;
  margin-bottom: 8px !important;
}
.stExpander:hover { border-color: #2D3348 !important; }
details summary {
  color: #9BA3B4 !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  padding: 12px 16px !important;
}

/* ── CHAT ─────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
  background: #13161E !important;
  border: 1px solid #1E2330 !important;
  border-radius: 12px !important;
  margin-bottom: 8px !important;
  padding: 12px 16px !important;
}
[data-testid="stChatMessage"]:hover { border-color: #2D3348 !important; }
[data-testid="stChatInput"] {
  background: #1A1F2C !important;
  border: 1px solid #2D3348 !important;
  border-radius: 10px !important;
}
[data-testid="stChatInput"]:focus-within {
  border-color: #4F46E5 !important;
  box-shadow: 0 0 0 3px rgba(79,70,229,0.12) !important;
}
[data-testid="stChatInput"] textarea { color: #D4D8E2 !important; }

/* ── FILE UPLOADER ────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
  background: #13161E !important;
  border: 1px dashed #2D3348 !important;
  border-radius: 12px !important;
  transition: border-color 0.2s ease !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: #4F46E5 !important;
  background: rgba(79,70,229,0.03) !important;
}

/* ── BADGES ───────────────────────────────────────────────────── */
.badge-pending {
  background: rgba(245,158,11,0.1);
  color: #FBBF24;
  border: 1px solid rgba(245,158,11,0.2);
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 600;
}
.badge-paid {
  background: rgba(16,185,129,0.1);
  color: #34D399;
  border: 1px solid rgba(16,185,129,0.2);
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 600;
}
.badge-overdue {
  background: rgba(239,68,68,0.1);
  color: #FCA5A5;
  border: 1px solid rgba(239,68,68,0.2);
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 600;
}

/* ── LOGIN PAGE ───────────────────────────────────────────────── */
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}
.login-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  max-width: 900px;
  width: 100%;
  gap: 0;
  background: #13161E;
  border-radius: 20px;
  border: 1px solid #1E2330;
  overflow: hidden;
}
.login-left {
  background: #0D0F14;
  padding: 52px 44px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-right: 1px solid #1E2330;
  position: relative;
  overflow: hidden;
}
.login-left::before {
  content: '';
  position: absolute;
  top: -80px; left: -80px;
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(79,70,229,0.12) 0%, transparent 70%);
  border-radius: 50%;
}
.login-left::after {
  content: '';
  position: absolute;
  bottom: -60px; right: -60px;
  width: 250px; height: 250px;
  background: radial-gradient(circle, rgba(14,165,233,0.08) 0%, transparent 70%);
  border-radius: 50%;
}
.login-logo {
  width: 52px; height: 52px;
  background: #4F46E5;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem;
  margin-bottom: 28px;
}
.login-headline {
  font-size: 2rem;
  font-weight: 700;
  color: #F1F3F7;
  line-height: 1.25;
  letter-spacing: -0.03em;
  margin-bottom: 12px;
}
.login-headline span { color: #818CF8; }
.login-tagline {
  font-size: 0.88rem;
  color: #4B5262;
  line-height: 1.6;
  margin-bottom: 36px;
}
.login-feature {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  font-size: 0.83rem;
  color: #6B7384;
}
.login-feature-icon {
  width: 28px; height: 28px;
  background: #1A1F2C;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.85rem;
  flex-shrink: 0;
  border: 1px solid #2D3348;
}
.login-right {
  padding: 48px 44px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.login-form-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: #F1F3F7;
  margin-bottom: 6px;
  letter-spacing: -0.02em;
}
.login-form-sub {
  font-size: 0.8rem;
  color: #4B5262;
  margin-bottom: 28px;
}

/* ── MISC ─────────────────────────────────────────────────────── */
.stMarkdown p { color: #9BA3B4 !important; line-height: 1.65; }
.stMarkdown h1,.stMarkdown h2,.stMarkdown h3 {
  color: #D4D8E2 !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em !important;
}
.stMarkdown strong { color: #818CF8 !important; }
.stMarkdown code {
  background: #1A1F2C !important;
  color: #94A3B8 !important;
  border-radius: 5px !important;
  padding: 1px 6px !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.82em !important;
}
.stCaption { color: #3D4454 !important; font-size: 0.76rem !important; }
hr { border: none !important; border-top: 1px solid #1E2330 !important; margin: 16px 0 !important; }

.stSlider > div > div > div > div { background: #4F46E5 !important; }
.stSlider > div > div > div > div > div {
  background: #818CF8 !important;
  border: 2px solid #1A1F2C !important;
  box-shadow: 0 0 0 2px #4F46E5 !important;
}

[data-testid="stNumberInput"] button {
  background: #1A1F2C !important;
  border: 1px solid #2D3348 !important;
  color: #6B7384 !important;
  border-radius: 6px !important;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2D3348; border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: #3D4454; }

[data-testid="stToast"] {
  background: #13161E !important;
  border: 1px solid #2D3348 !important;
  border-radius: 12px !important;
  color: #D4D8E2 !important;
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
        title=dict(text=title, font=dict(color='#6B7384', size=11,
                   family='DM Sans'), x=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(26,31,44,0.5)',
        font=dict(color='#6B7384', size=11, family='DM Sans'),
        height=height,
        margin=dict(l=10, r=10, t=38, b=10),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='#4B5262', size=11)),
        xaxis=dict(gridcolor='rgba(45,51,72,0.6)', color='#4B5262',
                   linecolor='#1E2330', tickfont=dict(size=10)),
        yaxis=dict(gridcolor='rgba(45,51,72,0.6)', color='#4B5262',
                   linecolor='#1E2330', tickfont=dict(size=10)),
    )
    return fig


def _cat_idx(cat):
    cats = fm.get_expense_categories()
    return cats.index(cat) if cat in cats else len(cats)-1


def _parse_date_safe(s):
    if not s: return None
    for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
        try: return datetime.strptime(s, fmt)
        except: continue
    return None


def check_and_send_email_alert(user: dict):
    if not user or not user.get('email_enabled', 1): return
    to_email = user.get('email', '')
    if not to_email or '@' not in to_email: return
    se = db.get_setting('sender_email', '')
    sp = db.get_setting('sender_password', '')
    if not es.is_configured(se, sp): return
    month  = datetime.now().strftime('%Y-%m')
    status = fm.get_budget_status(month)
    if not status: return
    pct   = status['percentage_used']
    phone = user.get('phone', '')
    name  = user.get('name', 'User')
    thresholds_str = db.get_user_setting('thresholds', '80,100', phone)
    try:
        thresholds = sorted([int(t) for t in thresholds_str.split(',') if t.strip()])
    except Exception:
        thresholds = [80, 100]
    for level in thresholds:
        if pct >= level:
            key = f"email_sent_{level}_{month}_{phone}"
            if not st.session_state.get(key, False):
                with st.spinner(f"Sending {level}% budget alert..."):
                    ok, msg = es.send_multi_threshold_alert(
                        se, sp, to_email, name,
                        status['spent'], status['budget'], pct, level)
                if ok:
                    st.session_state[key] = True
                    st.toast(f"{'🚨' if level >= 100 else '⚠️'} {level}% alert sent", icon="✅")
                else:
                    st.warning(f"Email alert ({level}%) failed: {msg}")
                break


# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN PAGE — Split layout
# ══════════════════════════════════════════════════════════════════════════════
def page_login():
    inject_css()

    # Left panel with branding
    st.markdown("""
    <div style='max-width:860px;margin:0 auto;margin-top:3vh;'>
    <div style='display:grid;grid-template-columns:1fr 1fr;background:#13161E;
         border-radius:20px;border:1px solid #1E2330;overflow:hidden;min-height:560px;'>

      <!-- LEFT PANEL -->
      <div style='background:#0D0F14;padding:52px 44px;border-right:1px solid #1E2330;
           position:relative;overflow:hidden;'>
        <div style='position:absolute;top:-80px;left:-80px;width:280px;height:280px;
             background:radial-gradient(circle,rgba(79,70,229,0.12) 0%,transparent 70%);
             border-radius:50%;pointer-events:none;'></div>
        <div style='position:absolute;bottom:-60px;right:-60px;width:220px;height:220px;
             background:radial-gradient(circle,rgba(14,165,233,0.08) 0%,transparent 70%);
             border-radius:50%;pointer-events:none;'></div>
        <div style='position:relative;z-index:1;'>
          <div style='width:48px;height:48px;background:#4F46E5;border-radius:13px;
               display:flex;align-items:center;justify-content:center;font-size:1.3rem;
               margin-bottom:28px;'>&#128200;</div>
          <div style='font-size:1.85rem;font-weight:700;color:#F1F3F7;line-height:1.25;
               letter-spacing:-0.03em;margin-bottom:10px;'>
            Smart<br><span style='color:#818CF8;'>Finance</span> Brain
          </div>
          <div style='font-size:0.84rem;color:#4B5262;line-height:1.6;margin-bottom:36px;'>
            Your personal AI-powered finance<br>management system
          </div>
          <div style='display:flex;flex-direction:column;gap:12px;'>
            <div style='display:flex;align-items:center;gap:10px;font-size:0.82rem;color:#6B7384;'>
              <div style='width:28px;height:28px;background:#1A1F2C;border-radius:8px;
                   border:1px solid #2D3348;display:flex;align-items:center;
                   justify-content:center;flex-shrink:0;'>&#128202;</div>
              Expense Tracking &amp; Analysis
            </div>
            <div style='display:flex;align-items:center;gap:10px;font-size:0.82rem;color:#6B7384;'>
              <div style='width:28px;height:28px;background:#1A1F2C;border-radius:8px;
                   border:1px solid #2D3348;display:flex;align-items:center;
                   justify-content:center;flex-shrink:0;'>&#129302;</div>
              AI Assistant &amp; Bill Scanner
            </div>
            <div style='display:flex;align-items:center;gap:10px;font-size:0.82rem;color:#6B7384;'>
              <div style='width:28px;height:28px;background:#1A1F2C;border-radius:8px;
                   border:1px solid #2D3348;display:flex;align-items:center;
                   justify-content:center;flex-shrink:0;'>&#128200;</div>
              Budget &amp; Forecasting
            </div>
            <div style='display:flex;align-items:center;gap:10px;font-size:0.82rem;color:#6B7384;'>
              <div style='width:28px;height:28px;background:#1A1F2C;border-radius:8px;
                   border:1px solid #2D3348;display:flex;align-items:center;
                   justify-content:center;flex-shrink:0;'>&#128274;</div>
              Private &amp; Secure Data
            </div>
          </div>
          <div style='margin-top:40px;font-size:0.7rem;color:#2D3348;'>
            v7.0 &nbsp;·&nbsp; BCA Final Year Project
          </div>
        </div>
      </div>

      <!-- RIGHT PANEL placeholder for Streamlit widgets -->
      <div style='padding:48px 44px;'>
        <div style='font-size:1.15rem;font-weight:700;color:#F1F3F7;
             letter-spacing:-0.02em;margin-bottom:4px;'>Welcome back</div>
        <div style='font-size:0.8rem;color:#4B5262;margin-bottom:24px;'>
          Sign in to your account
        </div>
      </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # The actual form — centered
    _, col, _ = st.columns([0.62, 0.76, 0.62])
    with col:
        tab_login, tab_register, tab_reset = st.tabs(["Sign In", "Create Account", "Reset PIN"])

        with tab_login:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            method = st.radio("Login with", ["📱 Phone + PIN", "📧 Email + PIN"],
                               horizontal=True, label_visibility="collapsed",
                               key="login_method")
            with st.form("login_form", clear_on_submit=False):
                if "Phone" in method:
                    identifier = st.text_input("Phone Number", placeholder="10-digit mobile number", max_chars=10)
                else:
                    identifier = st.text_input("Email Address", placeholder="yourname@gmail.com")
                pin = st.text_input("PIN", type="password", placeholder="4-digit PIN", max_chars=4)
                login_btn = st.form_submit_button("Sign In →", use_container_width=True)
            if login_btn:
                if not identifier.strip():
                    st.error("Enter your phone number or email.")
                elif len(pin) != 4 or not pin.isdigit():
                    st.error("PIN must be exactly 4 digits.")
                else:
                    user = (db.verify_user(identifier.strip(), pin)
                            if "Phone" in method
                            else db.verify_user_by_email(identifier.strip(), pin))
                    if user:
                        db.set_current_user(user['phone'])
                        st.session_state.user      = user
                        st.session_state.logged_in = True
                        st.session_state.page      = "🤖 AI Assistant"
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")

        with tab_register:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.form("register_form", clear_on_submit=True):
                rc1, rc2 = st.columns(2)
                with rc1:
                    r_name  = st.text_input("Full Name *", placeholder="Rahul Sharma")
                    r_phone = st.text_input("Phone *", placeholder="10 digits", max_chars=10)
                    r_pin   = st.text_input("Create PIN *", type="password", placeholder="4 digits", max_chars=4)
                with rc2:
                    r_email = st.text_input("Email *", placeholder="yourname@gmail.com")
                    r_alert = st.slider("Alert threshold (%)", 50, 95, 80, 10)
                    r_pin2  = st.text_input("Confirm PIN *", type="password", placeholder="Repeat", max_chars=4)
                r_email_on = st.checkbox("Enable Email Budget Alerts", value=True)
                reg_btn = st.form_submit_button("Create Account →", use_container_width=True)
            if reg_btn:
                err = None
                if not r_name.strip(): err = "Enter your full name."
                elif len(r_phone) != 10 or not r_phone.isdigit(): err = "Enter a valid 10-digit phone."
                elif not r_email.strip() or '@' not in r_email: err = "Enter a valid email."
                elif len(r_pin) != 4 or not r_pin.isdigit(): err = "PIN must be 4 digits."
                elif r_pin != r_pin2: err = "PINs do not match."
                elif db.get_user_by_phone(r_phone): err = "Phone already registered."
                elif db.get_user_by_email(r_email.strip()): err = "Email already registered."
                if err:
                    st.error(err)
                else:
                    ok = db.create_user(r_phone, r_name.strip(), r_pin,
                                        r_email.strip().lower(), r_alert, int(r_email_on))
                    if ok:
                        db.set_current_user(r_phone)
                        db.set_user_setting('thresholds', '80,100', r_phone)
                        user = db.get_user_by_phone(r_phone)
                        st.session_state.user      = user
                        st.session_state.logged_in = True
                        st.session_state.page      = "🤖 AI Assistant"
                        st.rerun()
                    else:
                        st.error("Registration failed. Try a different phone number.")

        with tab_reset:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.form("reset_form", clear_on_submit=True):
                f_email   = st.text_input("Registered Email", placeholder="yourname@gmail.com")
                f_new_pin = st.text_input("New PIN", type="password", placeholder="4 digits", max_chars=4)
                f_confirm = st.text_input("Confirm PIN", type="password", placeholder="Repeat", max_chars=4)
                reset_btn = st.form_submit_button("Reset PIN →", use_container_width=True)
            if reset_btn:
                if not f_email.strip() or '@' not in f_email:
                    st.error("Enter a valid email.")
                elif len(f_new_pin) != 4 or not f_new_pin.isdigit():
                    st.error("PIN must be 4 digits.")
                elif f_new_pin != f_confirm:
                    st.error("PINs do not match.")
                else:
                    found = db.get_user_by_email(f_email.strip())
                    if found:
                        db.update_user_pin(found['phone'], f_new_pin)
                        st.success("PIN reset! Sign in with your new PIN.")
                    else:
                        st.error("No account found with that email.")


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    user  = _user()
    phone = _phone()
    name  = user.get('name', 'User')

    with st.sidebar:
        # Brand
        st.markdown(f"""
        <div class='sb-brand'>
          <div class='sb-brand-icon'>&#128200;</div>
          <div>
            <div class='sb-brand-name'>SmartFinance</div>
            <div class='sb-brand-sub'>Brain v7.0</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # User card
        initials = ''.join([w[0].upper() for w in name.split()[:2]])
        st.markdown(f"""
        <div class='sb-user'>
          <div style='display:flex;align-items:center;gap:10px;'>
            <div style='width:34px;height:34px;background:#4F46E5;border-radius:9px;
                 display:flex;align-items:center;justify-content:center;font-size:0.8rem;
                 font-weight:700;color:#fff;flex-shrink:0;'>{initials}</div>
            <div>
              <div class='sb-user-name'>{name}</div>
              <div class='sb-user-sub'>{user.get('email','')[:26]}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation
        st.markdown("<div class='sb-section'>Navigation</div>", unsafe_allow_html=True)

        pages = {
            "🤖 AI Assistant":      "ai",
            "💰 Expense Manager":   "expense",
            "📊 Budget & Forecast": "budget",
            "📈 Dashboard":         "dashboard",
        }
        if 'page' not in st.session_state:
            st.session_state.page = "🤖 AI Assistant"

        for page in pages:
            active = st.session_state.page == page
            if st.sidebar.button(page, key=f"nav_{page}",
                                 use_container_width=True,
                                 type="primary" if active else "secondary"):
                st.session_state.page = page
                st.rerun()

        # Stats
        st.markdown("<div class='sb-section'>This Month</div>", unsafe_allow_html=True)
        now         = datetime.now()
        month_total = fm.get_current_month_total()
        budget      = db.get_monthly_budget(now.strftime('%Y-%m'))
        obl_s       = om.get_obligation_summary()

        pct_used = (month_total / budget * 100) if budget and month_total else 0
        bar_color = "#EF4444" if pct_used >= 100 else "#F59E0B" if pct_used >= 80 else "#4F46E5"

        st.markdown(f"""
        <div class='sb-stat'>
          <div class='sb-stat-label'>Spent</div>
          <div class='sb-stat-value'>&#8377;{month_total:,.0f}</div>
          <div style='background:#1E2330;border-radius:3px;height:3px;margin:8px 0 6px;overflow:hidden;'>
            <div style='width:{min(pct_used,100):.0f}%;height:100%;background:{bar_color};border-radius:3px;'></div>
          </div>
          <div class='sb-stat-sub'>{'of ₹'+f'{budget:,.0f}' if budget else 'No budget set'} {'· '+f'{pct_used:.0f}%' if budget else ''}</div>
        </div>
        """, unsafe_allow_html=True)

        if obl_s['overdue'] > 0:
            st.markdown(f"""<div style='background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.18);
                border-radius:8px;padding:7px 12px;font-size:0.76rem;color:#FCA5A5;margin-bottom:5px;'>
                &#9888;&#65039; {obl_s['overdue']} overdue bill{'s' if obl_s['overdue']>1 else ''}</div>""",
                unsafe_allow_html=True)
        if obl_s['upcoming_7d'] > 0:
            st.markdown(f"""<div style='background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.15);
                border-radius:8px;padding:7px 12px;font-size:0.76rem;color:#FBBF24;margin-bottom:5px;'>
                &#128197; {obl_s['upcoming_7d']} due this week</div>""",
                unsafe_allow_html=True)

        # Status
        st.markdown("<div class='sb-section'>System</div>", unsafe_allow_html=True)
        se = db.get_setting('sender_email', '')
        sp = db.get_setting('sender_password', '')
        email_ok = user.get('email_enabled', 1) and es.is_configured(se, sp) and bool(user.get('email', ''))
        ai_ok    = ae.is_configured()

        st.markdown(f"""
        <div style='background:#13161E;border:1px solid #1E2330;border-radius:10px;padding:10px 12px;'>
          <div class='sb-status'>
            <div class='dot {"dot-green" if ai_ok else "dot-yellow"}'></div>
            <span style='font-size:0.76rem;color:{"#34D399" if ai_ok else "#FBBF24"};'>
              Groq AI {"Active" if ai_ok else "— Key needed"}</span>
          </div>
          <div class='sb-status'>
            <div class='dot {"dot-green" if email_ok else "dot-gray"}'></div>
            <span style='font-size:0.76rem;color:{"#34D399" if email_ok else "#3D4454"};'>
              Email Alerts {"On" if email_ok else "Off"}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("Sign Out", use_container_width=True, type="secondary", key="logout_btn"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# helper — renders the new-style page header
def _page_header(title: str, subtitle: str, badges: list = None):
    """
    title   : main heading, use ** for accent color e.g. "AI **Assistant**"
    subtitle: small subtext
    badges  : list of (text, style) where style is 'green','yellow','blue'
    """
    # Parse **accent** in title
    import re
    title_html = re.sub(r'\*\*(.+?)\*\*', r'<span style="color:#818CF8">\1</span>', title)
    badge_html = ''
    if badges:
        for text, style in badges:
            colors = {
                'green':  ('rgba(16,185,129,0.1)','#34D399','rgba(16,185,129,0.2)'),
                'yellow': ('rgba(245,158,11,0.1)','#FBBF24','rgba(245,158,11,0.2)'),
                'blue':   ('rgba(79,70,229,0.1)', '#818CF8','rgba(79,70,229,0.2)'),
            }
            bg, fg, bd = colors.get(style, colors['blue'])
            badge_html += f"""<span style='background:{bg};color:{fg};border:1px solid {bd};
                padding:4px 12px;border-radius:6px;font-size:0.72rem;font-weight:600;
                margin-left:8px;'>{text}</span>"""

    st.markdown(f"""
    <div style='margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid #1E2330;'>
      <div style='display:flex;align-items:center;flex-wrap:wrap;gap:4px;'>
        <h1 style='font-size:1.5rem;font-weight:700;color:#F1F3F7;letter-spacing:-0.025em;
             margin:0;line-height:1.2;'>{title_html}</h1>
        {badge_html}
      </div>
      <div style='font-size:0.8rem;color:#4B5262;margin-top:5px;'>{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def page_ai_assistant():
    user  = _user()
    phone = _phone()

    inject_css()
    _page_header("🤖 AI **Assistant**",
                 "Chat with AI · Upload bills & receipts · Auto-extract expenses",
                 [("Groq AI Active" if ae.is_configured() else "No API Key", "green" if ae.is_configured() else "yellow")])

    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = [{
            'role': 'assistant',
            'content': (
                f"Hello {user.get('name','there')}! I'm your SmartFinance AI.\n\n"
                "I have **full access to your data** and can take actions for you:\n"
                "- 💬 **Ask** — *'How much did I spend on food this month?'*\n"
                "- ➕ **Add expense** — *'Add 250 for lunch today'*\n"
                "- 💰 **Set budget** — *'Set my budget to 20000'*\n"
                "- 🔔 **Add bill reminder** — *'Add electricity bill 800 due on 25th'*\n"
                "- 📎 **Upload** any bill or receipt image for auto-extraction\n\n"
                "Just type naturally — I'll handle it!"
            )
        }]
    if 'pending_expense' not in st.session_state:
        st.session_state.pending_expense = None
    if 'camera_open' not in st.session_state:
        st.session_state.camera_open = False

    col_chat, col_right = st.columns([2, 1])

    with col_right:
        # Upload
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 📎 Upload Document")
        st.markdown("<div style='color:#64748B;font-size:.8rem;margin-bottom:6px;'>PDF, Image, Excel, CSV accepted</div>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Drop file here",
            type=["pdf","png","jpg","jpeg","bmp","tiff","xlsx","xls","csv","txt","docx"],
            label_visibility="collapsed", key="ai_file_upload")
        st.markdown("</div>", unsafe_allow_html=True)

        # Camera toggle
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 📷 Capture Receipt")
        cam_c1, cam_c2 = st.columns(2)
        with cam_c1:
            if not st.session_state.camera_open:
                if st.button("📷 Open Camera", use_container_width=True):
                    st.session_state.camera_open = True
                    st.rerun()
            else:
                if st.button("✖ Close Camera", use_container_width=True, type="secondary"):
                    st.session_state.camera_open = False
                    st.rerun()

        camera_img = None
        if st.session_state.camera_open:
            st.caption("Point camera at your receipt and capture.")
            camera_img = st.camera_input("Capture", label_visibility="collapsed")
            if camera_img:
                st.session_state.camera_open = False
        else:
            st.caption("Camera is off. Click Open Camera when needed.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Pending expense
        if st.session_state.pending_expense:
            pexp = st.session_state.pending_expense
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("#### ✅ Save Extracted Expense?")
            with st.form("confirm_exp_form"):
                desc     = st.text_input("Description", value=str(pexp.get('vendor','') or 'Unknown'))
                amt      = st.number_input("Amount (₹)", value=float(pexp.get('total',0) or 0), min_value=0.0)
                cat      = st.selectbox("Category", fm.get_expense_categories(), index=_cat_idx(pexp.get('category','Other')))
                pm       = st.selectbox("Payment Method", fm.get_payment_methods())
                exp_date = st.date_input("Date", value=_parse_date_safe(pexp.get('date')) or datetime.now())
                sc1, sc2 = st.columns(2)
                save_exp = sc1.form_submit_button("💾 Save", use_container_width=True)
                skip_exp = sc2.form_submit_button("✖ Skip", use_container_width=True)
                if save_exp:
                    if db.add_expense(exp_date.strftime('%Y-%m-%d'), desc, amt, cat, pm, source='ai', phone=phone):
                        st.success("Expense saved!")
                        check_and_send_email_alert(user)
                        st.session_state.chat_messages.append({'role':'assistant','content':f"✅ Saved: **{desc}** · ₹{amt:,.2f} · {cat}"})
                    st.session_state.pending_expense = None
                    st.rerun()
                if skip_exp:
                    st.session_state.pending_expense = None
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Quick stats
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 📊 Quick Stats")
        expenses = db.get_all_expenses(phone)
        total    = sum(e['amount'] for e in expenses)
        st.metric("All-time",   f"₹{total:,.0f}")
        st.metric("This Month", f"₹{fm.get_current_month_total():,.0f}")
        st.metric("Entries",    f"{len(expenses):,}")
        if st.button("🗑 Clear Chat", use_container_width=True, type="secondary", key="clr"):
            st.session_state.chat_messages = [{'role':'assistant','content':"Chat cleared. How can I help?"}]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_chat:
        # Handle file upload
        if uploaded_file is not None:
            fname    = uploaded_file.name
            ext      = os.path.splitext(fname)[1].lower()
            user_msg = f"📎 Uploaded: **{fname}**"
            if not any(m['content'] == user_msg for m in st.session_state.chat_messages[-3:]):
                st.session_state.chat_messages.append({'role':'user','content':user_msg})
                if ext in ['.xlsx','.xls','.csv']:
                    with st.spinner("Importing data..."):
                        fn  = fp.process_csv_file if ext == '.csv' else fp.process_excel_file
                        ok, msg = fn(uploaded_file, phone)
                    reply = f"{'✅' if ok else '❌'} {msg}"
                    if ok: check_and_send_email_alert(user)
                else:
                    with st.spinner("Analysing document with AI..."):
                        img_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
                        vision_summary = ""
                        if ext in img_exts:
                            vision_summary = ae.summarize_image(uploaded_file)
                            uploaded_file.seek(0)
                        ok, result = dm.process_document(uploaded_file, phone)
                    if ok:
                        fin          = result.get('financial', {})
                        summary_text = vision_summary if vision_summary else result.get('summary', '')
                        reply = f"✅ **{fname}** processed!\n\n📄 {summary_text}\n\n"
                        if fin.get('total'):
                            reply += f"💰 **Detected:** ₹{fin['total']:,.2f} · {fin.get('category','Other')}"
                            st.session_state.pending_expense = fin
                        else:
                            reply += "No financial amount detected."
                    else:
                        reply = f"❌ Processing failed: {result}"
                st.session_state.chat_messages.append({'role':'assistant','content':reply})
                st.rerun()

        # Handle camera
        if camera_img is not None:
            import hashlib
            img_hash = hashlib.md5(camera_img.getvalue()).hexdigest()[:8]
            cam_key  = f"cam_{img_hash}"
            if cam_key not in st.session_state:
                st.session_state[cam_key] = True
                st.session_state.chat_messages.append({'role':'user','content':'📷 Captured receipt'})
                with st.spinner("Running OCR on receipt..."):
                    try:
                        from PIL import Image as PILImage
                        img_obj   = PILImage.open(camera_img)
                        img_bytes = io.BytesIO()
                        img_obj.save(img_bytes, format='PNG')
                        img_bytes.name = 'camera_capture.png'
                        img_bytes.seek(0)
                        ok, result = dm.process_document(img_bytes, phone)
                        if ok:
                            fin   = result.get('financial', {})
                            reply = f"📷 **Receipt scanned!**\n\n{result.get('summary','')}\n\n"
                            if fin.get('total'):
                                reply += f"💰 Detected: ₹{fin['total']:,.2f} · {fin.get('category','Other')}"
                                st.session_state.pending_expense = fin
                            else:
                                reply += "No amount detected. Verify manually."
                        else:
                            reply = f"❌ {result}"
                    except Exception as e:
                        reply = f"❌ Camera error: {e}"
                st.session_state.chat_messages.append({'role':'assistant','content':reply})
                st.rerun()

        # Display chat
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg['role'], avatar="💎" if msg['role']=='assistant' else "👤"):
                st.markdown(msg['content'])

        if prompt := st.chat_input("Ask anything — add expenses, set budget, check spending..."):
            st.session_state.chat_messages.append({'role':'user','content':prompt})
            with st.spinner("Thinking..."):
                reply, actions = ae.chat_response(prompt, phone=phone)
            # Show action confirmations as separate messages
            if actions:
                action_text = "\n".join(actions)
                full_reply  = f"{reply}\n\n{action_text}".strip() if reply else action_text
            else:
                full_reply = reply
            st.session_state.chat_messages.append({'role':'assistant','content':full_reply})
            # Rerun to refresh sidebar stats if data changed
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 · EXPENSE MANAGER
# ══════════════════════════════════════════════════════════════════════════════
def page_expense_manager():
    user  = _user()
    phone = _phone()

    inject_css()
    _page_header("💰 **Expense** Manager",
                 "Add, view, filter, import and manage your expenses")

    tab_view, tab_add, tab_import, tab_files = st.tabs([
        "📋 View", "➕ Add", "📂 Import", "🗂 Imported Files"
    ])

    with tab_view:
        df = fm.get_expenses_as_dataframe()
        if df.empty:
            st.info("No expenses yet. Add one in the **Add** tab!")
        else:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("All-Time",   f"₹{df['Amount'].sum():,.2f}")
            c2.metric("This Month", f"₹{fm.get_current_month_total():,.2f}")
            c3.metric("Average",    f"₹{df['Amount'].mean():,.2f}")
            c4.metric("Entries",    f"{len(df):,}")
            st.markdown("---")

            with st.expander("🔍 Filter & Search"):
                f1,f2,f3,f4 = st.columns(4)
                cats  = ["All"] + sorted(df['Category'].unique().tolist())
                fcat  = f1.selectbox("Category", cats)
                pms   = ["All"] + sorted(df['Payment Method'].unique().tolist())
                fpm   = f2.selectbox("Payment", pms)
                fsrc  = f3.text_input("Search", placeholder="keyword")
                fsort = f4.selectbox("Sort", ["Date ↓","Date ↑","Amount ↓","Amount ↑"])

            filtered = df.copy()
            if fcat != "All": filtered = filtered[filtered['Category']==fcat]
            if fpm  != "All": filtered = filtered[filtered['Payment Method']==fpm]
            if fsrc:          filtered = filtered[filtered['Description'].str.contains(fsrc, case=False, na=False)]
            sm = {"Date ↓":('Date',False),"Date ↑":('Date',True),"Amount ↓":('Amount',False),"Amount ↑":('Amount',True)}
            sc, sa = sm[fsort]
            filtered = filtered.sort_values(sc, ascending=sa)

            st.markdown(f"<div style='color:#64748B;font-size:.8rem;margin-bottom:6px;'>Showing <b style='color:#FFD700;'>{len(filtered)}</b> of {len(df)} entries</div>", unsafe_allow_html=True)
            disp = filtered[['Date','Description','Amount','Category','Payment Method','Notes']].copy()
            disp['Date']   = disp['Date'].dt.strftime('%d %b %Y')
            disp['Amount'] = disp['Amount'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(disp, use_container_width=True, hide_index=True)

            dc1, dc2 = st.columns([1,3])
            dc1.download_button("📥 Export CSV",
                data=filtered.assign(Date=filtered['Date'].dt.strftime('%Y-%m-%d')).to_csv(index=False),
                file_name=f"expenses_{phone}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv", use_container_width=True)

            with st.expander("🗑 Delete Expense"):
                del_id = st.number_input("Expense ID", min_value=1, step=1)
                if st.button("Delete", type="primary"):
                    if db.delete_expense(int(del_id), phone):
                        st.success(f"Expense #{del_id} deleted.")
                        st.rerun()
                    else:
                        st.error("Not found.")

    with tab_add:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        with st.form("add_exp_form", clear_on_submit=True):
            a1, a2 = st.columns(2)
            with a1:
                exp_date = st.date_input("Date", value=datetime.now())
                desc     = st.text_input("Description *", placeholder="e.g. Swiggy Order")
                amount   = st.number_input("Amount (₹) *", min_value=0.01, step=1.0)
            with a2:
                suggested = fm.auto_categorize(desc) if desc else "Other"
                cat       = st.selectbox("Category", fm.get_expense_categories(), index=_cat_idx(suggested))
                pm        = st.selectbox("Payment Method", fm.get_payment_methods())
                notes     = st.text_area("Notes", height=82)
            submitted = st.form_submit_button("💾 Save Expense", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        if submitted:
            if not desc:
                st.error("Enter a description.")
            elif amount <= 0:
                st.error("Enter a valid amount.")
            else:
                if db.add_expense(exp_date.strftime('%Y-%m-%d'), desc, amount, cat, pm, notes, phone=phone):
                    st.success(f"✅ Saved: **{desc}** · ₹{amount:,.2f}")
                    st.balloons()
                    check_and_send_email_alert(user)
                else:
                    st.error("Failed to save.")

    with tab_import:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 📂 Import Expenses")
        i1, i2, i3 = st.tabs(["Excel", "CSV", "Text File"])
        for tab_obj, file_type, ext_list, key_pfx, proc_fn in [
            (i1, "Excel", ["xlsx","xls"], "excel", fp.process_excel_file),
            (i2, "CSV",   ["csv"],        "csv",   fp.process_csv_file),
        ]:
            with tab_obj:
                uf = st.file_uploader(f"Upload {file_type}", type=ext_list, key=f"imp_{key_pfx}")
                if uf:
                    if st.button(f"👁 Preview", key=f"prev_{key_pfx}"):
                        prev = fp.get_import_preview(uf)
                        if prev is not None:
                            st.dataframe(prev, use_container_width=True)
                            st.caption(f"{len(prev)} rows shown")
                            uf.seek(0)
                        else:
                            st.error("Could not preview this file.")
                    if st.button(f"📥 Import All", type="primary", key=f"do_{key_pfx}"):
                        with st.spinner("Importing..."):
                            uf.seek(0)
                            ok, msg = proc_fn(uf, phone)
                        (st.success if ok else st.error)(msg)
                        if ok: check_and_send_email_alert(user)

        with i3:
            tf = st.file_uploader("Upload Text (.txt)", type=["txt"], key="imp_txt")
            if tf:
                if st.button("👁 Preview", key="prev_txt"):
                    prev = fp.get_import_preview(tf)
                    if prev is not None:
                        st.dataframe(prev, use_container_width=True)
                    tf.seek(0)
                if st.button("📥 Import All", type="primary", key="do_txt"):
                    with st.spinner("Importing..."):
                        tf.seek(0)
                        ok, msg = fp.process_text_file(tf, phone)
                    (st.success if ok else st.error)(msg)
                    if ok: check_and_send_email_alert(user)

        st.markdown("---")
        st.markdown("#### 📄 Download Templates")
        t1, t2 = st.columns(2)
        sdf = fp.create_sample_excel()
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as w:
            sdf.to_excel(w, index=False)
        t1.download_button("📥 Excel Template", buf.getvalue(), "expense_template.xlsx", use_container_width=True)
        t2.download_button("📥 CSV Template", sdf.to_csv(index=False), "expense_template.csv", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── IMPORTED FILES MANAGEMENT ─────────────────────────────────────────────
    with tab_files:
        st.markdown("#### 🗂 Manage Imported Files")
        st.markdown("<div style='color:#94A3B8;font-size:.82rem;'>Delete an imported file to also remove all expenses that came from it.</div>", unsafe_allow_html=True)
        imported_files = db.get_all_imported_files(phone)
        if not imported_files:
            st.info("No imported files yet. Import data from the **Import** tab.")
        else:
            for ifile in imported_files:
                with st.expander(f"📄 {ifile['filename']}  ·  {ifile['rows_imported']} rows  ·  {ifile['import_date'][:10]}"):
                    fc1, fc2, fc3 = st.columns(3)
                    fc1.markdown(f"**Type:** {ifile['file_type'].upper()}")
                    fc2.markdown(f"**Rows imported:** {ifile['rows_imported']}")
                    exists = os.path.exists(ifile.get('file_path', ''))
                    fc3.markdown(f"**File on disk:** {'Yes' if exists else 'No'}")
                    if st.button(f"🗑 Delete file + its {ifile['rows_imported']} expenses",
                                 key=f"del_import_{ifile['id']}", type="primary"):
                        count, removed = fp.delete_imported_file(ifile, phone)
                        st.success(f"Deleted {count} expense(s). File {'removed from disk.' if removed else 'was already missing.'}")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 3 · BUDGET & FORECAST
# ══════════════════════════════════════════════════════════════════════════════
def page_budget_forecast():
    user  = _user()
    phone = _phone()

    inject_css()
    _page_header("📊 Budget &amp; **Forecast**",
                 "Set budget · Multi-threshold alerts · Recurring detection · Predict spending")

    try:
        import plotly.graph_objects as go
        PLOTLY = True
    except ImportError:
        PLOTLY = False

    t1, t2, t3, t4, t5, t6 = st.tabs(["💵 Budget", "🔁 Recurring", "🔮 Forecast", "🎮 Simulate", "📋 Bills", "⚙ Settings"])

    with t1:
        curr_month    = datetime.now().strftime('%Y-%m')
        budget_status = fm.get_budget_status(curr_month)
        bc1, bc2      = st.columns([1,1])

        with bc1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown("#### Set Monthly Budget")
            cv = float(budget_status['budget']) if budget_status else 10000.0
            with st.form("budget_form"):
                bamt     = st.number_input("Budget Amount (₹)", min_value=100.0, step=500.0, value=cv)
                alert_p  = st.slider("Alert threshold (%)", 50, 95, user.get('budget_alert',80), 10)
                if st.form_submit_button("💾 Save Budget", type="primary", use_container_width=True):
                    if db.set_monthly_budget(curr_month, bamt, phone):
                        db.update_user(phone, user['name'], user.get('email',''), alert_p, user.get('email_enabled',1))
                        st.session_state.user['budget_alert'] = alert_p
                        st.success(f"Budget saved: ₹{bamt:,.0f}")
                        check_and_send_email_alert(user)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with bc2:
            if budget_status:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.markdown("#### This Month")
                b,s,r,pct = (budget_status['budget'], budget_status['spent'],
                              budget_status['remaining'], budget_status['percentage_used'])
                m1,m2,m3 = st.columns(3)
                m1.metric("Budget",    f"₹{b:,.0f}")
                m2.metric("Spent",     f"₹{s:,.0f}")
                m3.metric("Remaining", f"₹{r:,.0f}")
                st.progress(min(pct/100, 1.0))
                c = "#EF4444" if pct>=100 else "#F59E0B" if pct>=80 else "#10B981"
                st.markdown(f"<div style='color:{c};font-weight:700;font-size:1.05rem;'>{pct:.1f}% used</div>", unsafe_allow_html=True)
                if pct >= 100: st.error(f"Budget exceeded by ₹{s-b:,.0f}!")
                elif pct >= 80: st.warning(f"Only ₹{r:,.0f} remaining.")
                else:           st.success(f"₹{r:,.0f} remaining — on track.")
                st.markdown("</div>", unsafe_allow_html=True)
                if PLOTLY:
                    import plotly.graph_objects as go
                    monthly = fm.get_monthly_summary(6)
                    if monthly:
                        fig = go.Figure()
                        fig.add_trace(go.Bar(x=list(monthly.keys()), y=list(monthly.values()), marker_color='#FFD700', name='Spent'))
                        fig.add_hline(y=b, line_dash="dash", line_color="#EF4444", annotation_text="Budget")
                        dark_layout(fig, "6-Month vs Budget")
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No budget set. Set one on the left!")

    with t2:
        recurring = fm.detect_recurring_expenses()
        if recurring:
            st.success(f"Found **{len(recurring)}** recurring patterns")
            for item in recurring:
                with st.expander(f"🔄 {item['description'].title()} · {item['occurrences']} months · avg ₹{item['avg_amount']:,.0f}"):
                    ec = st.columns(min(len(item['expenses']), 4))
                    for i, exp in enumerate(item['expenses'][:4]):
                        ec[i].metric(exp['date'], f"₹{exp['amount']:,.0f}")
                    if st.button("✅ Mark Recurring", key=f"mk_{item['description']}", type="primary"):
                        for exp in item['expenses']:
                            db.update_recurring_status(exp['id'], 1, phone)
                        st.success("Marked!")
                        st.rerun()
        else:
            st.info("No recurring patterns detected yet. Add more months of data.")
        st.markdown("---")
        st.markdown("#### Marked Recurring")
        rec = fm.get_recurring_expenses()
        if rec:
            rdf = pd.DataFrame(rec)[['date','description','amount','category']]
            rdf.columns = ['Date','Description','Amount','Category']
            rdf['Amount'] = rdf['Amount'].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(rdf, use_container_width=True, hide_index=True)
            st.metric("Monthly Recurring Total", f"₹{sum(e['amount'] for e in rec):,.2f}")
        else:
            st.info("None marked yet.")

    with t3:
        predicted = fm.forecast_next_month_spending()
        if predicted:
            curr = fm.get_current_month_total()
            prev = fm.get_previous_month_total()
            fc1, fc2, fc3 = st.columns(3)
            fc1.metric("Previous Month", f"₹{prev:,.0f}")
            fc2.metric("Current Month",  f"₹{curr:,.0f}")
            fc3.metric("Predicted Next", f"₹{predicted:,.0f}", delta=f"₹{predicted-curr:,.0f}")
            if PLOTLY:
                import plotly.graph_objects as go
                monthly   = fm.get_monthly_summary(6)
                forecasts = fm.forecast_multi_month(3)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=list(monthly.keys()), y=list(monthly.values()), mode='lines+markers', name='Actual', line=dict(color='#00D4AA', width=2.5), fill='tozeroy', fillcolor='rgba(0,212,170,0.05)'))
                if monthly and forecasts:
                    fig.add_trace(go.Scatter(x=[list(monthly.keys())[-1]]+[f['month'] for f in forecasts], y=[list(monthly.values())[-1]]+[f['predicted'] for f in forecasts], mode='lines+markers', name='Forecast', line=dict(color='#FFD700', width=2, dash='dash'), marker=dict(size=9, symbol='diamond')))
                dark_layout(fig, "Spending Forecast (Linear Regression)", height=400)
                st.plotly_chart(fig, use_container_width=True)
            st.markdown("#### 3-Month Forecast")
            rc1,rc2,rc3 = st.columns(3)
            for i, f in enumerate(fm.forecast_multi_month(3)[:3]):
                [rc1,rc2,rc3][i].metric(f['month'], f"₹{f['predicted']:,.0f}")
        else:
            st.warning("Need at least 2 months of data to forecast.")

    with t4:
        cat_totals = fm.get_category_wise_total_current_month()
        if cat_totals:
            s1, s2 = st.columns(2)
            sel_cat = s1.selectbox("Category", list(cat_totals.keys()))
            inc_pct = s2.slider("Increase (%)", 0, 300, 20, 5)
            if st.button("▶ Run Simulation", type="primary"):
                result = fm.simulate_category_increase(sel_cat, inc_pct)
                if result:
                    r1, r2 = st.columns(2)
                    r1.metric(f"Current {sel_cat}",  f"₹{result['current_amount']:,.0f}")
                    r1.metric("Current Total",        f"₹{result['current_total']:,.0f}")
                    r2.metric(f"After {inc_pct}%",    f"₹{result['increased_amount']:,.0f}", delta=f"+₹{result['difference']:,.0f}")
                    r2.metric("New Total",             f"₹{result['new_total']:,.0f}", delta=f"+₹{result['difference']:,.0f}")
        else:
            st.info("Add some expenses this month first.")

    with t5:
        obl_s = om.get_obligation_summary()
        ob1,ob2,ob3,ob4 = st.columns(4)
        ob1.metric("Total",   obl_s['total'])
        ob2.metric("Pending", obl_s['pending'])
        ob3.metric("Overdue", obl_s['overdue'])
        ob4.metric("Paid",    obl_s['paid'])
        with st.expander("➕ Add New Bill"):
            with st.form("add_obl_form"):
                oc1, oc2 = st.columns(2)
                with oc1:
                    oname = st.text_input("Bill Name *")
                    oamt  = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
                    odue  = st.date_input("Due Date")
                with oc2:
                    ocat   = st.selectbox("Category", fm.get_expense_categories())
                    orecur = st.checkbox("Recurring?")
                    orper  = st.selectbox("Period", ["monthly","quarterly","annually"], disabled=not orecur)
                if st.form_submit_button("Add Bill", type="primary", use_container_width=True):
                    if oname:
                        om.add_obligation(oname, oamt, odue.strftime('%Y-%m-%d'), ocat, int(orecur), orper)
                        st.success(f"Added: {oname}")
                        st.rerun()
        for obl in om.get_all_obligations():
            s    = obl['status']
            icon = '🔴' if s=='overdue' else '🟡' if s=='pending' else '🟢'
            amt  = f"₹{obl['amount']:,.0f}" if obl['amount'] else "—"
            due  = obl['due_date'] or "No date"
            with st.expander(f"{icon} {obl['name']}  ·  {amt}  ·  {due}"):
                bc1, bc2, bc3 = st.columns(3)
                if s != 'paid' and bc1.button("✅ Paid", key=f"pay_{obl['id']}"):
                    om.mark_paid(obl['id'])
                    st.rerun()
                if bc2.button("📧 Email Reminder", key=f"em_{obl['id']}"):
                    se = db.get_setting('sender_email','')
                    sp = db.get_setting('sender_password','')
                    ue = user.get('email','')
                    if es.is_configured(se, sp) and ue:
                        ok, info = es.send_obligation_reminder(se, sp, ue, user.get('name',''), obl['name'], obl['amount'], due)
                        (st.success if ok else st.error)(f"{'Reminder sent to '+ue if ok else info}")
                    else:
                        st.warning("Configure Gmail in Settings tab first.")
                if bc3.button("🗑 Delete", key=f"delobl_{obl['id']}"):
                    om.delete_obligation(obl['id'])
                    st.rerun()

    # ── SETTINGS ──────────────────────────────────────────────────────────────
    with t6:
        st.markdown("#### ⚙ Account & Email Settings")

        # ── Groq API Key ──────────────────────────────────────────────────────
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**🤖 Groq AI — Free API Key**")
        st.caption("Powers the AI chatbot, document summaries, and image/receipt analysis. Free at console.groq.com")
        current_key = db.get_setting('groq_api_key', '')
        masked_key  = ('●' * 20 + current_key[-4:]) if len(current_key) > 4 else ''
        with st.form("groq_form"):
            new_key   = st.text_input("Groq API Key", placeholder="gsk_xxxxxxxxxxxxxxxxxxxx",
                                       value="", type="password",
                                       help="Free at console.groq.com → API Keys → Create Key")
            if masked_key:
                st.caption(f"Saved key: {masked_key}")
            gk1, gk2 = st.columns(2)
            save_groq = gk1.form_submit_button("💾 Save Key", use_container_width=True)
            test_groq = gk2.form_submit_button("🔌 Test Connection", use_container_width=True)
        if save_groq:
            k = new_key.strip()
            if k and len(k) > 20:
                db.set_setting('groq_api_key', k)
                ae.set_api_key(k)
                st.success("✅ Groq API key saved! AI features are now active.")
                st.rerun()
            else:
                st.error("Enter a valid Groq key (starts with gsk_).")
        if test_groq:
            key_to_test = new_key.strip() or current_key
            if key_to_test:
                ae.set_api_key(key_to_test)
                with st.spinner("Testing Groq connection..."):
                    ok_g, info_g = ae.test_connection()
                (st.success if ok_g else st.error)(info_g)
            else:
                st.error("Enter a key first.")
        if not current_key:
            st.info("💡 Get your free key in 2 minutes: console.groq.com → Sign Up → API Keys → Create Key")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")

        se = db.get_setting('sender_email', '')
        sp = db.get_setting('sender_password', '')

        # Gmail config
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**📧 Gmail Sender Configuration**")
        st.caption("This Gmail account SENDS alerts. Users receive alerts at their own email.")
        with st.form("gmail_form"):
            new_se = st.text_input("Sender Gmail", value=se, placeholder="yourapp@gmail.com")
            new_sp = st.text_input("App Password (16 chars)", value=sp, type="password", placeholder="Google App Password")
            gc1, gc2 = st.columns(2)
            save_g = gc1.form_submit_button("💾 Save", use_container_width=True)
            test_g = gc2.form_submit_button("🔌 Test Connection", use_container_width=True)
        if save_g:
            if new_se and '@' in new_se and new_sp and len(new_sp.replace(' ','')) >= 8:
                db.set_setting('sender_email',    new_se.strip())
                db.set_setting('sender_password', new_sp.strip())
                st.success("Gmail saved!")
                st.rerun()
            else:
                st.error("Enter a valid Gmail address and App Password.")
        if test_g:
            with st.spinner("Testing Gmail connection..."):
                ok, info = es.test_connection(new_se, new_sp)
            (st.success if ok else st.error)(info)

        # Send test email button
        ue = user.get('email','')
        if es.is_configured(se, sp) and ue:
            st.markdown("---")
            if st.button("📨 Send Test Email to My Account", use_container_width=True):
                with st.spinner("Sending..."):
                    ok, info = es.send_test_email(se, sp, ue, user.get('name','User'))
                (st.success if ok else st.error)(f"{'Test email sent to '+ue if ok else info}")
        st.markdown("</div>", unsafe_allow_html=True)

        # Alert thresholds
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**📊 Budget Alert Thresholds**")
        st.caption("Email sent once per month when spending crosses each selected level.")
        thresholds_str = db.get_user_setting('thresholds', '80,100', phone)
        try:
            cur_t = [int(t) for t in thresholds_str.split(',') if t.strip()]
        except Exception:
            cur_t = [80, 100]
        all_t = [50, 60, 70, 80, 90, 100]
        sel_t = []
        tc = st.columns(6)
        for i, lvl in enumerate(all_t):
            with tc[i]:
                if st.checkbox(f"{lvl}%", value=(lvl in cur_t), key=f"thr_{lvl}"):
                    sel_t.append(lvl)
        if sorted(sel_t) != sorted(cur_t) and sel_t:
            db.set_user_setting('thresholds', ','.join(map(str, sorted(sel_t))), phone)
            st.success("Thresholds updated!")
            m_ = datetime.now().strftime('%Y-%m')
            for lvl in all_t:
                st.session_state.pop(f"email_sent_{lvl}_{m_}_{phone}", None)
        st.markdown("</div>", unsafe_allow_html=True)

        # Delete account
        st.markdown("<div class='danger-card'>", unsafe_allow_html=True)
        st.markdown("**🗑 Delete Account**")
        st.markdown("<div style='color:#EF4444;font-size:.82rem;'>Permanently deletes all your data, expenses, documents, and uploaded files.</div>", unsafe_allow_html=True)
        with st.expander("Delete my account permanently"):
            del_pin = st.text_input("Confirm with your PIN:", type="password", max_chars=4, key="del_pin_input")
            if st.button("🗑 Delete Everything", type="primary", key="del_acct_btn"):
                if del_pin != user.get('pin',''):
                    st.error("Wrong PIN. Cancelled.")
                else:
                    ue2 = user.get('email','')
                    if es.is_configured(se, sp) and ue2:
                        es.send_account_deleted(se, sp, ue2, user.get('name',''))
                    ok2, file_paths = db.delete_user_account(phone)
                    if ok2:
                        removed = 0
                        for fp_path in file_paths:
                            try:
                                if fp_path and os.path.exists(fp_path):
                                    os.remove(fp_path)
                                    removed += 1
                            except Exception:
                                pass
                        for k in list(st.session_state.keys()):
                            del st.session_state[k]
                        st.success(f"Account deleted. {removed} file(s) removed.")
                        st.rerun()
                    else:
                        st.error("Deletion failed.")
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 4 · DASHBOARD  (8 charts)
# ══════════════════════════════════════════════════════════════════════════════
def page_dashboard():
    phone = _phone()
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("Plotly not installed: pip install plotly")
        return

    import plotly.graph_objects as go

    inject_css()
    _page_header("📈 Financial **Dashboard**",
                 "Real-time analytics · 8 interactive charts")

    expenses = db.get_all_expenses(phone)
    if not expenses:
        st.info("No data yet. Import sample CSV or add expenses first.")
        return

    df_all = pd.DataFrame(expenses)
    df_all['date_parsed'] = pd.to_datetime(df_all['date'])
    total  = df_all['amount'].sum()
    now    = datetime.now()
    budget = db.get_monthly_budget(now.strftime('%Y-%m'), phone)

    # KPIs
    curr_m = fm.get_current_month_total()
    prev_m = fm.get_previous_month_total()
    avg_m  = df_all.groupby(df_all['date_parsed'].dt.to_period('M'))['amount'].sum().mean()
    pred   = fm.forecast_next_month_spending() or 0
    obl_s  = om.get_obligation_summary()

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("This Month",  f"₹{curr_m:,.0f}", delta=f"₹{curr_m-prev_m:,.0f}")
    k2.metric("Last Month",  f"₹{prev_m:,.0f}")
    k3.metric("All-Time",    f"₹{total:,.0f}")
    k4.metric("Avg/Month",   f"₹{avg_m:,.0f}")
    k5.metric("Forecast",    f"₹{pred:,.0f}")
    k6.metric("Bills Due",   f"{obl_s['pending']}")

    st.markdown("---")

    # Chart Row 1
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        monthly = fm.get_monthly_summary(12)
        if monthly:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=list(monthly.keys()), y=list(monthly.values()), mode='lines+markers', name='Spending', fill='tozeroy', fillcolor='rgba(255,215,0,0.05)', line=dict(color='#FFD700', width=2.5), marker=dict(size=8)))
            if budget: fig.add_hline(y=budget, line_dash="dot", line_color="#EF4444", annotation_text="Budget")
            dark_layout(fig, "📉 Monthly Trend (12m)")
            st.plotly_chart(fig, use_container_width=True)

    with r1c2:
        cat_tot = fm.get_category_wise_total()
        if cat_tot:
            fig = go.Figure(data=[go.Pie(labels=list(cat_tot.keys()), values=list(cat_tot.values()), hole=0.55, marker=dict(colors=CHART_COLORS), textinfo='label+percent', textfont=dict(color='#CBD5E1', size=11))])
            fig.update_layout(title=dict(text="🍕 By Category", font=dict(color='#FFD700', size=14)), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#CBD5E1'), height=360, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # Chart Row 2
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        pm_tot = fm.get_payment_method_totals()
        if pm_tot:
            spm = dict(sorted(pm_tot.items(), key=lambda x: x[1], reverse=True))
            fig = go.Figure(go.Bar(x=list(spm.keys()), y=list(spm.values()), marker_color=CHART_COLORS[:len(spm)], text=[f"₹{v:,.0f}" for v in spm.values()], textposition='outside', textfont=dict(color='#CBD5E1')))
            dark_layout(fig, "💳 By Payment Method", height=320)
            st.plotly_chart(fig, use_container_width=True)

    with r2c2:
        dates_, amts_ = fm.get_daily_spending_trend(30)
        if dates_:
            fig = go.Figure(go.Bar(x=dates_, y=amts_, marker_color='#00D4AA', opacity=0.8))
            dark_layout(fig, "📅 Daily (Last 30 Days)", height=320)
            fig.update_xaxes(tickangle=-45, nticks=10)
            st.plotly_chart(fig, use_container_width=True)

    # Chart Row 3
    r3c1, r3c2 = st.columns(2)
    with r3c1:
        top10 = fm.get_top_expenses(10)
        if top10:
            labels  = [e['description'][:22] for e in top10][::-1]
            amounts = [e['amount'] for e in top10][::-1]
            fig = go.Figure(go.Bar(x=amounts, y=labels, orientation='h', marker_color='#7C3AED', text=[f"₹{a:,.0f}" for a in amounts], textposition='outside', textfont=dict(color='#CBD5E1')))
            dark_layout(fig, "🏆 Top 10 Expenses", height=360)
            st.plotly_chart(fig, use_container_width=True)

    with r3c2:
        df_r  = df_all[df_all['is_recurring']==1]
        df_nr = df_all[df_all['is_recurring']==0]
        def msum(d):
            if d.empty: return {}
            return d.set_index('date_parsed').resample('ME')['amount'].sum().tail(6).to_dict()
        rm = msum(df_r); nrm = msum(df_nr)
        all_m = sorted(set(list(rm.keys())+list(nrm.keys())))
        if all_m:
            ml = [str(m)[:7] for m in all_m]
            fig = go.Figure(data=[go.Bar(name='Recurring', x=ml, y=[rm.get(m,0) for m in all_m], marker_color='#7C3AED'), go.Bar(name='One-Time', x=ml, y=[nrm.get(m,0) for m in all_m], marker_color='#00D4AA')])
            fig.update_layout(barmode='stack')
            dark_layout(fig, "🔁 Recurring vs One-Time (6m)", height=360)
            st.plotly_chart(fig, use_container_width=True)

    # Chart Row 4
    r4c1, r4c2 = st.columns(2)
    with r4c1:
        wd   = fm.get_weekday_spending()
        days = list(wd['totals'].keys())
        vals = list(wd['totals'].values())
        fig  = go.Figure(go.Bar(x=days, y=vals, marker_color=[CHART_COLORS[i%len(CHART_COLORS)] for i in range(7)], text=[f"₹{v:,.0f}" for v in vals], textposition='outside', textfont=dict(color='#CBD5E1')))
        dark_layout(fig, "📆 By Day of Week", height=320)
        st.plotly_chart(fig, use_container_width=True)

    with r4c2:
        hist = fm.get_monthly_summary(6)
        fore = fm.forecast_multi_month(3)
        hm = list(hist.keys()); ha = list(hist.values())
        fm_ = [f['month'] for f in fore]; fa = [f['predicted'] for f in fore]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hm, y=ha, mode='lines+markers', name='Actual', line=dict(color='#00D4AA', width=2), marker=dict(size=8)))
        if hm and fm_:
            fig.add_trace(go.Scatter(x=[hm[-1]]+fm_, y=[ha[-1]]+fa, mode='lines+markers', name='Forecast', line=dict(color='#FFD700', width=2, dash='dash'), marker=dict(size=9, symbol='diamond')))
        if budget: fig.add_hline(y=budget, line_dash='dot', line_color='#EF4444', annotation_text="Budget")
        dark_layout(fig, "🔮 Actual vs Forecast", height=320)
        st.plotly_chart(fig, use_container_width=True)

    # Summary table
    st.markdown("---")
    st.markdown("#### 📋 Category Summary")
    cat_all = fm.get_category_wise_total()
    curr_mo = fm.get_category_wise_total_current_month()
    rows    = [{'Category':c,'All-Time':f"₹{cat_all.get(c,0):,.2f}",'This Month':f"₹{curr_mo.get(c,0):,.2f}",'Share':f"{cat_all.get(c,0)/total*100:.1f}%" if total else "0%"} for c in fm.get_expense_categories() if c in cat_all or c in curr_mo]
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
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
