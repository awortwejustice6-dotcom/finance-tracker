import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px  
from datetime import datetime, timedelta

# ==========================================
# --- 0. HELPER: CUSTOM PROGRESS BAR ---
# We create a new function OUTSIDE main()
# ==========================================
def render_progress_bar(label, current_spent, target_limit):
    """Renders a custom HTML/CSS progress bar that changes color based on percentage."""
    
    # Calculate the raw percentage (can be > 100%)
    pct = current_spent / target_limit if target_limit > 0 else 0.0
    
    # Calculate the width for the visual fill (capped at 100% so it doesn't break the bar)
    fill_width = min(pct, 1.0) * 100

    # Determine the bar color based on 'traffic light' logic
    # Healthy (Green)
    if pct < 0.8:
        bar_color = "#2ecc71"  # A beautiful, vibrant Green hex code
    # Warning (Yellow)
    elif 0.8 <= pct <= 1.0:
        bar_color = "#f1c40f"  # A rich Yellow
    # Danger / Over Budget (Red)
    else:
        bar_color = "#e74c3c"  # A bright Red

    # Use st.markdown with unsafe_allow_html=True to inject custom HTML/CSS
    html_code = f"""
    <div style="font-family: sans-serif; margin-bottom: 20px;">
        <div style="font-size: 16px; margin-bottom: 8px;">
            <strong>{label}: GHS {current_spent:,.2f} / GHS {target_limit:,.2f}</strong>
        </div>
        <div style="height: 12px; background-color: #31333f; border-radius: 6px; overflow: hidden; width: 100%;">
            <div style="height: 100%; width: {fill_width}%; background-color: {bar_color}; border-radius: 6px; transition: width 0.3s ease-in-out;"></div>
        </div>
    </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)


# ==========================================
# 1. DATABASE MANAGER (The Filing Cabinet)
# ==========================================
class DatabaseManager:
    def __init__(self, db_name="finance_tracker.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL,
                category TEXT,
                type TEXT,
                date DATE
            )
        ''')
        self.conn.commit()

    def add_transaction(self, amount, category, t_type, date):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO transactions (amount, category, type, date) VALUES (?, ?, ?, ?)",
                       (amount, category, t_type, date))
        self.conn.commit()

    def get_transactions(self):
        return pd.read_sql_query("SELECT * FROM transactions", self.conn)

    def delete_transaction(self, transaction_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        self.conn.commit()

# ==========================================
# 2. BUDGET ALLOCATOR (The Financial Advisor)
# ==========================================
class BudgetAllocator:
    def __init__(self, mode="Standard", custom_splits=None):
        self.mode = mode
        self.custom_splits = custom_splits or {"Needs": 50, "Wants": 30, "Savings": 20}

    def calculate_split(self, total_income):
        if self.mode == "Standard":
            return {
                "Needs": total_income * 0.50,
                "Wants": total_income * 0.30,
                "Savings": total_income * 0.20
            }
        else:
            return {
                "Needs": total_income * (self.custom_splits["Needs"] / 100),
                "Wants": total_income * (self.custom_splits["Wants"] / 100),
                "Savings": total_income * (self.custom_splits["Savings"] / 100)
            }

# ==========================================
# 3. FINANCIAL SUMMARY (The Accountant)
# ==========================================
class FinancialSummary:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_totals(self):
        df = self.db.get_transactions()
        if df.empty:
            return 0.0, 0.0, 0.0
        
        df['date'] = pd.to_datetime(df['date'])
        today = pd.Timestamp.today().normalize()
        expenses = df[df['type'] == 'Expense']
        
        daily = expenses[expenses['date'] == today]['amount'].sum()
        weekly = expenses[expenses['date'] >= (today - timedelta(days=7))]['amount'].sum()
        monthly = expenses[expenses['date'].dt.month == today.month]['amount'].sum()
        
        return daily, weekly, monthly

# ==========================================
# 4. STREAMLIT WEB INTERFACE (The Storefront)
# ==========================================
def main():
    st.set_page_config(page_title="Personal Finance Tracker", layout="wide")
    
    # --- THE ULTIMATE INVISIBILITY CLOAK ---
    hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            [data-testid="stToolbar"] {visibility: hidden !important;}
            
            /* Hide the floating "Hosted with Streamlit" badge */
            div[class^="viewerBadge"] {display: none !important;}
            .viewerBadge_container__1QSob {display: none !important;}
            a[href^="https://streamlit.io/cloud"] {display: none !important;}
            </style>
            """
    st.markdown(hide_st_style, unsafe_allow_html=True)

    st.title("💸 Monthly Finance & Budget Tracker")

    db = DatabaseManager()
    summary = FinancialSummary(db)

   # --- MOVED TO MAIN PAGE: Budget Setup ---
    # ==========================================
    st.header("1. Budget Setup")
    
    # Put income and strategy side-by-side so it doesn't take up too much vertical space
    setup_col1, setup_col2 = st.columns(2)
    with setup_col1:
        monthly_income = st.number_input("Monthly Income (GHS)", min_value=0.0, value=1000.0, step=100.0)
    with setup_col2:
        budget_mode = st.radio("Allocation Strategy", ["Standard (50/30/20)", "Custom"])
    
    custom_splits = {"Needs": 50, "Wants": 30, "Savings": 20}
    if budget_mode == "Custom":
        st.write("Set your percentages (must equal 100%):")
        # Put the sliders side-by-side for a clean look
        c1, c2, c3 = st.columns(3)
        custom_splits["Needs"] = c1.slider("Needs %", 0, 100, 50)
        custom_splits["Wants"] = c2.slider("Wants %", 0, 100, 30)
        custom_splits["Savings"] = c3.slider("Savings %", 0, 100, 20)
        
        if sum(custom_splits.values()) != 100:
            st.error("Percentages must add up to exactly 100!")

    allocator = BudgetAllocator(mode="Custom" if budget_mode == "Custom" else "Standard", custom_splits=custom_splits)
    allocations = allocator.calculate_split(monthly_income)

    st.divider()
   # --- MAIN DASHBOARD: Expense Summary ---
    st.header("2. Expense Dashboard")
    daily_tot, weekly_tot, monthly_tot = summary.get_totals()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Today's Expenses", f"GHS {daily_tot:,.2f}")
    col2.metric("Past 7 Days", f"GHS {weekly_tot:,.2f}")
    col3.metric("This Month's Expenses", f"GHS {monthly_tot:,.2f}")

    st.divider()

    # --- BUDGET ALLOCATION DISPLAY ---
    st.subheader("Income Allocation Target")
    b_col1, b_col2, b_col3 = st.columns(3)
    b_col1.info(f"**Needs:** GHS {allocations['Needs']:,.2f}")
    b_col2.warning(f"**Wants:** GHS {allocations['Wants']:,.2f}")
    b_col3.success(f"**Savings:** GHS {allocations['Savings']:,.2f}")

    st.divider()

    # ==========================================
    # --- UPGRADED: BUDGET PROGRESS BARS ---
    # We now call our custom render function.
    # ==========================================
    st.subheader("Current Spending vs. Targets")
    
    needs_categories = ["Food", "Transport", "Utilities"]
    wants_categories = ["Entertainment", "Shopping", "Other"]
    
    df_history = db.get_transactions()
    expenses_df = df_history[df_history['type'] == 'Expense']
    
    if not expenses_df.empty:
        expenses_df['date'] = pd.to_datetime(expenses_df['date'])
        this_month_expenses = expenses_df[expenses_df['date'].dt.month == datetime.today().month]
        
        spent_needs = this_month_expenses[this_month_expenses['category'].isin(needs_categories)]['amount'].sum()
        spent_wants = this_month_expenses[this_month_expenses['category'].isin(wants_categories)]['amount'].sum()
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            # === CALL THE NEW HELPER ===
            # This replaces st.write() and st.progress()
            render_progress_bar("Needs", spent_needs, allocations['Needs'])
            
        with col_p2:
            # === CALL THE NEW HELPER ===
            render_progress_bar("Wants", spent_wants, allocations['Wants'])
    else:
        st.info("Log some expenses to see your budget progress bars fill up!")

    st.divider()
    # ==========================================

   

    # --- TRANSACTION ENTRY FORM ---
    st.subheader("Log a Transaction")
    with st.form("transaction_form"):
        t_amount = st.number_input("Amount (GHS)", min_value=0.1, step=10.0)
        t_category = st.selectbox("Category", ["Food", "Transport", "Utilities", "Entertainment", "Shopping", "Other"])
        t_type = st.selectbox("Type", ["Expense", "Income"])
        t_date = st.date_input("Date", datetime.today())
        
        submitted = st.form_submit_button("Save Transaction")
        if submitted:
            db.add_transaction(t_amount, t_category, t_type, t_date)
            st.success("Transaction logged successfully!")
            st.rerun()

    # --- VIEW HISTORY & DELETE FEATURE ---
    st.subheader("Transaction History")
    if not df_history.empty:
        df_display = df_history.sort_values(by="id", ascending=False)
        st.dataframe(df_display, use_container_width=True)

        st.divider()

        # 2. The Delete Control Valve
        st.subheader("🗑️ Delete a Transaction")
        options = {f"ID {row['id']}: {row['type']} of GHS {row['amount']} for {row['category']} on {row['date']}": row['id'] for _, row in df_display.iterrows()}
        selected_text = st.selectbox("Select a mistake to remove:", list(options.keys()))
        
        if st.button("Delete Selected"):
            transaction_id_to_delete = options[selected_text]
            db.delete_transaction(transaction_id_to_delete)
            st.success("Transaction safely flushed from the system!")
            st.rerun() 
    else:
        st.write("No transactions logged yet.")

if __name__ == "__main__":
    main()