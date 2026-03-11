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
    Initialize database and create all tables
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
            notes TEXT,
            is_recurring INTEGER DEFAULT 0
        )
    ''')
    
    # Create budget table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            amount REAL NOT NULL,
            created_date TEXT NOT NULL
        )
    ''')
    
    # Create documents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            content TEXT,
            upload_date TEXT NOT NULL,
            summary TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")


def add_expense(date, description, amount, category, payment_method, notes="", is_recurring=0):
    """
    Add new expense to database
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO expenses (date, description, amount, category, payment_method, notes, is_recurring)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (date, description, amount, category, payment_method, notes, is_recurring))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding expense: {e}")
        return False


def get_all_expenses():
    """
    Get all expenses from database
    """
    try:
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
                'notes': row['notes'],
                'is_recurring': row['is_recurring']
            })
        
        conn.close()
        return expenses
    except Exception as e:
        print(f"Error getting expenses: {e}")
        return []


def update_recurring_status(expense_id, is_recurring):
    """
    Update recurring status of an expense
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE expenses SET is_recurring = ? WHERE id = ?', (is_recurring, expense_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating recurring status: {e}")
        return False


def set_monthly_budget(month, amount):
    """
    Set budget for a specific month
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        from datetime import datetime
        created_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check if budget exists for this month
        cursor.execute('SELECT id FROM budget WHERE month = ?', (month,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('UPDATE budget SET amount = ?, created_date = ? WHERE month = ?', 
                          (amount, created_date, month))
        else:
            cursor.execute('INSERT INTO budget (month, amount, created_date) VALUES (?, ?, ?)',
                          (month, amount, created_date))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting budget: {e}")
        return False


def get_monthly_budget(month):
    """
    Get budget for a specific month
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT amount FROM budget WHERE month = ?', (month,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting budget: {e}")
        return None


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
    except Exception as e:
        print(f"Error deleting expense: {e}")
        return False


# ===== DOCUMENT FUNCTIONS =====

def save_document(filename, file_path, content, upload_date, summary):
    """
    Save document information to database
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO documents (filename, file_path, content, upload_date, summary)
            VALUES (?, ?, ?, ?, ?)
        ''', (filename, file_path, content, upload_date, summary))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving document: {e}")
        return False


def get_all_documents():
    """
    Get all uploaded documents from database
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM documents ORDER BY upload_date DESC')
        rows = cursor.fetchall()
        
        documents = []
        for row in rows:
            documents.append({
                'id': row['id'],
                'filename': row['filename'],
                'file_path': row['file_path'],
                'content': row['content'],
                'upload_date': row['upload_date'],
                'summary': row['summary']
            })
        
        conn.close()
        return documents
    except Exception as e:
        print(f"Error getting documents: {e}")
        return []


def delete_document(document_id):
    """
    Delete a document by ID
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM documents WHERE id = ?', (document_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting document: {e}")
        return False


def get_document_by_id(document_id):
    """
    Get a specific document by ID
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM documents WHERE id = ?', (document_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                'id': row['id'],
                'filename': row['filename'],
                'file_path': row['file_path'],
                'content': row['content'],
                'upload_date': row['upload_date'],
                'summary': row['summary']
            }
        return None
    except Exception as e:
        print(f"Error getting document: {e}")
        return None