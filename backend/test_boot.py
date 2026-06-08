import os
import logging
import mysql.connector
from dotenv import load_dotenv

# Force terminal logs
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Manually load your .env file
load_dotenv()

from github_monitor import bootstrap_repo

# Define an isolated DB connector just for this test
def get_test_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "banking")
    )

print("Starting manual foreground bootstrap...")

# Run the bootstrap using our isolated DB connector
bootstrap_repo(get_test_db, "aaryaman1221/SecureBank")

print("Finished!")