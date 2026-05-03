"""
server.py — SmartFinance Brain HTML Frontend Server
====================================================
This connects your new HTML/CSS/JS frontend to your existing database.

HOW TO RUN:
  1. Place this file in your SmartFinanceBrain/ root folder
     (same folder as app.py, database.py)

  2. Install Flask (one time):
     pip install flask flask-cors

  3. Run the server:
     python server.py

  4. Open your browser and go to:
     http://localhost:5000

  That's it. Your HTML frontend will now use your real database.

FOLDER STRUCTURE NEEDED:
  SmartFinanceBrain/
  ├── server.py          ← THIS FILE (new)
  ├── app.py             ← your existing Streamlit app
  ├── database.py        ← your existing database
  ├── modules/           ← your existing modules
  ├── ui/                ← your HTML frontend folder
  │   ├── index.html
  │   ├── login.html
  │   ├── dashboard.html
  │   ├── css/
  │   │   └── dashboard.css
  │   └── js/
  │       └── dashboard.js
  └── data/              ← your existing data (auto-created)
"""

import os
import sys
import json
import base64
from datetime import datetime, timedelta
from functools import wraps

# ── PATH SETUP — makes database.py and modules/ importable ──────────────────
ROOT    = os.path.dirname(os.path.abspath(__file__))
MODULES = os.path.join(ROOT, 'modules')
UI_DIR  = os.path.join(ROOT, 'ui')

for p in [ROOT, MODULES]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── FLASK ────────────────────────────────────────────────────────────────────
try:
    from flask import Flask, request, jsonify, send_from_directory, session
    from flask_cors import CORS
except ImportError:
    print("\n❌ Flask not installed. Run this command first:\n")
    print("   pip install flask flask-cors\n")
    sys.exit(1)

# ── YOUR EXISTING MODULES ────────────────────────────────────────────────────
import database as db

try:
    from modules import finance_manager    as fm
    from modules import obligation_manager as om
    from modules import automation_engine  as ae
    from modules import document_manager  as dm
    import email_service as es
    MODULES_OK = True
except Exception as e:
    print(f"⚠ Could not load some modules: {e}")
    MODULES_OK = False

# ── APP SETUP ────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=UI_DIR, static_url_path='')
app.secret_key = 'sfb-secret-key-change-in-production'
CORS(app, supports_credentials=True)

# Init database on startup
db.init_global_database()


# ════════════════════════════════════════════════════════════════════════════
#  SERVE HTML FILES
# ════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Serve the main index page."""
    return send_from_directory(UI_DIR, 'index.html')

@app.route('/login.html')
def login_page():
    return send_from_directory(UI_DIR, 'login.html')

@app.route('/dashboard.html')
def dashboard_page():
    return send_from_directory(UI_DIR, 'dashboard.html')

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(UI_DIR, 'css'), filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(UI_DIR, 'js'), filename)


# ════════════════════════════════════════════════════════════════════════════
#  AUTH HELPER — reads phone from session or request header
# ════════════════════════════════════════════════════════════════════════════

def get_phone():
    """Get current user's phone from session."""
    return session.get('phone', '')

def ok(data=None, **kwargs):
    resp = {'success': True}
    if data: resp.update(data)
    resp.update(kwargs)
    return jsonify(resp)

def err(message, code=400):
    return jsonify({'success': False, 'message': message}), code


# ════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/login', methods=['POST'])
def api_login():
    """Login with phone+PIN or email+PIN."""
    data       = request.json or {}
    identifier = (data.get('identifier') or '').strip()
    pin        = (data.get('pin') or '').strip()
    use_phone  = data.get('use_phone', True)

    if not identifier:
        return err('Enter your phone number or email.')
    if len(pin) != 4 or not pin.isdigit():
        return err('PIN must be exactly 4 digits.')

    if use_phone:
        user = db.verify_user(identifier, pin)
    else:
        user = db.verify_user_by_email(identifier, pin)

    if not user:
        return err('Invalid credentials. Please check your phone/email and PIN.')

    # Start session
    session['phone'] = user['phone']
    db.set_current_user(user['phone'])

    # Load Groq key for this user
    if MODULES_OK:
        groq_key = db.get_setting('groq_api_key', '')
        if groq_key:
            ae.set_api_key(groq_key)

    return ok({'user': {
        'name':  user.get('name', 'User'),
        'phone': user.get('phone', ''),
        'email': user.get('email', ''),
    }})


@app.route('/api/register', methods=['POST'])
def api_register():
    """Create a new account."""
    data   = request.json or {}
    name   = (data.get('name') or '').strip()
    phone  = (data.get('phone') or '').strip()
    email  = (data.get('email') or '').strip().lower()
    pin    = (data.get('pin') or '').strip()
    alerts = data.get('email_alerts', True)

    if not name:               return err('Enter your full name.')
    if len(phone) != 10 or not phone.isdigit(): return err('Enter a valid 10-digit phone number.')
    if '@' not in email:       return err('Enter a valid email address.')
    if len(pin) != 4:          return err('PIN must be exactly 4 digits.')
    if db.get_user_by_phone(phone): return err('Phone number already registered.')
    if db.get_user_by_email(email): return err('Email already registered.')

    ok_created = db.create_user(phone, name, pin, email, 80, int(alerts))
    if not ok_created:
        return err('Registration failed. Please try again.')

    db.set_current_user(phone)
    db.set_user_setting('thresholds', '80,100', phone)
    session['phone'] = phone

    return ok({'user': {'name': name, 'phone': phone, 'email': email}})


@app.route('/api/reset-pin', methods=['POST'])
def api_reset_pin():
    """Legacy direct reset (kept for compatibility)."""
    data    = request.json or {}
    email   = (data.get('email') or '').strip()
    new_pin = (data.get('new_pin') or '').strip()
    if '@' not in email:  return err('Enter a valid email.')
    if len(new_pin) != 4: return err('PIN must be 4 digits.')
    user = db.get_user_by_email(email)
    if not user:          return err('No account found with that email.')
    db.update_user_pin(user['phone'], new_pin)
    return ok({'message': 'PIN reset successfully!'})


# ─── OTP store (in-memory, expires in 10 min) ──────────────────────────────
import random, time
_otp_store = {}   # { email: { otp: str, expires: float, phone: str } }

OTP_EXPIRY_SECONDS = 600   # 10 minutes


@app.route('/api/otp/send', methods=['POST'])
def api_otp_send():
    data  = request.json or {}
    email = (data.get('email') or '').strip().lower()

    if '@' not in email:
        return err('Enter a valid email address.')

    user = db.get_user_by_email(email)
    if not user:
        print(f'[OTP] No account found for email: {email}')
        return ok({'message': 'If that email is registered, an OTP has been sent.'})

    se = (db.get_setting('sender_email', '') or '').strip()
    sp = (db.get_setting('sender_password', '') or '').strip()

    # Always store OTP first regardless of email config
    otp_code = str(random.randint(100000, 999999))
    _otp_store[email] = {
        'otp':     otp_code,
        'expires': time.time() + OTP_EXPIRY_SECONDS,
        'phone':   user['phone'],
    }
    print(f'[OTP] Stored OTP for {email}: {otp_code}')

    # Dev mode: no Gmail configured
    if not se or not sp:
        print(f'[OTP][DEV] OTP for {email}: {otp_code}')
        return ok({
            'message': 'Gmail not configured — OTP printed in server console.',
            'dev_mode': True,
            'dev_otp':  otp_code,
        })

    # Send using es.send_email() — the function that exists in email_service.py
    name    = user.get('name', 'User')
    subject = 'SmartFinance Brain — Your PIN Reset OTP'
    body = (
        f'Hi {name},\n\n'
        f'Your One-Time Password (OTP) for PIN reset is:\n\n'
        f'    {otp_code}\n\n'
        'This OTP is valid for 10 minutes. Do not share it with anyone.\n\n'
        'If you did not request this, please ignore this email.\n\n'
        '-- SmartFinance Brain'
    )

    ok_flag, msg = False, 'not attempted'
    try:
        ok_flag, msg = es.send_email(se, sp, email, subject, body)
        print(f'[OTP] Email send result -> ok={ok_flag}, msg={msg}')
    except Exception as ex:
        msg = str(ex)
        print(f'[OTP] Email exception: {ex}')

    if ok_flag:
        return ok({'message': 'OTP sent to your registered email. Valid for 10 minutes.'})
    else:
        # OTP is stored — tell user to check console if email fails
        print(f'[OTP][FALLBACK] OTP for {email}: {otp_code}')
        return ok({
            'message': f'OTP generated but email failed: {msg}. Check Gmail settings.',
            'email_error': msg,
        })


@app.route('/api/otp/verify', methods=['POST'])
def api_otp_verify():
    """
    Step 2: verify the OTP. Returns a short-lived reset token if correct.
    Body: { "email": "...", "otp": "123456" }
    """
    data  = request.json or {}
    email = (data.get('email') or '').strip().lower()
    otp   = (data.get('otp')   or '').strip()

    record = _otp_store.get(email)
    if not record:
        return err('No OTP request found. Please request a new OTP.')

    if time.time() > record['expires']:
        _otp_store.pop(email, None)
        return err('OTP has expired. Please request a new one.')

    if record['otp'] != otp:
        return err('Incorrect OTP. Please try again.')

    # OTP correct — issue a reset token (random, stored for 5 min)
    import secrets
    reset_token = secrets.token_hex(16)
    _otp_store[email]['reset_token'] = reset_token
    _otp_store[email]['token_expires'] = time.time() + 300   # 5 min

    return ok({'message': 'OTP verified!', 'reset_token': reset_token})


@app.route('/api/otp/reset', methods=['POST'])
def api_otp_reset():
    """
    Step 3: set new PIN using the reset token.
    Body: { "email": "...", "reset_token": "...", "new_pin": "1234" }
    """
    data        = request.json or {}
    email       = (data.get('email')        or '').strip().lower()
    reset_token = (data.get('reset_token')  or '').strip()
    new_pin     = (data.get('new_pin')      or '').strip()

    if len(new_pin) != 4 or not new_pin.isdigit():
        return err('PIN must be exactly 4 digits.')

    record = _otp_store.get(email)
    if not record or record.get('reset_token') != reset_token:
        return err('Invalid or expired reset session. Start over.')

    if time.time() > record.get('token_expires', 0):
        _otp_store.pop(email, None)
        return err('Reset session expired. Please start over.')

    phone = record.get('phone')
    if not phone:
        return err('Account not found.')

    db.update_user_pin(phone, new_pin)
    _otp_store.pop(email, None)   # Consumed — remove from store
    return ok({'message': 'PIN reset successfully! You can now log in.'})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return ok()


# ════════════════════════════════════════════════════════════════════════════
#  DASHBOARD DATA
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    """Return all data needed for the dashboard in one call."""
    phone = get_phone()
    if not phone:
        return err('Not logged in', 401)

    db.set_current_user(phone)
    now       = datetime.now()
    month_str = now.strftime('%Y-%m')

    # --- Basic totals ---
    expenses     = db.get_all_expenses(phone) or []
    all_time     = sum(e['amount'] for e in expenses)
    budget       = db.get_monthly_budget(month_str, phone)

    month_exps   = [e for e in expenses if e['date'].startswith(month_str)]
    month_total  = sum(e['amount'] for e in month_exps)
    month_count  = len(month_exps)

    # Previous month
    prev_month   = (now.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    prev_exps    = [e for e in expenses if e['date'].startswith(prev_month)]
    prev_total   = sum(e['amount'] for e in prev_exps)

    # --- Monthly trend (last 6 months) ---
    monthly_labels = []
    monthly_data   = []
    for i in range(5, -1, -1):
        d = now.replace(day=1) - timedelta(days=i*30)
        m = d.strftime('%Y-%m')
        total = sum(e['amount'] for e in expenses if e['date'].startswith(m))
        monthly_labels.append(d.strftime('%b'))
        monthly_data.append(round(total, 2))

    # --- Category totals (this month) ---
    cat_totals = {}
    for e in month_exps:
        cat = e.get('category', 'Other')
        cat_totals[cat] = cat_totals.get(cat, 0) + e['amount']

    # --- Payment method totals ---
    pm_totals = {}
    for e in expenses:
        pm = e.get('payment_method', 'Other')
        pm_totals[pm] = pm_totals.get(pm, 0) + e['amount']

    # --- Daily trend (last 30 days) ---
    daily_data = []
    for i in range(30, -1, -1):
        d = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        total = sum(e['amount'] for e in expenses if e['date'] == d)
        daily_data.append({'day': 30 - i + 1, 'amount': round(total, 2)})

    # --- Recent expenses ---
    recent = sorted(expenses, key=lambda x: x.get('date', ''), reverse=True)[:20]

    # --- Recurring patterns ---
    recurring = []
    if MODULES_OK:
        try:
            recurring = fm.detect_recurring_expenses() or []
        except Exception:
            pass

    # --- Forecast ---
    forecast = []
    if MODULES_OK:
        try:
            raw = fm.forecast_multi_month(3) or []
            forecast = [{'month': f.get('month', ''), 'predicted': f.get('predicted', 0)} for f in raw]
        except Exception:
            pass

    # --- Obligations summary ---
    obl_summary = {}
    if MODULES_OK:
        try:
            om.update_overdue_statuses()
            obl_summary = om.get_obligation_summary()
        except Exception:
            pass

    # --- Status flags ---
    se = db.get_setting('sender_email', '')
    sp = db.get_setting('sender_password', '')
    user_obj = db.get_user_by_phone(phone) or {}
    groq_active  = MODULES_OK and ae.is_configured() if MODULES_OK else False
    email_active = bool(se and sp) and user_obj.get('email_enabled', 0)

    return ok({
        'all_time_total':  round(all_time, 2),
        'month_total':     round(month_total, 2),
        'prev_total':      round(prev_total, 2),
        'month_count':     month_count,
        'total_count':     len(expenses),
        'budget':          budget,
        'groq_active':     groq_active,
        'email_active':    bool(email_active),
        'monthly_trend':   {'labels': monthly_labels, 'data': monthly_data},
        'category_data':   {k: round(v, 2) for k, v in cat_totals.items()},
        'payment_methods': {k: round(v, 2) for k, v in pm_totals.items()},
        'daily_data':      daily_data,
        'recent_expenses': recent,
        'recurring':       recurring[:5] if recurring else [],
        'forecast':        forecast,
        'obl_summary':     obl_summary,
    })


# ════════════════════════════════════════════════════════════════════════════
#  EXPENSES
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/expenses', methods=['GET'])
def api_get_expenses():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)
    expenses = db.get_all_expenses(phone) or []
    return ok({'expenses': expenses})


@app.route('/api/expenses', methods=['POST'])
def api_add_expense():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    data   = request.json or {}
    date   = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    desc   = (data.get('description') or '').strip()
    amount = float(data.get('amount', 0))
    cat    = data.get('category', 'Other')
    pm     = data.get('payment_method', 'Not Specified')
    notes  = data.get('notes', '')

    if not desc:    return err('Description is required.')
    if amount <= 0: return err('Amount must be greater than 0.')

    added = db.add_expense(date, desc, amount, cat, pm, notes, phone=phone)
    if added:
        return ok({'message': f'Expense added: {desc} — ₹{amount:,.2f}'})
    return err('Failed to add expense.')


@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def api_delete_expense(expense_id):
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    deleted = db.delete_expense(expense_id, phone)
    if deleted:
        return ok({'message': f'Expense #{expense_id} deleted.'})
    return err('Expense not found.')


# ════════════════════════════════════════════════════════════════════════════
#  BUDGET
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/budget', methods=['GET'])
def api_get_budget():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    month_str   = datetime.now().strftime('%Y-%m')
    budget      = db.get_monthly_budget(month_str, phone)
    expenses    = db.get_all_expenses(phone) or []
    month_exps  = [e for e in expenses if e['date'].startswith(month_str)]
    month_total = sum(e['amount'] for e in month_exps)

    forecast = []
    if MODULES_OK:
        try:
            forecast = fm.forecast_multi_month(3) or []
        except Exception:
            pass

    recurring = []
    if MODULES_OK:
        try:
            recurring = fm.detect_recurring_expenses() or []
        except Exception:
            pass

    monthly = {}
    if MODULES_OK:
        try:
            monthly = fm.get_monthly_summary(6) or {}
        except Exception:
            pass

    return ok({
        'budget':       budget,
        'month_total':  round(month_total, 2),
        'monthly_trend': {
            'labels': list(monthly.keys()),
            'data':   [round(v, 2) for v in monthly.values()],
        } if monthly else {},
        'forecast':   forecast,
        'recurring':  recurring[:8] if recurring else [],
    })


@app.route('/api/budget', methods=['POST'])
def api_set_budget():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    data   = request.json or {}
    amount = float(data.get('amount', 0))
    if amount <= 0: return err('Budget must be greater than 0.')

    month = datetime.now().strftime('%Y-%m')
    saved = db.set_monthly_budget(month, amount, phone)
    if saved:
        return ok({'message': f'Budget set to ₹{amount:,.0f}'})
    return err('Failed to save budget.')


# ════════════════════════════════════════════════════════════════════════════
#  OBLIGATIONS (BILLS)
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/obligations', methods=['GET'])
def api_get_obligations():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    obligations = db.get_all_obligations(phone) or []
    return ok({'obligations': obligations})


@app.route('/api/obligations', methods=['POST'])
def api_add_obligation():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    data     = request.json or {}
    name     = (data.get('name') or '').strip()
    amount   = float(data.get('amount', 0))
    due_date = data.get('due_date', '')
    category = data.get('category', 'Other')

    if not name: return err('Bill name is required.')

    obl_id = db.add_obligation(name, amount, due_date, category)
    if obl_id:
        return ok({'message': f'Bill added: {name}', 'id': obl_id})
    return err('Failed to add bill.')


@app.route('/api/obligations/<int:obl_id>/paid', methods=['POST'])
def api_mark_paid(obl_id):
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    updated = db.update_obligation_status(obl_id, 'paid', phone=phone)
    return ok() if updated else err('Bill not found.')


@app.route('/api/obligations/<int:obl_id>', methods=['DELETE'])
def api_delete_obligation(obl_id):
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    deleted = db.delete_obligation(obl_id)
    return ok() if deleted else err('Bill not found.')


# ════════════════════════════════════════════════════════════════════════════
#  AI CHAT
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/chat', methods=['POST'])
def api_chat():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    if not MODULES_OK or not ae.is_configured():
        return ok({
            'response': (
                "Groq AI is not configured. Go to **Budget → Settings**, "
                "enter your free Groq API key from console.groq.com, and save it."
            ),
            'actions': [],
        })

    data    = request.json or {}
    message = (data.get('message') or '').strip()
    history = data.get('history', [])

    if not message:
        return err('Message cannot be empty.')

    try:
        history.append({'role': 'user', 'content': message})
        response_text, actions = ae.chat_response_with_history(history, phone=phone)

        return ok({
            'response': response_text,
            'actions':  actions,
        })
    except Exception as e:
        return ok({
            'response': f'Error: {str(e)}. Please try again.',
            'actions':  [],
        })


# ════════════════════════════════════════════════════════════════════════════
#  FILE UPLOAD (bills, receipts, documents)
# ════════════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════════════
#  IMAGE PROCESSING HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _process_image_groq(raw_bytes: bytes, filename: str, groq_key: str) -> dict:
    """
    Send image to Groq vision API (llama-4-scout or maverick).
    Returns dict with keys: success, summary, financial, text, error.
    """
    import base64, requests as req

    # Groq vision models in priority order
    VISION_MODELS = [
        'meta-llama/llama-4-scout-17b-16e-instruct',
        'meta-llama/llama-4-maverick-17b-128e-instruct',
        'llama-3.2-90b-vision-preview',
    ]

    # Detect mime type
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {'.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.png':'image/png',
                '.bmp':'image/bmp', '.webp':'image/webp',
                '.tiff':'image/tiff', '.tif':'image/tiff'}
    mime = mime_map.get(ext, 'image/jpeg')

    b64 = base64.b64encode(raw_bytes).decode('utf-8')

    SYSTEM = (
        "You are an expert at reading financial documents, bills, receipts, "
        "and invoices. Extract ALL text and financial information accurately."
    )
    PROMPT = (
        "Read this image carefully. Extract:\n"
        "1. All text visible (vendor name, items, amounts, dates, address)\n"
        "2. Total amount (the final payable amount)\n"
        "3. Date\n"
        "4. Vendor/Company name\n"
        "5. Category (Food & Dining / Bills & Utilities / Shopping / Health / "
        "Transportation / Education / Investment / Other)\n\n"
        "Then return a JSON object ONLY (no extra text) in this exact format:\n"
        '{"text":"all extracted text here","summary":"2-3 sentence description",'
        '"vendor":"name","date":"YYYY-MM-DD","total":0.0,'
        '"category":"category name","confidence":"high/medium/low"}'
    )

    last_error = "No models tried"
    for model in VISION_MODELS:
        try:
            payload = {
                "model": model,
                "max_tokens": 1024,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url",
                         "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        {"type": "text", "text": PROMPT}
                    ]
                }]
            }
            resp = req.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}",
                         "Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            print(f"[VISION] {model} -> HTTP {resp.status_code}")

            if resp.status_code == 200:
                raw_text = resp.json()['choices'][0]['message']['content'].strip()
                print(f"[VISION] Response: {raw_text[:200]}")

                # Parse JSON from response
                import re, json as jsonlib
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    parsed = jsonlib.loads(json_match.group())
                    fin = {
                        'vendor':   parsed.get('vendor'),
                        'date':     parsed.get('date'),
                        'total':    parsed.get('total'),
                        'category': parsed.get('category', 'Other'),
                        'confidence': parsed.get('confidence', 'high'),
                    }
                    return {
                        'success':  True,
                        'text':     parsed.get('text', raw_text),
                        'summary':  parsed.get('summary', raw_text[:300]),
                        'financial': fin,
                        'model':    model,
                    }
                else:
                    # Response was plain text, not JSON — still useful
                    fin = _extract_financial_from_text(raw_text)
                    return {
                        'success':  True,
                        'text':     raw_text,
                        'summary':  raw_text[:400],
                        'financial': fin,
                        'model':    model,
                    }

            elif resp.status_code in (404, 400):
                last_error = f"Model {model} not available ({resp.status_code})"
                print(f"[VISION] {last_error}")
                continue  # try next model
            elif resp.status_code == 401:
                return {'success': False, 'error': 'Invalid Groq API key. Check Settings.'}
            else:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                continue

        except req.exceptions.Timeout:
            last_error = f"Timeout on {model}"
            print(f"[VISION] {last_error}")
            continue
        except Exception as e:
            last_error = str(e)
            print(f"[VISION] Exception on {model}: {e}")
            continue

    return {'success': False, 'error': last_error}


def _process_image_ocr(raw_bytes: bytes, filename: str, phone: str) -> dict:
    """
    Tesseract OCR fallback for images when Groq is unavailable.
    Returns dict with summary, financial, text.
    """
    text = ''
    try:
        import io
        from PIL import Image, ImageFilter, ImageEnhance
        import pytesseract

        if os.name == 'nt':
            for tp in [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            ]:
                if os.path.exists(tp):
                    pytesseract.pytesseract.tesseract_cmd = tp
                    break

        img = Image.open(io.BytesIO(raw_bytes))

        # Preprocess: scale up + grayscale + sharpen
        w, h = img.size
        if w < 1200:
            scale = 1200 / w
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        gray = img.convert('L')
        sharp = ImageEnhance.Sharpness(gray).enhance(2.5)
        contrast = ImageEnhance.Contrast(sharp).enhance(2.0)

        # Try multiple PSM modes, take the longest result
        best = ''
        for psm in [6, 3, 4]:
            try:
                cfg = f'--oem 3 --psm {psm}'
                t = pytesseract.image_to_string(contrast, lang='eng', config=cfg)
                if len(t.strip()) > len(best.strip()):
                    best = t
            except Exception:
                continue
        text = best.strip()
        print(f"[OCR] Extracted {len(text)} chars via Tesseract")

    except ImportError as ie:
        print(f"[OCR] Library missing: {ie}")
        text = ''
    except Exception as e:
        print(f"[OCR] Error: {e}")
        text = ''

    if not text or len(text) < 10:
        return {
            'summary':  (
                'Could not extract text from this image. '
                'For best results: set a Groq API key in Settings, '
                'or ensure the image is clear and well-lit.'
            ),
            'financial': {},
            'text': '',
        }

    fin = _extract_financial_from_text(text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    summary = f"Extracted {len(text)} characters. " + ' '.join(lines[:4])
    if fin.get('total'):
        summary += f" Total: Rs.{fin['total']}"
    if fin.get('vendor'):
        summary += f" | Vendor: {fin['vendor']}"

    return {'summary': summary, 'financial': fin, 'text': text}


def _groq_analyze_text(text: str, groq_key: str) -> dict:
    """Use Groq chat (not vision) to summarize and extract from already-extracted text."""
    import requests as req, json as jl, re

    prompt = (
        f"Analyze this financial document text and return ONLY JSON:\n\n{text[:2000]}\n\n"
        'Return: {"summary":"2-3 sentences","vendor":"name or null",'
        '"date":"YYYY-MM-DD or null","total":0.0 or null,'
        '"category":"Food & Dining|Bills & Utilities|Shopping|Health|Transportation|Other"}'
    )
    try:
        resp = req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "max_tokens": 400,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=15
        )
        if resp.status_code == 200:
            raw = resp.json()['choices'][0]['message']['content'].strip()
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                parsed = jl.loads(m.group())
                fin = {k: parsed.get(k) for k in ['vendor','date','total','category']}
                return {'summary': parsed.get('summary',''), 'financial': fin}
    except Exception as e:
        print(f"[GROQ TEXT] Error: {e}")
    return {}


def _extract_financial_from_text(text: str) -> dict:
    """Rule-based financial data extraction from text — works without AI."""
    import re
    result = {'vendor': None, 'date': None, 'total': None, 'category': 'Other', 'confidence': 'low'}

    # Amount: look for total/amount/grand total patterns
    patterns = [
        r'(?:grand\s*total|total\s*amount|net\s*payable|amount\s*due|total)\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*([\d,]+\.?\d*)',
        r'(?:rs\.?|inr|₹)\s*([\d,]+\.?\d{2})',
        r'([\d,]+\.\d{2})(?:\s*(?:rs|inr|₹))?',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                result['total'] = float(m.group(1).replace(',',''))
                if result['total'] > 0:
                    result['confidence'] = 'medium'
                    break
            except ValueError:
                continue

    # Date
    date_m = re.search(r'(\d{1,2}[/\-\.](\d{1,2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[/\-\.]\d{2,4})', text, re.IGNORECASE)
    if date_m:
        result['date'] = date_m.group(1)

    # Vendor: first non-empty line, or line after "from:"
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 3]
    if lines:
        vendor_line = lines[0]
        for l in lines:
            if re.search(r'(?:from|vendor|company|shop|store|merchant)\s*[:\-]\s*(\w+)', l, re.IGNORECASE):
                m = re.search(r'(?:from|vendor|company|shop|store|merchant)\s*[:\-]\s*(.+)', l, re.IGNORECASE)
                if m: vendor_line = m.group(1).strip()[:50]; break
        result['vendor'] = vendor_line[:60]

    # Category from keywords
    cat_map = {
        'Food & Dining':     ['swiggy','zomato','food','restaurant','cafe','dhaba','hotel','pizza','burger','biryani','meal','dining'],
        'Transportation':    ['uber','ola','rapido','auto','taxi','bus','train','petrol','diesel','fuel','metro','toll'],
        'Bills & Utilities': ['electricity','water','gas','broadband','internet','wifi','bill','recharge','mobile','jio','airtel','bsnl'],
        'Health':            ['pharmacy','medical','hospital','clinic','doctor','medicine','health','apollo','wellness'],
        'Shopping':          ['amazon','flipkart','myntra','shop','store','mart','supermarket','purchase','order'],
        'Education':         ['school','college','university','course','tuition','library','book'],
        'Entertainment':     ['netflix','amazon prime','hotstar','movie','cinema','ticket','pvr','inox','game'],
        'Investment':        ['mutual fund','sip','zerodha','groww','lic','insurance','policy','premium'],
    }
    text_lower = text.lower()
    for cat, keywords in cat_map.items():
        if any(kw in text_lower for kw in keywords):
            result['category'] = cat
            break

    return result


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """
    Handle ANY file upload from the AI assistant panel.
    - Excel/CSV/TXT → import as expenses
    - PDF/Images/DOCX → extract text + financial data via document_manager
    """
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    if 'file' not in request.files:
        return err('No file provided.')

    file = request.files['file']
    if not file.filename:
        return err('No file selected.')

    ext = os.path.splitext(file.filename)[1].lower()

    # ── Wrap in BytesIO so seek() always works ──────────────────────────────
    import io
    raw_bytes = file.read()
    file_obj  = io.BytesIO(raw_bytes)
    file_obj.name = file.filename   # modules check .name for extension

    if not MODULES_OK:
        return ok({
            'summary':   f'File received: {file.filename}. Modules not loaded.',
            'financial': {},
            'is_dataset': False,
        })

    # ── Excel / CSV / TXT → treat as expense dataset ────────────────────────
    if ext in ('.xlsx', '.xls', '.csv', '.txt'):
        try:
            from modules import file_processor as fp
            file_obj.seek(0)
            if ext in ('.xlsx', '.xls'):
                success, msg = fp.process_excel_file(file_obj, phone)
            elif ext == '.csv':
                success, msg = fp.process_csv_file(file_obj, phone)
            else:
                success, msg = fp.process_text_file(file_obj, phone)

            # Also build a preview for the AI to describe
            file_obj.seek(0)
            preview = fp.get_import_preview(file_obj, max_rows=6)
            preview_text = ''
            row_count    = 0
            if preview is not None:
                preview_text = preview.to_string(index=False)
                row_count    = len(preview)

            return ok({
                'summary':    msg,
                'is_dataset': True,
                'imported':   False,   # NOT auto-imported — user must confirm in UI
                'preview':    preview_text,
                'row_count':  row_count,
                'financial':  {},
            })
        except Exception as e:
            return ok({
                'summary': f'Dataset processing error: {str(e)}',
                'is_dataset': True,
                'imported': False,
                'financial': {},
            })

    # ── Images → Groq vision API (primary) + Tesseract OCR (fallback) ─────────
    elif ext in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'):
        groq_key = db.get_setting('groq_api_key', '').strip()

        # ── Path A: Groq vision ─────────────────────────────────────────────
        if groq_key:
            result = _process_image_groq(raw_bytes, file.filename, groq_key)
            if result.get('success'):
                return ok({
                    'summary':    result['summary'],
                    'financial':  result['financial'],
                    'doc_type':   result.get('doc_type', 'receipt'),
                    'filename':   file.filename,
                    'is_dataset': False,
                    'text':       result.get('text', ''),
                })
            # Groq failed — fall through to OCR
            print(f'[UPLOAD] Groq vision failed: {result.get("error")} — trying OCR')

        # ── Path B: Tesseract OCR fallback ──────────────────────────────────
        ocr_result = _process_image_ocr(raw_bytes, file.filename, phone)
        return ok({
            'summary':    ocr_result['summary'],
            'financial':  ocr_result['financial'],
            'doc_type':   'image',
            'filename':   file.filename,
            'is_dataset': False,
            'text':       ocr_result.get('text', ''),
        })

    # ── PDF / DOCX → document_manager pipeline ───────────────────────────────
    elif ext in ('.pdf', '.docx', '.md'):
        try:
            file_obj.seek(0)
            groq_key = db.get_setting('groq_api_key', '').strip()
            # For PDF — extract text then summarise via Groq chat if available
            success, result = dm.process_document(file_obj, phone)
            summary = ''
            financial = {}
            text = ''
            if success:
                text     = result.get('text', '')
                financial = result.get('financial', {})
                # If Groq key available, get better summary and financial extraction
                if groq_key and text:
                    gr = _groq_analyze_text(text[:3000], groq_key)
                    if gr.get('summary'): summary = gr['summary']
                    if gr.get('financial'): financial = gr['financial']
                if not summary:
                    summary = result.get('summary', f'Document processed: {file.filename}')
            else:
                summary = str(result)
            return ok({
                'summary':    summary,
                'financial':  financial,
                'doc_type':   'document',
                'filename':   file.filename,
                'is_dataset': False,
                'text':       text[:500],
            })
        except Exception as e:
            return ok({'summary': f'Document error: {e}', 'financial': {}, 'is_dataset': False})

    else:
        return err(f'Unsupported file type: {ext}. Supported: Images (JPG/PNG), PDF, Excel, CSV, DOCX')


# ════════════════════════════════════════════════════════════════════════════
#  IMPORT (Excel/CSV)
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/import', methods=['POST'])
def api_import():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    if 'file' not in request.files:
        return err('No file provided.')

    file = request.files['file']
    ext  = os.path.splitext(file.filename)[1].lower()

    if not MODULES_OK:
        return ok({'message': 'Import received (modules not loaded).'})

    try:
        from modules import file_processor as fp
        if ext in ('.xlsx', '.xls'):
            success, msg = fp.process_excel_file(file, phone)
        elif ext == '.csv':
            success, msg = fp.process_csv_file(file, phone)
        elif ext == '.txt':
            success, msg = fp.process_text_file(file, phone)
        else:
            return err(f'Unsupported file type: {ext}')

        return ok({'message': msg}) if success else err(msg)
    except Exception as e:
        return err(f'Import error: {str(e)}')




# ════════════════════════════════════════════════════════════════════════════
#  IMPORT PREVIEW — Returns headers + first 50 rows as JSON for editing
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/import/preview', methods=['POST'])
def api_import_preview():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    if 'file' not in request.files: return err('No file provided.')
    file = request.files['file']
    ext  = os.path.splitext(file.filename)[1].lower()
    try:
        import pandas as pd, io
        content_bytes = file.read()
        if ext in ('.xlsx', '.xls'):
            df = pd.read_excel(io.BytesIO(content_bytes)).head(100)
        elif ext == '.csv':
            df = pd.read_csv(io.BytesIO(content_bytes)).head(100)
        else:
            return err(f'Preview not supported for {ext}')
        df = df.fillna('')
        return ok({
            'headers': df.columns.tolist(),
            'rows':    df.values.tolist(),
            'total':   len(df),
            'filename': file.filename,
        })
    except Exception as e:
        return err(f'Preview error: {str(e)}')


# ════════════════════════════════════════════════════════════════════════════
#  IMPORTED FILES — list all + delete one (with its expenses)
# ════════════════════════════════════════════════════════════════════════════
@app.route('/api/import/files', methods=['GET'])
def api_imported_files_list():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)
    try:
        files = db.get_all_imported_files(phone)
        # Enrich with file size if file exists on disk
        import os as _os
        for f in files:
            path = f.get('file_path', '')
            f['file_size'] = _os.path.getsize(path) if path and _os.path.exists(path) else 0
        return ok({'files': files})
    except Exception as e:
        return ok({'files': []})


@app.route('/api/import/files/<int:file_id>', methods=['DELETE'])
def api_delete_imported_file(file_id):
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)
    try:
        files = db.get_all_imported_files(phone)
        record = next((f for f in files if f['id'] == file_id), None)
        if not record: return err('File record not found', 404)
        if MODULES_OK:
            from modules import file_processor as fp
            count, removed = fp.delete_imported_file(record, phone)
        else:
            count, removed = 0, False
            db.delete_imported_file_record(file_id, phone)
        return ok({'success': True, 'expenses_deleted': count, 'file_removed': removed})
    except Exception as e:
        return err(f'Delete error: {str(e)}')


# ════════════════════════════════════════════════════════════════════════════
#  SCENARIO SIMULATION
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/scenario', methods=['POST'])
def api_scenario():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    data     = request.json or {}
    category = data.get('category', '')
    increase = float(data.get('increase_pct', 10))

    if not MODULES_OK:
        return err('Modules not loaded.')

    result = fm.simulate_category_increase(category, increase)
    if result:
        return ok({'result': result})
    return err(f'No expenses found for category: {category}')


@app.route('/api/scenario/categories', methods=['GET'])
def api_scenario_categories():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)
    if not MODULES_OK: return ok({'categories': []})
    cats = fm.get_category_wise_total_current_month()
    return ok({'categories': list(cats.keys()), 'totals': cats})


# ════════════════════════════════════════════════════════════════════════════
#  RECURRING PATTERNS
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/recurring', methods=['GET'])
def api_recurring():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)
    if not MODULES_OK: return ok({'patterns': [], 'marked': []})

    try:
        patterns = fm.detect_recurring_expenses() or []
        marked   = fm.get_recurring_expenses() or []
        return ok({'patterns': patterns, 'marked': marked})
    except Exception as e:
        return ok({'patterns': [], 'marked': [], 'error': str(e)})


@app.route('/api/recurring/<int:expense_id>/mark', methods=['POST'])
def api_mark_recurring(expense_id):
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)
    ok_flag = db.update_recurring_status(expense_id, 1, phone)
    return ok() if ok_flag else err('Expense not found.')


# ════════════════════════════════════════════════════════════════════════════
#  WEEKDAY SPENDING
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/weekday', methods=['GET'])
def api_weekday():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)
    if not MODULES_OK: return ok({'totals': {}, 'counts': {}})
    try:
        wd = fm.get_weekday_spending()
        return ok({'totals': wd.get('totals', {}), 'counts': wd.get('counts', {})})
    except Exception as e:
        return ok({'totals': {}, 'counts': {}, 'error': str(e)})


# ════════════════════════════════════════════════════════════════════════════
#  EMAIL ALERTS — budget threshold + due date check
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/alerts/check', methods=['POST'])
def api_check_alerts():
    phone = get_phone()
    if not phone:
        return err('Not logged in', 401)
    db.set_current_user(phone)

    if not MODULES_OK:
        return ok({'sent': [], 'skipped': 'finance modules not loaded'})

    user = db.get_user_by_phone(phone) or {}
    if not user.get('email_enabled', 1):
        return ok({'sent': [], 'skipped': 'email alerts disabled'})

    to_email = (user.get('email') or '').strip()
    if not to_email or '@' not in to_email:
        return ok({'sent': [], 'skipped': 'no email on account'})

    se = (db.get_setting('sender_email', '') or '').strip()
    sp = (db.get_setting('sender_password', '') or '').strip()
    if not se or not sp:
        return ok({'sent': [], 'skipped': 'Gmail not configured in Settings'})
    if not es.is_configured(se, sp):
        return ok({'sent': [], 'skipped': 'Gmail credentials invalid'})

    name      = user.get('name', 'User')
    now       = datetime.now()
    today     = now.strftime('%Y-%m-%d')
    tomorrow  = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    month_str = now.strftime('%Y-%m')
    sent      = []
    errors    = []

    # 1. Budget threshold alert
    try:
        status = fm.get_budget_status(month_str)
        if status is None:
            print(f'[ALERT] No budget set for {month_str}')
        else:
            pct    = float(status.get('percentage_used', 0))
            spent  = float(status.get('spent', 0))
            budget = float(status.get('budget', 0))
            print(f'[ALERT] Budget status: spent={spent} budget={budget} pct={pct}%')

            if budget > 0 and pct > 0:
                raw    = db.get_user_setting('thresholds', '80,100', phone)
                levels = sorted([int(t) for t in raw.split(',') if t.strip().isdigit()])
                for level in levels:
                    if pct < level:
                        continue
                    key = f'budget_alert_{level}_{month_str}'
                    if db.get_user_setting(key, '0', phone) == '1':
                        print(f'[ALERT] Budget {level}% already sent this month')
                        break
                    ok_flag, msg = es.send_multi_threshold_alert(
                        se, sp, to_email, name, spent, budget, pct, level)
                    print(f'[ALERT] Budget {level}% email: ok={ok_flag} msg={msg}')
                    if ok_flag:
                        db.set_user_setting(key, '1', phone)
                        sent.append(f'Budget {level}% alert sent')
                    else:
                        errors.append(f'Budget email failed: {msg}')
                    break  # only one threshold per check
    except Exception as ex:
        errors.append(f'Budget check error: {str(ex)}')
        print(f'[ALERT] Budget exception: {ex}')

    # 2. Bill reminders: 1-day-before, day-of, overdue
    # Dedup key: bill_alert_{id}_{YYYY-MM-DD}  →  once per bill per day
    try:
        for bill in (db.get_all_obligations(phone) or []):
            if bill.get('status') == 'paid':
                continue
            due = (bill.get('due_date') or '').strip()
            if not due or len(due) < 8:
                continue

            bill_id = bill.get('id')
            bname   = (bill.get('name') or 'Bill').strip()
            amount  = float(bill.get('amount') or 0)

            if   due == tomorrow: alert_type = '1 day before due'
            elif due == today:    alert_type = 'due today'
            elif due < today:     alert_type = 'overdue'
            else:                 continue

            key = f'bill_alert_{bill_id}_{today}'
            if db.get_user_setting(key, '0', phone) == '1':
                print(f'[ALERT] Bill "{bname}" already alerted on {today}')
                continue

            ok_flag, msg = es.send_obligation_reminder(
                se, sp, to_email, name, bname, amount, due)
            print(f'[ALERT] Bill "{bname}" ({alert_type}): ok={ok_flag} msg={msg}')

            if ok_flag:
                db.set_user_setting(key, '1', phone)
                sent.append(f'Bill reminder ({alert_type}): {bname}')
            else:
                errors.append(f'Bill "{bname}" email failed: {msg}')

    except Exception as ex:
        errors.append(f'Bill check error: {str(ex)}')
        print(f'[ALERT] Bill exception: {ex}')

    return ok({'sent': sent, 'errors': errors, 'count': len(sent)})


@app.route('/api/account/change-pin', methods=['POST'])
def api_change_pin():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)

    data    = request.json or {}
    old_pin = (data.get('old_pin') or '').strip()
    new_pin = (data.get('new_pin') or '').strip()

    user = db.get_user_by_phone(phone)
    if not user:
        return err('Account not found.')
    if user.get('pin') != old_pin:
        return err('Current PIN is incorrect.')
    if len(new_pin) != 4 or not new_pin.isdigit():
        return err('New PIN must be exactly 4 digits.')

    db.update_user_pin(phone, new_pin)
    return ok({'message': 'PIN changed successfully!'})


@app.route('/api/settings/email/send-test', methods=['POST'])
def api_send_test_email():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    user = db.get_user_by_phone(phone) or {}
    se   = db.get_setting('sender_email', '')
    sp   = db.get_setting('sender_password', '')
    to   = user.get('email', '')
    name = user.get('name', 'User')
    if not MODULES_OK: return err('Modules not loaded.')
    if not es.is_configured(se, sp): return err('Configure Gmail settings first.')
    if not to: return err('No email on your account.')
    ok_flag, msg = es.send_test_email(se, sp, to, name)
    return ok({'message': msg}) if ok_flag else err(msg)


@app.route('/api/account/update', methods=['POST'])
def api_update_account():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)

    data          = request.json or {}
    name          = (data.get('name') or '').strip()
    email         = (data.get('email') or '').strip()
    budget_alert  = int(data.get('budget_alert', 80))
    email_enabled = int(data.get('email_enabled', 1))
    thresholds    = data.get('thresholds', '')

    # Only validate if these fields are actually being set
    if name and email:
        if '@' not in email: return err('Invalid email address.')
        db.update_user(phone, name, email, budget_alert, email_enabled)

    if thresholds:
        db.set_user_setting('thresholds', thresholds, phone)
        # Reset sent flags so new thresholds apply fresh
        month_str = datetime.now().strftime('%Y-%m')
        for lvl in [50, 60, 70, 80, 90, 100]:
            db.set_user_setting(f'budget_alert_{lvl}_{month_str}', '0', phone)

    if 'email_enabled' in data and not name:
        # Partial update — just email_enabled
        user = db.get_user_by_phone(phone) or {}
        db.update_user(phone, user.get('name',''), user.get('email',''),
                       user.get('budget_alert',80), email_enabled)

    return ok({'message': 'Settings updated!'})


@app.route('/api/account/info', methods=['GET'])
def api_account_info():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)

    user = db.get_user_by_phone(phone) or {}
    se   = db.get_setting('sender_email', '')
    groq = db.get_setting('groq_api_key', '')
    thresholds = db.get_user_setting('thresholds', '80,100', phone)

    return ok({
        'name':           user.get('name', ''),
        'email':          user.get('email', ''),
        'phone':          phone,
        'budget_alert':   user.get('budget_alert', 80),
        'email_enabled':  user.get('email_enabled', 1),
        'sender_email':   se,
        'groq_configured': bool(groq),
        'thresholds':     thresholds,
    })

@app.route('/api/settings/groq', methods=['POST'])
def api_save_groq():
    data = request.json or {}
    key  = (data.get('key') or '').strip()
    if not key: return err('API key cannot be empty.')

    db.set_setting('groq_api_key', key)
    if MODULES_OK:
        ae.set_api_key(key)
    return ok({'message': 'Groq API key saved!'})


@app.route('/api/settings/groq/test', methods=['POST'])
def api_test_groq():
    data = request.json or {}
    key  = (data.get('key') or '').strip() or db.get_setting('groq_api_key', '')

    if not key:
        return ok({'success': False, 'message': 'No API key provided.'})

    if not MODULES_OK:
        return ok({'success': False, 'message': 'Modules not loaded.'})

    ae.set_api_key(key)
    ok_flag, msg = ae.test_connection()
    return ok({'success': ok_flag, 'message': msg})


@app.route('/api/settings/email', methods=['POST'])
def api_save_email():
    data     = request.json or {}
    email    = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()

    if not email or not password:
        return err('Email and App Password are required.')

    db.set_setting('sender_email', email)
    db.set_setting('sender_password', password)
    return ok({'message': 'Email settings saved!'})


@app.route('/api/settings/email/test', methods=['POST'])
def api_test_email():
    data     = request.json or {}
    email    = (data.get('email') or '').strip() or db.get_setting('sender_email', '')
    password = (data.get('password') or '').strip() or db.get_setting('sender_password', '')

    if not MODULES_OK:
        return ok({'success': False, 'message': 'Modules not loaded.'})

    ok_flag, msg = es.test_connection(email, password)
    return ok({'success': ok_flag, 'message': msg})


# ════════════════════════════════════════════════════════════════════════════
#  ACCOUNT
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/account', methods=['DELETE'])
def api_delete_account():
    phone = get_phone()
    if not phone: return err('Not logged in', 401)

    data = request.json or {}
    pin  = (data.get('pin') or '').strip()

    user = db.get_user_by_phone(phone)
    if not user or user.get('pin') != pin:
        return err('Wrong PIN. Account not deleted.')

    ok_flag, file_paths = db.delete_user_account(phone)
    if ok_flag:
        # Clean up uploaded files
        for fp_path in (file_paths or []):
            try:
                if fp_path and os.path.exists(fp_path):
                    os.remove(fp_path)
            except Exception:
                pass
        session.clear()
        return ok({'message': 'Account deleted successfully.'})

    return err('Failed to delete account.')


# ════════════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/health', methods=['GET'])
def api_health():
    return ok({
        'status':     'running',
        'modules_ok': MODULES_OK,
        'ui_dir':     UI_DIR,
        'ui_exists':  os.path.exists(UI_DIR),
    })


# ════════════════════════════════════════════════════════════════════════════
#  REPORTS DATA
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/reports/data', methods=['GET'])
def api_reports_data():
    """Return filtered report data for the Reports page."""
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    month    = request.args.get('month', '')    # '2026-03'
    year     = request.args.get('year', '')     # '2026'
    category = request.args.get('category', '') # 'Food & Dining'

    expenses = db.get_all_expenses(phone) or []

    # Filter
    filtered = expenses
    if month:
        filtered = [e for e in filtered if e.get('date', '').startswith(month)]
    elif year:
        filtered = [e for e in filtered if e.get('date', '').startswith(year)]
    if category:
        filtered = [e for e in filtered if e.get('category') == category]

    total    = sum(e['amount'] for e in filtered)
    count    = len(filtered)
    avg      = total / count if count else 0
    largest  = max(filtered, key=lambda e: e['amount'], default=None)

    # Category totals
    cat_totals = {}
    for e in filtered:
        c = e.get('category', 'Other')
        cat_totals[c] = cat_totals.get(c, 0) + e['amount']
    top_cat = max(cat_totals, key=cat_totals.get, default='—') if cat_totals else '—'

    # Daily totals
    daily = {}
    for e in filtered:
        d = e.get('date', '')[:10]
        daily[d] = daily.get(d, 0) + e['amount']
    daily_sorted = sorted(daily.items())

    # Budget
    now       = datetime.now()
    month_str = month or now.strftime('%Y-%m')
    budget    = db.get_monthly_budget(month_str, phone)
    budget_left = (budget - total) if budget else None

    # Bills
    bills = db.get_all_obligations(phone) or []
    pending_bills = [b for b in bills if b.get('status') in ('pending', 'overdue')]

    # Available months/years/categories for filter dropdowns
    all_months = sorted({e['date'][:7] for e in expenses if e.get('date')}, reverse=True)
    all_years  = sorted({e['date'][:4] for e in expenses if e.get('date')}, reverse=True)
    all_cats   = sorted({e.get('category','Other') for e in expenses})

    return ok({
        'total':        round(total, 2),
        'count':        count,
        'avg':          round(avg, 2),
        'budget':       budget,
        'budget_left':  round(budget_left, 2) if budget_left is not None else None,
        'largest':      largest,
        'top_category': top_cat,
        'category_data': {k: round(v, 2) for k, v in cat_totals.items()},
        'daily_data':   [{'date': d, 'amount': round(a, 2)} for d, a in daily_sorted],
        'expenses':     filtered,
        'pending_bills': pending_bills,
        'available_months':    all_months,
        'available_years':     all_years,
        'available_categories': all_cats,
    })


# ════════════════════════════════════════════════════════════════════════════
#  PDF REPORT DOWNLOAD
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/reports/pdf', methods=['GET'])
def api_reports_pdf():
    """Generate and download a PDF report for the current user."""
    phone = get_phone()
    if not phone: return err('Not logged in', 401)
    db.set_current_user(phone)

    month    = request.args.get('month', datetime.now().strftime('%Y-%m'))
    category = request.args.get('category', '')

    user     = db.get_user_by_phone(phone) or {}
    expenses = db.get_all_expenses(phone) or []

    # Filter by month
    filtered = [e for e in expenses if e.get('date', '').startswith(month)]
    if category:
        filtered = [e for e in filtered if e.get('category') == category]

    total   = sum(e['amount'] for e in filtered)
    budget  = db.get_monthly_budget(month, phone)
    bills   = db.get_all_obligations(phone) or []
    pending = [b for b in bills if b.get('status') in ('pending', 'overdue')]

    cat_totals = {}
    for e in filtered:
        c = e.get('category', 'Other')
        cat_totals[c] = cat_totals.get(c, 0) + e['amount']

    saved = (budget - total) if budget and budget > total else 0

    # Generate HTML for PDF
    now_str   = datetime.now().strftime('%d %B %Y, %I:%M %p')
    month_lbl = datetime.strptime(month, '%Y-%m').strftime('%B %Y') if len(month) == 7 else month

    rows_html = ''
    for e in sorted(filtered, key=lambda x: x.get('date',''), reverse=True)[:100]:
        rows_html += f"""
        <tr>
          <td>{e.get('date','')}</td>
          <td>{e.get('description','')}</td>
          <td><span class="badge">{e.get('category','')}</span></td>
          <td>{e.get('payment_method','')}</td>
          <td class="amount">₹{e.get('amount',0):,.2f}</td>
        </tr>"""

    cat_rows = ''
    for cat, amt in sorted(cat_totals.items(), key=lambda x: -x[1]):
        pct = (amt / total * 100) if total else 0
        cat_rows += f"""
        <tr>
          <td>{cat}</td>
          <td>₹{amt:,.2f}</td>
          <td>{pct:.1f}%</td>
        </tr>"""

    bill_rows = ''
    for b in pending:
        status_color = '#EF4444' if b.get('status') == 'overdue' else '#F59E0B'
        bill_rows += f"""
        <tr>
          <td>{b.get('name','')}</td>
          <td>₹{b.get('amount',0):,.2f}</td>
          <td>{b.get('due_date','—')}</td>
          <td style="color:{status_color};font-weight:700;">{b.get('status','').upper()}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', Arial, sans-serif; background: #fff; color: #0F172A; font-size: 13px; }}
  .header {{ background: linear-gradient(135deg, #4F46E5, #7C3AED); padding: 32px 40px; color: white; }}
  .header h1 {{ font-size: 1.6rem; font-weight: 800; letter-spacing: -0.03em; }}
  .header p  {{ opacity: 0.8; font-size: 0.85rem; margin-top: 4px; }}
  .user-info {{ display: flex; gap: 32px; margin-top: 18px; }}
  .user-info div span {{ display: block; }}
  .user-info div span:first-child {{ font-size: 0.72rem; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.06em; }}
  .user-info div span:last-child  {{ font-size: 0.95rem; font-weight: 700; margin-top: 2px; }}
  .body {{ padding: 28px 40px; }}
  .kpi-row {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 28px; }}
  .kpi {{ background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; text-align: center; }}
  .kpi label {{ display: block; font-size: 0.68rem; font-weight: 700; color: #94A3B8; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 6px; }}
  .kpi b {{ font-size: 1.3rem; font-weight: 800; color: #0F172A; display: block; }}
  .kpi.accent b {{ color: #4F46E5; }}
  .kpi.green b  {{ color: #10B981; }}
  .kpi.red b    {{ color: #EF4444; }}
  .section-title {{ font-size: 0.85rem; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.08em; margin: 24px 0 12px; padding-bottom: 8px; border-bottom: 2px solid #E2E8F0; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }}
  th {{ background: #F1F5F9; padding: 9px 12px; text-align: left; font-size: 0.69rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.07em; }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #F1F5F9; font-size: 0.84rem; color: #475569; }}
  tr:last-child td {{ border-bottom: none; }}
  .amount {{ text-align: right; font-weight: 700; color: #EF4444; font-family: monospace; }}
  .badge {{ background: #EEF2FF; color: #4F46E5; padding: 2px 8px; border-radius: 5px; font-size: 0.71rem; font-weight: 700; }}
  .footer {{ margin-top: 32px; padding: 16px 0; border-top: 1px solid #E2E8F0; text-align: center; font-size: 0.75rem; color: #94A3B8; }}
</style>
</head>
<body>
<div class="header">
  <h1>&#128200; SmartFinance Brain — Financial Report</h1>
  <p>Generated on {now_str}</p>
  <div class="user-info">
    <div><span>Account</span><span>{user.get('name','User')}</span></div>
    <div><span>Phone</span><span>{phone}</span></div>
    <div><span>Email</span><span>{user.get('email','—')}</span></div>
    <div><span>Period</span><span>{month_lbl}{' · '+category if category else ''}</span></div>
  </div>
</div>
<div class="body">
  <div class="kpi-row">
    <div class="kpi accent"><label>Total Spent</label><b>₹{total:,.2f}</b></div>
    <div class="kpi"><label>Budget</label><b>{'₹'+f'{budget:,.2f}' if budget else 'Not set'}</b></div>
    <div class="kpi green"><label>Saved</label><b>₹{saved:,.2f}</b></div>
    <div class="kpi"><label>Transactions</label><b>{len(filtered)}</b></div>
  </div>

  <div class="section-title">Spending by Category</div>
  <table><thead><tr><th>Category</th><th>Amount</th><th>% of Total</th></tr></thead>
  <tbody>{cat_rows}</tbody></table>

  {'<div class="section-title">Pending &amp; Overdue Bills</div><table><thead><tr><th>Bill</th><th>Amount</th><th>Due Date</th><th>Status</th></tr></thead><tbody>'+bill_rows+'</tbody></table>' if bill_rows else ''}

  <div class="section-title">Transaction Details (up to 100)</div>
  <table><thead><tr><th>Date</th><th>Description</th><th>Category</th><th>Method</th><th>Amount</th></tr></thead>
  <tbody>{rows_html}</tbody></table>
</div>
<div class="footer">SmartFinance Brain v8.0 &nbsp;|&nbsp; BCA Final Year Project &nbsp;|&nbsp; {user.get('name','User')} &nbsp;|&nbsp; {now_str}</div>
</body></html>"""

    # Try WeasyPrint for PDF, fall back to HTML download
    try:
        from weasyprint import HTML as WH
        pdf_bytes = WH(string=html).write_pdf()
        from flask import Response
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="SFB_Report_{month}_{phone}.pdf"'}
        )
    except ImportError:
        # WeasyPrint not installed — return HTML file (user can print to PDF from browser)
        from flask import Response
        return Response(
            html,
            mimetype='text/html',
            headers={'Content-Disposition': f'attachment; filename="SFB_Report_{month}_{phone}.html"'}
        )


# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print()
    print('=' * 55)
    print('  SmartFinance Brain — Web Server')
    print('=' * 55)
    print()

    # Check ui/ folder exists
    if not os.path.exists(UI_DIR):
        print(f'⚠ WARNING: ui/ folder not found at: {UI_DIR}')
        print('  Create a ui/ folder and put your HTML files inside it.')
        print()
    else:
        html_files = [f for f in os.listdir(UI_DIR) if f.endswith('.html')]
        print(f'✓ UI folder found: {UI_DIR}')
        print(f'  HTML files: {", ".join(html_files) or "none"}')

    # Check modules
    print(f'✓ Modules loaded: {"Yes" if MODULES_OK else "No (check modules/ folder)"}')

    # Check database
    db_path = os.path.join(ROOT, 'data', 'users.db')
    print(f'✓ Database: {"exists" if os.path.exists(db_path) else "will be created on first login"}')

    # Check Groq key
    groq_key = db.get_setting('groq_api_key', '')
    print(f'✓ Groq AI: {"configured" if groq_key else "not set (add in Settings after login)"}')

    print()
    print('  Open your browser and go to:')
    print()
    print('  ➜  http://localhost:5000')
    print()
    print('  Press Ctrl+C to stop the server.')
    print('=' * 55)
    print()

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False,
    )
