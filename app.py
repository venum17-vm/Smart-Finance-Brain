"""
app.py — Smart Finance Brain v5.0
File structure:
  data/users.db           — global user accounts
  data/{phone}/finance.db — per-user finance data
  uploads/{phone}/        — per-user uploaded files
  reports/{phone}/        — per-user generated reports
  models/phi3_mini/       — Phi-3 cached (one-time download)
"""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os, sys, io

# ── Path setup ────────────────────────────────────────────────────────────────
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
    page_title="Smart Finance Brain",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Init global DB on every run
db.init_global_database()

# If already logged in, init per-user DB too
if st.session_state.get('logged_in') and st.session_state.get('user'):
    phone = st.session_state['user'].get('phone', '')
    if phone:
        db.set_current_user(phone)
        om.update_overdue_statuses()

CHART_COLORS = ['#FFD700','#00D4AA','#7C3AED','#F59E0B','#3B82F6',
                '#EF4444','#10B981','#EC4899','#8B5CF6','#06B6D4']


# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}

.stApp{background:linear-gradient(135deg,#030810 0%,#071020 50%,#0A1830 100%);min-height:100vh;}

section[data-testid="stSidebar"]{background:linear-gradient(180deg,#020810 0%,#071428 100%)!important;border-right:1px solid rgba(255,215,0,0.12);}
section[data-testid="stSidebar"] *{color:#E2E8F0!important;}

#MainMenu,footer,header{visibility:hidden;}

[data-testid="metric-container"]{background:linear-gradient(135deg,rgba(10,22,56,0.95),rgba(15,32,75,0.9));border:1px solid rgba(255,215,0,0.18);border-radius:14px;padding:16px 20px;box-shadow:0 4px 20px rgba(0,0,0,0.4);transition:transform .2s;}
[data-testid="metric-container"]:hover{transform:translateY(-3px);}
[data-testid="metric-container"] label{color:#94A3B8!important;font-size:.73rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;}
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#FFD700!important;font-size:1.6rem;font-weight:700;}

.stButton>button{background:linear-gradient(135deg,#FFD700,#F59E0B)!important;color:#0A0E1A!important;border:none!important;border-radius:10px!important;font-weight:700!important;padding:10px 22px!important;transition:all .2s!important;box-shadow:0 4px 14px rgba(255,215,0,0.3)!important;}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 6px 22px rgba(255,215,0,0.45)!important;}
.stButton>button[kind="secondary"]{background:rgba(15,30,70,0.8)!important;color:#94A3B8!important;border:1px solid rgba(148,163,184,0.2)!important;box-shadow:none!important;}

.stTextInput input,.stTextArea textarea,.stNumberInput input,.stSelectbox select,.stDateInput input{background:rgba(5,12,35,0.9)!important;color:#E2E8F0!important;border:1px solid rgba(255,215,0,0.18)!important;border-radius:8px!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:rgba(255,215,0,0.5)!important;box-shadow:0 0 0 3px rgba(255,215,0,0.08)!important;}

.stTabs [data-baseweb="tab-list"]{background:rgba(5,11,31,0.9);border-radius:12px;padding:4px;gap:4px;}
.stTabs [data-baseweb="tab"]{background:transparent;color:#94A3B8!important;border-radius:8px;padding:8px 18px;font-weight:600;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#FFD700,#F59E0B)!important;color:#0A0E1A!important;}

.stProgress>div>div{background:linear-gradient(90deg,#FFD700,#00D4AA)!important;border-radius:4px;}

.stSuccess{background:rgba(16,185,129,0.08);border-left:4px solid #10B981;border-radius:8px;}
.stWarning{background:rgba(245,158,11,0.08);border-left:4px solid #F59E0B;border-radius:8px;}
.stError{background:rgba(239,68,68,0.08);border-left:4px solid #EF4444;border-radius:8px;}
.stInfo{background:rgba(59,130,246,0.08);border-left:4px solid #3B82F6;border-radius:8px;}

.stDataFrame{background:rgba(5,12,35,0.7);border:1px solid rgba(255,215,0,0.1);border-radius:12px;}
.stExpander{background:rgba(5,12,35,0.7)!important;border:1px solid rgba(255,215,0,0.1)!important;border-radius:12px!important;}

[data-testid="stChatMessage"]{background:rgba(5,12,35,0.8);border:1px solid rgba(255,215,0,0.08);border-radius:14px;margin-bottom:8px;}

.page-header{background:linear-gradient(135deg,rgba(255,215,0,0.06),rgba(0,212,170,0.03));border:1px solid rgba(255,215,0,0.15);border-radius:18px;padding:22px 30px;margin-bottom:24px;}
.page-header h1{color:#FFD700;font-size:1.7rem;font-weight:800;margin:0;}
.page-header p{color:#94A3B8;margin:5px 0 0;font-size:.86rem;}
.card{background:rgba(5,12,35,0.75);border:1px solid rgba(255,215,0,0.1);border-radius:14px;padding:20px;margin-bottom:16px;}
.danger-card{background:rgba(5,12,35,0.75);border:1px solid rgba(239,68,68,0.25);border-radius:14px;padding:20px;margin-bottom:16px;}

/* Login page */
.login-hero{background:linear-gradient(135deg,rgba(255,215,0,0.06),rgba(0,212,170,0.03));border:1px solid rgba(255,215,0,0.15);border-radius:20px;padding:40px;text-align:center;margin-bottom:24px;}
.login-hero h1{color:#FFD700;font-size:2rem;font-weight:800;margin:8px 0 4px;}
.login-hero p{color:#64748B;font-size:.9rem;margin:0;}
.feature-pill{display:inline-block;background:rgba(255,215,0,0.08);border:1px solid rgba(255,215,0,0.2);border-radius:20px;padding:4px 12px;font-size:.75rem;color:#FFD700;margin:3px;}

.badge-pending{background:rgba(245,158,11,0.15);color:#F59E0B;padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:700;}
.badge-paid{background:rgba(16,185,129,0.15);color:#10B981;padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:700;}
.badge-overdue{background:rgba(239,68,68,0.15);color:#EF4444;padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:700;}

::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:rgba(5,11,31,0.5);}
::-webkit-scrollbar-thumb{background:rgba(255,215,0,0.2);border-radius:3px;}
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
        title=dict(text=title, font=dict(color='#FFD700', size=14), x=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(5,12,35,0.4)',
        font=dict(color='#CBD5E1', size=11), height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color='#94A3B8')),
        xaxis=dict(gridcolor='rgba(255,255,255,0.04)', color='#94A3B8'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.04)', color='#94A3B8'),
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
    """Multi-threshold email alert — fires once per threshold per month."""
    if not user or not user.get('email_enabled', 1):
        return
    to_email = user.get('email', '')
    if not to_email or '@' not in to_email:
        return
    se = db.get_setting('sender_email', '')
    sp = db.get_setting('sender_password', '')
    if not es.is_configured(se, sp):
        return

    month  = datetime.now().strftime('%Y-%m')
    status = fm.get_budget_status(month)
    if not status:
        return

    pct   = status['percentage_used']
    phone = user.get('phone', '')
    name  = user.get('name', 'User')

    thresholds_str = db.get_user_setting(f'thresholds', '80,100', phone)
    try:
        thresholds = sorted([int(t) for t in thresholds_str.split(',') if t.strip()])
    except Exception:
        thresholds = [80, 100]

    for level in thresholds:
        if pct >= level:
            key = f"email_sent_{level}_{month}_{phone}"
            if not st.session_state.get(key, False):
                with st.spinner(f"Sending {level}% budget alert email..."):
                    ok, msg = es.send_multi_threshold_alert(
                        se, sp, to_email, name,
                        status['spent'], status['budget'], pct, level
                    )
                if ok:
                    st.session_state[key] = True
                    icon = "🚨" if level >= 100 else "⚠️"
                    st.toast(f"{icon} {level}% alert emailed to {to_email}", icon="✅")
                else:
                    st.warning(f"Email alert ({level}%) failed: {msg}")
                break


# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN PAGE  (redesigned)
# ══════════════════════════════════════════════════════════════════════════════
def page_login():
    inject_css()

    # Hero section
    st.markdown("""
    <div class='login-hero'>
      <div style='font-size:3.5rem;margin-bottom:8px;'>&#128142;</div>
      <h1>Smart Finance Brain</h1>
      <p>Your Personal Digital Finance Management System</p>
      <div style='margin-top:16px;'>
        <span class='feature-pill'>📊 Expense Tracking</span>
        <span class='feature-pill'>🔮 AI Forecasting</span>
        <span class='feature-pill'>📧 Smart Alerts</span>
        <span class='feature-pill'>🔒 Private Data</span>
        <span class='feature-pill'>📄 Bill Scanning</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([0.8, 1.4, 0.8])
    with col:
        tab_login, tab_register, tab_reset = st.tabs(["🔑 Login", "✨ Register", "🔓 Reset PIN"])

        # ── LOGIN ─────────────────────────────────────────────────────────────
        with tab_login:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            method = st.radio("", ["📱 Phone + PIN", "📧 Email + PIN"],
                               horizontal=True, label_visibility="collapsed",
                               key="login_method")
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            with st.form("login_form", clear_on_submit=False):
                if "Phone" in method:
                    identifier = st.text_input("Phone Number",
                                               placeholder="10-digit mobile number",
                                               max_chars=10)
                else:
                    identifier = st.text_input("Email Address",
                                               placeholder="yourname@gmail.com")
                pin    = st.text_input("PIN", type="password",
                                       placeholder="4-digit PIN", max_chars=4)
                login_btn = st.form_submit_button("Login →", use_container_width=True)

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
                        st.session_state.user       = user
                        st.session_state.logged_in  = True
                        st.session_state.page       = "🤖 AI Assistant"
                        st.success(f"Welcome back, {user['name']}!")
                        st.rerun()
                    else:
                        if "Phone" in method:
                            st.error("Invalid phone number or PIN.")
                        else:
                            st.error("Invalid email or PIN.")

        # ── REGISTER ──────────────────────────────────────────────────────────
        with tab_register:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            st.markdown("<div style='color:#94A3B8;font-size:.82rem;'>Each account is completely private. Your data never mixes with other users.</div>", unsafe_allow_html=True)
            with st.form("register_form", clear_on_submit=True):
                rc1, rc2 = st.columns(2)
                with rc1:
                    r_name  = st.text_input("Full Name *", placeholder="Rahul Sharma")
                    r_phone = st.text_input("Phone Number *", placeholder="10 digits", max_chars=10)
                    r_pin   = st.text_input("Create PIN *", type="password",
                                            placeholder="4 digits", max_chars=4)
                with rc2:
                    r_email = st.text_input("Email Address *", placeholder="yourname@gmail.com",
                                            help="Budget alerts sent here. Also used for login.")
                    r_alert = st.slider("Alert me at (%)", 50, 95, 80, 10)
                    r_pin2  = st.text_input("Confirm PIN *", type="password",
                                            placeholder="Repeat PIN", max_chars=4)

                r_email_on = st.checkbox("Enable Email Budget Alerts", value=True)
                reg_btn    = st.form_submit_button("Create My Account →", use_container_width=True)

            if reg_btn:
                err = None
                if not r_name.strip():
                    err = "Please enter your full name."
                elif len(r_phone) != 10 or not r_phone.isdigit():
                    err = "Enter a valid 10-digit phone number."
                elif not r_email.strip() or '@' not in r_email:
                    err = "Enter a valid email address."
                elif len(r_pin) != 4 or not r_pin.isdigit():
                    err = "PIN must be exactly 4 digits."
                elif r_pin != r_pin2:
                    err = "PINs do not match."
                elif db.get_user_by_phone(r_phone):
                    err = "Phone number already registered. Please login."
                elif db.get_user_by_email(r_email.strip()):
                    err = "Email already registered. Please login."

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
                        se = db.get_setting('sender_email', '')
                        sp = db.get_setting('sender_password', '')
                        if r_email_on and es.is_configured(se, sp):
                            with st.spinner("Sending welcome email..."):
                                es.send_welcome(se, sp, r_email.strip(), r_name.strip())
                        st.success(f"Account created! Welcome, {r_name}!")
                        st.rerun()
                    else:
                        st.error("Registration failed. Try a different phone number.")

        # ── RESET PIN ─────────────────────────────────────────────────────────
        with tab_reset:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            st.info("Enter your registered email to reset your PIN.")
            with st.form("reset_form", clear_on_submit=True):
                f_email   = st.text_input("Registered Email", placeholder="yourname@gmail.com")
                f_new_pin = st.text_input("New PIN", type="password",
                                          placeholder="4 digits", max_chars=4)
                f_confirm = st.text_input("Confirm New PIN", type="password",
                                          placeholder="Repeat", max_chars=4)
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
                        se = db.get_setting('sender_email', '')
                        sp = db.get_setting('sender_password', '')
                        if es.is_configured(se, sp):
                            es.send_email(se, sp, f_email.strip(),
                                          "SmartFinance: PIN Reset Successful",
                                          f"Hi {found['name']},\n\nYour PIN has been reset.\n"
                                          f"Login with your new PIN.\n\n-- Smart Finance Brain")
                        st.success("PIN reset! Login with your new PIN.")
                    else:
                        st.error("No account found with that email.")

    st.markdown("<div style='text-align:center;color:#1E293B;font-size:.72rem;margin-top:24px;'>Smart Finance Brain v5.0 &nbsp;|&nbsp; BCA Final Year Project</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    user  = _user()
    phone = _phone()
    name  = user.get('name', 'User')

    with st.sidebar:
        st.markdown(f"""
        <div style='text-align:center;padding:18px 0 12px;'>
          <div style='font-size:2.6rem;'>&#128142;</div>
          <div style='color:#FFD700;font-size:1rem;font-weight:800;'>Smart Finance Brain</div>
          <div style='margin-top:10px;padding:10px;background:rgba(255,215,0,0.06);
               border-radius:10px;border:1px solid rgba(255,215,0,0.12);'>
            <div style='color:#E2E8F0;font-weight:600;'>&#128100; {name}</div>
            <div style='color:#64748B;font-size:.72rem;'>&#128241; {phone}</div>
            <div style='color:#64748B;font-size:.7rem;text-overflow:ellipsis;overflow:hidden;'>{user.get('email','')[:28]}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        pages = {
            "🤖 AI Assistant":      "Chat · Upload · Camera",
            "💰 Expense Manager":   "Add · View · Import",
            "📊 Budget & Forecast": "Budget · Recurring · Predict",
            "📈 Dashboard":         "8 Charts · Analytics",
        }
        if 'page' not in st.session_state:
            st.session_state.page = "🤖 AI Assistant"

        for page, _ in pages.items():
            active = st.session_state.page == page
            if st.sidebar.button(page, key=f"nav_{page}",
                                 use_container_width=True,
                                 type="primary" if active else "secondary"):
                st.session_state.page = page
                st.rerun()

        st.markdown("---")
        now         = datetime.now()
        month_total = fm.get_current_month_total()
        budget      = db.get_monthly_budget(now.strftime('%Y-%m'))
        obl_s       = om.get_obligation_summary()

        st.markdown(f"""
        <div style='padding:12px;background:rgba(255,215,0,0.04);border-radius:10px;
             border:1px solid rgba(255,215,0,0.1);margin-bottom:8px;'>
          <div style='color:#64748B;font-size:.7rem;font-weight:700;letter-spacing:.06em;'>THIS MONTH</div>
          <div style='color:#FFD700;font-size:1.3rem;font-weight:800;'>&#8377;{month_total:,.0f}</div>
          <div style='color:#94A3B8;font-size:.74rem;'>Budget: {'&#8377;'+f'{budget:,.0f}' if budget else 'Not set'}</div>
        </div>
        """, unsafe_allow_html=True)

        if obl_s['overdue'] > 0:
            st.markdown(f"<div style='padding:7px 12px;background:rgba(239,68,68,0.08);border-radius:8px;border:1px solid rgba(239,68,68,0.2);color:#EF4444;font-size:.78rem;margin-bottom:6px;'>&#9888; {obl_s['overdue']} overdue bill(s)</div>", unsafe_allow_html=True)
        if obl_s['upcoming_7d'] > 0:
            st.markdown(f"<div style='padding:7px 12px;background:rgba(245,158,11,0.08);border-radius:8px;border:1px solid rgba(245,158,11,0.2);color:#F59E0B;font-size:.78rem;margin-bottom:6px;'>&#128197; {obl_s['upcoming_7d']} due in 7 days</div>", unsafe_allow_html=True)

        st.markdown("---")
        se = db.get_setting('sender_email', '')
        sp = db.get_setting('sender_password', '')
        email_ready = user.get('email_enabled', 1) and es.is_configured(se, sp) and bool(user.get('email', ''))
        email_color = "#10B981" if email_ready else "#64748B"
        email_label = "&#128140; Email Alerts: ON" if email_ready else "&#128140; Email Alerts: OFF"
        st.markdown(f"<div style='text-align:center;color:{email_color};font-size:.76rem;font-weight:600;'>{email_label}</div>", unsafe_allow_html=True)

        model_status = ae.get_model_status()
        model_icons  = {"loaded":"&#129302; AI: Active","cached":"&#128190; AI: Cached (not loaded)",
                        "failed":"&#128308; AI: Load Failed","not_downloaded":"&#9711; AI: Not Downloaded"}
        model_colors = {"loaded":"#10B981","cached":"#3B82F6","failed":"#EF4444","not_downloaded":"#64748B"}
        st.markdown(f"<div style='text-align:center;color:{model_colors.get(model_status,'#64748B')};font-size:.74rem;margin-top:4px;'>{model_icons.get(model_status,'')}</div>", unsafe_allow_html=True)

        if model_status in ("not_downloaded", "failed", "cached"):
            btn_label = "&#9889; Load AI Model" if model_status == "cached" else "&#11015; Download Phi-3 AI"
            if st.button(btn_label, use_container_width=True, key="load_ai"):
                with st.spinner("Loading AI model from cache..." if model_status == "cached" else "Downloading Phi-3 (first time ~7GB)..."):
                    tok, mdl = ae.load_model()
                if mdl:
                    st.success("AI model ready!")
                else:
                    st.error("Load failed. App works without AI.")

        st.markdown("---")
        if st.button("&#128682; Logout", use_container_width=True, type="secondary", key="logout_btn"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.markdown("<div style='text-align:center;color:#1E293B;font-size:.68rem;margin-top:12px;'>Smart Finance Brain v5.0</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 · AI ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════
def page_ai_assistant():
    user  = _user()
    phone = _phone()

    st.markdown("""<div class='page-header'><h1>🤖 AI Financial Assistant</h1>
    <p>Upload bills &amp; receipts · Capture with camera · Chat · Auto-extract expenses</p></div>""",
    unsafe_allow_html=True)

    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = [{
            'role': 'assistant',
            'content': (
                f"Hello {user.get('name','there')}! I'm your SmartFinance AI.\n\n"
                "I can help you:\n"
                "- 📎 **Upload** bills, receipts, invoices (PDF/Images)\n"
                "- 📷 **Capture** receipts with your camera\n"
                "- 💬 **Ask** anything about your spending\n"
                "- 🔍 **Auto-extract** amounts from documents\n\n"
                "Get started with the panel on the right!"
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
                    with st.spinner("Extracting text and financial data..."):
                        ok, result = dm.process_document(uploaded_file, phone)
                    if ok:
                        fin   = result.get('financial', {})
                        reply = f"✅ **{fname}** processed!\n\n📄 {result.get('summary','')}\n\n"
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

        if prompt := st.chat_input("Ask about your finances, upload a bill..."):
            st.session_state.chat_messages.append({'role':'user','content':prompt})
            expenses    = db.get_all_expenses(phone)
            month_total = fm.get_current_month_total()
            budget      = db.get_monthly_budget(datetime.now().strftime('%Y-%m'))
            obl         = om.get_obligation_summary()
            context = (f"User: {user.get('name')}. Month total: ₹{month_total:,.0f}. "
                       f"Budget: {'₹'+str(budget) if budget else 'not set'}. "
                       f"Pending bills: {obl['pending']}. Total entries: {len(expenses)}.")
            with st.spinner("Thinking..."):
                reply = ae.chat_response(prompt, context)
            st.session_state.chat_messages.append({'role':'assistant','content':reply})
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 · EXPENSE MANAGER
# ══════════════════════════════════════════════════════════════════════════════
def page_expense_manager():
    user  = _user()
    phone = _phone()

    st.markdown("""<div class='page-header'><h1>💰 Expense Manager</h1>
    <p>Add · View · Filter · Import · Manage imported files</p></div>""",
    unsafe_allow_html=True)

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

    st.markdown("""<div class='page-header'><h1>📊 Budget, Recurring &amp; Forecast</h1>
    <p>Set budget · Multi-threshold alerts · Recurring detection · Predict future spending</p></div>""",
    unsafe_allow_html=True)

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

    st.markdown("""<div class='page-header'><h1>📈 Financial Dashboard</h1>
    <p>8 interactive charts · Real-time analytics</p></div>""",
    unsafe_allow_html=True)

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
