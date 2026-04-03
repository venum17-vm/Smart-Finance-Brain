"""
obligation_manager.py — Smart Finance Brain
Handles bills, subscriptions, warranties — extraction + tracking.
"""

import re
import os, sys
from datetime import datetime, timedelta

# ── Path fix: works whether this file is at root OR inside modules/ ───────────
_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
for _p in [_THIS_DIR, _PARENT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
# ─────────────────────────────────────────────────────────────────────────────

import database as db

# ─────────────────────────────────────────────
#  DUE DATE EXTRACTION FROM TEXT
# ─────────────────────────────────────────────
DATE_PATTERNS = [
    r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',          # DD/MM/YYYY or DD-MM-YYYY
    r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',             # YYYY-MM-DD
    r'\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{2,4})\b',       # 15 March 2024
    r'\b([A-Za-z]{3,9})\s+(\d{1,2})[,\s]+(\d{2,4})\b',    # March 15, 2024
]

AMOUNT_PATTERNS = [
    r'(?:rs\.?|inr|₹)\s*([0-9,]+(?:\.[0-9]{1,2})?)',
    r'(?:total|amount|due|payable|balance)[:\s]+(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.[0-9]{1,2})?)',
    r'\b([0-9]{1,7}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\s*(?:rs\.?|inr|₹|rupees?)',
]

OBLIGATION_KEYWORDS = {
    'electricity': 'Bills & Utilities',
    'water':       'Bills & Utilities',
    'gas':         'Bills & Utilities',
    'internet':    'Bills & Utilities',
    'broadband':   'Bills & Utilities',
    'mobile':      'Bills & Utilities',
    'rent':        'Bills & Utilities',
    'maintenance': 'Bills & Utilities',
    'insurance':   'Investment',
    'premium':     'Investment',
    'emi':         'Investment',
    'loan':        'Investment',
    'credit':      'Investment',
    'netflix':     'Entertainment',
    'spotify':     'Entertainment',
    'amazon prime':'Entertainment',
    'hotstar':     'Entertainment',
    'gym':         'Health',
    'hospital':    'Health',
    'school':      'Education',
    'college':     'Education',
    'tuition':     'Education',
}


def extract_due_date(text: str) -> str | None:
    """Extract most probable due/payment date from document text."""
    text_lower = text.lower()

    # Prioritise lines that mention "due", "pay by", "payment date"
    priority_lines = []
    for line in text.split('\n'):
        ll = line.lower()
        if any(kw in ll for kw in ['due', 'pay by', 'payment date', 'last date',
                                    'due date', 'before', 'deadline']):
            priority_lines.append(line)

    search_text = '\n'.join(priority_lines) + '\n' + text

    for pat in DATE_PATTERNS:
        match = re.search(pat, search_text, re.IGNORECASE)
        if match:
            parsed = _try_parse_date(match)
            if parsed:
                return parsed.strftime('%Y-%m-%d')
    return None


def extract_amount(text: str) -> float | None:
    """Extract total/due amount from text."""
    for pat in AMOUNT_PATTERNS:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(',', '')
            try:
                return float(raw)
            except ValueError:
                continue
    return None


def detect_obligation_type(text: str) -> tuple[str, str]:
    """Return (name, category) based on keywords in document text."""
    text_lower = text.lower()
    for keyword, category in OBLIGATION_KEYWORDS.items():
        if keyword in text_lower:
            name = keyword.title() + ' Bill'
            return name, category
    return 'Document Obligation', 'Other'


def create_obligation_from_text(text: str, doc_id: int = None,
                                 filename: str = '') -> dict:
    """
    Analyse document text and create an obligation record.
    Returns a dict with extracted fields (not yet saved — caller decides).
    """
    due_date = extract_due_date(text)
    amount   = extract_amount(text)
    name, category = detect_obligation_type(text)

    if filename:
        base = filename.rsplit('.', 1)[0].replace('_', ' ').title()
        if len(base) < 50:
            name = base

    # Guess if recurring
    is_recurring = 1 if any(
        kw in text.lower() for kw in
        ['monthly', 'quarterly', 'annually', 'yearly', 'every month',
         'subscription', 'emi', 'recurring']
    ) else 0

    recurrence_period = 'monthly'
    if 'quarterly' in text.lower():
        recurrence_period = 'quarterly'
    elif 'annually' in text.lower() or 'yearly' in text.lower():
        recurrence_period = 'annually'

    return {
        'name': name,
        'amount': amount or 0.0,
        'due_date': due_date,
        'category': category,
        'is_recurring': is_recurring,
        'recurrence_period': recurrence_period,
        'document_id': doc_id,
        'status': 'pending'
    }


# ─────────────────────────────────────────────
#  CRUD WRAPPERS
# ─────────────────────────────────────────────
def add_obligation(name, amount=0.0, due_date=None, category='Other',
                   is_recurring=0, recurrence_period='monthly',
                   notes='', document_id=None):
    return db.add_obligation(name, amount, due_date, category,
                             is_recurring, recurrence_period, notes, document_id)


def get_all_obligations() -> list:
    return db.get_all_obligations()


def get_pending_obligations() -> list:
    return [o for o in db.get_all_obligations() if o['status'] == 'pending']


def get_overdue_obligations() -> list:
    today = datetime.now().strftime('%Y-%m-%d')
    return [
        o for o in db.get_all_obligations()
        if o['status'] == 'pending' and o['due_date'] and o['due_date'] < today
    ]


def get_upcoming_obligations(days: int = 7) -> list:
    today = datetime.now()
    cutoff = (today + timedelta(days=days)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    return [
        o for o in db.get_all_obligations()
        if o['status'] == 'pending'
        and o['due_date']
        and today_str <= o['due_date'] <= cutoff
    ]


def mark_paid(obl_id: int) -> bool:
    return db.update_obligation_status(obl_id, 'paid')


def mark_overdue(obl_id: int) -> bool:
    return db.update_obligation_status(obl_id, 'overdue')


def delete_obligation(obl_id: int) -> bool:
    return db.delete_obligation(obl_id)


def update_overdue_statuses():
    """Auto-flag any pending obligations whose due_date has passed."""
    today = datetime.now().strftime('%Y-%m-%d')
    updated = 0
    for o in db.get_all_obligations():
        if o['status'] == 'pending' and o['due_date'] and o['due_date'] < today:
            db.update_obligation_status(o['id'], 'overdue')
            updated += 1
    return updated


def get_obligation_summary() -> dict:
    all_obl = db.get_all_obligations()
    today = datetime.now().strftime('%Y-%m-%d')
    pending  = [o for o in all_obl if o['status'] == 'pending']
    overdue  = [o for o in all_obl if o['status'] in ('overdue',) or
                (o['status'] == 'pending' and o['due_date'] and o['due_date'] < today)]
    paid     = [o for o in all_obl if o['status'] == 'paid']
    upcoming = get_upcoming_obligations(7)
    total_due = sum(o['amount'] for o in pending if o['amount'])
    return {
        'total': len(all_obl),
        'pending': len(pending),
        'overdue': len(overdue),
        'paid': len(paid),
        'upcoming_7d': len(upcoming),
        'total_due_amount': total_due,
        'upcoming_list': upcoming,
    }


# ─────────────────────────────────────────────
#  INTERNAL HELPERS
# ─────────────────────────────────────────────
MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10,
    'november': 11, 'december': 12,
}


def _try_parse_date(match) -> datetime | None:
    groups = match.groups()
    try:
        if len(groups) == 3:
            g0, g1, g2 = groups[0], groups[1], groups[2]

            # YYYY-MM-DD
            if len(str(g0)) == 4 and str(g0).isdigit():
                return datetime(int(g0), int(g1), int(g2))

            # Month name patterns
            if isinstance(g1, str) and not g1.isdigit():
                mon = MONTH_MAP.get(g1.lower()[:3])
                if mon:
                    yr = int(g2) if len(str(g2)) == 4 else 2000 + int(g2)
                    return datetime(yr, mon, int(g0))
            if isinstance(g0, str) and not g0.isdigit():
                mon = MONTH_MAP.get(g0.lower()[:3])
                if mon:
                    yr = int(g2) if len(str(g2)) == 4 else 2000 + int(g2)
                    return datetime(yr, mon, int(g1))

            # DD/MM/YYYY  or  MM/DD/YYYY — try DD/MM first
            d, m, y = int(g0), int(g1), int(g2)
            yr = y if y > 999 else (2000 + y)
            if 1 <= m <= 12 and 1 <= d <= 31:
                return datetime(yr, m, d)
    except Exception:
        pass
    return None
