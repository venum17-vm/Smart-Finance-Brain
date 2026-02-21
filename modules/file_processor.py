"""
file_processor.py
Handles file uploads and data extraction from various formats
"""

import pandas as pd
import os
from datetime import datetime
import database as db
from modules import finance_manager as fm


def process_excel_file(uploaded_file):
    """
    Process Excel file (.xlsx, .xls) and import expenses
    
    Expected columns: Date, Description, Amount
    Optional columns: Category, Payment Method, Notes
    """
    try:
        # Read Excel file
        df = pd.read_excel(uploaded_file)
        
        return process_dataframe(df, uploaded_file.name)
    
    except Exception as e:
        return False, f"Error reading Excel file: {str(e)}"


def process_csv_file(uploaded_file):
    """
    Process CSV file and import expenses
    
    Expected columns: Date, Description, Amount
    Optional columns: Category, Payment Method, Notes
    """
    try:
        # Read CSV file
        df = pd.read_csv(uploaded_file)
        
        return process_dataframe(df, uploaded_file.name)
    
    except Exception as e:
        return False, f"Error reading CSV file: {str(e)}"


def process_dataframe(df, filename):
    """
    Common function to process DataFrame from any file format
    """
    try:
        # Check required columns
        required_cols = ['Date', 'Description', 'Amount']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return False, f"Missing required columns: {', '.join(missing_cols)}"
        
        # Clean data
        df = df.dropna(subset=['Date', 'Description', 'Amount'])
        
        imported_count = 0
        skipped_count = 0
        
        for index, row in df.iterrows():
            try:
                # Get date
                date = row['Date']
                if isinstance(date, str):
                    # Try different date formats
                    date_str = parse_date_string(date)
                else:
                    # pandas datetime
                    date_str = date.strftime('%Y-%m-%d')
                
                # Get description
                description = str(row['Description']).strip()
                
                # Get amount
                amount = float(row['Amount'])
                
                if amount <= 0:
                    skipped_count += 1
                    continue
                
                # Get category (auto-categorize if not provided)
                if 'Category' in df.columns and pd.notna(row['Category']):
                    category = str(row['Category']).strip()
                else:
                    category = fm.auto_categorize(description)
                
                # Get payment method
                if 'Payment Method' in df.columns and pd.notna(row['Payment Method']):
                    payment_method = str(row['Payment Method']).strip()
                else:
                    payment_method = "Not Specified"
                
                # Get notes
                notes = ""
                if 'Notes' in df.columns and pd.notna(row['Notes']):
                    notes = str(row['Notes']).strip()
                
                # Add to database
                success = db.add_expense(date_str, description, amount, category, payment_method, notes)
                if success:
                    imported_count += 1
                else:
                    skipped_count += 1
            
            except Exception as e:
                skipped_count += 1
                continue
        
        message = f"✅ Successfully imported {imported_count} expenses!"
        if skipped_count > 0:
            message += f"\n⚠️ Skipped {skipped_count} invalid entries."
        
        return True, message
    
    except Exception as e:
        return False, f"Error processing data: {str(e)}"


def parse_date_string(date_str):
    """
    Try to parse date string in various formats
    """
    date_formats = [
        '%Y-%m-%d',      # 2024-02-18
        '%d-%m-%Y',      # 18-02-2024
        '%d/%m/%Y',      # 18/02/2024
        '%m/%d/%Y',      # 02/18/2024
        '%Y/%m/%d',      # 2024/02/18
        '%d-%b-%Y',      # 18-Feb-2024
        '%d %B %Y',      # 18 February 2024
    ]
    
    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime('%Y-%m-%d')
        except:
            continue
    
    # If all fail, try pandas parser
    try:
        date_obj = pd.to_datetime(date_str)
        return date_obj.strftime('%Y-%m-%d')
    except:
        raise ValueError(f"Could not parse date: {date_str}")


def process_text_file(uploaded_file):
    """
    Process plain text file with simple format
    Format: Date | Description | Amount | Category (optional)
    Example: 2024-02-18 | Lunch | 500 | Food
    """
    try:
        content = uploaded_file.read().decode('utf-8')
        lines = content.strip().split('\n')
        
        imported_count = 0
        skipped_count = 0
        
        for line in lines:
            try:
                parts = [p.strip() for p in line.split('|')]
                
                if len(parts) < 3:
                    skipped_count += 1
                    continue
                
                date_str = parse_date_string(parts[0])
                description = parts[1]
                amount = float(parts[2])
                
                if amount <= 0:
                    skipped_count += 1
                    continue
                
                # Get category
                if len(parts) >= 4:
                    category = parts[3]
                else:
                    category = fm.auto_categorize(description)
                
                # Get payment method
                if len(parts) >= 5:
                    payment_method = parts[4]
                else:
                    payment_method = "Not Specified"
                
                # Get notes
                notes = parts[5] if len(parts) >= 6 else ""
                
                success = db.add_expense(date_str, description, amount, category, payment_method, notes)
                if success:
                    imported_count += 1
                else:
                    skipped_count += 1
            
            except Exception as e:
                skipped_count += 1
                continue
        
        message = f"✅ Successfully imported {imported_count} expenses!"
        if skipped_count > 0:
            message += f"\n⚠️ Skipped {skipped_count} invalid entries."
        
        return True, message
    
    except Exception as e:
        return False, f"Error processing text file: {str(e)}"


def create_sample_excel():
    """
    Create a sample Excel template for download
    """
    sample_data = {
        'Date': ['2024-02-18', '2024-02-17', '2024-02-16', '2024-02-15'],
        'Description': ['Lunch at Restaurant', 'Uber Ride', 'Movie Ticket', 'Grocery Shopping'],
        'Amount': [500, 150, 300, 2000],
        'Category': ['Food & Dining', 'Transportation', 'Entertainment', 'Shopping'],
        'Payment Method': ['UPI', 'Cash', 'Credit Card', 'Debit Card'],
        'Notes': ['With friends', 'To office', 'IMAX 3D', 'Monthly groceries']
    }
    
    df = pd.DataFrame(sample_data)
    return df


def create_sample_csv():
    """
    Create a sample CSV template
    """
    return create_sample_excel()


def create_sample_text():
    """
    Create sample text format
    """
    sample = """2024-02-18 | Lunch at Restaurant | 500 | Food & Dining | UPI | With friends
2024-02-17 | Uber Ride | 150 | Transportation | Cash | To office
2024-02-16 | Movie Ticket | 300 | Entertainment | Credit Card | IMAX 3D
2024-02-15 | Grocery Shopping | 2000 | Shopping | Debit Card | Monthly groceries"""
    
    return sample


def validate_file_format(filename):
    """
    Check if file format is supported
    """
    supported_formats = ['.xlsx', '.xls', '.csv', '.txt']
    file_ext = os.path.splitext(filename)[1].lower()
    return file_ext in supported_formats


def get_file_format_info():
    """
    Return information about supported formats
    """
    formats = {
        'Excel': {
            'extensions': ['.xlsx', '.xls'],
            'description': 'Microsoft Excel files with columns: Date, Description, Amount, Category (optional), Payment Method (optional), Notes (optional)'
        },
        'CSV': {
            'extensions': ['.csv'],
            'description': 'Comma-separated values with same columns as Excel'
        },
        'Text': {
            'extensions': ['.txt'],
            'description': 'Plain text with pipe-separated values: Date | Description | Amount | Category | Payment Method | Notes'
        }
    }
    return formats