"""
finance_manager.py
Finance business logic and helper functions
"""

import database as db
from datetime import datetime
import pandas as pd


def auto_categorize(description):
    """
    Auto-categorize expense based on keywords
    """
    desc = description.lower()
    
    # Define category keywords
    categories = {
        "Food & Dining": ['restaurant', 'food', 'lunch', 'dinner', 'cafe', 'pizza', 'swiggy', 'zomato'],
        "Transportation": ['uber', 'ola', 'taxi', 'bus', 'metro', 'fuel', 'petrol'],
        "Shopping": ['amazon', 'flipkart', 'shopping', 'mall', 'clothes'],
        "Entertainment": ['movie', 'netflix', 'spotify', 'game'],
        "Bills & Utilities": ['electricity', 'water', 'internet', 'mobile', 'rent'],
        "Health": ['hospital', 'doctor', 'medicine', 'pharmacy'],
        "Education": ['book', 'course', 'college', 'fee']
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
                                    'Category', 'Payment Method', 'Notes'])
    
    df = pd.DataFrame(expenses)
    df = df.rename(columns={
        'id': 'ID',
        'date': 'Date',
        'description': 'Description',
        'amount': 'Amount',
        'category': 'Category',
        'payment_method': 'Payment Method',
        'notes': 'Notes'
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