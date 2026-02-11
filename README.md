# SecureBank: End-to-End Secure Financial Dashboard

SecureBank is a full-stack financial application developed as an **Information Security (IS) Lab Project**. It demonstrates the practical application of modern cryptographic techniques to protect sensitive banking data.

# Pictures:
<img width="1470" height="956" alt="Screenshot 2026-02-10 at 9 24 05 PM" src="https://github.com/user-attachments/assets/4ed0f6a6-aaac-4176-966c-475e3edaf90e" />

## 🔒 Key Security Implementations

### 1. Homomorphic Encryption (Paillier)
The system implements **Paillier Additive Homomorphic Encryption** for privacy-preserving computations.
* **Functionality**: The `/compute` endpoint allows the server to sum encrypted balances without ever decrypting them, ensuring the server never sees raw financial data.
* **Implementation**: Utilizes the `phe` library to manage public/private key pairs and encrypted number objects.

### 2. Symmetric Data-at-Rest Encryption (Fernet)
All sensitive database fields, including `account_name`, `balance`, and `asset_name`, are encrypted using **Fernet (AES-128 in CBC mode)** before storage.
* **Key Management**: Encryption keys are loaded via environment variables to prevent source code leaks.

### 3. Secure Authentication & Session Management
* **Password Security**: Implements PBKDF2 hashing with unique salts for every user.
* **JWT Authorization**: Protects API routes using **JSON Web Tokens (HS256)**, ensuring only authenticated users can access their private financial data.



---

## 🛠 Tech Stack
* **Backend**: Python 3.10+ / Flask
* **Frontend**: Streamlit / Plotly
* **Database**: MySQL
* **API**: Yahoo Finance (`yfinance`) for real-time market tracking

---

## 🚀 Installation & Setup

### Prerequisites
* **Python 3.10+**: Crucial for modern type-hinting support used in `yfinance` and backend classes.
* **MySQL**: A running instance of MySQL server.

### Local Setup
1. **Clone the repository**:
   ```bash
   git clone [https://github.com/aaryaman2112/Secure_Vault.git](https://github.com/aaryaman2112/Secure_Vault.git)
   cd Secure_Vault
2. **Set up Environment Variables: Create a .env file in the root directory**:
   ```bash
   JWT_SECRET_KEY=your_random_secret_string
    ENCRYPTION_KEY=your_generated_fernet_key
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
4. **Initialize Database**:
   ```bash
   python backend/database.py
5. **Run the application**:
   ```bash
   Start Backend: python backend/app.py
   Start Frontend: streamlit run frontend/dashboard.py

   


