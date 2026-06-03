"""
github_chatbot.py
-----------------
Standalone Streamlit chatbot for querying GitHub change summaries
across one or more repositories.

Run:
    streamlit run github_chatbot.py

Environment variables (same as github_monitor.py):
    LLM_API_KEY       – OpenAI-compatible API key
    LLM_API_BASE_URL  – defaults to https://api.openai.com/v1
    LLM_MODEL         – defaults to gpt-4o-mini
    DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME
                      – MySQL connection for github_summaries table
"""

import os
import streamlit as st

# st.set_page_config MUST be the first Streamlit call
st.set_page_config(
    page_title="GitHub Chatbot",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Load .env file automatically so you don't need to export vars manually
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass  # python-dotenv not installed; shell env vars will be used instead

# ---------------------------------------------------------------------------
# Safe imports – show a friendly error if github_monitor is missing
# ---------------------------------------------------------------------------
try:
    import mysql.connector
    from github_monitor import (
        answer_from_summaries,
        build_summary_query_result,
        ensure_github_tables,
        fetch_recent_summaries,
        extract_search_term,
        get_commits_from_graph,
        fetch_summaries_by_commits
    )
    IMPORT_OK = True
except ImportError as _ie:
    IMPORT_OK = False
    IMPORT_ERROR = str(_ie)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
.repo-pill {
    display: inline-block;
    background: #0d1117;
    color: #58a6ff;
    border: 1px solid #30363d;
    border-radius: 2em;
    padding: 2px 12px;
    font-size: 0.82rem;
    margin: 2px 2px;
}
.bubble-user {
    background: #1f6feb22;
    border-left: 3px solid #1f6feb;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 6px 0;
}
.bubble-bot {
    background: #23863622;
    border-left: 3px solid #238636;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 6px 0;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Guard: show error page if imports failed
# ---------------------------------------------------------------------------
if not IMPORT_OK:
    st.error("Missing dependency")
    st.code(f"ImportError: {IMPORT_ERROR}")
    st.info("Make sure `github_monitor.py` and its dependencies are in the same directory.")
    st.stop()

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _db_config():
    return {
        "host":     os.getenv("DB_HOST", "localhost"),
        "port":     int(os.getenv("DB_PORT", 3306)),
        "user":     os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "Pass@#123"),
        "database": os.getenv("DB_NAME", "banking"),
    }

def get_db():
    return mysql.connector.connect(**_db_config())

def try_init_tables():
    """Returns (True, None) on success or (False, error_str) on failure."""
    try:
        ensure_github_tables(get_db)
        return True, None
    except Exception as exc:
        return False, str(exc)

def get_known_repositories():
    """Returns list of distinct repo names, or empty list on DB error."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT repository_full_name "
            "FROM github_summaries ORDER BY repository_full_name"
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def _init_state():
    defaults = {
        "messages": [],
        "selected_repos": [],
        "result_limit": 20,
        "db_ok": None,
        "db_error": "",
        "known_repos": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("GitHub Repository Chatbot")
st.caption("Ask questions about commits and pull requests across your repositories.")
st.divider()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    if st.session_state.db_ok is None:
        ok, err = try_init_tables()
        st.session_state.db_ok = ok
        st.session_state.db_error = err or ""

    if st.session_state.db_ok:
        st.success("Database connected")
    else:
        st.error("Database error")
        st.caption(st.session_state.db_error)
        st.info("Set DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME and restart the app.")

    st.divider()
    st.subheader("Repositories")

    if st.session_state.known_repos is None:
        st.session_state.known_repos = get_known_repositories()

    known_repos = st.session_state.known_repos

    if st.button("Refresh list", use_container_width=True):
        st.session_state.known_repos = get_known_repositories()
        st.rerun()

    if not known_repos:
        st.info("No repositories found yet.\nWebhook events will appear here once received.")
        selected_repos = []
    else:
        all_selected = st.checkbox("All repositories", value=True, key="all_repos_cb")
        if all_selected:
            selected_repos = []
            for repo in known_repos:
                st.markdown(f'<span class="repo-pill">📦 {repo}</span>', unsafe_allow_html=True)
        else:
            selected_repos = st.multiselect(
                "Select repositories",
                options=known_repos,
                default=known_repos[:1],
                label_visibility="collapsed",
            )

    st.session_state.selected_repos = selected_repos

    st.divider()
    st.subheader("Context Depth")
    st.session_state.result_limit = st.slider(
        "Max summaries fetched per answer",
        min_value=5,
        max_value=50,
        value=st.session_state.result_limit,
        step=5,
    )

    st.divider()
    if st.button("Clear chat history", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    with st.expander("About"):
        st.markdown(
            """
**GitHub Chatbot** reads AI-generated summaries of commits and pull requests
stored by the `github_monitor` webhook.

**Env vars:**
- `LLM_API_KEY` – LLM API key
- `LLM_API_BASE_URL` – API base URL
- `LLM_MODEL` – model name
- `DB_*` – MySQL connection
"""
        )

# ---------------------------------------------------------------------------
# Chat display
# ---------------------------------------------------------------------------
if not st.session_state.messages:
    st.info(
        "**Ask me anything about your repository changes**, e.g.\n\n"
        "- *What changed in the last push to main?*\n"
        "- *Were there any bug fixes this week?*\n"
        "- *Who modified the authentication code?*\n"
        "- *What commit added the react module?*"
    )
else:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="bubble-user"> {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="bubble-bot"> {msg["content"]}</div>', unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# Input bar (Graph RAG Logic)
# ---------------------------------------------------------------------------
with st.form("chat_form", clear_on_submit=True):
    cols = st.columns([8, 1])
    question = cols[0].text_input(
        "question",
        placeholder="e.g. What files changed in the last commit?",
        label_visibility="collapsed",
    )
    submitted = cols[1].form_submit_button("Send", use_container_width=True)

if submitted and question.strip():
    if not st.session_state.db_ok:
        st.error("Cannot query — database is not connected. Check sidebar for details.")
        st.stop()

    user_q = question.strip()
    st.session_state.messages.append({"role": "user", "content": user_q})

    with st.spinner("Searching graph and generating answer…"):
        try:
            repos_to_query = st.session_state.selected_repos
            limit = st.session_state.result_limit
            
            # 1. Figure out what the user is asking about
            search_keyword = extract_search_term(user_q)
            all_summaries = []
            
            # 2. Try the Knowledge Graph First
            if search_keyword:
                st.toast(f"🔍 Searching graph for: {search_keyword}")
                targeted_commits = get_commits_from_graph(search_keyword, max_hops=1)
                
                if targeted_commits:
                    st.toast(f"🎯 Graph found {len(targeted_commits)} relevant commits!")
                    all_summaries = fetch_summaries_by_commits(get_db, targeted_commits)
            
            # 3. Fallback to basic DB search if graph finds nothing
            if not all_summaries:
                st.toast("⚠️ No graph connections found. Falling back to recent history.")
                if repos_to_query:
                    for repo in repos_to_query:
                        all_summaries.extend(fetch_recent_summaries(get_db, repo, limit))
                else:
                    all_summaries = fetch_recent_summaries(get_db, limit=limit)
                    
            # 4. Cap results to save LLM tokens and rank them
            all_summaries = all_summaries[:limit]
            ranked = build_summary_query_result(user_q, all_summaries)
            
            # 5. Generate final AI Answer
            answer = answer_from_summaries(user_q, ranked)

        except Exception as exc:
            answer = f"⚠️ Error while fetching answer: {exc}"

    st.session_state.messages.append({"role": "bot", "content": answer})
    st.rerun()