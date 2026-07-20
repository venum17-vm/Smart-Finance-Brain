"""
automation_engine.py — Smart Finance Brain v7.0
Groq API + Full Tool Access

GROQ API SETUP:
  1. Get a free API key from: https://console.groq.com/keys
  2. Set it in your .env file: GROQ_API_KEY=your_key_here
  3. If not set, the app falls back to Tesseract OCR (slower but free)

OPTIONAL: Users can also set their own Groq key via Settings in the UI.
"""

import re, json, os, sys, base64
from datetime import datetime

# ── ENVIRONMENT SETUP ────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
_ROOT       = _PARENT_DIR if os.path.basename(_THIS_DIR) == "modules" else _THIS_DIR
for _p in [_THIS_DIR, _PARENT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

GROQ_API_URL    = "https://api.groq.com/openai/v1/chat/completions"
MODEL_CHAT      = "llama-3.3-70b-versatile"
MODEL_VISION    = "meta-llama/llama-4-scout-17b-16e-instruct"
MODEL_FAST      = "llama-3.1-8b-instant"
REQUEST_TIMEOUT = 30
_api_key: str   = ""

def set_api_key(key: str):
    """Set Groq API key explicitly (e.g., from user settings)."""
    global _api_key
    _api_key = (key or "").strip()

def get_api_key() -> str:
    """
    Get Groq API key from:
      1. User-provided key (highest priority)
      2. Environment variable GROQ_API_KEY
      3. Empty string (feature disabled)
    """
    global _api_key
    if not _api_key:
        _api_key = os.environ.get("GROQ_API_KEY", "").strip()
    return _api_key

def is_configured() -> bool:
    return bool(get_api_key())

def get_model_status() -> str:
    return "loaded" if is_configured() else "not_downloaded"

def get_cache_size_mb() -> float:
    return 0.0

def load_model(force: bool = False):
    return None, None

def _groq_chat(messages, model=MODEL_CHAT, max_tokens=600, temperature=0.3):
    key = get_api_key()
    if not key:
        return ""
    try:
        import requests as _req
        resp = _req.post(GROQ_API_URL,
            headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"},
            json={"model":model,"messages":messages,"max_tokens":max_tokens,"temperature":temperature},
            timeout=REQUEST_TIMEOUT, verify=True)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        print(f"[Groq] HTTP {resp.status_code}: {resp.text[:200]}")
        return ""
    except Exception as e:
        print(f"[Groq] {type(e).__name__}: {e}")
        return ""

def _groq_vision(image_b64, mime, prompt, max_tokens=800):
    key = get_api_key()
    if not key:
        return ""
    vision_models = [
        MODEL_VISION,
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "llama-3.2-90b-vision-preview",
    ]
    messages = [{"role":"user","content":[
        {"type":"image_url","image_url":{"url":f"data:{mime};base64,{image_b64}","detail":"high"}},
        {"type":"text","text":prompt}
    ]}]
    try:
        import requests as _req
        for model in vision_models:
            resp = _req.post(GROQ_API_URL,
                headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"},
                json={"model":model,"messages":messages,"max_tokens":max_tokens},
                timeout=REQUEST_TIMEOUT, verify=True)
            if resp.status_code == 200:
                print(f"[Groq Vision] OK — {model}")
                return resp.json()["choices"][0]["message"]["content"].strip()
            err = resp.text[:300]
            if resp.status_code == 400 and any(w in err.lower() for w in ["decommissioned","no longer supported","deprecated"]):
                print(f"[Groq Vision] {model} decommissioned, trying next...")
                continue
            print(f"[Groq Vision] HTTP {resp.status_code} ({model}): {err}")
        return ""
    except Exception as e:
        print(f"[Groq Vision] {type(e).__name__}: {e}")
        return ""

def test_connection():
    if not is_configured():
        return False, "No API key set. Enter your Groq key in Settings."
    try:
        import requests as _req
        resp = _req.post(GROQ_API_URL,
            headers={"Content-Type":"application/json","Authorization":f"Bearer {get_api_key()}"},
            json={"model":MODEL_FAST,"messages":[{"role":"user","content":"Say OK"}],"max_tokens":5},
            timeout=15, verify=True)
        if resp.status_code == 200:
            return True, "✅ Groq connected! AI is ready."
        return False, f"❌ HTTP {resp.status_code}: {resp.text[:150]}"
    except Exception as e:
        return False, f"❌ {type(e).__name__}: {e}"

def _build_full_context(phone=""):
    try:
        import database as db
        import finance_manager as fm
        now       = datetime.now()
        month_str = now.strftime('%Y-%m')
        expenses  = db.get_all_expenses(phone) or []
        mt        = fm.get_current_month_total()
        pt        = fm.get_previous_month_total()
        budget    = db.get_monthly_budget(month_str, phone)
        cat_tot   = fm.get_category_wise_total_current_month()
        top5      = fm.get_top_expenses(5)
        trend     = fm.get_monthly_summary(6)
        try:
            import obligation_manager as om
            obl = om.get_obligation_summary()
            upcoming = obl.get('upcoming_list', [])
        except Exception:
            obl = {}; upcoming = []

        lines = [
            f"=== LIVE FINANCIAL DATA ({now.strftime('%d %b %Y %H:%M')}) ===",
            f"Total expense records: {len(expenses)}",
            f"This month ({month_str}): Rs.{mt:,.2f}",
            f"Last month: Rs.{pt:,.2f}",
            f"Budget: {'Rs.'+f'{budget:,.2f}' if budget else 'Not set'}",
        ]
        if budget and mt:
            lines.append(f"Budget used: {(mt/budget*100):.1f}%")
        if cat_tot:
            lines.append("This month by category:")
            for c,a in sorted(cat_tot.items(), key=lambda x:-x[1]):
                if a > 0: lines.append(f"  {c}: Rs.{a:,.2f}")
        if expenses:
            recent = sorted(expenses, key=lambda x: x.get('date',''), reverse=True)[:10]
            lines.append("Recent 10 expenses:")
            for e in recent:
                lines.append(f"  [ID:{e.get('id')}] {e.get('date')} | {e.get('description')} | Rs.{e.get('amount',0):,.2f} | {e.get('category')} | {e.get('payment_method')}")
        if top5:
            lines.append("Top 5 all-time:")
            for e in top5:
                lines.append(f"  {e.get('description')} Rs.{e.get('amount',0):,.2f} ({e.get('date')})")
        if trend:
            lines.append("6-month trend:")
            for m,a in trend.items(): lines.append(f"  {m}: Rs.{a:,.2f}")
        if obl:
            lines.append(f"Bills: {obl.get('total',0)} total, {obl.get('pending',0)} pending, {obl.get('overdue',0)} overdue")
            for b in upcoming[:5]:
                lines.append(f"  {b.get('name')} Rs.{b.get('amount',0):,.2f} due {b.get('due_date')}")
        lines.append("=== END ===")
        return "\n".join(lines)
    except Exception as e:
        return f"[Context error: {e}]"

def _normalize_date(s):
    s = s.strip().lower()
    today = datetime.now()
    if s in ('today','now',''): return today.strftime('%Y-%m-%d')
    if s == 'yesterday':
        from datetime import timedelta
        return (today - timedelta(days=1)).strftime('%Y-%m-%d')
    for fmt in ['%Y-%m-%d','%d-%m-%Y','%d/%m/%Y','%m/%d/%Y','%d %b %Y','%d %B %Y']:
        try: return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except: continue
    return today.strftime('%Y-%m-%d')

def _parse_and_execute_action(ai_response, phone=""):
    actions_done = []
    cleaned = ai_response
    try:
        import database as db
        import finance_manager as fm
        import obligation_manager as om

        for m in re.finditer(r'\[ADD_EXPENSE:\s*([^|\]]+)\|([^|\]]+)\|([^|\]]+)\|([^|\]]+)\|([^\]]+)\]', ai_response, re.IGNORECASE):
            date_s,desc,amt_s,cat,pm = [x.strip() for x in m.groups()]
            try:
                amt = float(re.sub(r'[^\d.]','',amt_s))
                date = _normalize_date(date_s)
                cats = fm.get_expense_categories()
                if cat not in cats: cat = fm.auto_categorize(desc)
                if pm not in fm.get_payment_methods(): pm = 'UPI'
                ok = db.add_expense(date, desc, amt, cat, pm, '', phone=phone)
                actions_done.append(f"✅ Added expense: **{desc}** — Rs.{amt:,.2f} ({cat}) on {date}" if ok else f"❌ Failed to add: {desc}")
            except Exception as e:
                actions_done.append(f"❌ Expense error: {e}")
            cleaned = cleaned.replace(m.group(), '').strip()

        for m in re.finditer(r'\[SET_BUDGET:\s*([^\]]+)\]', ai_response, re.IGNORECASE):
            try:
                amt = float(re.sub(r'[^\d.]','',m.group(1).strip()))
                ok = db.set_monthly_budget(datetime.now().strftime('%Y-%m'), amt, phone)
                actions_done.append(f"✅ Budget set to **Rs.{amt:,.2f}**" if ok else "❌ Failed to set budget")
            except Exception as e:
                actions_done.append(f"❌ Budget error: {e}")
            cleaned = cleaned.replace(m.group(), '').strip()

        for m in re.finditer(r'\[ADD_BILL:\s*([^|\]]+)\|([^|\]]+)\|([^|\]]+)\|([^\]]+)\]', ai_response, re.IGNORECASE):
            name,amt_s,due_s,cat = [x.strip() for x in m.groups()]
            try:
                amt = float(re.sub(r'[^\d.]','',amt_s)) if amt_s not in ('0','') else 0.0
                due = _normalize_date(due_s)
                ok = om.add_obligation(name, amt, due, cat)
                actions_done.append(f"✅ Bill added: **{name}** Rs.{amt:,.2f} due {due}" if ok else f"❌ Failed: {name}")
            except Exception as e:
                actions_done.append(f"❌ Bill error: {e}")
            cleaned = cleaned.replace(m.group(), '').strip()

        for m in re.finditer(r'\[DELETE_EXPENSE:\s*(\d+)\]', ai_response, re.IGNORECASE):
            try:
                eid = int(m.group(1))
                ok = db.delete_expense(eid, phone)
                actions_done.append(f"✅ Expense #{eid} deleted." if ok else f"❌ Expense #{eid} not found.")
            except Exception as e:
                actions_done.append(f"❌ Delete error: {e}")
            cleaned = cleaned.replace(m.group(), '').strip()

    except Exception as e:
        print(f"[Action parser] {e}")
    return cleaned.strip(), actions_done

_SYSTEM_PROMPT = """You are SmartFinance AI — a personal finance assistant for Indian users with FULL ACCESS to the user's data and ability to perform actions.

=== ACTIONS (use these tags in your response to execute them) ===
Add expense:    [ADD_EXPENSE: YYYY-MM-DD|description|amount|category|payment_method]
Set budget:     [SET_BUDGET: amount]
Add bill:       [ADD_BILL: bill_name|amount|YYYY-MM-DD|category]
Delete expense: [DELETE_EXPENSE: id]

Categories: Food & Dining, Transportation, Shopping, Entertainment, Bills & Utilities, Health, Education, Investment, Other
Payment: Cash, UPI, Credit Card, Debit Card, Net Banking, Not Specified

=== RULES ===
- Use Rs. for Indian rupees
- When user says "add expense/spent/paid", DO IT with the action tag
- When user says "set budget to X", DO IT with [SET_BUDGET: X]
- When user says "add reminder/bill", DO IT with [ADD_BILL: ...]
- You have the user's live data — NEVER say you can't access it
- You CAN modify data — NEVER say you can't
- Be brief, friendly, use bullet points
- Confirm every action clearly

Examples:
"add 300 for pizza"     → [ADD_EXPENSE: today|Pizza|300|Food & Dining|UPI]
"set budget 20000"      → [SET_BUDGET: 20000]
"remind electricity 800 due 25th" → [ADD_BILL: Electricity|800|2026-04-25|Bills & Utilities]
"""

def chat_response(user_message, context="", phone=""):
    if not is_configured():
        return ("Add your Groq API key in **Budget → Settings** to enable AI features.\nFree key at console.groq.com", [])
    full_context = _build_full_context(phone)
    messages = [
        {"role":"system","content":_SYSTEM_PROMPT},
        {"role":"system","content":full_context},
        {"role":"user",  "content":user_message},
    ]
    raw = _groq_chat(messages, max_tokens=600)
    if not raw:
        return "Couldn't get a response. Please try again.", []
    return _parse_and_execute_action(raw, phone)

def chat_response_with_history(messages_history, phone=""):
    if not is_configured():
        return "Add your Groq API key in Budget → Settings.", []
    full_context = _build_full_context(phone)
    messages = [
        {"role":"system","content":_SYSTEM_PROMPT},
        {"role":"system","content":full_context},
    ]
    messages.extend(messages_history[-16:])
    raw = _groq_chat(messages, max_tokens=600)
    if not raw:
        return "Couldn't get a response. Try again.", []
    return _parse_and_execute_action(raw, phone)

def summarize_document(text, max_length=300):
    if is_configured():
        result = _groq_chat([
            {"role":"system","content":"Summarize financial documents concisely: vendor, date, total in Rs., purpose. 3-4 sentences."},
            {"role":"user","content":f"Summarize:\n\n{text[:3000]}"},
        ], max_tokens=max_length)
        if result and len(result) > 20:
            return result
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    words = text.split()
    facts = []
    for line in lines[:30]:
        if any(kw in line.lower() for kw in ["total","amount","due","date","bill","invoice","rs."]):
            facts.append(line[:120])
            if len(facts) >= 4: break
    s = f"Document ({len(words)} words). {' '.join(words[:40])}..."
    if facts: s += " Key info: " + " | ".join(facts[:3])
    return s

def summarize_image(file_obj):
    if not is_configured(): return ""
    try:
        file_obj.seek(0)
        raw  = file_obj.read()
        b64  = base64.b64encode(raw).decode("utf-8")
        name = getattr(file_obj,"name","image.jpg").lower()
        mime = "image/png" if name.endswith(".png") else "image/jpeg"
        return _groq_vision(b64, mime,
            "Read ALL text in this financial document. List every item, amount, total, service charge, taxes, date, vendor name. Format clearly line by line.",
            max_tokens=800) or ""
    except Exception as e:
        print(f"[summarize_image] {e}"); return ""

def extract_financial_data(text):
    result = {"vendor":None,"date":None,"total":None,"category":"Other","items":[],"confidence":"low"}
    if is_configured():
        raw = _groq_chat([
            {"role":"system","content":"Extract financial data. Return ONLY valid JSON."},
            {"role":"user","content":f"Extract:\n\n{text[:2500]}\n\nReturn ONLY: {{\"vendor\":\"\",\"date\":\"YYYY-MM-DD\",\"total\":0.0,\"category\":\"Food & Dining|Transportation|Shopping|Entertainment|Bills & Utilities|Health|Education|Investment|Other\",\"items\":[{{\"name\":\"\",\"amount\":0.0}}]}}"},
        ], model=MODEL_FAST, max_tokens=300, temperature=0.1)
        parsed = _safe_json(raw)
        if parsed:
            result.update({k:v for k,v in parsed.items() if v is not None})
            result["confidence"] = "high"
            return result
    result["total"]    = _extract_amount(text)
    result["date"]     = _extract_date(text)
    result["vendor"]   = _extract_vendor(text)
    result["category"] = _extract_category(text)
    if result["total"]: result["confidence"] = "medium"
    return result

def extract_financial_data_from_image(file_obj):
    result = {"vendor":None,"date":None,"total":None,"category":"Other","items":[],"confidence":"low"}
    if not is_configured(): return result
    try:
        file_obj.seek(0)
        raw  = file_obj.read()
        b64  = base64.b64encode(raw).decode("utf-8")
        name = getattr(file_obj,"name","image.jpg").lower()
        mime = "image/png" if name.endswith(".png") else "image/jpeg"
        raw_reply = _groq_vision(b64, mime,
            'Extract financial data. Return ONLY JSON: {"vendor":"","date":"YYYY-MM-DD","total":0.0,"category":"Food & Dining|Transportation|Shopping|Entertainment|Bills & Utilities|Health|Education|Investment|Other","items":[{"name":"","qty":1,"amount":0.0}],"service_charge":0.0,"taxes":0.0}',
            max_tokens=400)
        parsed = _safe_json(raw_reply)
        if parsed:
            result.update({k:v for k,v in parsed.items() if v is not None})
            result["confidence"] = "high"
    except Exception as e:
        print(f"[extract_financial_data_from_image] {e}")
    return result

def answer_question(document_text, question):
    if is_configured():
        result = _groq_chat([
            {"role":"system","content":"Answer questions about financial documents accurately. Use Rs."},
            {"role":"user","content":f"Document:\n{document_text[:2500]}\n\nQuestion: {question}"},
        ], max_tokens=250)
        if result and len(result) > 10: return result
    q_words = [w for w in question.lower().split() if len(w) > 3]
    for line in document_text.split("\n"):
        if any(w in line.lower() for w in q_words):
            return f"From document: {line.strip()}"
    return "Could not find a specific answer."

def _safe_json(text):
    if not text: return None
    text = re.sub(r"```json|```","",text).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    raw = m.group() if m else text
    try: return json.loads(raw)
    except: return None

def _extract_amount(text):
    for pat in [
        r"(?:total|amount due|balance due|payable|grand total)[:\s]+(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        r"(?:rs\.?|inr|₹)\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try: return float(m.group(1).replace(",",""))
            except: continue
    return None

def _extract_date(text):
    for pat in [r"\b(\d{4}[-/]\d{2}[-/]\d{2})\b", r"\b(\d{2}[-/]\d{2}[-/]\d{4})\b"]:
        m = re.search(pat, text)
        if m:
            raw = m.group(1).replace("/","-")
            p = raw.split("-")
            if len(p[0]) == 4: return raw
            try: return f"{p[2]}-{p[1]:0>2}-{p[0]:0>2}"
            except: pass
    return None

def _extract_vendor(text):
    for line in text.strip().split("\n")[:5]:
        s = line.strip()
        if s and 3 < len(s) < 60 and not re.search(r"^\d",s): return s
    return None

_CATEGORY_RULES = {
    "Bills & Utilities":"electricity|water|gas|internet|broadband|mobile|rent|maintenance|recharge|dth|wifi",
    "Food & Dining":"restaurant|food|lunch|dinner|cafe|pizza|swiggy|zomato|hotel|tea|snack",
    "Transportation":"uber|ola|taxi|bus|metro|fuel|petrol|diesel|auto|parking|toll|train|flight",
    "Shopping":"amazon|flipkart|shopping|mall|clothes|shoes|myntra|grocery|supermarket",
    "Entertainment":"movie|netflix|spotify|prime|hotstar|game|cinema|concert|subscription",
    "Health":"hospital|doctor|medicine|pharmacy|health|gym|dental|clinic|lab|test",
    "Education":"book|course|college|fee|school|tuition|coaching|exam|udemy|coursera",
    "Investment":"insurance|premium|emi|loan|sip|mutual fund|stock|zerodha|groww|fd|ppf",
}

def _extract_category(text):
    tl = text.lower()
    for cat, kws in _CATEGORY_RULES.items():
        if any(kw in tl for kw in kws.split("|")): return cat
    return "Other"
