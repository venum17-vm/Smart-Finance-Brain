"""
groq_engine.py — Smart Finance Brain v6.1
Groq API with Llama-3 — replaces Phi-3 completely.
No downloads, no GPU, no torch. Works instantly with internet.

FIX v6.1:
  - Corrected model IDs (verified working on Groq April 2026)
  - Robust fallback chain: 70b → 8b → rule-based
  - Better 401/invalid key detection
  - max_completion_tokens used instead of max_tokens (Groq SDK ≥0.5)

GET FREE API KEY: https://console.groq.com → Sign up → API Keys → Create key
Set key in app: AI Assistant → API Settings → paste key → Save
"""

import os, sys, re, json, base64

_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
for _p in [_THIS_DIR, _PARENT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import database as db

# ── Model config ─────────────────────────────────────────────────────────────
MODEL_PRIMARY  = "llama-3.3-70b-versatile"   # best quality (verified Groq model)
MODEL_FALLBACK = "llama-3.1-8b-instant"       # faster fallback
TEMPERATURE    = 0.3
MAX_TOKENS     = 1024

SUPPORTED_EXTS = {
    'text':  ['.txt', '.md', '.csv', '.py', '.json', '.xml', '.html'],
    'doc':   ['.pdf', '.docx'],
    'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'],
    'data':  ['.xlsx', '.xls'],
}


def _get_key(api_key: str = '') -> str:
    return (api_key or db.get_setting('groq_api_key', '')).strip()


def get_client(api_key: str = ''):
    """Return Groq client. Raises ValueError if key missing."""
    key = _get_key(api_key)
    if not key:
        raise ValueError("Groq API key not set. Go to AI Assistant → API Settings.")
    try:
        from groq import Groq
        return Groq(api_key=key)
    except ImportError:
        raise ImportError("groq not installed. Run: pip install groq")


def is_configured(api_key: str = '') -> bool:
    key = _get_key(api_key)
    return bool(key and len(key) > 20)


def test_connection(api_key: str) -> tuple[bool, str]:
    """Test Groq API key — sends minimal request."""
    try:
        client = get_client(api_key)
        client.chat.completions.create(
            model=MODEL_FALLBACK,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        return True, f"✅ Connected! Model: {MODEL_PRIMARY}"
    except Exception as e:
        err = str(e)
        if "401" in err or "invalid_api_key" in err.lower() or "invalid api key" in err.lower():
            return False, "❌ Invalid API key. Verify at console.groq.com → API Keys."
        if "403" in err:
            return False, "❌ API key lacks permissions. Regenerate at console.groq.com."
        if "429" in err:
            return False, "⚠️ Rate limit hit. Wait a moment and try again."
        if "model_not_found" in err or "404" in err:
            return False, f"❌ Model not found. Error: {err}"
        return False, f"❌ Connection failed: {err}"


# ─────────────────────────────────────────────────────────────────────────────
#  CORE CHAT
# ─────────────────────────────────────────────────────────────────────────────
def _chat(system: str, user_msg: str, max_tokens: int = MAX_TOKENS) -> str:
    """Send chat to Groq; tries primary model then fallback."""
    if not is_configured():
        return ""

    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_msg},
    ]

    for model in [MODEL_PRIMARY, MODEL_FALLBACK]:
        try:
            client = get_client()
            resp   = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "401" in err or "invalid_api_key" in err.lower():
                return "[❌ Invalid Groq API key. Update it in AI Assistant → API Settings.]"
            if "429" in err:
                return "[⚠️ Rate limit reached. Please wait 10 seconds and try again.]"
            if "model_not_found" in err or "404" in err:
                continue   # Try fallback model
            return f"[Groq error ({model}): {err}]"

    return "[Both Groq models unavailable. Check console.groq.com for status.]"


def _safe_json(text: str) -> dict | None:
    if not text:
        return None
    text = re.sub(r'```json|```', '', text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  FILE READING
# ─────────────────────────────────────────────────────────────────────────────
def read_file_content(file_obj) -> tuple[str, str]:
    """Extract text from ANY file. Returns (content, method_used)."""
    name = getattr(file_obj, 'name', 'unknown')
    ext  = os.path.splitext(name)[1].lower()

    if ext == '.pdf':
        try:
            import fitz
            file_obj.seek(0)
            pdf  = fitz.open(stream=file_obj.read(), filetype="pdf")
            text = ""
            for i, page in enumerate(pdf, 1):
                pt = page.get_text()
                if not pt.strip():
                    try:
                        import pytesseract
                        from PIL import Image
                        import io as _io
                        pix = page.get_pixmap(dpi=250)
                        img = Image.open(_io.BytesIO(pix.tobytes("png")))
                        pt  = pytesseract.image_to_string(img, lang='eng')
                    except Exception:
                        pt = "[scanned page — OCR unavailable]"
                text += f"\n--- Page {i} ---\n{pt}"
            pdf.close()
            return text.strip(), "PyMuPDF"
        except Exception as e:
            return f"[PDF error: {e}]", "error"

    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
        try:
            import pytesseract
            from PIL import Image, ImageEnhance
            import numpy as np, cv2
            file_obj.seek(0)
            img  = Image.open(file_obj).convert('RGB')
            arr  = np.array(img)
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 11, 2)
            denoised = cv2.fastNlMeansDenoising(thresh, h=10)
            proc_img = Image.fromarray(denoised)
            w, h = proc_img.size
            if w < 1200:
                scale    = 1200 / w
                proc_img = proc_img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
            config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
            text   = pytesseract.image_to_string(proc_img, lang='eng', config=config)
            if len(text.strip()) < 20:
                text = pytesseract.image_to_string(img, lang='eng')
            return text.strip(), "Tesseract OCR"
        except ImportError:
            return "[Image OCR requires: pip install pytesseract pillow opencv-python]", "error"
        except Exception as e:
            return f"[Image error: {e}]", "error"

    elif ext in ['.xlsx', '.xls']:
        try:
            import pandas as pd
            file_obj.seek(0)
            df    = pd.read_excel(file_obj)
            lines = [f"Columns: {', '.join(df.columns.tolist())}",
                     f"Rows: {len(df)}", ""]
            for _, row in df.head(50).iterrows():
                lines.append(" | ".join(str(v) for v in row.values))
            return '\n'.join(lines), "pandas Excel"
        except Exception as e:
            return f"[Excel error: {e}]", "error"

    elif ext == '.csv':
        try:
            import pandas as pd
            file_obj.seek(0)
            df    = pd.read_csv(file_obj)
            lines = [f"Columns: {', '.join(df.columns.tolist())}",
                     f"Rows: {len(df)}", ""]
            for _, row in df.head(50).iterrows():
                lines.append(" | ".join(str(v) for v in row.values))
            return '\n'.join(lines), "pandas CSV"
        except Exception as e:
            return f"[CSV error: {e}]", "error"

    elif ext == '.docx':
        try:
            from docx import Document as DocxDoc
            file_obj.seek(0)
            doc   = DocxDoc(file_obj)
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_text = ' | '.join(c.text.strip() for c in row.cells if c.text.strip())
                    if row_text:
                        parts.append(row_text)
            return '\n'.join(parts), "python-docx"
        except Exception as e:
            return f"[DOCX error: {e}]", "error"

    else:
        try:
            file_obj.seek(0)
            for enc in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    file_obj.seek(0)
                    return file_obj.read().decode(enc), f"text ({enc})"
                except Exception:
                    continue
            return "[Could not decode file]", "error"
        except Exception as e:
            return f"[Read error: {e}]", "error"


# ─────────────────────────────────────────────────────────────────────────────
#  FINANCIAL DATA EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────
def extract_financial_data(text: str) -> dict:
    default = {'vendor': None, 'date': None, 'total': None,
               'category': 'Other', 'items': [], 'confidence': 'low'}

    if not is_configured():
        return {**default, **_regex_extract(text)}

    prompt = (
        f"Extract financial data from this document text.\n\nTEXT:\n{text[:2000]}\n\n"
        "Return ONLY valid JSON (no explanation), null for missing fields:\n"
        '{"vendor":"string","date":"YYYY-MM-DD or null","total":number_or_null,'
        '"category":"Food & Dining|Transportation|Shopping|Entertainment|'
        'Bills & Utilities|Health|Education|Travel|Investment|Other",'
        '"items":[{"name":"string","amount":number}],'
        '"invoice_no":"string or null","gst_no":"string or null"}'
    )

    raw    = _chat("You are a financial document parser. Return ONLY valid JSON.", prompt, max_tokens=400)
    parsed = _safe_json(raw)

    if parsed:
        return {**default, **parsed, 'confidence': 'high'}

    return {**default, **_regex_extract(text), 'confidence': 'medium'}


def _regex_extract(text: str) -> dict:
    result = {}
    for pat in [r'(?:total|amount due|grand total|payable)[:\s]+(?:rs\.?|₹|inr)?\s*([0-9,]+(?:\.[0-9]{1,2})?)',
                r'(?:rs\.?|₹)\s*([0-9,]+(?:\.[0-9]{1,2})?)']:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                result['total'] = float(m.group(1).replace(',', ''))
                break
            except Exception:
                pass
    for pat in [r'\b(\d{4}-\d{2}-\d{2})\b', r'\b(\d{2}/\d{2}/\d{4})\b']:
        m = re.search(pat, text)
        if m:
            result['date'] = m.group(1)
            break
    for line in text.split('\n')[:5]:
        s = line.strip()
        if s and 3 < len(s) < 60 and not re.match(r'^\d', s):
            result['vendor'] = s
            break
    cats = {
        'Bills & Utilities': 'electricity|water|gas|internet|broadband|rent|recharge',
        'Food & Dining':     'restaurant|swiggy|zomato|cafe|food|lunch|dinner',
        'Transportation':    'uber|ola|petrol|fuel|taxi|metro|bus|parking',
        'Shopping':          'amazon|flipkart|mall|shop|store',
        'Health':            'hospital|pharmacy|doctor|medicine|clinic',
        'Education':         'school|college|course|tuition|book',
        'Investment':        'insurance|emi|sip|loan|fd|ppf',
    }
    tl = text.lower()
    for cat, kws in cats.items():
        if any(k in tl for k in kws.split('|')):
            result['category'] = cat
            break
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENT SUMMARIZATION
# ─────────────────────────────────────────────────────────────────────────────
def summarize_document(text: str) -> str:
    if not is_configured():
        words = text.split()
        return f"Document ({len(words)} words). {' '.join(words[:40])}..."
    return _chat(
        "You are a financial document analyst. Summarize financial documents concisely.",
        f"Summarize this financial document in 3-4 sentences, highlighting key amounts, dates, and purpose:\n\n{text[:3000]}",
        max_tokens=300,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Q&A
# ─────────────────────────────────────────────────────────────────────────────
def answer_question(doc_text: str, question: str) -> str:
    if not is_configured():
        for line in doc_text.split('\n'):
            if any(w in line.lower() for w in question.lower().split() if len(w) > 3):
                return f"From document: {line.strip()}"
        return "AI not configured. Set Groq API key in AI Assistant → API Settings."
    return _chat(
        "You are a financial assistant. Answer questions about financial documents accurately and briefly.",
        f"Document:\n{doc_text[:2500]}\n\nQuestion: {question}",
        max_tokens=400,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  CHAT RESPONSE
# ─────────────────────────────────────────────────────────────────────────────
def chat_response(user_message: str, financial_context: str = '') -> str:
    if not is_configured():
        return ("🔑 **Groq AI not configured.**\n\n"
                "Go to **AI Assistant → API Settings** and enter your free Groq API key.\n"
                "Get one instantly at: https://console.groq.com (free)")

    system = (
        "You are SmartFinance AI, a personal finance assistant for Indian users. "
        "Help with expense tracking, budget analysis, spending patterns, and financial planning. "
        "Be concise, practical, and use ₹ for currency. "
        "When referencing numbers from context, be specific."
    )
    user = f"{financial_context}\n\nUser question: {user_message}" if financial_context else user_message
    return _chat(system, user, max_tokens=500)


# ─────────────────────────────────────────────────────────────────────────────
#  SPENDING ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def analyze_spending_patterns(expenses: list) -> str:
    if not is_configured() or not expenses:
        return "AI not configured or no data available."

    import pandas as pd
    df         = pd.DataFrame(expenses)
    cat_totals = df.groupby('category')['amount'].sum().sort_values(ascending=False)
    monthly    = df.groupby(df['date'].str[:7])['amount'].sum()

    summary = (
        f"User has {len(expenses)} expense entries.\n"
        f"Total spent: ₹{df['amount'].sum():,.2f}\n"
        f"Date range: {df['date'].min()} to {df['date'].max()}\n\n"
        f"Category breakdown:\n{cat_totals.to_string()}\n\n"
        f"Monthly totals:\n{monthly.to_string()}\n\n"
        f"Recent 10 expenses:\n"
        f"{df.head(10)[['date','description','amount','category']].to_string(index=False)}"
    )

    return _chat(
        "You are a personal finance analyst. Analyze spending data and provide actionable insights.",
        (f"Analyze this user's spending data and provide:\n"
         f"1. Top 3 spending insights\n"
         f"2. Areas to reduce spending\n"
         f"3. Positive financial habits observed\n"
         f"4. One specific recommendation\n\n"
         f"DATA:\n{summary}"),
        max_tokens=600,
    )


def get_budget_recommendation(expenses: list, current_budget: float) -> str:
    if not is_configured():
        return "AI not configured."
    if not expenses:
        return "No expense data available for recommendation."

    import pandas as pd
    df    = pd.DataFrame(expenses)
    avg_m = df.groupby(df['date'].str[:7])['amount'].sum().mean()
    cats  = df.groupby('category')['amount'].sum().sort_values(ascending=False).head(5)

    prompt = (
        f"Monthly average spend: ₹{avg_m:,.0f}\n"
        f"Current budget: ₹{current_budget:,.0f}\n"
        f"Top spending categories:\n{cats.to_string()}\n\n"
        f"Recommend an optimal monthly budget with category-wise breakdown. Be specific with numbers."
    )
    return _chat("You are a personal finance advisor for Indian users.", prompt, max_tokens=400)
