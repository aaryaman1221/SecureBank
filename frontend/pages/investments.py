import streamlit as st
import requests
import pandas as pd
import locale
from datetime import datetime
import plotly.express as px
import time 

# --- Config ---
BACKEND_URL = "http://127.0.0.1:5001"

# --- Page Setup ---
st.set_page_config(page_title="Investment Calculator", page_icon="📈", layout="wide")


# --- Custom CSS for Centering Headings AND ALL FONT FIXES ---
st.markdown("""
<style>
/* --- (NEW) STICKY LOGOUT BUTTON --- */
/* This button is in the sidebar, but CSS moves it to the top-right */
[data-testid="stSidebar"] [data-testid="stButton"] button {
    position: fixed; /* Fix to viewport */
    top: 0.5rem;
    right: 1rem;
    z-index: 9999;
    
    /* Style it */
    width: auto !important; 
    background-color: #DC3545 !important;
    color: white !important;
    border: none !important;
    padding: 0.5rem 1rem !important; /* Bigger padding */
    border-radius: 5px !important;
    font-weight: 600 !important;
    font-size: 1.1rem !important; /* Bigger font */
}
/* Make the button's *original* container in the sidebar take up no space */
[data-testid="stSidebar"] [data-testid="stButton"] {
    height: 0px;
    margin: 0;
    padding: 0;
}
/* --- END NEW LOGOUT CSS --- */

h1, h2, h3 {
    text-align: center;
}

/* --- (NEW) RULE FOR SIDEBAR NAV LINKS (e.g., "dashboard") --- */
[data-testid="stSidebarNavLink"] span {
    font-size: 1.1rem !important; /* Use the same size */
}

/* --- CORRECT RULE FOR TAB FONT SIZE --- */
button[role="tab"] p {
    font-size: 1.1rem !important; /* Adjust this value as needed */
}
            
/* --- RULE FOR WIDGET LABELS (e.g., "Select accounts:") --- */
[data-testid="stWidgetLabel"] > div {
    font-size: 1.1rem !important; /* Use the same size as your tabs */
}

/* --- RULE FOR TEXT INSIDE TEXT/NUMBER INPUTS --- */
input[data-testid="stNumberInput"],
input[data-testid="stTextInput"] {
    font-size: 1.1rem !important; /* Use the same size */
}

/* --- RULE FOR TEXT INSIDE SELECT BOXES (e.g., "Choose options", "sum") --- */
div[data-baseweb="select"] div {
    font-size: 1.1rem !important; 
}

/* --- (NEW) RULE FOR METRIC LABELS (e.g., "Bitcoin Price") --- */
[data-testid="stMetricLabel"] {
    font-size: 1.1rem !important; 
}

/* --- [NEW] FANCY LOADER (Copied from dashboard.py) --- */
.loader-container {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    width: 100%;
    height: 70vh; /* Full viewport height */
}
.loader {
    border: 12px solid #f3f3f3; /* Light grey */
    border-top: 12px solid #007BFF; /* Blue */
    border-radius: 50%;
    width: 100px;
    height: 100px;
    animation: spin 1s linear infinite;
}
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
/* --- End Loader --- */

</style>
""", unsafe_allow_html=True)

# --- Locale Setup ---
try:
    locale.setlocale(locale.LC_ALL, 'en_IN.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

# Check for login status
if not st.session_state.get('logged_in'):
    st.warning("Please log in to access this page.")
    st.stop()

# --- START: NEW STICKY LOGOUT BUTTON ---
# This is placed in the sidebar, but CSS moves it to the top-right
with st.sidebar:
    if st.button("Logout", key="global_logout_invest"): # Use a unique key
        for key in list(st.session_state.keys()):
            if key != 'page_scripts': # Don't delete the special key
                del st.session_state[key]
        st.rerun()
# --- END: NEW STICKY LOGOUT BUTTON ---

# Helper function to create authorization headers
def get_auth_headers():
    if "jwt_token" in st.session_state and st.session_state.jwt_token:
        return {"authorization": f"Bearer {st.session_state.jwt_token}"}
    return {}

# --- Helper Functions ---
@st.cache_data(ttl=900)
def get_market_data():
    headers = get_auth_headers()
    if not headers: return None
    try:
        res = requests.get(f"{BACKEND_URL}/market_data", headers=headers)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        error_msg = e.response.json().get('error', str(e)) if e.response else str(e)
        st.error(f"Could not fetch live market data: {error_msg}")
        return None

@st.cache_data(ttl=86400)
def get_historical_data():
    headers = get_auth_headers()
    if not headers: return None
    try:
        res = requests.get(f"{BACKEND_URL}/historical_data", headers=headers)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        error_msg = e.response.json().get('error') if e.response and e.response.content else str(e)
        st.error(f"Could not build graph: {error_msg}")
        return None

def get_transactions():
    headers = get_auth_headers()
    if not headers: return pd.DataFrame()
    try:
        res = requests.get(f"{BACKEND_URL}/transactions", headers=headers)
        res.raise_for_status()
        df = pd.DataFrame(res.json())
        if not df.empty:
            df['purchase_date'] = pd.to_datetime(df['purchase_date'], errors='coerce')
            df['quantity'] = pd.to_numeric(df['quantity'])
            df['purchase_price'] = pd.to_numeric(df['purchase_price'])
            df.dropna(subset=['purchase_date'], inplace=True)
        return df
    except Exception as e:
        st.error(f"Failed to get transactions: {e}")
        return pd.DataFrame()

# --- START: REPLACED SPINNER WITH FULL-PAGE LOADER ---

# 1. Create a placeholder that will take over the page
loader_placeholder = st.empty()

with loader_placeholder.container():
    # 2. Show the full-page loader HTML
    st.markdown("""
        <div class="loader-container">
            <div class="loader"></div>
            <h3 style='text-align: center;'>Fetching current market prices...</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # 3. Fetch the data
    market_data = get_market_data()
    transactions_df = get_transactions()
    time.sleep(1.5) # Force it to display for at least 1.5s

# 4. Clear the loader placeholder
loader_placeholder.empty()

# --- END: REPLACEMENT ---


# --- Live Price Dashboard (Now runs *after* loader) ---
st.title("📈 Investment Portfolio")
st.header("Live Market Prices")
if market_data:
    cols = st.columns(3)
    usd_to_inr = market_data.get('USD_INR', 83.5)

    # Bitcoin
    btc_price_usd = market_data.get('Bitcoin', {}).get('price', 0)
    btc_price_inr = btc_price_usd * usd_to_inr
    formatted_btc_inr = locale.format_string("₹%.2f", btc_price_inr, grouping=True)
    formatted_btc_usd_delta = f"${btc_price_usd:,.2f}"
    cols[0].metric("Bitcoin Price", formatted_btc_inr, formatted_btc_usd_delta)

    # Gold
    gold_price_usd = market_data.get('Gold', {}).get('price', 0)
    gold_price_inr = gold_price_usd * usd_to_inr
    formatted_gold_inr = locale.format_string("₹%.2f", gold_price_inr, grouping=True)
    formatted_gold_usd_delta = f"${gold_price_usd:,.2f}"
    cols[1].metric("Gold (GLD ETF) Price", formatted_gold_inr, formatted_gold_usd_delta)

    # Nifty 50
    nifty_price = market_data.get('Nifty 50', {}).get('price', 0)
    formatted_nifty_inr = locale.format_string("₹%.2f", nifty_price, grouping=True)
    cols[2].metric("Nifty 50 (NIFTYBEES.NS) Price", formatted_nifty_inr)
else:
    st.error("Could not load market data.")

# --- Current Portfolio Value Section ---
st.header("Current Portfolio Value")
# transactions_df = get_transactions() # Already called above

if not transactions_df.empty and market_data:
    total_portfolio_value = 0.0
    portfolio_breakdown = []
    
    assets = transactions_df['asset_name'].unique()
    
    for asset in assets:
        total_quantity = transactions_df[transactions_df['asset_name'] == asset]['quantity'].sum()
        current_price = market_data.get(asset, {}).get('price', 0)
        currency = market_data.get(asset, {}).get('currency', 'INR')
        
        current_value = total_quantity * current_price
        if currency == 'USD':
            current_value *= market_data.get('USD_INR', 83.0)
            
        total_portfolio_value += current_value
        portfolio_breakdown.append({'Asset': asset, 'Value (INR)': current_value})

    col1, col2 = st.columns([1, 2])
    
    with col1:
        formatted_total_value = locale.format_string("₹%.2f", total_portfolio_value, grouping=True)
        st.metric("Total Value", formatted_total_value)

    with col2:
        if portfolio_breakdown:
            df_breakdown = pd.DataFrame(portfolio_breakdown)
            fig = px.pie(df_breakdown, names='Asset', values='Value (INR)', title='Portfolio Allocation')
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Add a transaction to see your portfolio value.")


# =========================================================================
# --- START: REPLACED 'Performance' & 'Transactions' (Suggestion 4) ---
# =========================================================================

st.divider()

# --- Use Tabs for Performance and Transactions ---
tab1, tab2 = st.tabs(["📈 Portfolio Performance", "🧾 Transaction Log"])

with tab1:
    st.subheader("Performance Over Time") # Use subheader for tab content
    if not transactions_df.empty and market_data:
        historical_data = get_historical_data()
        if historical_data and any(historical_data.values()):
            date_range = pd.date_range(start=transactions_df['purchase_date'].min(), end=pd.Timestamp.today())
            portfolio_values = []
            for current_date in date_range:
                daily_total = 0
                for asset, group in transactions_df.groupby('asset_name'):
                    if asset in historical_data and historical_data[asset]:
                        price_series = pd.Series(historical_data[asset], dtype=float)
                        price_series.index = pd.to_datetime(price_series.index)
                        quantity = group[group['purchase_date'] <= current_date]['quantity'].sum()
                        if quantity > 0:
                            price = price_series.asof(current_date)
                            if not pd.isna(price):
                                value = quantity * price
                                if market_data.get(asset, {}).get('currency') == 'USD':
                                    value *= market_data.get('USD_INR', 83.5)
                                daily_total += value
                if daily_total > 0: # Only append if value is not zero
                    portfolio_values.append({'date': current_date, 'value': daily_total})
            
            if portfolio_values:
                chart_df = pd.DataFrame(portfolio_values)
                chart_df['Formatted Value'] = chart_df['value'].apply(lambda x: locale.format_string("₹%.2f", x, grouping=True))

                fig_line = px.line(
                    chart_df,
                    x='date',
                    y='value',
                    custom_data=['Formatted Value']
                )

                fig_line.update_traces(hovertemplate='<b>%{x|%b %d, %Y}</b><br>Value: %{customdata[0]}')
                fig_line.update_xaxes(tickformat='%b %Y', title='Date')
                fig_line.update_yaxes(title='Portfolio Value (INR)')

                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("Not enough data to plot the graph.")
        else:
            st.info("No historical data available to plot the graph.")
    else:
        st.info("Add a transaction to see your portfolio performance.")

with tab2:
    st.subheader("Manage Transactions")
    
    # Use a popover for the "Add Transaction" form
    with st.popover("➕ Add New Transaction"):
        with st.form("add_tx_form", clear_on_submit=True):
            asset = st.selectbox("Asset", ["Bitcoin", "Gold", "Nifty 50"])
            quantity = st.number_input("Quantity", min_value=0.0, format="%.8f")
            price = st.number_input("Purchase Price (per unit, in original currency)", min_value=0.01)
            date_input = st.date_input("Purchase Date")
            
            if st.form_submit_button("Add Transaction"):
                payload = {
                    'asset_name': asset, 'quantity': quantity,
                    'purchase_price': price, 'purchase_date': date_input.strftime('%Y-%m-%d')
                }
                requests.post(f"{BACKEND_URL}/transactions", headers=get_auth_headers(), json=payload)
                st.cache_data.clear()
                st.rerun()
    
    # Display the log
    st.markdown("---") # Add a small separator
    st.subheader("History")
    log_transactions_df = get_transactions() # Get fresh data
    
    if not log_transactions_df.empty:
        # Let's clean up the df for display
        display_df = log_transactions_df.copy()
        display_df['purchase_date'] = display_df['purchase_date'].dt.strftime('%Y-%m-%d')
        display_df['quantity'] = display_df['quantity'].astype(float).map('{:,.6f}'.format)
        display_df['purchase_price'] = display_df['purchase_price'].astype(float).map(lambda x: locale.format_string("₹%.2f", x, grouping=True))
        
        st.dataframe(
            display_df[['asset_name', 'purchase_date', 'quantity', 'purchase_price']],
            use_container_width=True,
            hide_index=True
        )
        
        # Add a separate section for deleting
        st.markdown("---")
        st.subheader("Delete a Transaction")
        
        # Create a display-friendly list for the selectbox
        log_transactions_df['display'] = log_transactions_df.apply(
            lambda row: f"{row['asset_name']} ({row['quantity']:.4f}) on {row['purchase_date'].strftime('%Y-%m-%d')}", 
            axis=1
        )
        
        tx_to_delete_display = st.selectbox(
            "Select transaction to delete", 
            options=log_transactions_df['display'], 
            index=None, 
            placeholder="Select a transaction..."
        )
        
        if tx_to_delete_display:
            # Find the ID of the selected transaction
            tx_id_to_delete = log_transactions_df[log_transactions_df['display'] == tx_to_delete_display].iloc[0]['id']
            
            if st.button(f"Delete Transaction (ID: {tx_id_to_delete})", type="primary"):
                try:
                    requests.delete(f"{BACKEND_URL}/transactions/{tx_id_to_delete}", headers=get_auth_headers())
                    st.cache_data.clear()
                    st.rerun()
                except requests.exceptions.RequestException as e:
                    st.error("Failed to delete.")
    else:
        st.info("Your transaction log is empty. Add one using the button above.")

# =========================================================================
# --- END: REPLACEMENT SECTION ---
# =========================================================================