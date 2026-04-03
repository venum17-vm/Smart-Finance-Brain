"""
database.py — Smart Finance Brain v5.0
Two-layer database architecture:
  data/users.db           → global: user accounts + app settings
  data/{phone}/finance.db → per-user: expenses, budget, docs, obligations

Each user is completely isolated — their data never mixes with another user's.
"""

import sqlite3
import os
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────────────────────────────────────
_ROOT       = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(_ROOT, 'data')
USERS_DB    = os.path.join(DATA_DIR, 'users.db')

# Active user phone (set on login, used by all per-user functions)
_current_phone: str = ""


def set_current_user(phone: str):
    """Call this on login to activate per-user database."""
    global _current_phone
    _current_phone = phone
    _ensure_user_dirs(phone)
    init_user_database(phone)


def get_user_db_path(phone: str = "") -> str:
    p = phone or _current_phone
    return os.path.join(DATA_DIR, p, 'finance.db')


def get_upload_dir(phone: str = "") -> str:
    p = phone or _current_phone
    return os.path.join(_ROOT, 'uploads', p)


def get_reports_dir(phone: str = "") -> str:
    p = phone or _current_phone
    return os.path.join(_ROOT, 'reports', p)


def _ensure_user_dirs(phone: str):
    for d in [
        os.path.join(DATA_DIR, phone),
        os.path.join(_ROOT, 'uploads', phone),
        os.path.join(_ROOT, 'reports', phone),
    ]:
        os.makedirs(d, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CONNECTION HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _pragma(conn):
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    conn.execute("PRAGMA temp_store=memory")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def get_connection(phone: str = ""):
    """Get per-user finance database connection."""
    path = get_user_db_path(phone)
    return _pragma(sqlite3.connect(path, check_same_thread=False))


def get_users_connection():
    """Get global users database connection."""
    os.makedirs(DATA_DIR, exist_ok=True)
    return _pragma(sqlite3.connect(USERS_DB, check_same_thread=False))


# ─────────────────────────────────────────────────────────────────────────────
#  INIT — GLOBAL USERS DB
# ─────────────────────────────────────────────────────────────────────────────
def init_global_database():
    """Create users.db with users and settings tables."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = get_users_connection()
    cur  = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            phone          TEXT    NOT NULL UNIQUE,
            name           TEXT    NOT NULL DEFAULT 'User',
            pin            TEXT    NOT NULL DEFAULT '1234',
            email          TEXT    DEFAULT '',
            budget_alert   INTEGER DEFAULT 80,
            email_enabled  INTEGER DEFAULT 1,
            created_at     TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    ''')

    # Migrations
    _col(cur, 'users', 'email',         "TEXT DEFAULT ''")
    _col(cur, 'users', 'budget_alert',  'INTEGER DEFAULT 80')
    _col(cur, 'users', 'email_enabled', 'INTEGER DEFAULT 1')

    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone ON users(phone)')
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  INIT — PER-USER FINANCE DB
# ─────────────────────────────────────────────────────────────────────────────
def init_user_database(phone: str):
    """Create per-user finance.db with all finance tables."""
    _ensure_user_dirs(phone)
    conn = get_connection(phone)
    cur  = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            description     TEXT    NOT NULL,
            amount          REAL    NOT NULL,
            category        TEXT    NOT NULL,
            payment_method  TEXT    NOT NULL,
            notes           TEXT    DEFAULT '',
            is_recurring    INTEGER DEFAULT 0,
            source          TEXT    DEFAULT 'manual',
            tags            TEXT    DEFAULT '',
            import_file     TEXT    DEFAULT '',
            created_at      TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS budget (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            month        TEXT    NOT NULL UNIQUE,
            amount       REAL    NOT NULL,
            created_date TEXT    NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            filename     TEXT NOT NULL,
            file_path    TEXT NOT NULL,
            content      TEXT DEFAULT '',
            upload_date  TEXT NOT NULL DEFAULT '',
            summary      TEXT DEFAULT '',
            doc_type     TEXT DEFAULT 'general',
            word_count   INTEGER DEFAULT 0,
            file_size    INTEGER DEFAULT 0
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS obligations (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            name              TEXT    NOT NULL,
            amount            REAL    DEFAULT 0.0,
            due_date          TEXT    DEFAULT '',
            status            TEXT    DEFAULT 'pending',
            category          TEXT    DEFAULT 'Other',
            is_recurring      INTEGER DEFAULT 0,
            recurrence_period TEXT    DEFAULT 'monthly',
            notes             TEXT    DEFAULT '',
            document_id       INTEGER DEFAULT NULL,
            paid_date         TEXT    DEFAULT '',
            created_at        TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            role          TEXT NOT NULL,
            content       TEXT NOT NULL,
            attached_file TEXT DEFAULT '',
            timestamp     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS imported_files (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            filename      TEXT NOT NULL,
            file_path     TEXT NOT NULL,
            file_type     TEXT NOT NULL,
            rows_imported INTEGER DEFAULT 0,
            import_date   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            key   TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    ''')

    # Migrations on existing DBs
    _col(cur, 'expenses',  'import_file', "TEXT DEFAULT ''")
    _col(cur, 'documents', 'file_size',   'INTEGER DEFAULT 0')

    # Indexes
    for stmt in [
        'CREATE INDEX IF NOT EXISTS idx_exp_date   ON expenses(date)',
        'CREATE INDEX IF NOT EXISTS idx_exp_cat    ON expenses(category)',
        'CREATE INDEX IF NOT EXISTS idx_exp_recur  ON expenses(is_recurring)',
        'CREATE INDEX IF NOT EXISTS idx_exp_import ON expenses(import_file)',
        'CREATE INDEX IF NOT EXISTS idx_obl_due    ON obligations(due_date)',
        'CREATE INDEX IF NOT EXISTS idx_obl_status ON obligations(status)',
        'CREATE INDEX IF NOT EXISTS idx_doc_date   ON documents(upload_date)',
    ]:
        try:
            cur.execute(stmt)
        except Exception:
            pass

    conn.commit()
    conn.close()


def init_database():
    """Initialise both global and (if user is set) per-user databases."""
    init_global_database()
    if _current_phone:
        init_user_database(_current_phone)


def _col(cur, table, col, defn):
    try:
        rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {r[1] for r in rows}
        if col not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  USER MANAGEMENT  (global users.db)
# ─────────────────────────────────────────────────────────────────────────────
def create_user(phone, name, pin, email='', budget_alert=80, email_enabled=1) -> bool:
    try:
        conn = get_users_connection()
        conn.execute(
            'INSERT INTO users (phone,name,pin,email,budget_alert,email_enabled) '
            'VALUES (?,?,?,?,?,?)',
            (phone, name, pin, email.lower().strip(), budget_alert, email_enabled)
        )
        conn.commit()
        conn.close()
        # Create per-user dirs and DB
        _ensure_user_dirs(phone)
        init_user_database(phone)
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"create_user: {e}")
        return False


def get_user_by_phone(phone) -> dict | None:
    try:
        conn = get_users_connection()
        row  = conn.execute('SELECT * FROM users WHERE phone=?', (phone,)).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_user_by_phone: {e}")
        return None


def get_user_by_email(email) -> dict | None:
    try:
        conn = get_users_connection()
        row  = conn.execute(
            'SELECT * FROM users WHERE LOWER(email)=LOWER(?)', (email.strip(),)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_user_by_email: {e}")
        return None


def verify_user(phone, pin) -> dict | None:
    u = get_user_by_phone(phone)
    return u if u and u['pin'] == pin else None


def verify_user_by_email(email, pin) -> dict | None:
    u = get_user_by_email(email)
    return u if u and u['pin'] == pin else None


def update_user(phone, name, email='', budget_alert=80, email_enabled=1) -> bool:
    try:
        conn = get_users_connection()
        conn.execute(
            'UPDATE users SET name=?,email=?,budget_alert=?,email_enabled=? WHERE phone=?',
            (name, email.lower().strip(), budget_alert, email_enabled, phone)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"update_user: {e}")
        return False


def update_user_pin(phone, new_pin) -> bool:
    try:
        conn = get_users_connection()
        conn.execute('UPDATE users SET pin=? WHERE phone=?', (new_pin, phone))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"update_user_pin: {e}")
        return False


def delete_user_account(phone: str) -> tuple[bool, list]:
    """Delete user + all their per-user data. Returns (ok, [file_paths])."""
    try:
        conn = get_connection(phone)
        rows = conn.execute(
            'SELECT file_path FROM documents WHERE file_path IS NOT NULL'
        ).fetchall()
        file_paths = [r[0] for r in rows if r[0]]
        rows2 = conn.execute(
            'SELECT file_path FROM imported_files WHERE file_path IS NOT NULL'
        ).fetchall()
        file_paths += [r[0] for r in rows2 if r[0]]
        conn.close()

        # Delete per-user DB file
        db_path = get_user_db_path(phone)
        if os.path.exists(db_path):
            os.remove(db_path)

        # Remove from global users.db
        uc = get_users_connection()
        uc.execute('DELETE FROM users WHERE phone=?', (phone,))
        uc.commit()
        uc.close()

        return True, file_paths
    except Exception as e:
        print(f"delete_user_account: {e}")
        return False, []


# ─────────────────────────────────────────────────────────────────────────────
#  SETTINGS  (global — app-wide like sender Gmail)
# ─────────────────────────────────────────────────────────────────────────────
def get_setting(key: str, default: str = '') -> str:
    try:
        conn = get_users_connection()
        row  = conn.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        return default


def set_setting(key: str, value: str) -> bool:
    try:
        conn = get_users_connection()
        conn.execute(
            'INSERT INTO settings(key,value) VALUES(?,?) '
            'ON CONFLICT(key) DO UPDATE SET value=excluded.value',
            (key, value)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"set_setting: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  USER SETTINGS  (per-user, stored in finance.db/user_settings)
# ─────────────────────────────────────────────────────────────────────────────
def get_user_setting(key: str, default: str = '', phone: str = '') -> str:
    try:
        conn = get_connection(phone)
        row  = conn.execute('SELECT value FROM user_settings WHERE key=?', (key,)).fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        return default


def set_user_setting(key: str, value: str, phone: str = '') -> bool:
    try:
        conn = get_connection(phone)
        conn.execute(
            'INSERT INTO user_settings(key,value) VALUES(?,?) '
            'ON CONFLICT(key) DO UPDATE SET value=excluded.value',
            (key, value)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"set_user_setting: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  EXPENSES
# ─────────────────────────────────────────────────────────────────────────────
def add_expense(date, description, amount, category, payment_method,
                notes='', is_recurring=0, source='manual', tags='',
                import_file='', phone='') -> bool:
    try:
        conn = get_connection(phone)
        conn.execute('''
            INSERT INTO expenses
              (date,description,amount,category,payment_method,
               notes,is_recurring,source,tags,import_file)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        ''', (date, description, amount, category, payment_method,
               notes, is_recurring, source, tags, import_file))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"add_expense: {e}")
        return False


def get_all_expenses(phone='') -> list:
    try:
        conn = get_connection(phone)
        rows = conn.execute('SELECT * FROM expenses ORDER BY date DESC').fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_all_expenses: {e}")
        return []


def delete_expense(expense_id, phone='') -> bool:
    try:
        conn = get_connection(phone)
        conn.execute('DELETE FROM expenses WHERE id=?', (expense_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"delete_expense: {e}")
        return False


def delete_expenses_by_import_file(import_filename: str, phone='') -> int:
    """Delete all expenses imported from a specific file. Returns count deleted."""
    try:
        conn = get_connection(phone)
        cur  = conn.execute(
            'DELETE FROM expenses WHERE import_file=?', (import_filename,)
        )
        count = cur.rowcount
        conn.commit()
        conn.close()
        return count
    except Exception as e:
        print(f"delete_expenses_by_import_file: {e}")
        return 0


def update_recurring_status(expense_id, is_recurring, phone='') -> bool:
    try:
        conn = get_connection(phone)
        conn.execute('UPDATE expenses SET is_recurring=? WHERE id=?',
                     (is_recurring, expense_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"update_recurring_status: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  BUDGET
# ─────────────────────────────────────────────────────────────────────────────
def set_monthly_budget(month, amount, phone='') -> bool:
    try:
        conn  = get_connection(phone)
        today = datetime.now().strftime('%Y-%m-%d')
        conn.execute('''
            INSERT INTO budget (month,amount,created_date) VALUES (?,?,?)
            ON CONFLICT(month) DO UPDATE
            SET amount=excluded.amount, created_date=excluded.created_date
        ''', (month, amount, today))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"set_monthly_budget: {e}")
        return False


def get_monthly_budget(month, phone='') -> float | None:
    try:
        conn = get_connection(phone)
        row  = conn.execute('SELECT amount FROM budget WHERE month=?', (month,)).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print(f"get_monthly_budget: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENTS
# ─────────────────────────────────────────────────────────────────────────────
def save_document(filename, file_path, content, upload_date, summary,
                  doc_type='general', phone='') -> bool:
    try:
        wc   = len(content.split()) if content else 0
        size = os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0
        conn = get_connection(phone)
        conn.execute('''
            INSERT INTO documents
              (filename,file_path,content,upload_date,summary,doc_type,word_count,file_size)
            VALUES (?,?,?,?,?,?,?,?)
        ''', (filename, file_path, content, upload_date, summary, doc_type, wc, size))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"save_document: {e}")
        return False


def get_all_documents(phone='') -> list:
    try:
        conn = get_connection(phone)
        rows = conn.execute(
            'SELECT * FROM documents ORDER BY upload_date DESC'
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_all_documents: {e}")
        return []


def get_document_by_id(doc_id, phone='') -> dict | None:
    try:
        conn = get_connection(phone)
        row  = conn.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"get_document_by_id: {e}")
        return None


def delete_document(doc_id, phone='') -> bool:
    try:
        conn = get_connection(phone)
        conn.execute('DELETE FROM documents WHERE id=?', (doc_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"delete_document: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  OBLIGATIONS
# ─────────────────────────────────────────────────────────────────────────────
def add_obligation(name, amount=0.0, due_date=None, category='Other',
                   is_recurring=0, recurrence_period='monthly',
                   notes='', document_id=None, phone='') -> bool:
    try:
        conn = get_connection(phone)
        conn.execute('''
            INSERT INTO obligations
              (name,amount,due_date,category,is_recurring,recurrence_period,notes,document_id)
            VALUES (?,?,?,?,?,?,?,?)
        ''', (name, amount, due_date, category, is_recurring,
               recurrence_period, notes, document_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"add_obligation: {e}")
        return False


def get_all_obligations(phone='') -> list:
    try:
        conn = get_connection(phone)
        rows = conn.execute(
            'SELECT * FROM obligations ORDER BY due_date ASC'
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_all_obligations: {e}")
        return []


def update_obligation_status(obl_id, status, paid_date=None, phone='') -> bool:
    try:
        pd_str = paid_date or (datetime.now().strftime('%Y-%m-%d') if status == 'paid' else '')
        conn   = get_connection(phone)
        conn.execute('UPDATE obligations SET status=?,paid_date=? WHERE id=?',
                     (status, pd_str, obl_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"update_obligation_status: {e}")
        return False


def delete_obligation(obl_id, phone='') -> bool:
    try:
        conn = get_connection(phone)
        conn.execute('DELETE FROM obligations WHERE id=?', (obl_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"delete_obligation: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  IMPORTED FILES REGISTRY
# ─────────────────────────────────────────────────────────────────────────────
def save_imported_file(filename, file_path, file_type,
                        rows_imported=0, phone='') -> bool:
    try:
        conn = get_connection(phone)
        conn.execute('''
            INSERT INTO imported_files (filename,file_path,file_type,rows_imported)
            VALUES (?,?,?,?)
        ''', (filename, file_path, file_type, rows_imported))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"save_imported_file: {e}")
        return False


def get_all_imported_files(phone='') -> list:
    try:
        conn = get_connection(phone)
        rows = conn.execute(
            'SELECT * FROM imported_files ORDER BY import_date DESC'
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"get_all_imported_files: {e}")
        return []


def delete_imported_file_record(file_id, phone='') -> bool:
    try:
        conn = get_connection(phone)
        conn.execute('DELETE FROM imported_files WHERE id=?', (file_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"delete_imported_file_record: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  CHAT HISTORY
# ─────────────────────────────────────────────────────────────────────────────
def save_chat_message(role, content, attached_file='', phone='') -> bool:
    try:
        conn = get_connection(phone)
        conn.execute(
            'INSERT INTO chat_history (role,content,attached_file) VALUES (?,?,?)',
            (role, content, attached_file)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"save_chat_message: {e}")
        return False


def get_chat_history(limit=50, phone='') -> list:
    try:
        conn = get_connection(phone)
        rows = conn.execute(
            'SELECT * FROM chat_history ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]
    except Exception as e:
        print(f"get_chat_history: {e}")
        return []


def clear_chat_history(phone='') -> bool:
    try:
        conn = get_connection(phone)
        conn.execute('DELETE FROM chat_history')
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"clear_chat_history: {e}")
        return False
