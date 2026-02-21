"""
finance_manager.py
Finance business logic and advanced analytics
"""

import database as db
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression


def auto_categorize(description):
    """
    Auto-categorize expense based on keywords
    """
    desc = description.lower()
    
    # Define category keywords
    categories = {
        "Food & Dining": ['restaurant', 'food', 'lunch', 'dinner', 'cafe', 'pizza', 'swiggy', 'zomato', 'burger'],
        "Transportation": ['uber', 'ola', 'taxi', 'bus', 'metro', 'fuel', 'petrol', 'diesel'],
        "Shopping": ['amazon', 'flipkart', 'shopping', 'mall', 'clothes', 'shoes'],
        "Entertainment": ['movie', 'netflix', 'spotify', 'game', 'cinema'],
        "Bills & Utilities": ['electricity', 'water', 'internet', 'mobile', 'rent', 'bill'],
        "Health": ['hospital', 'doctor', 'medicine', 'pharmacy', 'clinic'],
        "Education": ['book', 'course', 'college', 'fee', 'tuition']
    }
    
    # Check keywords
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in desc:
                return category
    
    return "Other"


def add_new_expense(date, description, amount, category, payment_method, notes=""):
    """
    Add expense with validation
    """
    if not description.strip():
        return False
    
    if amount <= 0:
        return False
    
    return db.add_expense(date, description, amount, category, payment_method, notes)


def get_expenses_as_dataframe():
    """
    Get expenses as pandas DataFrame
    """
    expenses = db.get_all_expenses()
    
    if not expenses:
        return pd.DataFrame(columns=['ID', 'Date', 'Description', 'Amount', 
                                    'Category', 'Payment Method', 'Notes', 'Is Recurring'])
    
    df = pd.DataFrame(expenses)
    df = df.rename(columns={
        'id': 'ID',
        'date': 'Date',
        'description': 'Description',
        'amount': 'Amount',
        'category': 'Category',
        'payment_method': 'Payment Method',
        'notes': 'Notes',
        'is_recurring': 'Is Recurring'
    })
    
    return df


def get_monthly_total(year, month):
    """
    Get total expenses for specific month
    """
    expenses = db.get_all_expenses()
    total = 0
    
    for expense in expenses:
        exp_date = datetime.strptime(expense['date'], '%Y-%m-%d')
        if exp_date.year == year and exp_date.month == month:
            total += expense['amount']
    
    return total


def get_current_month_total():
    """
    Get current month total
    """
    now = datetime.now()
    return get_monthly_total(now.year, now.month)


def get_previous_month_total():
    """
    Get previous month total
    """
    now = datetime.now()
    prev_month = now.month - 1 if now.month > 1 else 12
    prev_year = now.year if now.month > 1 else now.year - 1
    return get_monthly_total(prev_year, prev_month)


def get_category_wise_total():
    """
    Get total by category
    """
    expenses = db.get_all_expenses()
    category_totals = {}
    
    for expense in expenses:
        category = expense['category']
        amount = expense['amount']
        
        if category in category_totals:
            category_totals[category] += amount
        else:
            category_totals[category] = amount
    
    return category_totals


def get_category_wise_total_current_month():
    """
    Get category totals for current month only
    """
    expenses = db.get_all_expenses()
    category_totals = {}
    now = datetime.now()
    
    for expense in expenses:
        exp_date = datetime.strptime(expense['date'], '%Y-%m-%d')
        if exp_date.year == now.year and exp_date.month == now.month:
            category = expense['category']
            amount = expense['amount']
            
            if category in category_totals:
                category_totals[category] += amount
            else:
                category_totals[category] = amount
    
    return category_totals


def get_daily_spending_trend():
    """
    Get daily spending for line chart
    """
    expenses = db.get_all_expenses()
    daily_totals = {}
    
    for expense in expenses:
        date = expense['date']
        amount = expense['amount']
        
        if date in daily_totals:
            daily_totals[date] += amount
        else:
            daily_totals[date] = amount
    
    # Convert to sorted list
    dates = sorted(daily_totals.keys())
    amounts = [daily_totals[d] for d in dates]
    
    return dates, amounts


def detect_recurring_expenses():
    """
    Detect recurring expenses based on description appearing in multiple months
    """
    expenses = db.get_all_expenses()
    
    # Group by description
    description_months = {}
    for expense in expenses:
        desc = expense['description'].lower().strip()
        exp_date = datetime.strptime(expense['date'], '%Y-%m-%d')
        month_key = f"{exp_date.year}-{exp_date.month:02d}"
        
        if desc not in description_months:
            description_months[desc] = set()
        description_months[desc].add(month_key)
    
    # Find descriptions appearing in 2+ months
    recurring = []
    for desc, months in description_months.items():
        if len(months) >= 2:
            # Get all expenses with this description
            matching_expenses = [e for e in expenses if e['description'].lower().strip() == desc]
            recurring.append({
                'description': desc,
                'occurrences': len(months),
                'expenses': matching_expenses
            })
    
    return recurring


def get_recurring_expenses():
    """
    Get all expenses marked as recurring
    """
    expenses = db.get_all_expenses()
    recurring = [e for e in expenses if e['is_recurring'] == 1]
    return recurring


def forecast_next_month_spending():
    """
    Predict next month spending using Linear Regression
    """
    expenses = db.get_all_expenses()
    
    if not expenses:
        return None
    
    # Group by month
    monthly_totals = {}
    for expense in expenses:
        exp_date = datetime.strptime(expense['date'], '%Y-%m-%d')
        month_key = f"{exp_date.year}-{exp_date.month:02d}"
        
        if month_key in monthly_totals:
            monthly_totals[month_key] += expense['amount']
        else:
            monthly_totals[month_key] = expense['amount']
    
    # Need at least 2 months of data
    if len(monthly_totals) < 2:
        return None
    
    # Sort by month
    sorted_months = sorted(monthly_totals.items())
    
    # Create numeric index (X) and amounts (y)
    X = np.array(range(len(sorted_months))).reshape(-1, 1)
    y = np.array([amount for _, amount in sorted_months])
    
    # Train Linear Regression
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict next month (index = len(sorted_months))
    next_month_index = np.array([[len(sorted_months)]])
    predicted_amount = model.predict(next_month_index)[0]
    
    return max(0, predicted_amount)  # Ensure non-negative


def simulate_category_increase(category, percentage_increase):
    """
    Simulate what happens if spending in a category increases by X%
    """
    category_totals = get_category_wise_total_current_month()
    
    if category not in category_totals:
        return None
    
    current_amount = category_totals[category]
    increased_amount = current_amount * (1 + percentage_increase / 100)
    difference = increased_amount - current_amount
    
    # Calculate new total
    current_total = sum(category_totals.values())
    new_total = current_total + difference
    
    return {
        'category': category,
        'current_amount': current_amount,
        'increased_amount': increased_amount,
        'difference': difference,
        'current_total': current_total,
        'new_total': new_total
    }


def get_budget_status(month):
    """
    Get budget status for a month
    """
    budget = db.get_monthly_budget(month)
    
    if not budget:
        return None
    
    # Get spending for that month
    year, month_num = map(int, month.split('-'))
    spent = get_monthly_total(year, month_num)
    
    percentage_used = (spent / budget) * 100 if budget > 0 else 0
    remaining = budget - spent
    
    return {
        'budget': budget,
        'spent': spent,
        'remaining': remaining,
        'percentage_used': percentage_used
    }


def get_expense_categories():
    """
    Return available categories
    """
    return [
        "Food & Dining",
        "Transportation",
        "Shopping",
        "Entertainment",
        "Bills & Utilities",
        "Health",
        "Education",
        "Other"
    ]


def get_payment_methods():
    """
    Return available payment methods
    """
    return [
        "Cash",
        "Credit Card",
        "Debit Card",
        "UPI",
        "Net Banking",
        "Wallet"
    ]