import time
from github_chatbot import get_db
from github_monitor import bootstrap_repo

repo_name = "aaryaman1221/SecureBank"
print(f"🚀 Forcing manual bootstrap for {repo_name}...")

# Calling the synchronous version so the script doesn't exit before it finishes
bootstrap_repo(get_db, repo_name)

print("✅ Complete! You can now refresh your Streamlit app.")