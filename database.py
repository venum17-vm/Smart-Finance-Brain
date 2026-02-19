"""
database.py
Handles SQLite database operations for Smart Finance Brain
"""

import sqlite3
import os

# Database file path
DB_PATH = os.path.join('data', 'finance_brain.db')


def init_database():
    """
    Initialize database and create tables
    """
    # Create data folder if not exists
    if not os.path.exists('data'):
        os.makedirs('data')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            notes TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


def add_expense(date, description, amount, category, payment_method, notes=""):
    """
    Add new expense to database
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO expenses (date, description, amount, category, payment_method, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (date, description, amount, category, payment_method, notes))
        
        conn.commit()
        conn.close()
        return True
    except:
        return False


def get_all_expenses():
    """
    Get all expenses from database
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM expenses ORDER BY date DESC')
    rows = cursor.fetchall()
    
    expenses = []
    for row in rows:
        expenses.append({
            'id': row['id'],
            'date': row['date'],
            'description': row['description'],
            'amount': row['amount'],
            'category': row['category'],
            'payment_method': row['payment_method'],
            'notes': row['notes']
        })
    
    conn.close()
    return expenses


def delete_expense(expense_id):
    """
    Delete expense by ID
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False