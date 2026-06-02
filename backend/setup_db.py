# Save this as rebuild_db.py and run: python3.11 rebuild_db.py
import mysql.connector

from mysql.connector import errorcode

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Pass@#123"
    )
    cursor = conn.cursor()

    try:
        cursor.execute("CREATE DATABASE banking2")
        print("Database 'banking2' created.")
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_DB_CREATE_EXISTS:
            pass
        else:
            raise err

    cursor.execute("USE banking2")

    print("Cleaning up old tables...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("DROP TABLE IF EXISTS transactions")
    cursor.execute("DROP TABLE IF EXISTS github_summaries")
    cursor.execute("DROP TABLE IF EXISTS github_events")
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

    print("Creating 'github_events' table...")
    cursor.execute('''
    CREATE TABLE github_events (
        id INT AUTO_INCREMENT PRIMARY KEY,
        delivery_id VARCHAR(255) UNIQUE,
        event_type VARCHAR(64) NOT NULL,
        repository_full_name VARCHAR(255) NOT NULL,
        actor_login VARCHAR(255),
        commit_sha VARCHAR(128),
        pr_number INT,
        source_url VARCHAR(1024),
        payload_json LONGTEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    print("Creating 'github_summaries' table...")
    cursor.execute('''
    CREATE TABLE github_summaries (
        id INT AUTO_INCREMENT PRIMARY KEY,
        delivery_id VARCHAR(255),
        event_type VARCHAR(64) NOT NULL,
        repository_full_name VARCHAR(255) NOT NULL,
        actor_login VARCHAR(255),
        commit_sha VARCHAR(128),
        pr_number INT,
        source_url VARCHAR(1024),
        summary_text LONGTEXT NOT NULL,
        diff_text LONGTEXT,
        files_json LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    print("✅ Database tables created successfully!")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    if 'conn' in locals(): conn.close()
