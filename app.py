"""
app.py
Main Streamlit application for Smart Finance Brain
1121212212121212121221
"""

import streamlit as st
from datetime import datetime
import sys
import os
import pandas as pd

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
st.subheader("Personal Finance Management System")

# Sidebar
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Select Option:", ["Add Expense", "View Expenses", "Dashboard"])

st.sidebar.markdown("---")
st.sidebar.info("Finance Module v1.0")


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
                    st.info(f"Added: ₹{amount:.2f} for {description}")
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
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        st.download_button(
            label="📥 Download CSV",
            data=df.to_csv(index=False),
            file_name=f"expenses_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


# ===== DASHBOARD =====
elif menu == "Dashboard":
    st.header("📈 Finance Dashboard")
    
    current_month_total = fm.get_current_month_total()
    current_month_name = datetime.now().strftime('%B %Y')
    
    st.subheader(f"Spending This Month ({current_month_name})")
    st.metric("Total Spent", f"₹{current_month_total:,.2f}")
    
    st.markdown("---")
    st.subheader("Category-wise Spending")
    
    category_totals = fm.get_category_wise_total()
    
    if category_totals:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            import pandas as pd
            category_df = pd.DataFrame(
                list(category_totals.items()), 
                columns=['Category', 'Amount']
            )
            category_df = category_df.sort_values('Amount', ascending=False)
            st.bar_chart(category_df.set_index('Category'))
        
        with col2:
            for category, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
                percentage = (total / sum(category_totals.values())) * 100
                st.write(f"**{category}**")
                st.write(f"₹{total:,.2f} ({percentage:.1f}%)")
                st.progress(percentage / 100)
                st.write("")
    else:
        st.info("No data available for dashboard.")


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Made with ❤️ for BCA Project")