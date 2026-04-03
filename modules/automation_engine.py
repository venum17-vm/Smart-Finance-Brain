"""
modules/automation_engine.py — Smart Finance Brain v5.0
Phi-3-mini-4k-instruct with persistent local cache.

MODEL CACHE: models/phi3_mini/ — downloaded once, loads from disk forever after.
Rule-based fallback when model is not loaded — app works without AI.
"""

import re
import json
import os
import sys

_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
_ROOT       = _PARENT_DIR if os.path.basename(_THIS_DIR) == 'modules' else _THIS_DIR
for _p in [_THIS_DIR, _PARENT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ─────────────────────────────────────────────────────────────────────────────
#  MODEL CACHE PATH  — stored inside project, not in HuggingFace cache
# ─────────────────────────────────────────────────────────────────────────────
MODEL_CACHE_DIR = os.path.join(_ROOT, 'models', 'phi3_mini')
MODEL_NAME      = "microsoft/Phi-3-mini-4k-instruct"

_tokenizer  = None
_model      = None
_model_ok   = False
_load_tried = False


def get_model_status() -> str:
    if _model_ok:
        return "loaded"
    if _load_tried:
        return "failed"
    if _is_cached():
        return "cached"       # Downloaded but not yet loaded into RAM
    return "not_downloaded"


def _is_cached() -> bool:
    """Check if model files exist in local cache."""
    config_path = os.path.join(MODEL_CACHE_DIR, 'config.json')
    return os.path.exists(config_path)


def load_model(force: bool = False) -> tuple:
    """
    Load Phi-3. If already downloaded to models/phi3_mini/, loads from there instantly.
    First-time: downloads from HuggingFace and saves to models/phi3_mini/.
    Never re-downloads if cache exists.

    Returns (tokenizer, model) or (None, None).
    """
    global _tokenizer, _model, _model_ok, _load_tried

    if _model_ok and not force:
        return _tokenizer, _model
    if _load_tried and not force:
        return None, None

    _load_tried = True

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

        # ── Load from local cache if available ───────────────────────────────
        if _is_cached():
            print(f"Loading Phi-3 from local cache: {MODEL_CACHE_DIR}")
            source = MODEL_CACHE_DIR
        else:
            print(f"Downloading Phi-3 for first time → saving to {MODEL_CACHE_DIR}")
            source = MODEL_NAME

        _tokenizer = AutoTokenizer.from_pretrained(
            source,
            trust_remote_code=True,
            local_files_only=_is_cached(),
        )
        if _tokenizer.pad_token is None:
            _tokenizer.pad_token = _tokenizer.eos_token

        # Try 4-bit quantization first (saves ~5GB RAM), fall back to float16
        try:
            _model = AutoModelForCausalLM.from_pretrained(
                source,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
                load_in_4bit=True,
                local_files_only=_is_cached(),
            )
        except Exception:
            _model = AutoModelForCausalLM.from_pretrained(
                source,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
                local_files_only=_is_cached(),
            )

        # ── Save to local cache if this was a fresh download ─────────────────
        if source == MODEL_NAME:
            print(f"Saving model to local cache: {MODEL_CACHE_DIR}")
            _tokenizer.save_pretrained(MODEL_CACHE_DIR)
            _model.save_pretrained(MODEL_CACHE_DIR)
            print("Model cached. Future loads will be instant.")

        _model.eval()
        _model_ok = True
        print("Phi-3 ready.")
        return _tokenizer, _model

    except Exception as e:
        print(f"Phi-3 load failed: {e}")
        _model_ok = False
        return None, None


def get_cache_size_mb() -> float:
    """Return size of model cache folder in MB."""
    total = 0
    if os.path.exists(MODEL_CACHE_DIR):
        for dirpath, _, filenames in os.walk(MODEL_CACHE_DIR):
            for f in filenames:
                total += os.path.getsize(os.path.join(dirpath, f))
    return round(total / 1_048_576, 1)


# ─────────────────────────────────────────────────────────────────────────────
#  INFERENCE
# ─────────────────────────────────────────────────────────────────────────────
def _run(prompt: str, max_new_tokens: int = 300) -> str:
    tok, mdl = load_model()
    if not tok or not mdl:
        return ''
    try:
        import torch
        inputs = tok(prompt, return_tensors="pt",
                     max_length=3072, truncation=True).to(mdl.device)
        with torch.no_grad():
            out = mdl.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.3,
                do_sample=True,
                use_cache=False,
                pad_token_id=tok.pad_token_id,
                eos_token_id=tok.eos_token_id,
            )
        full = tok.decode(out[0], skip_special_tokens=True)
        if "<|assistant|>" in full:
            return full.split("<|assistant|>")[-1].strip()
        if prompt in full:
            return full[len(prompt):].strip()
        return full.strip()
    except Exception as e:
        print(f"Phi-3 inference error: {e}")
        return ''


def _chat(system: str, user: str, max_new_tokens: int = 300) -> str:
    prompt = (
        f"<|system|>\n{system}<|end|>\n"
        f"<|user|>\n{user}<|end|>\n"
        f"<|assistant|>\n"
    )
    return _run(prompt, max_new_tokens)


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────
def summarize_document(text: str, max_length: int = 250) -> str:
    truncated = text[:2500]

    if _model_ok:
        result = _chat(
            "You are a financial document analyst. Create concise summaries of financial documents.",
            f"Summarize this financial document in 3-4 sentences:\n\n{truncated}",
            max_new_tokens=max_length,
        )
        if result and len(result) > 30:
            return result

    # Rule-based fallback
    lines  = [l.strip() for l in text.split('\n') if l.strip()]
    words  = text.split()
    facts  = []
    for line in lines[:25]:
        ll = line.lower()
        if any(kw in ll for kw in ['total', 'amount', 'due', 'date', 'bill',
                                    'invoice', 'balance', 'paid', 'account', 'rs.']):
            facts.append(line[:120])
            if len(facts) >= 4:
                break

    summary = f"Document ({len(words)} words). {' '.join(words[:40])}..."
    if facts:
        summary += " Key info: " + " | ".join(facts[:3])
    return summary


def extract_financial_data(text: str) -> dict:
    """Extract structured data: vendor, date, amount, category from document text."""
    result = {
        'vendor':     None,
        'date':       None,
        'total':      None,
        'category':   'Other',
        'items':      [],
        'confidence': 'low',
    }

    if _model_ok:
        raw = _chat(
            "You are a financial data extractor. Return ONLY valid JSON.",
            (
                f"Extract from this document:\n\n{text[:1800]}\n\n"
                'Return ONLY this JSON (null for missing):\n'
                '{"vendor":"","date":"YYYY-MM-DD","total":0.0,'
                '"category":"Food & Dining|Transportation|Shopping|Entertainment|'
                'Bills & Utilities|Health|Education|Investment|Other",'
                '"items":[{"name":"","amount":0.0}]}'
            ),
            max_new_tokens=200,
        )
        parsed = _safe_json(raw)
        if parsed:
            result.update({k: v for k, v in parsed.items() if v is not None})
            result['confidence'] = 'high'
            return result

    # Rule-based fallback
    result['total']    = _extract_amount(text)
    result['date']     = _extract_date(text)
    result['vendor']   = _extract_vendor(text)
    result['category'] = _extract_category(text)
    if result['total']:
        result['confidence'] = 'medium'
    return result


def answer_question(document_text: str, question: str) -> str:
    if _model_ok:
        result = _chat(
            "You are a financial document assistant. Answer questions accurately and briefly.",
            f"Document:\n{document_text[:1800]}\n\nQuestion: {question}",
            max_new_tokens=200,
        )
        if result and len(result) > 10:
            return result

    # Keyword search fallback
    q_words = [w for w in question.lower().split() if len(w) > 3]
    for line in document_text.split('\n'):
        if any(w in line.lower() for w in q_words):
            return f"From document: {line.strip()}"
    return "Could not find a specific answer. Load the AI model for better results."


def chat_response(user_message: str, context: str = '') -> str:
    system = (
        "You are SmartFinance AI, a personal finance assistant for Indian users. "
        "Help with expense tracking, budget analysis, and financial decisions. "
        "Be concise and practical. Use Rs. for currency."
    )
    user_prompt = f"{context}\n\nUser: {user_message}" if context else user_message

    if _model_ok:
        result = _chat(system, user_prompt, max_new_tokens=250)
        if result and len(result) > 10:
            return result

    # Rule-based responses
    msg = user_message.lower()
    if any(w in msg for w in ['hello', 'hi', 'hey', 'namaste']):
        return ("Hello! I'm SmartFinance AI.\n\n"
                "I can help you track expenses, analyze spending patterns, and manage budgets.\n"
                "Upload a bill or ask me anything about your finances!")
    if any(w in msg for w in ['upload', 'bill', 'receipt', 'invoice']):
        return ("Use the **Upload File** button to upload bills and receipts.\n"
                "I'll extract the amount, date, and category automatically!")
    if any(w in msg for w in ['budget', 'spend', 'how much']):
        return ("Check your **Budget & Forecast** page for a full breakdown.\n"
                "Your Dashboard shows 8 charts with complete spending analysis.")
    return ("I'm your SmartFinance AI assistant!\n\n"
            "Upload documents to extract expenses, or ask about your spending patterns, "
            "budget, and financial health.")


# ─────────────────────────────────────────────────────────────────────────────
#  RULE-BASED HELPERS
# ─────────────────────────────────────────────────────────────────────────────
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


def _extract_amount(text: str) -> float | None:
    patterns = [
        r'(?:total|amount due|balance due|payable|grand total|net amount)'
        r'[:\s]+(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.[0-9]{1,2})?)',
        r'(?:rs\.?|inr|₹)\s*([0-9,]+(?:\.[0-9]{1,2})?)',
        r'\b([0-9]{1,7}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\s*(?:rs\.?|rupees?)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(',', ''))
            except ValueError:
                continue
    return None


def _extract_date(text: str) -> str | None:
    for pat in [r'\b(\d{4}[-/]\d{2}[-/]\d{2})\b',
                r'\b(\d{2}[-/]\d{2}[-/]\d{4})\b']:
        m = re.search(pat, text)
        if m:
            raw = m.group(1).replace('/', '-')
            parts = raw.split('-')
            if len(parts[0]) == 4:
                return raw
            try:
                return f"{parts[2]}-{parts[1]:0>2}-{parts[0]:0>2}"
            except Exception:
                pass
    return None


def _extract_vendor(text: str) -> str | None:
    for line in text.strip().split('\n')[:5]:
        s = line.strip()
        if s and 3 < len(s) < 60 and not re.search(r'^\d', s):
            return s
    return None


_CATEGORY_RULES = {
    'Bills & Utilities': 'electricity|water|gas|internet|broadband|mobile|rent|maintenance|recharge|dth|wifi',
    'Food & Dining':     'restaurant|food|lunch|dinner|cafe|pizza|swiggy|zomato|hotel|tea|snack',
    'Transportation':    'uber|ola|taxi|bus|metro|fuel|petrol|diesel|auto|parking|toll|train|flight',
    'Shopping':          'amazon|flipkart|shopping|mall|clothes|shoes|myntra|grocery|supermarket',
    'Entertainment':     'movie|netflix|spotify|prime|hotstar|game|cinema|concert|subscription',
    'Health':            'hospital|doctor|medicine|pharmacy|health|gym|dental|clinic|lab|test',
    'Education':         'book|course|college|fee|school|tuition|coaching|exam|udemy|coursera',
    'Investment':        'insurance|premium|emi|loan|sip|mutual fund|stock|zerodha|groww|fd|ppf',
}


def _extract_category(text: str) -> str:
    tl = text.lower()
    for cat, keywords in _CATEGORY_RULES.items():
        if any(kw in tl for kw in keywords.split('|')):
            return cat
    return 'Other'
