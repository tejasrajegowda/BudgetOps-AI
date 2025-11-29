"""BudgetOps AI - Streamlit Dashboard"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import pytz
import os

# Page config
st.set_page_config(
    page_title="BudgetOps AI",
    page_icon="💰",
    layout="wide"
)

# API base URL
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Title
st.title("💰 BudgetOps AI - Budget Tracker")
st.markdown("AI-powered expense tracking and insights")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    if st.button("🔄 Process New Emails"):
        with st.spinner("Processing emails..."):
            response = requests.post(f"{API_URL}/transactions/process-emails", json={
                "sender": "alerts@hdfcbank.net",
                "max_results": 10,
                "mark_as_read": True
            })
            if response.status_code == 200:
                data = response.json()
                st.success(f"✓ Processed {data['inserted']} new transactions!")
            else:
                st.error("Failed to process emails")
    
    st.markdown("---")
    selected_date = st.date_input("Select Date", value=date.today())

# Main content
tabs = st.tabs(["📊 Dashboard", "💡 Insights", "📋 Transactions"])

# Tab 1: Dashboard
with tabs[0]:
    st.header(f"Daily Summary - {selected_date}")
    
    # Fetch daily summary
    response = requests.get(f"{API_URL}/transactions/daily-summary", 
                           params={"target_date": str(selected_date)})
    
    if response.status_code == 200:
        summary = response.json()
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💸 Total Spent", f"₹{summary.get('total_spent', 0):.2f}")
        with col2:
            st.metric("💰 Total Earned", f"₹{summary.get('total_earned', 0):.2f}")
        with col3:
            st.metric("📊 Net", f"₹{summary.get('net', 0):.2f}")
        with col4:
            st.metric("🔢 Transactions", summary.get('transaction_count', 0))
        
        # Transaction chart
        if summary.get('transactions'):
            df = pd.DataFrame(summary['transactions'])
            
            # Category breakdown
            if 'category' in df.columns:
                st.subheader("Category Breakdown")
                debit_df = df[df['transaction_type'] == 'debit']
                if not debit_df.empty:
                    category_sum = debit_df.groupby('category')['amount'].sum().reset_index()
                    fig = px.pie(category_sum, values='amount', names='category',
                                title='Spending by Category')
                    st.plotly_chart(fig, use_container_width=True)

# Tab 2: Insights
with tabs[1]:
    st.header("💡 AI Insights")
    
    # Daily insight
    response = requests.get(f"{API_URL}/insights/daily",
                          params={"target_date": str(selected_date)})
    
    if response.status_code == 200:
        data = response.json()
        st.info(data.get('insight', 'No insight available'))
        
        with st.expander("View Details"):
            st.json(data.get('summary', {}))

# Tab 3: Transactions
with tabs[2]:
    st.header("📋 Recent Transactions")
    
    response = requests.get(f"{API_URL}/transactions/transactions", 
                          params={"limit": 50})
    
    if response.status_code == 200:
        data = response.json()
        transactions = data.get('transactions', [])
        
        if transactions:
            df = pd.DataFrame(transactions)
            display_cols = ['transaction_date', 'amount', 'transaction_type', 
                          'to_merchant', 'category']
            st.dataframe(df[display_cols] if all(c in df.columns for c in display_cols) else df, 
                        use_container_width=True)