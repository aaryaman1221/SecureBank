from flask import Flask, request, jsonify
from phe import paillier
import json
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import decimal
import os
from dotenv import load_dotenv
import jwt
from functools import wraps
from cryptography.fernet import Fernet
import logging
import time
import yfinance as yf
import pandas as pd
from github_monitor import (
    answer_from_summaries,
    build_summary_query_result,
    enqueue_github_event,
    ensure_github_tables,
    fetch_recent_summaries,
    verify_github_signature,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
app = Flask(__name__)

# --- Configuration ---
DB_CONFIG = {
    'host': "localhost",
    'user': "root",
    'password': "Pass@#123",
    'database': "banking"
}
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

# Initialize the encryption suite
if ENCRYPTION_KEY:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
else:
    raise ValueError("ENCRYPTION_KEY not found in environment variables.")

# --- Helper Functions ---
def encrypt_data(data):
    if data is None: return None
    return cipher_suite.encrypt(str(data).encode()).decode()

def decrypt_data(encrypted_data):
    if encrypted_data is None: return None
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, paillier.PaillierPublicKey): return {'n': obj.n}
        if isinstance(obj, paillier.EncryptedNumber): return {'ciphertext': obj.ciphertext(be_secure=False)}
        if isinstance(obj, (date, datetime)): return obj.isoformat()
        if isinstance(obj, decimal.Decimal): return float(obj)
        return super().default(obj)
app.json_encoder = CustomEncoder

def deserialize_data(json_data):
    pub_key_data = json_data['public_key']
    public_key = paillier.PaillierPublicKey(n=int(pub_key_data['n']))
    encrypted_numbers_data = json_data['values']
    encrypted_numbers = [paillier.EncryptedNumber(public_key, int(x['ciphertext'])) for x in encrypted_numbers_data]
    return public_key, encrypted_numbers

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('authorization', ' ').split(" ")[-1]
        if not token: return jsonify({'error': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            conn = get_db(); cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE id = %s", (data['user_id'],))
            current_user = cursor.fetchone()
            cursor.close(); conn.close()
            if not current_user: return jsonify({'error': 'User not found!'}), 401
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': f'Token is invalid or expired: {str(e)}'}), 401
    return decorated

# --- Routes ---
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(); username, password = data.get('username'), data.get('password')
    if not username or not password: return jsonify({'error': 'Username and password are required'}), 400
    password_hash = generate_password_hash(password)
    conn = get_db(); cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
        conn.commit()
    except mysql.connector.IntegrityError: return jsonify({'error': 'Username already exists'}), 409
    finally: cursor.close(); conn.close()
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(); username, password = data.get('username'), data.get('password')
    conn = get_db(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close(); conn.close()
    if user and check_password_hash(user['password_hash'], password):
        token = jwt.encode({'user_id': user['id'], 'exp': datetime.utcnow() + timedelta(hours=24)}, JWT_SECRET_KEY, algorithm="HS256")
        return jsonify({'message': 'Login successful', 'token': token, 'username': user['username']})
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/accounts', methods=['GET', 'POST'])
@token_required
def handle_accounts(current_user):
    conn = get_db(); cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'GET':
            cursor.execute("SELECT id, account_name, balance FROM accounts WHERE user_id = %s", (current_user['id'],))
            accounts = cursor.fetchall()
            decrypted_accounts = [{'id': acc['id'], 'account_name': decrypt_data(acc['account_name']), 'balance': decrypt_data(acc['balance'])} for acc in accounts]
            return jsonify(decrypted_accounts)
        elif request.method == 'POST':
            data = request.get_json()
            cursor.execute("INSERT INTO accounts (user_id, account_name, balance) VALUES (%s, %s, %s)",
                           (current_user['id'], encrypt_data(data.get('account_name')), encrypt_data(data.get('balance'))))
            conn.commit()
            return jsonify({'message': 'Account added successfully'}), 201
    except Exception as e:
        app.logger.error(f"Error handling accounts: {e}"); conn.rollback()
        return jsonify({'error': 'Could not process account request.'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/accounts/<int:account_id>', methods=['PUT', 'DELETE'])
@token_required
def handle_single_account(current_user, account_id):
    conn = get_db(); cursor = conn.cursor()
    try:
        if request.method == 'PUT':
            data = request.get_json()
            cursor.execute("UPDATE accounts SET account_name = %s, balance = %s WHERE id = %s AND user_id = %s",
                           (encrypt_data(data.get('account_name')), encrypt_data(data.get('balance')), account_id, current_user['id']))
        elif request.method == 'DELETE':
            cursor.execute("DELETE FROM accounts WHERE id = %s AND user_id = %s", (account_id, current_user['id']))
        if cursor.rowcount == 0: return jsonify({'error': 'Account not found or no permission'}), 404
        conn.commit()
        return jsonify({'message': f'Account {("updated" if request.method == "PUT" else "deleted")} successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error with account {account_id}: {e}"); conn.rollback()
        return jsonify({'error': 'Could not process account request.'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/accounts/transfer', methods=['POST'])
@token_required
def transfer_funds(current_user):
    data = request.get_json()
    from_id, to_id, amount_str = data.get('from_account_id'), data.get('to_account_id'), data.get('amount')
    if not all([from_id, to_id, amount_str]): return jsonify({'error': 'Missing required fields.'}), 400
    amount = decimal.Decimal(amount_str)
    if from_id == to_id: return jsonify({'error': 'Cannot transfer to the same account.'}), 400
    if amount <= 0: return jsonify({'error': 'Transfer amount must be positive.'}), 400
    conn = get_db(); cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cursor.execute("SELECT id, balance FROM accounts WHERE id IN (%s, %s) AND user_id = %s FOR UPDATE", (from_id, to_id, current_user['id']))
        accounts = {acc['id']: acc for acc in cursor.fetchall()}
        if len(accounts) != 2:
            conn.rollback(); return jsonify({'error': 'One or both accounts not found.'}), 404
        from_balance = decimal.Decimal(decrypt_data(accounts[from_id]['balance']))
        if from_balance < amount:
            conn.rollback(); return jsonify({'error': 'Insufficient funds.'}), 400
        to_balance = decimal.Decimal(decrypt_data(accounts[to_id]['balance']))
        cursor.execute("UPDATE accounts SET balance = %s WHERE id = %s", (encrypt_data(from_balance - amount), from_id))
        cursor.execute("UPDATE accounts SET balance = %s WHERE id = %s", (encrypt_data(to_balance + amount), to_id))
        conn.commit()
        return jsonify({'message': 'Transfer successful.'}), 200
    except Exception as e:
        conn.rollback(); app.logger.error(f"Transfer error: {e}")
        return jsonify({'error': 'An error occurred during the transfer.'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/market_data', methods=['GET'])
@token_required
def get_market_data(current_user):
    try:
        live_prices = {'USD_INR': 83.50}
        assets = {'Bitcoin': 'BTC-USD', 'Gold': 'GLD', 'Nifty 50': 'NIFTYBEES.NS'}
        for name, symbol in assets.items():
            info = yf.Ticker(symbol).info
            price = info.get('regularMarketPrice') or info.get('previousClose')
            if not price: raise ValueError(f"Price not found for {name}")
            live_prices[name] = {'price': price, 'currency': ('USD' if symbol != 'NIFTYBEES.NS' else 'INR')}
        return jsonify(live_prices)
    except Exception as e:
        app.logger.error(f"yfinance error in /market_data: {e}", exc_info=True)
        return jsonify({'error': 'Server error fetching market data.'}), 500

@app.route('/historical_data', methods=['GET'])
@token_required
def get_historical_data(current_user):
    conn = get_db(); cursor = conn.cursor(dictionary=True)
    first_date, historical_prices = None, {}
    try:
        cursor.execute("SELECT MIN(purchase_date) as first_date FROM transactions WHERE user_id = %s", (current_user['id'],))
        result = cursor.fetchone()
        if result: first_date = result.get('first_date')
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
    if not first_date: return jsonify({})

    start_date = first_date.strftime('%Y-%m-%d')
    end_date = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    symbols = {'Bitcoin': 'BTC-USD', 'Gold': 'GLD', 'Nifty 50': 'NIFTYBEES.NS'}
    
    try:
        data = yf.download(list(symbols.values()), start=start_date, end=end_date, progress=False)
        if data.empty or 'Close' not in data:
            app.logger.error("yfinance download returned empty or invalid data.")
            return jsonify({})

        for asset_name, symbol in symbols.items():
            # For multiple tickers, yfinance nests columns. We access them like this:
            if ('Close', symbol) in data:
                price_series = data['Close'][symbol].dropna()
                if not price_series.empty:
                    historical_prices[asset_name] = {idx.strftime('%Y-%m-%d'): val for idx, val in price_series.items()}
    except Exception as e:
        app.logger.error(f"yfinance download failed: {e}")

    return jsonify(historical_prices)

@app.route('/transactions', methods=['GET', 'POST'])
@token_required
def handle_transactions(current_user):
    conn = get_db(); cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        if request.method == 'POST':
            data = request.get_json()
            cursor.execute("INSERT INTO transactions (user_id, asset_name, quantity, purchase_price, purchase_date) VALUES (%s, %s, %s, %s, %s)",
                           (current_user['id'], encrypt_data(data.get('asset_name')), encrypt_data(data.get('quantity')), encrypt_data(data.get('purchase_price')), data.get('purchase_date')))
            conn.commit()
            return jsonify({'message': 'Transaction added successfully'}), 201
        
        cursor.execute("SELECT id, asset_name, quantity, purchase_price, purchase_date FROM transactions WHERE user_id = %s ORDER BY purchase_date DESC", (current_user['id'],))
        transactions = cursor.fetchall()
        decrypted = [{'id': tx['id'], 'asset_name': decrypt_data(tx['asset_name']), 'quantity': decrypt_data(tx['quantity']), 'purchase_price': decrypt_data(tx['purchase_price']), 'purchase_date': tx['purchase_date']} for tx in transactions]
        return jsonify(decrypted)
    except Exception as e:
        app.logger.error(f"Error handling transactions: {e}"); conn.rollback()
        return jsonify({'error': 'Could not process transaction.'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/transactions/<int:transaction_id>', methods=['DELETE'])
@token_required
def delete_transaction(current_user, transaction_id):
    conn = get_db(); cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM transactions WHERE id = %s AND user_id = %s", (transaction_id, current_user['id']))
        if cursor.rowcount == 0: return jsonify({'error': 'Transaction not found'}), 404
        conn.commit()
        return jsonify({'message': 'Transaction deleted successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error deleting transaction {transaction_id}: {e}"); conn.rollback()
        return jsonify({'error': 'Could not delete transaction.'}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route('/compute', methods=['POST'])
@token_required
def compute(current_user):
    try:
        json_data = request.get_json()
        public_key, encrypted_numbers = deserialize_data(json_data)
        if not encrypted_numbers: return jsonify({'error': 'No encrypted values provided'}), 400
        encrypted_result = sum(encrypted_numbers)
        serialized_result = json.dumps({'result': encrypted_result}, cls=CustomEncoder)
        return serialized_result, 200, {'Content-Type': 'application/json'}
    except Exception as e:
        app.logger.error(f"Homomorphic computation error: {e}")
        return jsonify({'error': f'Computation error: {e}'}), 400

@app.route('/webhooks/github', methods=['POST'])
def github_webhook():
    raw_body = request.get_data()
    delivery_id = request.headers.get('X-GitHub-Delivery', str(int(time.time() * 1000)))
    event_type = request.headers.get('X-GitHub-Event', 'unknown')
    secret = os.getenv('GITHUB_WEBHOOK_SECRET')

    if not verify_github_signature(raw_body, request.headers.get('X-Hub-Signature-256'), secret):
        return jsonify({'error': 'Invalid GitHub signature'}), 401

    payload = request.get_json(silent=True) or {}
    if event_type not in {'push', 'pull_request'}:
        return jsonify({'message': f'Ignored event type: {event_type}'}), 200

    enqueue_github_event(get_db, payload, event_type, delivery_id)
    return jsonify({'message': 'Webhook received and queued for processing', 'delivery_id': delivery_id}), 202


@app.route('/github/summaries', methods=['GET'])
def github_summaries():
    repo = request.args.get('repo')
    keyword = request.args.get('q')
    limit = min(int(request.args.get('limit', 10)), 50)
    summaries = fetch_recent_summaries(get_db, repository_full_name=repo, limit=limit, keyword=keyword)
    return jsonify(summaries), 200


@app.route('/github/chat', methods=['POST'])
def github_chat():
    body = request.get_json(silent=True) or {}
    question = (body.get('question') or '').strip()
    repo = body.get('repo')
    limit = min(int(body.get('limit', 8)), 20)

    if not question:
        return jsonify({'error': 'question is required'}), 400

    summaries = fetch_recent_summaries(get_db, repository_full_name=repo, limit=limit, keyword=body.get('keyword'))
    ranked = build_summary_query_result(question, summaries)
    answer = answer_from_summaries(question, ranked[:limit])
    return jsonify({'question': question, 'answer': answer, 'matches': ranked[:limit]}), 200


ensure_github_tables(get_db)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
