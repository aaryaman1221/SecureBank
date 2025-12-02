import mysql.connector
from mysql.connector import errorcode

try:
    # Connect to the MySQL server (without specifying a database)
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="YOUR_DB_PASSWORD"
    )
    cursor = conn.cursor()

    # Try to create the database
    try:
        cursor.execute("CREATE DATABASE banking")
        print("Database 'banking' created.")
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_DB_CREATE_EXISTS:
            # Database already exists, which is fine
            pass
        else:
            # Some other error
            raise err

    # Now, tell the connection to use the 'banking' database
    cursor.execute("USE banking")

    # --- The rest of your script is the same ---

    # Drop existing tables to ensure a clean slate
    print("Dropping old tables (if they exist)...")
    cursor.execute('DROP TABLE IF EXISTS transactions')
    cursor.execute('DROP TABLE IF EXISTS investments') #This is a leftover from our previous attempt, good to keep for cleanup
    cursor.execute('DROP TABLE IF EXISTS accounts')
    cursor.execute('DROP TABLE IF EXISTS users')

    # Create the 'users' table
    print("Creating table 'users'...")
    cursor.execute('''
    CREATE TABLE users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL
    )
    ''')

    # Create the 'accounts' table
    print("Creating table 'accounts'...")
    cursor.execute('''
    CREATE TABLE accounts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        account_name VARCHAR(512) NOT NULL, -- Changed for encryption
        balance VARCHAR(512) NOT NULL,      -- Changed for encryption
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    # Create the 'transactions' table
    print("Creating table 'transactions'...")
    cursor.execute('''
    CREATE TABLE transactions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        asset_name VARCHAR(512) NOT NULL,      -- Changed for encryption
        quantity VARCHAR(512) NOT NULL,        -- Changed for encryption
        purchase_price VARCHAR(512) NOT NULL,  -- Changed for encryption
        purchase_date DATE NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    print("\nDatabase and tables re-created successfully with encryption-ready schema.")

    conn.commit()

except mysql.connector.Error as err:
    print(f"Failed to initialize database: {err}")

finally:
    # Ensure resources are closed
    if 'cursor' in locals() and cursor:
        cursor.close()
    if 'conn' in locals() and conn:
        conn.close()