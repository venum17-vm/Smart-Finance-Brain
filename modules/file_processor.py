"""
modules/file_processor.py — Smart Finance Brain v5.0
Import expenses from Excel / CSV / Text.
Tracks imported files per user. Supports deleting an imported file + its expenses.
Files saved to uploads/{phone}/
"""

import pandas as pd
import os, sys
from datetime import datetime

_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
_ROOT       = _PARENT_DIR if os.path.basename(_THIS_DIR) == 'modules' else _THIS_DIR
for _p in [_THIS_DIR, _PARENT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import database as db
import finance_manager as fm


def process_excel_file(uploaded_file, phone: str = '') -> tuple[bool, str]:
    try:
        df        = pd.read_excel(uploaded_file)
        saved_path = _save_import_file(uploaded_file, phone)
        ok, msg, count = _process_dataframe(df, uploaded_file.name, phone)
        if ok and saved_path:
            db.save_imported_file(uploaded_file.name, saved_path, 'excel', count, phone)
        return ok, msg
    except Exception as e:
        return False, f"Excel read error: {e}"


def process_csv_file(uploaded_file, phone: str = '') -> tuple[bool, str]:
    try:
        df        = pd.read_csv(uploaded_file)
        saved_path = _save_import_file(uploaded_file, phone)
        ok, msg, count = _process_dataframe(df, uploaded_file.name, phone)
        if ok and saved_path:
            db.save_imported_file(uploaded_file.name, saved_path, 'csv', count, phone)
        return ok, msg
    except Exception as e:
        return False, f"CSV read error: {e}"


def process_text_file(uploaded_file, phone: str = '') -> tuple[bool, str]:
    try:
        uploaded_file.seek(0)
        content   = uploaded_file.read().decode('utf-8')
        saved_path = _save_import_file(uploaded_file, phone)
        lines     = content.strip().split('\n')
        imported  = skipped = 0

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 3:
                skipped += 1
                continue
            try:
                date_str    = _parse_date(parts[0])
                description = parts[1]
                amount      = float(parts[2])
                if amount <= 0 or not description:
                    skipped += 1
                    continue
                category       = parts[3] if len(parts) >= 4 else fm.auto_categorize(description)
                payment_method = parts[4] if len(parts) >= 5 else 'Not Specified'
                notes          = parts[5] if len(parts) >= 6 else ''

                if db.add_expense(date_str, description, amount, category,
                                   payment_method, notes,
                                   source='import',
                                   import_file=uploaded_file.name,
                                   phone=phone):
                    imported += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1

        if imported > 0 and saved_path:
            db.save_imported_file(uploaded_file.name, saved_path, 'text', imported, phone)

        msg = f"Imported {imported} expense(s)."
        if skipped:
            msg += f" Skipped {skipped} invalid row(s)."
        return imported > 0, msg

    except Exception as e:
        return False, f"Text file error: {e}"


def delete_imported_file(file_record: dict, phone: str = '') -> tuple[int, bool]:
    """
    Delete an imported file record, its expenses, and the file from disk.
    Returns (expenses_deleted_count, file_removed_from_disk).
    """
    fname    = file_record.get('filename', '')
    fpath    = file_record.get('file_path', '')
    file_id  = file_record.get('id')

    # 1. Delete expenses linked to this file
    count = db.delete_expenses_by_import_file(fname, phone)

    # 2. Remove the physical file
    removed = False
    if fpath and os.path.exists(fpath):
        try:
            os.remove(fpath)
            removed = True
        except Exception:
            pass

    # 3. Remove the DB record
    if file_id:
        db.delete_imported_file_record(file_id, phone)

    return count, removed


def get_import_preview(uploaded_file, max_rows: int = 20) -> pd.DataFrame | None:
    """Return a preview DataFrame without importing."""
    try:
        name = uploaded_file.name
        ext  = os.path.splitext(name)[1].lower()
        uploaded_file.seek(0)
        if ext in ('.xlsx', '.xls'):
            return pd.read_excel(uploaded_file).head(max_rows)
        elif ext == '.csv':
            return pd.read_csv(uploaded_file).head(max_rows)
        elif ext == '.txt':
            content = uploaded_file.read().decode('utf-8')
            lines   = content.strip().split('\n')[:max_rows]
            rows    = []
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    parts = [p.strip() for p in line.split('|')]
                    rows.append(parts)
            if rows:
                cols = ['Date', 'Description', 'Amount', 'Category', 'Payment', 'Notes']
                return pd.DataFrame(rows, columns=cols[:len(rows[0])])
        return None
    except Exception:
        return None


def _process_dataframe(df: pd.DataFrame, filename: str,
                        phone: str) -> tuple[bool, str, int]:
    required = ['Date', 'Description', 'Amount']
    missing  = [c for c in required if c not in df.columns]
    if missing:
        return False, f"Missing columns: {', '.join(missing)}", 0

    df       = df.dropna(subset=required)
    imported = skipped = 0

    for _, row in df.iterrows():
        try:
            date_str    = _parse_date(row['Date'])
            description = str(row['Description']).strip()
            amount      = float(row['Amount'])
            if amount <= 0 or not description:
                skipped += 1
                continue

            category = (str(row['Category']).strip()
                        if 'Category' in df.columns and pd.notna(row.get('Category'))
                        else fm.auto_categorize(description))

            payment_method = (str(row['Payment Method']).strip()
                              if 'Payment Method' in df.columns and pd.notna(row.get('Payment Method'))
                              else 'Not Specified')

            notes = (str(row['Notes']).strip()
                     if 'Notes' in df.columns and pd.notna(row.get('Notes'))
                     else '')

            if db.add_expense(date_str, description, amount, category,
                               payment_method, notes,
                               source='import',
                               import_file=filename,
                               phone=phone):
                imported += 1
            else:
                skipped += 1
        except Exception:
            skipped += 1

    msg = f"Imported {imported} expense(s)."
    if skipped:
        msg += f" Skipped {skipped} invalid row(s)."
    return imported > 0, msg, imported


def _save_import_file(file_obj, phone: str) -> str:
    """Save the uploaded import file to uploads/{phone}/."""
    try:
        upload_dir = db.get_upload_dir(phone)
        os.makedirs(upload_dir, exist_ok=True)
        ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in file_obj.name if c.isalnum() or c in ('._-'))
        path      = os.path.join(upload_dir, f"import_{ts}_{safe_name}")
        file_obj.seek(0)
        with open(path, 'wb') as f:
            f.write(file_obj.read())
        file_obj.seek(0)
        return path
    except Exception:
        return ''


def _parse_date(value) -> str:
    if isinstance(value, str):
        for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y',
                    '%Y/%m/%d', '%d-%b-%Y', '%d %B %Y', '%d/%m/%y']:
            try:
                return datetime.strptime(value.strip(), fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return pd.to_datetime(value).strftime('%Y-%m-%d')
    try:
        return value.strftime('%Y-%m-%d')
    except Exception:
        return pd.to_datetime(str(value)).strftime('%Y-%m-%d')


# ─────────────────────────────────────────────────────────────────────────────
#  SAMPLE TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────
def create_sample_excel() -> pd.DataFrame:
    return pd.DataFrame({
        'Date':           ['2024-02-18', '2024-02-17', '2024-02-16', '2024-02-15'],
        'Description':    ['Lunch at Restaurant', 'Uber Ride', 'Movie Ticket', 'Grocery Shopping'],
        'Amount':         [500, 150, 300, 2000],
        'Category':       ['Food & Dining', 'Transportation', 'Entertainment', 'Shopping'],
        'Payment Method': ['UPI', 'Cash', 'Credit Card', 'Debit Card'],
        'Notes':          ['With friends', 'To office', 'IMAX 3D', 'Monthly groceries'],
    })


def create_sample_csv() -> pd.DataFrame:
    return create_sample_excel()


def create_sample_text() -> str:
    return (
        "2024-02-18 | Lunch at Restaurant | 500 | Food & Dining | UPI | With friends\n"
        "2024-02-17 | Uber Ride | 150 | Transportation | Cash | To office\n"
        "2024-02-16 | Movie Ticket | 300 | Entertainment | Credit Card | IMAX 3D\n"
        "2024-02-15 | Grocery Shopping | 2000 | Shopping | Debit Card | Monthly groceries"
    )


def get_file_format_info() -> dict:
    return {
        'Excel': {
            'extensions': ['.xlsx', '.xls'],
            'description': 'Columns: Date, Description, Amount [+ Category, Payment Method, Notes]'
        },
        'CSV': {
            'extensions': ['.csv'],
            'description': 'Same columns as Excel, comma-separated'
        },
        'Text': {
            'extensions': ['.txt'],
            'description': 'Pipe-separated: Date | Description | Amount | Category | Payment | Notes'
        },
    }
