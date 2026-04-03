"""
finance_manager.py — Smart Finance Brain
Business logic: categorisation, analytics, forecasting, simulation.
"""

import os, sys

# ── Path fix: works whether this file is at root OR inside modules/ ───────────
_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
for _p in [_THIS_DIR, _PARENT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
# ─────────────────────────────────────────────────────────────────────────────

import database as db
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False


# ─────────────────────────────────────────────
#  CATEGORIES & PAYMENT METHODS
# ─────────────────────────────────────────────
CATEGORIES = [
    "Food & Dining", "Transportation", "Shopping", "Entertainment",
    "Bills & Utilities", "Health", "Education", "Travel", "Investment", "Other"
]

PAYMENT_METHODS = [
    "Cash", "Credit Card", "Debit Card", "UPI", "Net Banking",
    "Wallet", "Cheque", "Not Specified"
]

CATEGORY_KEYWORDS = {
    "Food & Dining":    ['restaurant', 'food', 'lunch', 'dinner', 'breakfast', 'cafe',
                         'pizza', 'swiggy', 'zomato', 'domino', 'mcdonalds', 'kfc',
                         'snack', 'coffee', 'tea', 'biryani', 'hotel', 'eat'],
    "Transportation":   ['uber', 'ola', 'taxi', 'bus', 'metro', 'fuel', 'petrol',
                         'diesel', 'auto', 'rickshaw', 'train', 'flight', 'toll',
                         'parking', 'rapido'],
    "Shopping":         ['amazon', 'flipkart', 'shopping', 'mall', 'clothes', 'shirt',
                         'shoes', 'myntra', 'ajio', 'grocery', 'supermarket', 'mart',
                         'store', 'purchase'],
    "Entertainment":    ['movie', 'netflix', 'spotify', 'prime', 'hotstar', 'game',
                         'cinema', 'theatre', 'concert', 'event', 'park', 'fun',
                         'subscription', 'youtube'],
    "Bills & Utilities":['electricity', 'water', 'internet', 'mobile', 'rent', 'wifi',
                         'broadband', 'gas', 'recharge', 'bill', 'utility', 'airtel',
                         'jio', 'bsnl', 'maintenance'],
    "Health":           ['hospital', 'doctor', 'medicine', 'pharmacy', 'clinic',
                         'health', 'gym', 'fitness', 'medical', 'dental', 'optical',
                         'lab', 'test', 'scan'],
    "Education":        ['book', 'course', 'college', 'fee', 'school', 'tuition',
                         'exam', 'coaching', 'udemy', 'coursera', 'stationary'],
    "Travel":           ['hotel', 'resort', 'trip', 'tour', 'holiday', 'vacation',
                         'booking', 'makemytrip', 'goibibo', 'irctc'],
    "Investment":       ['sip', 'mutual fund', 'stock', 'share', 'investment',
                         'zerodha', 'groww', 'insurance', 'premium', 'fd', 'rd'],
}


def auto_categorize(description: str) -> str:
    desc = description.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc for kw in keywords):
            return cat
    return "Other"


def get_expense_categories():
    return CATEGORIES


def get_payment_methods():
    return PAYMENT_METHODS


# ─────────────────────────────────────────────
#  ADD EXPENSE
# ─────────────────────────────────────────────
def add_new_expense(date, description, amount, category, payment_method,
                    notes="", source="manual"):
    if not description.strip():
        return False
    if amount <= 0:
        return False
    return db.add_expense(date, description, amount, category,
                          payment_method, notes, 0, source)


# ─────────────────────────────────────────────
#  DATAFRAME HELPER
# ─────────────────────────────────────────────
def get_expenses_as_dataframe():
    expenses = db.get_all_expenses()
    if not expenses:
        return pd.DataFrame(columns=['ID', 'Date', 'Description', 'Amount',
                                     'Category', 'Payment Method', 'Notes', 'Is Recurring'])
    df = pd.DataFrame(expenses)
    df = df.rename(columns={
        'id': 'ID', 'date': 'Date', 'description': 'Description',
        'amount': 'Amount', 'category': 'Category',
        'payment_method': 'Payment Method', 'notes': 'Notes',
        'is_recurring': 'Is Recurring'
    })
    df['Date'] = pd.to_datetime(df['Date'])
    return df


# ─────────────────────────────────────────────
#  MONTHLY / CURRENT TOTALS
# ─────────────────────────────────────────────
def get_monthly_total(year: int, month: int) -> float:
    expenses = db.get_all_expenses()
    return sum(
        e['amount'] for e in expenses
        if _parse_date(e['date']).year == year
        and _parse_date(e['date']).month == month
    )


def get_current_month_total() -> float:
    n = datetime.now()
    return get_monthly_total(n.year, n.month)


def get_previous_month_total() -> float:
    n = datetime.now()
    if n.month == 1:
        return get_monthly_total(n.year - 1, 12)
    return get_monthly_total(n.year, n.month - 1)


# ─────────────────────────────────────────────
#  CATEGORY TOTALS
# ─────────────────────────────────────────────
def get_category_wise_total() -> dict:
    expenses = db.get_all_expenses()
    totals: dict = {}
    for e in expenses:
        totals[e['category']] = totals.get(e['category'], 0) + e['amount']
    return totals


def get_category_wise_total_current_month() -> dict:
    n = datetime.now()
    expenses = db.get_all_expenses()
    totals: dict = {}
    for e in expenses:
        d = _parse_date(e['date'])
        if d.year == n.year and d.month == n.month:
            totals[e['category']] = totals.get(e['category'], 0) + e['amount']
    return totals


# ─────────────────────────────────────────────
#  DAILY TREND
# ─────────────────────────────────────────────
def get_daily_spending_trend(days: int = 30):
    expenses = db.get_all_expenses()
    cutoff = datetime.now() - timedelta(days=days)
    daily: dict = {}
    for e in expenses:
        d = _parse_date(e['date'])
        if d >= cutoff:
            dk = d.strftime('%Y-%m-%d')
            daily[dk] = daily.get(dk, 0) + e['amount']
    if not daily:
        return [], []
    sorted_d = sorted(daily.items())
    return [x[0] for x in sorted_d], [x[1] for x in sorted_d]


# ─────────────────────────────────────────────
#  BUDGET STATUS
# ─────────────────────────────────────────────
def get_budget_status(month: str) -> dict | None:
    budget = db.get_monthly_budget(month)
    if budget is None:
        return None
    year, mon = map(int, month.split('-'))
    spent = get_monthly_total(year, mon)
    remaining = budget - spent
    pct = (spent / budget * 100) if budget > 0 else 0
    return {
        'budget': budget,
        'spent': spent,
        'remaining': remaining,
        'percentage_used': round(pct, 1)
    }


# ─────────────────────────────────────────────
#  RECURRING DETECTION
# ─────────────────────────────────────────────
def detect_recurring_expenses() -> list:
    expenses = db.get_all_expenses()
    desc_map: dict = {}
    for e in expenses:
        key = e['description'].strip().lower()
        d = _parse_date(e['date'])
        month_key = d.strftime('%Y-%m')
        if key not in desc_map:
            desc_map[key] = {}
        if month_key not in desc_map[key]:
            desc_map[key][month_key] = []
        desc_map[key][month_key].append(e)

    result = []
    for desc, months in desc_map.items():
        if len(months) >= 2:
            all_expenses = [e for ml in months.values() for e in ml]
            result.append({
                'description': desc,
                'occurrences': len(months),
                'expenses': all_expenses,
                'avg_amount': np.mean([e['amount'] for e in all_expenses])
            })
    return sorted(result, key=lambda x: x['occurrences'], reverse=True)


def get_recurring_expenses() -> list:
    return [e for e in db.get_all_expenses() if e['is_recurring'] == 1]


# ─────────────────────────────────────────────
#  MONTHLY SUMMARY (for charts)
# ─────────────────────────────────────────────
def get_monthly_summary(months: int = 6) -> dict:
    expenses = db.get_all_expenses()
    cutoff_date = datetime.now() - timedelta(days=30 * months)
    monthly: dict = {}
    for e in expenses:
        d = _parse_date(e['date'])
        if d >= cutoff_date:
            mk = d.strftime('%Y-%m')
            monthly[mk] = monthly.get(mk, 0) + e['amount']
    return dict(sorted(monthly.items()))


def get_payment_method_totals() -> dict:
    expenses = db.get_all_expenses()
    totals: dict = {}
    for e in expenses:
        pm = e['payment_method']
        totals[pm] = totals.get(pm, 0) + e['amount']
    return totals


def get_top_expenses(n: int = 10) -> list:
    expenses = db.get_all_expenses()
    return sorted(expenses, key=lambda x: x['amount'], reverse=True)[:n]


# ─────────────────────────────────────────────
#  FORECASTING (Linear Regression)
# ─────────────────────────────────────────────
def forecast_next_month_spending() -> float | None:
    monthly = get_monthly_summary(12)
    if len(monthly) < 2:
        return None

    months_list = list(monthly.keys())
    amounts_list = [monthly[m] for m in months_list]

    X = np.array(range(len(amounts_list))).reshape(-1, 1)
    y = np.array(amounts_list)

    if SKLEARN_OK:
        model = LinearRegression()
        model.fit(X, y)
        predicted = model.predict([[len(amounts_list)]])[0]
    else:
        # Simple moving average fallback
        predicted = float(np.mean(amounts_list[-3:]))

    return max(predicted, 0)


def forecast_multi_month(months_ahead: int = 3) -> list:
    monthly = get_monthly_summary(12)
    if len(monthly) < 2:
        return []

    amounts_list = list(monthly.values())
    X = np.array(range(len(amounts_list))).reshape(-1, 1)
    y = np.array(amounts_list)

    if SKLEARN_OK:
        model = LinearRegression()
        model.fit(X, y)
        forecasts = []
        n = datetime.now()
        for i in range(1, months_ahead + 1):
            pred = max(model.predict([[len(amounts_list) + i - 1]])[0], 0)
            if n.month + i > 12:
                mk = f"{n.year + 1}-{(n.month + i - 12):02d}"
            else:
                mk = f"{n.year}-{(n.month + i):02d}"
            forecasts.append({'month': mk, 'predicted': round(pred, 2)})
        return forecasts
    else:
        avg = float(np.mean(amounts_list[-3:]))
        n = datetime.now()
        result = []
        for i in range(1, months_ahead + 1):
            if n.month + i > 12:
                mk = f"{n.year + 1}-{(n.month + i - 12):02d}"
            else:
                mk = f"{n.year}-{(n.month + i):02d}"
            result.append({'month': mk, 'predicted': avg})
        return result


# ─────────────────────────────────────────────
#  SCENARIO SIMULATION
# ─────────────────────────────────────────────
def simulate_category_increase(category: str, increase_pct: float) -> dict | None:
    cat_totals = get_category_wise_total_current_month()
    if category not in cat_totals:
        return None
    current_amount = cat_totals[category]
    current_total = sum(cat_totals.values())
    added = current_amount * (increase_pct / 100)
    new_amount = current_amount + added
    new_total = current_total + added
    budget = db.get_monthly_budget(datetime.now().strftime('%Y-%m'))
    return {
        'category': category,
        'increase_pct': increase_pct,
        'current_amount': current_amount,
        'increased_amount': new_amount,
        'difference': added,
        'current_total': current_total,
        'new_total': new_total,
        'budget': budget,
        'all_categories': cat_totals
    }


# ─────────────────────────────────────────────
#  WEEKLY HEATMAP DATA
# ─────────────────────────────────────────────
def get_weekday_spending() -> dict:
    expenses = db.get_all_expenses()
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    totals = {d: 0.0 for d in days}
    counts = {d: 0 for d in days}
    for e in expenses:
        d = _parse_date(e['date'])
        dk = days[d.weekday()]
        totals[dk] += e['amount']
        counts[dk] += 1
    return {'totals': totals, 'counts': counts}


# ─────────────────────────────────────────────
#  INTERNAL
# ─────────────────────────────────────────────
def _parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except Exception:
        return datetime.now()
