import streamlit as st
import requests
from phe import paillier
import json
import pandas as pd
import locale
import logging
from decimal import Decimal
import plotly.graph_objects as go
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="SecureBank Main",
    page_icon="🏦",
    layout="wide"
)

# --- Custom CSS (Unchanged) ---
st.markdown("""
<style>
/* ... (all your CSS is unchanged) ... */
[data-testid="stSidebar"] [data-testid="stButton"] button {
    position: fixed; /* Fix to viewport */
    top: 0.5rem;
    right: 1rem;
    z-index: 9999;
    
    /* Style it */
    width: auto !important; /* <--- ADD THIS LINE */
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

/* --- (NEW) RULE FOR SIDEBAR NAV LINKS (e.g., "dashboard") --- */
[data-testid="stSidebarNavLink"] span {
    font-size: 1.1rem !important; /* Use the same size */
}

/* --- (NEW) RULE FOR METRIC LABELS (e.g., "Bitcoin Price") --- */
[data-testid="stMetricLabel"] {
    font-size: 1.1rem !important; 
}
/* --- END NEW RULE --- */

/* ========================================================================= */
/* --- START: [COMPUTATION LOADER CSS] --- */
/* ========================================================================= */
.computation-container {
    position: relative; /* For symbol positioning */
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    width: 100%;
    height: 20vh; /* Smaller height for the section */
    overflow: hidden; /* Hide symbols that float off-screen */
    border-radius: 10px;
    background-color: #f8f9fa;
}

.computation-text {
    font-size: 1.8rem;
    font-weight: 600;
    color: #333;
    animation: pulse 1.5s ease-in-out infinite;
    z-index: 10; /* Keep text on top */
}

@keyframes pulse {
    0% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.7; transform: scale(1.03); }
    100% { opacity: 1; transform: scale(1); }
}

.symbol {
    position: absolute;
    font-size: 1.5rem;
    color: #007BFF;
    opacity: 0;
    animation: float-up 4s ease-in-out infinite;
    z-index: 1;
}

@keyframes float-up {
    0% { transform: translateY(40px) scale(0.8); opacity: 0; }
    20% { opacity: 0.8; }
    80% { opacity: 0.8; }
    100% { transform: translateY(-80px) scale(1.2); opacity: 0; }
}

/* ... (all CSS symbols unchanged) ... */
.symbol-1 { left: 15%; animation-delay: 0s; }
.symbol-2 { left: 35%; animation-delay: 1s; font-size: 1.2rem; color: #DC3545; }
.symbol-3 { left: 55%; animation-delay: 0.5s; font-size: 1.7rem; }
.symbol-4 { left: 75%; animation-delay: 1.5s; color: #FD7E14; }
.symbol-5 { left: 25%; animation-delay: 2s; font-size: 1.4rem; }
.symbol-6 { left: 65%; animation-delay: 2.5s; color: #28a745; }
.symbol-7 { left: 10%; animation-delay: 1.2s; font-size: 1.6rem; color: #6f42c1; }
.symbol-8 { left: 80%; animation-delay: 0.2s; font-size: 1.3rem; color: #20c997; }
.symbol-9 { left: 45%; animation-delay: 2.2s; }
.symbol-10 { left: 85%; animation-delay: 1.8s; color: #DC3545; }
.symbol-11 { left: 5%; animation-delay: 3s; font-size: 1.4rem; color: #FD7E14; }
.symbol-12 { left: 90%; animation-delay: 2.8s; font-size: 1.6rem; color: #28a745; }
.symbol-13 { left: 12%; animation-delay: 0.3s; font-size: 1.2rem; color: #20c997; }
.symbol-14 { left: 22%; animation-delay: 0.8s; color: #6f42c1; }
.symbol-15 { left: 32%; animation-delay: 1.3s; font-size: 1.4rem; }
.symbol-16 { left: 42%; animation-delay: 1.8s; color: #FD7E14; }
.symbol-17 { left: 52%; animation-delay: 2.3s; font-size: 1.2rem; }
.symbol-18 { left: 62%; animation-delay: 2.8s; color: #DC3545; }
.symbol-19 { left: 72%; animation-delay: 3.3s; font-size: 1.5rem; color: #28a745; }
.symbol-20 { left: 82%; animation-delay: 3.8s; }
.symbol-21 { left: 92%; animation-delay: 0.6s; font-size: 1.3rem; color: #6f42c1; }
.symbol-22 { left: 2%; animation-delay: 1.1s; }
.symbol-23 { left: 18%; animation-delay: 1.6s; color: #FD7E14; }
.symbol-24 { left: 28%; animation-delay: 2.1s; font-size: 1.6rem; color: #20c997; }
.symbol-25 { left: 38%; animation-delay: 2.6s; }
.symbol-26 { left: 48%; animation-delay: 3.1s; color: #DC3545; }
.symbol-27 { left: 58%; animation-delay: 3.6s; font-size: 1.2rem; }
.symbol-28 { left: 68%; animation-delay: 0.1s; color: #28a745; }
.symbol-29 { left: 78%; animation-delay: 0.9s; font-size: 1.4rem; }
.symbol-30 { left: 88%; animation-delay: 1.4s; color: #6f42c1; }
.symbol-31 { left: 8%; animation-delay: 1.9s; font-size: 1.2rem; color: #FD7E14; }
.symbol-32 { left: 95%; animation-delay: 2.4s; }
.symbol-33 { left: 40%; animation-delay: 2.9s; color: #20c997; }
.symbol-34 { left: 50%; animation-delay: 3.4s; font-size: 1.5rem; }
.symbol-35 { left: 60%; animation-delay: 3.9s; color: #DC3545; }
.symbol-36 { left: 70%; animation-delay: 0.4s; font-size: 1.3rem; }

/* ========================================================================= */
/* --- END: [COMPUTATION LOADER CSS] --- */
/* ========================================================================= */


/* ========================================================================= */
/* --- START: [LOGIN LOADER CSS] --- */
/* ========================================================================= */
.loader-container {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    width: 100%;
    height: 70vh;
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
/* ========================================================================= */
/* --- END: [LOGIN LOADER CSS] --- */
/* ========================================================================= */


/* Center the login page hero image and text */
.empty-hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    margin-top: 2rem;
}
.empty-hero img {
    width: 150px;
    margin-bottom: 1rem;
}

/* --- BOLD SECTION TITLES --- */
.section-title-blue, .section-title-red, .section-title-orange {
    font-size: 1.75em;
    font-weight: 600;
    color: #FFFFFF;
    text-align: center;
    padding: 12px;
    border-radius: 10px;
    margin-top: 2rem;
    margin-bottom: 1.5rem;
}
.section-title-blue { background-color: #007BFF; }
.section-title-red { background-color: #DC3545; }
.section-title-orange { background-color: #FD7E14; }

/* --- COLORED ACCOUNT CARD --- */
.account-card {
    background-color: #F0F5FF;
    border: 1px solid #BBDDFF;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.05);
}
.account-balance {
    font-size: 2.2em;
    font-weight: 600;
    color: #0056b3;
    margin-bottom: 5px;
}
.account-name {
    font-size: 1.1em;
    font-weight: 500;
    color: #333;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)


# --- Config ---
BACKEND_URL = "http://127.0.0.1:5001"
BALANCE_PRECISION = 100

# --- Locale Setup ---
try:
    locale.setlocale(locale.LC_ALL, 'en_IN.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

# --- JSON Encoder for Paillier ---
class PaillierEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, paillier.PaillierPublicKey): return {'n': obj.n}
        if isinstance(obj, paillier.EncryptedNumber):
            return {'public_key': {'n': obj.public_key.n}, 'ciphertext': obj.ciphertext(be_secure=False)}
        return super().default(self)

# --- Session Init (Unchanged) ---
def init_session_state():
    defaults = {
        'logged_in': False, 'username': None, 'public_key': None,
        'private_key': None, 'accounts': pd.DataFrame(),
        'jwt_token': None
    }
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

# --- Helper Functions (Unchanged) ---
def get_auth_headers():
    if "jwt_token" in st.session_state and st.session_state.jwt_token:
        return {"authorization": f"Bearer {st.session_state.jwt_token}"}
    return {}

def fetch_accounts():
    headers = get_auth_headers()
    if not headers:
        st.error("Authentication error. Please log in again.")
        st.session_state.accounts = pd.DataFrame()
        return
    try:
        response = requests.get(f"{BACKEND_URL}/accounts", headers=headers)
        response.raise_for_status()
        df = pd.DataFrame(response.json())
        if not df.empty:
            df['balance'] = pd.to_numeric(df['balance'])
        st.session_state.accounts = df
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch accounts. Backend error: {e}")
        st.session_state.accounts = pd.DataFrame()

def safe_float(val, default=0.0):
    try:
        if val is None or (isinstance(val, str) and val.strip() == ""):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default

# --- Main Dashboard ---
def main_app():
    # --- START: NEW STICKY LOGOUT BUTTON ---
    with st.sidebar:
        if st.button("Logout", key="global_logout"):
            for key in list(st.session_state.keys()):
                if key != 'page_scripts': # Don't delete the special key
                    del st.session_state[key]
            st.rerun()
    # --- END: NEW STICKY LOGOUT BUTTON ---

    st.title(f"Welcome to SecureBank, {st.session_state.username}!")
    st.info("Navigate to the **📈 Investments** page in the sidebar to track your portfolio.", icon="👈")
    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    if not st.session_state.public_key:
        with st.spinner("Generating secure session keys..."):
            st.session_state.public_key, st.session_state.private_key = paillier.generate_paillier_keypair()

    # --- SECTION 1 (ACCOUNTS) ---
    st.markdown('<h2 class="section-title-blue">🏦 Manage Your Accounts</h2>', unsafe_allow_html=True)
    
    # --- Tabs (Unchanged) ---
    tab1, tab2, tab3 = st.tabs(["My Accounts", "Add Account", "Transfer Funds"])
    
    with tab1:
        # ... (tab1 content is unchanged) ...
        if not st.session_state.accounts.empty:
            cols = st.columns(3) 
            for index, row in st.session_state.accounts.iterrows():
                acc_id, acc_name, acc_balance = row['id'], row['account_name'], row['balance']
                balance_value = safe_float(acc_balance)
                formatted_balance = locale.format_string("₹%.2f", balance_value, grouping=True)
                col = cols[index % 3] 
                with col.container():
                    st.markdown(f"""
                    <div class="account-card">
                        <div class="account-name">{acc_name}</div>
                        <div class="account-balance">{formatted_balance}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    with st.popover(f"Manage '{acc_name}'"):
                        with st.form(f"edit_form_{acc_id}"):
                            st.subheader(f"Edit {acc_name}")
                            new_name = st.text_input("Account Name", value=acc_name)
                            new_balance = st.number_input("Balance", value=balance_value, min_value=0.0, format="%.2f")
                            c1, c2 = st.columns(2)
                            if c1.form_submit_button("Save Changes"):
                                requests.put(f"{BACKEND_URL}/accounts/{acc_id}", headers=get_auth_headers(), json={'account_name': new_name, 'balance': new_balance})
                                fetch_accounts(); st.rerun() # st.rerun() is OK here, it just reloads the tab
                            if c2.form_submit_button("Delete", type="primary"):
                                requests.delete(f"{BACKEND_URL}/accounts/{acc_id}", headers=get_auth_headers())
                                fetch_accounts(); st.rerun() # st.rerun() is OK here
        else:
            st.info("You have no accounts yet. Add one in the tab above 👆")
    
    # =========================================================================
    # --- START: [FIX 1] ---
    # =========================================================================
    with tab2:
        # --- REMOVED clear_on_submit=True ---
        with st.form("add_account_form"): 
            st.subheader("➕ Add New Account")
            acc_name = st.text_input("Account Name")
            acc_balance = st.number_input("Initial Balance (₹)", min_value=0.0, step=100.0, format="%.2f")
            
            if st.form_submit_button("Add Account"):
                payload = {'account_name': acc_name, 'balance': acc_balance}
                requests.post(f"{BACKEND_URL}/accounts", headers=get_auth_headers(), json=payload)
                fetch_accounts()
                st.success("Account added!") # Show success message
                # --- NO st.rerun() ---
                # This lets the form submit complete, which will JUMP to tab 1
    # =========================================================================
    # --- END: [FIX 1] ---
    # =========================================================================

    # =========================================================================
    # --- START: [FIX 2] ---
    # =========================================================================
    with tab3:
        st.subheader("💸 Transfer Between Your Accounts")
        accounts_df = st.session_state.accounts
        if len(accounts_df) < 2:
            st.info("You need at least two accounts to make a transfer.")
        else:
            # --- REMOVED clear_on_submit=True ---
            with st.form("transfer_form"):
                account_names = accounts_df['account_name'].tolist()
                
                from_account_name = st.selectbox(
                    "From Account", 
                    options=account_names, 
                    index=0
                )
                
                to_index = 1 if len(account_names) > 1 else 0
                to_account_name = st.selectbox(
                    "To Account", 
                    options=account_names, 
                    index=to_index
                )
                    
                amount = st.number_input("Amount (₹)", min_value=0.01, format="%.2f")
                
                if st.form_submit_button("Transfer Funds"):
                    
                    if from_account_name == to_account_name:
                        st.warning("Cannot transfer to the same account. No changes made.")
                        st.rerun() # --- st.rerun() will STAY on this tab
                    
                    else:
                        from_account = accounts_df[accounts_df['account_name'] == from_account_name].iloc[0]
                        to_account = accounts_df[accounts_df['account_name'] == to_account_name].iloc[0]
                        
                        if Decimal(str(amount)) > Decimal(str(from_account['balance'])):
                            st.error("Insufficient funds in the 'From' account.")
                            st.rerun() # --- st.rerun() will STAY on this tab
                        
                        else:
                            payload = {'from_account_id': int(from_account['id']), 'to_account_id': int(to_account['id']), 'amount': str(amount)}
                            try:
                                response = requests.post(f"{BACKEND_URL}/accounts/transfer", headers=get_auth_headers(), json=payload)
                                response.raise_for_status()
                                st.success("Transfer successful!")
                                fetch_accounts()
                                # --- NO st.rerun() ---
                                # This lets the form submit complete, which will JUMP to tab 1
                                
                            except requests.exceptions.RequestException as e:
                                error_msg = e.response.json().get('error', 'An unknown error occurred.')
                                st.error(f"Transfer failed: {error_msg}")
                                st.rerun() # --- st.rerun() will STAY on this tab
    # =========================================================================
    # --- END: [FIX 2] ---
    # =========================================================================
    
    st.divider()
    
    # --- SECTION 2 (ANALYTICS) (Unchanged) ---
    st.markdown('<h2 class="section-title-red">🔐 Privacy-Preserving Analytics</h2>', unsafe_allow_html=True)
    analytics_tab, = st.tabs(["**Run Secure Analysis**"])
    with analytics_tab:
        if not st.session_state.accounts.empty:
            options = st.multiselect("Select accounts:", options=st.session_state.accounts['account_name'])
            operation = st.selectbox("Select operation:", ("sum", "average"))
            
            if st.button("Calculate Securely"):
                balances = st.session_state.accounts[st.session_state.accounts['account_name'].isin(options)]['balance'].tolist()
                if balances:
                    placeholder = st.empty()
                    placeholder.markdown("""
                        <div class="computation-container">
                            <div class="computation-text">Calculating...</div>
                            <span class="symbol symbol-1">Σ</span>
                            <span class="symbol symbol-2">∫</span>
                            <span class="symbol symbol-3">π</span>
                            <span class="symbol symbol-4">√x</span>
                            <span class="symbol symbol-5">α</span>
                            <span class="symbol symbol-6">β</span>
                            <span class="symbol symbol-7">θ</span>
                            <span class="symbol symbol-8">Δ</span>
                            <span class="symbol symbol-9">μ</span>
                            <span class="symbol symbol-10">±</span>
                            <span class="symbol symbol-11">≈</span>
                            <span class="symbol symbol-12">≠</span>
                            <span class="symbol symbol-13">∂y</span>
                            <span class="symbol symbol-14">λ</span>
                            <span class="symbol symbol-15">ε</span>
                            <span class.symbol symbol-16">∀</span>
                            <span class="symbol symbol-17">∃</span>
                            <span class_("symbol symbol-18")">∞</span>
                            <span class="symbol symbol-19">γ</span>
                            <span class="symbol symbol-20">∇</span>
                            <span class="symbol symbol-21">ω</span>
                            <span class="symbol symbol-22">φ</span>
                            <span class="symbol symbol-23">σ</span>
                            <span class="symbol symbol-24">ρ</span>
                            <span class="symbol symbol-25">τ</span>
                            <span class="symbol symbol-26">ψ</span>
                            <span class="symbol symbol-27">ζ</span>
                            <span class.symbol symbol-28">κ</span>
                            <span class="symbol symbol-29">⊂</span>
                            <span class="symbol symbol-30">∈</span>
                            <span class="symbol symbol-31">χ</span>
                            <span class="symbol symbol-32">∩</span>
                            <span class="symbol symbol-33">∪</span>
                            <span class.symbol symbol-34">v</span>
                            <span class="symbol symbol-35">η</span>
                            <span class="symbol symbol-36">f(x)</span>
                        </div>
                    """, unsafe_allow_html=True)
                    start_time = time.time()
                    MIN_DISPLAY_TIME_SEC = 5.0
                    result_action = None
                    try:
                        pk, sk = st.session_state.public_key, st.session_state.private_key
                        int_balances = [int(safe_float(b) * BALANCE_PRECISION) for b in balances]
                        enc_balances = [pk.encrypt(b) for b in int_balances]
                        payload = json.dumps({'public_key': pk, 'values': enc_balances}, cls=PaillierEncoder)
                        headers = get_auth_headers()
                        headers['Content-Type'] = 'application/json'
                        response = requests.post(f"{BACKEND_URL}/compute", headers=headers, data=payload)
                        if response.status_code == 200:
                            enc_result = paillier.EncryptedNumber(pk, int(response.json()['result']['ciphertext']))
                            dec_sum_int = sk.decrypt(enc_result)
                            final_sum = dec_sum_int / BALANCE_PRECISION
                            result = (final_sum / len(balances)) if operation == 'average' else final_sum
                            formatted_result = locale.format_string("₹%.2f", result, grouping=True)
                            result_action = lambda: placeholder.metric(label=f"Decrypted {operation.capitalize()}", value=formatted_result)
                        else:
                            error_msg = f"Server error: {response.text}"
                            result_action = lambda: placeholder.error(error_msg)
                    except Exception as e:
                        error_msg = f"An error occurred: {e}"
                        result_action = lambda: placeholder.error(error_msg)
                    finally:
                        duration = time.time() - start_time
                        if duration < MIN_DISPLAY_TIME_SEC:
                            time.sleep(MIN_DISPLAY_TIME_SEC - duration)
                        if result_action:
                            result_action()
                else:
                    st.warning("Please select at least one account.")
        else:
            st.info("Add an account to use Privacy-Preserving Analytics.")
    
    st.divider()
    
    # --- SECTION 3 (FUTURE VALUE) (Unchanged) ---
    st.markdown('<h2 class="section-title-orange">📈 Future Value Calculator</h2>', unsafe_allow_html=True)
    fv_tab, = st.tabs(["**Run Projection**"])
    with fv_tab:
        if not st.session_state.accounts.empty:
            accounts_df = st.session_state.accounts
            account_names = accounts_df['account_name'].tolist()
            selected_account_name = st.selectbox("Select account:", options=account_names, key="fv_account")
            num_years = st.number_input("Number of years:", min_value=1, max_value=100, value=10, step=1, key="fv_years")
            interest_rate = 0.05 
            
            if st.button("Project Future Value"):
                placeholder = st.empty()
                placeholder.markdown("""
                    <div class="computation-container">
                        <div class="computation-text">Projecting...</div>
                        <span class="symbol symbol-1">Σ</span>
                        <span class="symbol symbol-2">∫</span>
                        <span class="symbol symbol-3">π</span>
                        <span class="symbol symbol-4">√x</span>
                        <span class="symbol symbol-5">α</span>
                        <span class.symbol symbol-6">β</span>
                        <span class="symbol symbol-7">θ</span>
                        <span class="symbol symbol-8">Δ</span>
                        <span class="symbol symbol-9">μ</span>
                        <span class="symbol symbol-10">±</span>
                        <span class="symbol symbol-11">≈</span>
                        <span class_("symbol symbol-12")">≠</span>
                        <span class="symbol symbol-13">∂y</span>
                        <span class="symbol symbol-14">λ</span>
                        <span class="symbol symbol-15">ε</span>
                        <span class="symbol symbol-16">∀</span>
                        <span class="symbol symbol-17">∃</span>
                        <span class="symbol symbol-18">∞</span>
                        <span class="symbol symbol-19">γ</span>
                        <span class="symbol symbol-20">∇</span>
                        <span class="symbol symbol-21">ω</span>
                        <span class="symbol symbol-22">φ</span>
                        <span class.symbol symbol-23">σ</span>
                        <span class="symbol symbol-24">ρ</span>
                        <span class="symbol symbol-25">τ</span>
                        <span class="symbol symbol-26">ψ</span>
                        <span class="symbol symbol-27">ζ</span>
                        <span class="symbol symbol-28">κ</span>
                        <span class="symbol symbol-29">⊂</span>
                        <span class.symbol symbol-30">∈</span>
                        <span class="symbol symbol-31">χ</span>
                        <span class="symbol symbol-32">∩</span>
                        <span class="symbol symbol-33">∪</span>
                        <span class="symbol symbol-34">v</span>
                        <span class="symbol symbol-35">η</span>
                        <span class="symbol symbol-36">f(x)</span>
                    </div>
                """, unsafe_allow_html=True)
                
                start_time = time.time()
                MIN_DISPLAY_TIME_SEC = 5.0
                result_action = None

                try:
                    present_value = float(accounts_df[accounts_df['account_name'] == selected_account_name]['balance'].iloc[0])
                    years = list(range(num_years + 1))
                    values = [present_value * ((1 + interest_rate) ** year) for year in years]
                    formatted_values = [locale.format_string("₹%.2f", v, grouping=True) for v in values]
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=years, 
                        y=values, 
                        mode='lines+markers',
                        fill='tozeroy',
                        customdata=formatted_values,
                        hovertemplate='Year %{x}: <b>%{customdata}</b><extra></extra>',
                        line=dict(color='#FD7E14')
                    ))
                    fig.update_layout(
                        title=f"Projection for '{selected_account_name}' at 5% APY",
                        xaxis_title="Year",
                        yaxis_title="Projected Value (INR)",
                        hovermode="x unified",
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                    )
                    
                    result_action = lambda: placeholder.plotly_chart(fig, use_container_width=True)

                except Exception as e:
                    error_msg = f"An error occurred: {e}"
                    result_action = lambda: placeholder.error(error_msg)
                
                finally:
                    duration = time.time() - start_time
                    if duration < MIN_DISPLAY_TIME_SEC:
                        time.sleep(MIN_DISPLAY_TIME_SEC - duration)
                    if result_action:
                        result_action()
        else:
            st.info("Add an account to use the Future Value Calculator.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<div class='footer'>© 2025 SecureBank </div>", unsafe_allow_html=True)

# --- LOGIN LOADER FUNCTION (Unchanged) ---
def perform_login_and_show_progress():
    username = st.session_state.login_username
    password = st.session_state.login_password
    st.markdown("""
        <div class="loader-container">
            <div class="loader"></div>
        </div>
    """, unsafe_allow_html=True)
    _, col_text, _ = st.columns([1, 2, 1])
    with col_text:
        loader_text_element = st.empty()
        loader_text_element.markdown("<h3 style='text-align: center;'>Logging in...</h3>", unsafe_allow_html=True)
    try:
        response = requests.post(f"{BACKEND_URL}/login", json={'username': username, 'password': password})
        if response.status_code != 200:
            st.session_state.login_error = response.json().get('error', 'Invalid username or password.')
            if 'login_attempt' in st.session_state: del st.session_state.login_attempt
            st.rerun()
            return
        loader_text_element.markdown("<h3 style='text-align: center;'>Verifying credentials...</h3>", unsafe_allow_html=True)
        response_data = response.json()
        st.session_state.logged_in = True
        st.session_state.username = response_data['username']
        st.session_state.jwt_token = response_data['token']
        loader_text_element.markdown("<h3 style='text-align: center;'>Fetching your accounts...</h3>", unsafe_allow_html=True)
        fetch_accounts()
        loader_text_element.markdown("<h3 style='text-align: center;'>Loading page...</h3>", unsafe_allow_html=True)
        time.sleep(1)
        if 'login_attempt' in st.session_state: del st.session_state.login_attempt
        if 'login_username' in st.session_state: del st.session_state.login_username
        if 'login_password' in st.session_state: del st.session_state.login_password
        st.rerun()
    except requests.exceptions.ConnectionError:
        st.session_state.login_error = "Connection failed. Is the backend running?"
        if 'login_attempt' in st.session_state: del st.session_state.login_attempt
        st.rerun()
    except Exception as e:
        st.session_state.login_error = f"An error occurred: {e}"
        if 'login_attempt' in st.session_state: del st.session_state.login_attempt
        st.rerun()

# --- AUTH VIEW (Unchanged) ---
def auth_view():
    st.title("Welcome to SecureBank")
    st.markdown("""
    <div class="empty-hero">
        <img src="https://cdn-icons-png.flaticon.com/512/3135/3135706.png" />
        <p>Experience secure, encrypted banking analytics powered by homomorphic encryption.</p>
    </div>
    """, unsafe_allow_html=True)
    if 'login_error' in st.session_state:
        st.sidebar.error(st.session_state.login_error)
        del st.session_state.login_error 
    choice = st.sidebar.selectbox("Menu", ["Login", "Register"])
    with st.sidebar.form(f"{choice.lower()}_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(choice)
        if submitted:
            if choice == "Register":
                try:
                    response = requests.post(f"{BACKEND_URL}/register", json={'username': username, 'password': password})
                    if response.status_code == 201:
                        st.sidebar.success("Registration successful! Please login.")
                    else:
                        st.sidebar.error(response.json().get('error', 'An unknown error occurred.'))
                except requests.exceptions.ConnectionError:
                    st.sidebar.error("Connection failed. Is the backend running?")
            elif choice == "Login":
                st.session_state.login_username = username
                st.session_state.login_password = password
                st.session_state.login_attempt = True
                st.rerun() 
                
# --- Controller (Unchanged) ---
init_session_state()

if st.session_state.get('login_attempt'):
    perform_login_and_show_progress()
elif st.session_state.get('logged_in'):
    main_app()
else:
    auth_view()