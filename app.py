"""
app.py
Main Streamlit application for Smart Finance Brain - Advanced Finance Module
"""

import streamlit as st#type:ignore
from datetime import datetime
import sys
import os
import matplotlib.pyplot as plt # type: ignore
import pandas as pd#type:ignore
# Download and install Tesseract from:
# https://github.com/UB-Mannheim/tesseract/wiki

# Then set path in your code:
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Add modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

import database as db
from modules import finance_manager as fm

# Page config
st.set_page_config(
    page_title="Smart Finance Brain",
    page_icon="💰",
    layout="wide"
)

# Initialize database
db.init_database()

# Title
st.title("💰 Smart Finance Brain")
st.subheader("Advanced Personal Finance Management System")

# Sidebar
st.sidebar.title("Navigation")
menu = st.sidebar.radio(
    "Select Option:", 
    ["Add Expense", "View Expenses", "Dashboard", "Budget Manager", 
     "Recurring Expenses", "Forecasting", "Scenario Simulator", "Import Data","AI Documents Brain"]  # NEW
)
st.sidebar.markdown("---")
st.sidebar.info("Finance Module v2.0")


# ===== ADD EXPENSE =====
if menu == "Add Expense":
    st.header("➕ Add New Expense")
    
    col1, col2 = st.columns(2)
    
    with col1:
        expense_date = st.date_input("Date", value=datetime.now())
        description = st.text_input("Description", placeholder="e.g., Lunch at Restaurant")
        amount = st.number_input("Amount (₹)", min_value=0.0, step=1.0)
    
    with col2:
        # Auto-suggest category
        suggested_category = "Other"
        if description:
            suggested_category = fm.auto_categorize(description)
        
        categories = fm.get_expense_categories()
        default_index = categories.index(suggested_category)
        category = st.selectbox("Category", options=categories, index=default_index)
        
        payment_methods = fm.get_payment_methods()
        payment_method = st.selectbox("Payment Method", options=payment_methods)
        
        notes = st.text_area("Notes (Optional)", placeholder="Additional notes...")
    
    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
    
    with col_btn1:
        if st.button("💾 Save Expense", type="primary", use_container_width=True):
            if not description:
                st.error("❌ Please enter description!")
            elif amount <= 0:
                st.error("❌ Please enter valid amount!")
            else:
                date_str = expense_date.strftime('%Y-%m-%d')
                success = fm.add_new_expense(date_str, description, amount, category, payment_method, notes)
                
                if success:
                    st.success("✅ Expense added successfully!")
                    st.balloons()
                else:
                    st.error("❌ Failed to add expense!")
    
    with col_btn2:
        if st.button("🔄 Clear", use_container_width=True):
            st.rerun()


# ===== VIEW EXPENSES =====
elif menu == "View Expenses":
    st.header("📊 View All Expenses")
    
    df = fm.get_expenses_as_dataframe()
    
    if df.empty:
        st.info("📭 No expenses yet. Add your first expense!")
    else:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Expenses", f"₹{df['Amount'].sum():,.2f}")
        with col2:
            st.metric("Average Expense", f"₹{df['Amount'].mean():,.2f}")
        with col3:
            st.metric("Total Entries", len(df))
        
        st.markdown("---")
        st.subheader("All Expenses")
        
        df_display = df.copy()
        df_display['Amount'] = df_display['Amount'].apply(lambda x: f"₹{x:,.2f}")
        df_display['Is Recurring'] = df_display['Is Recurring'].apply(lambda x: "✓" if x == 1 else "")
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        st.download_button(
            label="📥 Download CSV",
            data=df.to_csv(index=False),
            file_name=f"expenses_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


# ===== DASHBOARD =====
elif menu == "Dashboard":
    st.header("📈 Financial Dashboard")
    
    # Current and previous month totals
    current_total = fm.get_current_month_total()
    previous_total = fm.get_previous_month_total()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current Month", f"₹{current_total:,.2f}")
    with col2:
        st.metric("Previous Month", f"₹{previous_total:,.2f}")
    with col3:
        change = current_total - previous_total
        st.metric("Change", f"₹{change:,.2f}", delta=f"{change:,.2f}")
    
    st.markdown("---")
    
    # Category-wise spending (Pie Chart)
    st.subheader("📊 Category-wise Spending (Current Month)")
    
    category_totals = fm.get_category_wise_total_current_month()
    
    if category_totals:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Create pie chart
            fig, ax = plt.subplots(figsize=(8, 6))
            categories = list(category_totals.keys())
            amounts = list(category_totals.values())
            
            ax.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)
        
        with col2:
            st.write("**Breakdown:**")
            for category, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
                percentage = (total / sum(category_totals.values())) * 100
                st.write(f"**{category}**")
                st.write(f"₹{total:,.2f} ({percentage:.1f}%)")
                st.progress(percentage / 100)
                st.write("")
    else:
        st.info("No expenses in current month yet.")
    
    st.markdown("---")
    
    # Daily spending trend (Line Chart)
    st.subheader("📉 Daily Spending Trend")
    
    dates, amounts = fm.get_daily_spending_trend()
    
    if dates:
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(dates, amounts, marker='o', linestyle='-', color='#1f77b4')
        ax.set_xlabel('Date')
        ax.set_ylabel('Amount (₹)')
        ax.set_title('Daily Spending Trend')
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.info("No spending data available for trend.")


# ===== BUDGET MANAGER =====
elif menu == "Budget Manager":
    st.header("💵 Budget Manager")
    
    current_month = datetime.now().strftime('%Y-%m')
    
    st.subheader(f"Set Budget for {current_month}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        budget_amount = st.number_input("Monthly Budget (₹)", min_value=0.0, step=100.0, value=10000.0)
    
    with col2:
        if st.button("💾 Save Budget", type="primary"):
            success = db.set_monthly_budget(current_month, budget_amount)
            if success:
                st.success("✅ Budget saved!")
            else:
                st.error("❌ Failed to save budget!")
    
    st.markdown("---")
    
    # Show budget status
    budget_status = fm.get_budget_status(current_month)
    
    if budget_status:
        st.subheader("Current Budget Status")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Budget", f"₹{budget_status['budget']:,.2f}")
        with col2:
            st.metric("Spent", f"₹{budget_status['spent']:,.2f}")
        with col3:
            st.metric("Remaining", f"₹{budget_status['remaining']:,.2f}")
        
        # Progress bar
        st.write("**Budget Usage:**")
        progress_value = min(budget_status['percentage_used'] / 100, 1.0)
        st.progress(progress_value)
        st.write(f"**{budget_status['percentage_used']:.1f}%** of budget used")
        
        # Warnings
        if budget_status['percentage_used'] >= 100:
            st.error("🚨 **ALERT:** You have exceeded your budget!")
        elif budget_status['percentage_used'] >= 80:
            st.warning("⚠️ **WARNING:** You have used 80% of your budget!")
        else:
            st.success("✅ You are within budget limits")
    else:
        st.info("No budget set for current month. Set one above!")


# ===== RECURRING EXPENSES =====
elif menu == "Recurring Expenses":
    st.header("🔁 Recurring Expenses Detection")
    
    st.info("Detecting expenses that appear in multiple months...")
    
    recurring = fm.detect_recurring_expenses()
    
    if recurring:
        st.success(f"Found {len(recurring)} potential recurring expenses!")
        
        for item in recurring:
            with st.expander(f"📌 {item['description'].title()} - Occurs {item['occurrences']} times"):
                st.write(f"**Appears in {item['occurrences']} different months**")
                
                # Show occurrences
                for expense in item['expenses']:
                    exp_date = datetime.strptime(expense['date'], '%Y-%m-%d')
                    st.write(f"- {exp_date.strftime('%B %Y')}: ₹{expense['amount']:,.2f}")
                
                # Mark as recurring button
                if st.button(f"Mark as Recurring", key=f"mark_{item['description']}"):
                    for expense in item['expenses']:
                        db.update_recurring_status(expense['id'], 1)
                    st.success("✅ Marked as recurring!")
                    st.rerun()
    else:
        st.info("No recurring expenses detected yet. Add more expenses across multiple months!")
    
    st.markdown("---")
    
    # Show already marked recurring expenses
    st.subheader("✓ Marked Recurring Expenses")
    
    recurring_marked = fm.get_recurring_expenses()
    
    if recurring_marked:
        df = pd.DataFrame(recurring_marked)
        df_display = df[['date', 'description', 'amount', 'category']].copy()
        df_display.columns = ['Date', 'Description', 'Amount', 'Category']
        df_display['Amount'] = df_display['Amount'].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No expenses marked as recurring yet.")


# ===== FORECASTING =====
elif menu == "Forecasting":
    st.header("🔮 Next Month Spending Forecast")
    
    st.info("Using Linear Regression to predict next month's spending based on historical data")
    
    predicted = fm.forecast_next_month_spending()
    
    if predicted is not None:
        st.success("✅ Forecast Complete!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Predicted Next Month Spending", f"₹{predicted:,.2f}")
        
        with col2:
            current = fm.get_current_month_total()
            difference = predicted - current
            st.metric("Difference from Current Month", f"₹{difference:,.2f}", delta=f"{difference:,.2f}")
        
        st.markdown("---")
        
        # Show monthly trend
        st.subheader("📊 Monthly Spending Trend")
        
        expenses = db.get_all_expenses()
        monthly_totals = {}
        for expense in expenses:
            exp_date = datetime.strptime(expense['date'], '%Y-%m-%d')
            month_key = exp_date.strftime('%Y-%m')
            
            if month_key in monthly_totals:
                monthly_totals[month_key] += expense['amount']
            else:
                monthly_totals[month_key] = expense['amount']
        
        sorted_months = sorted(monthly_totals.items())
        months = [m for m, _ in sorted_months]
        amounts = [a for _, a in sorted_months]
        
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(months, amounts, marker='o', linestyle='-', label='Actual Spending')
        
        # Add predicted point
        next_month = datetime.now()
        if next_month.month == 12:
            next_month_str = f"{next_month.year + 1}-01"
        else:
            next_month_str = f"{next_month.year}-{next_month.month + 1:02d}"
        
        ax.plot([months[-1], next_month_str], [amounts[-1], predicted], 
                marker='o', linestyle='--', color='red', label='Predicted')
        
        ax.set_xlabel('Month')
        ax.set_ylabel('Amount (₹)')
        ax.set_title('Monthly Spending with Forecast')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
        
    else:
        st.warning("⚠️ Not enough data for forecasting. Need at least 2 months of expenses!")


# ===== SCENARIO SIMULATOR =====
elif menu == "Scenario Simulator":
    st.header("🎮 Spending Scenario Simulator")
    
    st.info("Simulate how your spending changes if you increase a category by X%")
    
    category_totals = fm.get_category_wise_total_current_month()
    
    if category_totals:
        col1, col2 = st.columns(2)
        
        with col1:
            selected_category = st.selectbox("Select Category", options=list(category_totals.keys()))
        
        with col2:
            increase_percentage = st.slider("Increase by (%)", min_value=0, max_value=200, value=20, step=5)
        
        if st.button("🔄 Run Simulation", type="primary"):
            result = fm.simulate_category_increase(selected_category, increase_percentage)
            
            if result:
                st.success("✅ Simulation Complete!")
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Current Scenario")
                    st.metric(f"{selected_category}", f"₹{result['current_amount']:,.2f}")
                    st.metric("Total Monthly Spending", f"₹{result['current_total']:,.2f}")
                
                with col2:
                    st.subheader("After Increase")
                    st.metric(f"{selected_category}", f"₹{result['increased_amount']:,.2f}", 
                             delta=f"+₹{result['difference']:,.2f}")
                    st.metric("Total Monthly Spending", f"₹{result['new_total']:,.2f}",
                             delta=f"+₹{result['difference']:,.2f}")
                
                st.markdown("---")
                
                # Comparison chart
                st.subheader("Visual Comparison")
                
                fig, ax = plt.subplots(figsize=(8, 5))
                scenarios = ['Current', 'After Increase']
                amounts = [result['current_total'], result['new_total']]
                colors = ['#1f77b4', '#ff7f0e']
                
                ax.bar(scenarios, amounts, color=colors)
                ax.set_ylabel('Total Spending (₹)')
                ax.set_title(f'Impact of {increase_percentage}% Increase in {selected_category}')
                
                for i, v in enumerate(amounts):
                    ax.text(i, v + 100, f'₹{v:,.0f}', ha='center', va='bottom')
                
                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.error("❌ Category not found!")
    else:
        st.warning("⚠️ No expenses in current month. Add some expenses first!")
# ===== IMPORT DATA PAGE =====
elif menu == "Import Data":
    st.header("📂 Import Expenses from Files")
    
    # Import file processor
    from modules import file_processor as fp
    
    st.write("Upload your expense data from various file formats")
    
    # Show supported formats
    with st.expander("📋 Supported File Formats"):
        formats = fp.get_file_format_info()
        for format_name, info in formats.items():
            st.write(f"**{format_name}** ({', '.join(info['extensions'])})")
            st.write(f"- {info['description']}")
            st.write("")
    
    # Create tabs for different import methods
    tab1, tab2, tab3, tab4 = st.tabs(["Excel Import", "CSV Import", "Text Import", "Download Templates"])
    
    # TAB 1: Excel Import
    with tab1:
        st.subheader("📊 Upload Excel File")
        st.info("Your file should have columns: **Date**, **Description**, **Amount**")
        st.write("Optional columns: Category, Payment Method, Notes")
        
        excel_file = st.file_uploader(
            "Choose Excel file", 
            type=['xlsx', 'xls'],
            key="excel_upload"
        )
        
        if excel_file is not None:
            # Show preview
            st.write("**File Preview:**")
            try:
                preview_df = pd.read_excel(excel_file)
                st.dataframe(preview_df.head(10), use_container_width=True)
                
                # Show file info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Rows", len(preview_df))
                with col2:
                    st.metric("Columns", len(preview_df.columns))
                with col3:
                    total_amount = preview_df['Amount'].sum() if 'Amount' in preview_df.columns else 0
                    st.metric("Total Amount", f"₹{total_amount:,.2f}")
                
                # Reset file pointer
                excel_file.seek(0)
                
                st.markdown("---")
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("📥 Import All Data", type="primary", use_container_width=True):
                        with st.spinner("Importing expenses..."):
                            success, message = fp.process_excel_file(excel_file)
                            if success:
                                st.success(message)
                                st.balloons()
                            else:
                                st.error(message)
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    
    # TAB 2: CSV Import
    with tab2:
        st.subheader("📄 Upload CSV File")
        st.info("Your CSV file should have columns: **Date**, **Description**, **Amount**")
        st.write("Optional columns: Category, Payment Method, Notes")
        
        csv_file = st.file_uploader(
            "Choose CSV file", 
            type=['csv'],
            key="csv_upload"
        )
        
        if csv_file is not None:
            # Show preview
            st.write("**File Preview:**")
            try:
                preview_df = pd.read_csv(csv_file)
                st.dataframe(preview_df.head(10), use_container_width=True)
                
                # Show file info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Rows", len(preview_df))
                with col2:
                    st.metric("Columns", len(preview_df.columns))
                with col3:
                    total_amount = preview_df['Amount'].sum() if 'Amount' in preview_df.columns else 0
                    st.metric("Total Amount", f"₹{total_amount:,.2f}")
                
                # Reset file pointer
                csv_file.seek(0)
                
                st.markdown("---")
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("📥 Import All Data", type="primary", use_container_width=True):
                        with st.spinner("Importing expenses..."):
                            success, message = fp.process_csv_file(csv_file)
                            if success:
                                st.success(message)
                                st.balloons()
                            else:
                                st.error(message)
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    
    # TAB 3: Text Import
    with tab3:
        st.subheader("📝 Upload Text File")
        st.info("Format: Date | Description | Amount | Category | Payment Method | Notes")
        st.write("Example: `2024-02-18 | Lunch | 500 | Food & Dining | UPI | With friends`")
        
        # Show example
        with st.expander("📖 View Example Format"):
            st.code(fp.create_sample_text(), language="text")
        
        text_file = st.file_uploader(
            "Choose Text file", 
            type=['txt'],
            key="text_upload"
        )
        
        if text_file is not None:
            st.write(f"**Uploaded:** {text_file.name}")
            
            # Show preview
            try:
                content = text_file.read().decode('utf-8')
                lines = content.strip().split('\n')
                st.write(f"**Total lines:** {len(lines)}")
                st.text_area("File Preview:", content[:500], height=150)
                
                # Reset file pointer
                text_file.seek(0)
                
                st.markdown("---")
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("📥 Import Data", type="primary", use_container_width=True):
                        text_file.seek(0)
                        with st.spinner("Importing expenses..."):
                            success, message = fp.process_text_file(text_file)
                            if success:
                                st.success(message)
                                st.balloons()
                            else:
                                st.error(message)
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    
    # TAB 4: Download Templates
    with tab4:
        st.subheader("📄 Download Templates")
        st.write("Download sample templates to see the correct format")
        
        col1, col2, col3 = st.columns(3)
        
        # Excel Template
        with col1:
            st.write("**Excel Template**")
            sample_df = fp.create_sample_excel()
            st.dataframe(sample_df, use_container_width=True, hide_index=True)
            
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                sample_df.to_excel(writer, index=False, sheet_name='Expenses')
            
            st.download_button(
                label="📥 Download Excel",
                data=output.getvalue(),
                file_name="expense_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        # CSV Template
        with col2:
            st.write("**CSV Template**")
            sample_csv = fp.create_sample_csv()
            st.dataframe(sample_csv, use_container_width=True, hide_index=True)
            
            st.download_button(
                label="📥 Download CSV",
                data=sample_csv.to_csv(index=False),
                file_name="expense_template.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Text Template
        with col3:
            st.write("**Text Template**")
            sample_text = fp.create_sample_text()
            st.code(sample_text, language="text")
            
            st.download_button(
                label="📥 Download Text",
                data=sample_text,
                file_name="expense_template.txt",
                mime="text/plain",
                use_container_width=True
            ) 

# ===== AI DOCUMENT BRAIN =====MOdified on 05-03-2026 with phi3 model
# ===== AI DOCUMENT BRAIN =====
elif menu == "AI Documents Brain":
    st.header("🧠 AI Personal Knowledge Assistant")
    
    # Show one-time setup message if first run
    st.info("💡 First time? Model will download automatically (~7GB, 10-20 min). After that, instant loading!")
    
    from modules import document_manager as dm
    
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "💬 Ask Questions", "📚 Document Library"])
    
    # TAB 1: Upload & Process
    with tab1:
        st.subheader("📄 Upload Your Document")
        
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "png", "jpg", "jpeg", "bmp", "tiff"],
            help="Upload PDFs, images, receipts, bills, or notes"
        )
        
        if uploaded_file:
            st.write("**📁 File Info:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Filename", uploaded_file.name[:20] + "...")
            with col2:
                st.metric("Size", f"{uploaded_file.size / 1024:.1f} KB")
            with col3:
                st.metric("Type", uploaded_file.name.split('.')[-1].upper())
            
            st.markdown("---")
            
            if st.button("🤖 Extract & Summarize", type="primary", use_container_width=True):
                with st.spinner("🔄 Processing document with AI... (First time may take longer)"):
                    success, result = dm.process_document(uploaded_file)
                
                if success:
                    st.success("✅ Document processed successfully!")
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.subheader("📝 AI-Generated Summary")
                        st.info(result["summary"])
                    
                    with col2:
                        st.subheader("📊 Statistics")
                        st.metric("Words", f"{result['word_count']:,}")
                        st.metric("Characters", f"{result['char_count']:,}")
                    
                    with st.expander("📄 View Full Text"):
                        st.text_area("", result["text"], height=400)
                
                else:
                    st.error(f"❌ Error: {result}")
    
    # TAB 2: Ask Questions
    with tab2:
        st.subheader("💬 Ask Questions About Your Documents")
        
        documents = db.get_all_documents()
        
        if documents:
            doc_names = [f"{doc['filename']} ({doc['upload_date']})" for doc in documents]
            selected_doc = st.selectbox("Select a document:", doc_names)
            
            if selected_doc:
                doc_index = doc_names.index(selected_doc)
                doc = documents[doc_index]
                
                st.write("**Document Summary:**")
                st.info(doc['summary'])
                
                question = st.text_input("❓ Ask a question:")
                
                if st.button("🔍 Get Answer", type="primary"):
                    if question:
                        with st.spinner("🤔 Thinking..."):
                            answer = dm.answer_question(doc['content'], question)
                            st.success("💡 Answer:")
                            st.write(answer)
                    else:
                        st.warning("Please enter a question!")
        else:
            st.warning("📭 No documents uploaded yet!")
    
    # TAB 3: Document Library
    with tab3:
        st.subheader("📚 Your Document Library")
        
        documents = db.get_all_documents()
        
        if documents:
            for doc in documents:
                with st.expander(f"📄 {doc['filename']} - {doc['upload_date']}"):
                    st.write("**Summary:**")
                    st.info(doc['summary'])
                    
                    if st.button(f"View Full Text", key=f"view_{doc['id']}"):
                        st.text_area("", doc['content'], height=200)
        else:
            st.info("📭 No documents in library yet.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Made with ❤️ for BCA Final Year Project")