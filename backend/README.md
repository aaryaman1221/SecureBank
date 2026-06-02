# 🏦 SecureBank: A Full-Stack Personal Finance Dashboard

A secure, full-stack web application for managing personal finances, featuring a privacy-preserving analytics tool built with homomorphic encryption. This project was developed as part of an Information Security course.

**![SecureBank Dashboard](./assets/dashboard-screenshot.png)**

## ✨ Features

- [x] **User Authentication:** Secure user registration and login system.
- [x] **Account Management:** Add, edit, delete, and view bank accounts.
- [x] **Fund Transfers:** Atomically transfer funds between user-owned accounts.
- [x] **Investment Tracking:** Log and track investments in Bitcoin, Gold, and Nifty 50.
- [x] **Live Market Data:** Real-time price updates for all tracked assets.
- [x] **Portfolio Visualization:** A dynamic graph and pie chart showing portfolio value and allocation.
- [x] **Future Value Calculator:** Project the future growth of an account balance.

## 🛡️ Security Features

This application was built with security as a primary focus:

- **JWT Authentication:** All API endpoints are protected, ensuring only authenticated users can access their data.
- **AES Database Encryption:** All sensitive user data (account names, balances, transactions) is encrypted at rest in the database.
- **Password Hashing:** User passwords are never stored directly. They are securely hashed using `werkzeug.security`.
- **Homomorphic Encryption:** The "Privacy-Preserving Analytics" feature uses the Paillier cryptosystem to calculate the sum/average of account balances on the server *without ever decrypting the data*, ensuring user privacy.

## 🛠️ Tech Stack

- **Backend:** Flask, Python, MySQL
- **Frontend:** Streamlit
- **Security:** PyJWT, python-dotenv, cryptography (for AES), phe (for Paillier)
- **Data:** yfinance

## 🚀 How to Run Locally

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/OppositeExpert/secure-bank-dashboard.git
    cd secure-bank-dashboard
    ```
2.  **Set up the environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
    

3.  **Set up the database:**
    - Make sure you have MySQL running.
    - Run the `database.py` script to create the tables: `python3 backend/database.py`

4.  **Configure environment variables:**
    - In the `backend/` folder, create a `.env` file and add your secret keys (database password, JWT secret, AES key).

5.  **Run the servers:**
    - In one terminal, run the backends: `python3 backend/app.py`
    - In another terminal, run the frontend: `streamlit run frontend/dashboard.py`