# Save this as rebuild_db.py and run: python3.11 rebuild_db.py
import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Pass@#123",
        database="banking2"
    )
    cursor = conn.cursor()

    print("Cleaning up old tables...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("DROP TABLE IF EXISTS transactions")
    cursor.execute("DROP TABLE IF EXISTS accounts")
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    print("Creating 'users' table...")
    cursor.execute('''
    CREATE TABLE users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL
    )
    ''')

    print("Creating 'accounts' table...")
    cursor.execute('''
    CREATE TABLE accounts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        account_name VARCHAR(512) NOT NULL,
        balance VARCHAR(512) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    print("Creating 'transactions' table...")
    cursor.execute('''
    CREATE TABLE transactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        asset_name VARCHAR(512) NOT NULL,
        quantity VARCHAR(512) NOT NULL,
        purchase_price VARCHAR(512) NOT NULL,
        purchase_date DATE NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    conn.commit()
    print("✅ Database tables created successfully!")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'conn' in locals(): conn.close()