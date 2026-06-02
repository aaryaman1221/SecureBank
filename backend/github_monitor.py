import hashlib
import hmac
import json
import logging
import os
import re
import threading
from datetime import datetime

import mysql.connector
import requests

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
IGNORED_FILENAMES = {
    ".ds_store",
    "cargo.lock",
    "gemfile.lock",
    "package-lock.json",
    "poetry.lock",
    "pnpm-lock.yaml",
    "yarn.lock",
}
IGNORED_SUFFIXES = (
    ".bin",
    ".dll",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".lock",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".so",
    ".svg",
    ".tar",
    ".tgz",
    ".ttf",
    ".woff",
    ".woff2",
    ".zip",
)


def ensure_github_tables(get_db):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS github_events (
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
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS github_summaries (
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
            """
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def verify_github_signature(raw_body, signature_header, secret):
    if not secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.split("=", 1)[1])


def _github_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _is_noise_file(filename):
    name = filename.lower().rsplit("/", 1)[-1]
    if name in IGNORED_FILENAMES:
        return True
    return any(name.endswith(suffix) for suffix in IGNORED_SUFFIXES)


def _truncate(text, limit=5000):
    if not text:
        return ""
    return text if len(text) <= limit else f"{text[:limit]}\n... [truncated]"


def _fetch_json(url, params=None):
    response = requests.get(url, headers=_github_headers(), params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_commit_files(repo_full_name, sha):
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/commits/{sha}"
    payload = _fetch_json(url)
    files = payload.get("files", []) or []
    return payload, files


def fetch_pull_request_files(repo_full_name, pr_number):
    all_files = []
    page = 1
    while True:
        url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/pulls/{pr_number}/files"
        files = _fetch_json(url, params={"per_page": 100, "page": page})
        if not files:
            break
        all_files.extend(files)
        if len(files) < 100:
            break
        page += 1
    return all_files


def build_compact_diff(files, max_files=12):
    filtered = []
    for item in files:
        filename = item.get("filename") or item.get("path") or "unknown"
        if _is_noise_file(filename):
            continue
        patch = item.get("patch")
        if not patch:
            continue
        filtered.append(
            {
                "filename": filename,
                "status": item.get("status", "modified"),
                "additions": item.get("additions", 0),
                "deletions": item.get("deletions", 0),
                "changes": item.get("changes", 0),
                "patch": _truncate(patch, 4000),
            }
        )

    filtered.sort(key=lambda x: x.get("changes", 0), reverse=True)
    return filtered[:max_files]


def render_diff_text(files):
    sections = []
    for item in files:
        sections.append(
            "\n".join(
                [
                    f"File: {item['filename']}",
                    f"Status: {item.get('status', 'modified')}",
                    f"Additions: {item.get('additions', 0)}",
                    f"Deletions: {item.get('deletions', 0)}",
                    "Patch:",
                    item.get("patch", ""),
                ]
            )
        )
    return "\n\n".join(sections)


def _llm_client_config():
    api_key = os.getenv("LLM_API_KEY") 
    model = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    return api_key, model


def summarize_with_llm(repo_full_name, event_type, actor_login, meta, compact_files, raw_diff):
    api_key, model = _llm_client_config()
    
    file_overview = "\n".join(
        [
            f"- {item['filename']} ({item.get('status', 'modified')} | +{item.get('additions', 0)} / -{item.get('deletions', 0)})"
            for item in compact_files
        ]
    ) or "- No text patches were available."

    user_prompt = f"""
Repository: {repo_full_name}
Event: {event_type}
Actor: {actor_login or 'unknown'}
Metadata: {json.dumps(meta, ensure_ascii=True, default=str)}

Files changed:
{file_overview}

Diff:
{_truncate(raw_diff, 20000)}
"""

    if not api_key:
        return heuristic_summary(repo_full_name, event_type, compact_files, meta)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "systemInstruction": {
            "parts": [{"text": "You are an expert senior developer reviewing code changes. Explain what changed and why it matters in plain English. Do not recite code lines. Focus on behavior, architecture, bug fixes, and risks. Keep it to at most 3 short paragraphs."}]
        },
        "contents": [{
            "parts": [{"text": user_prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 600
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Parse Gemini's JSON structure
        generated_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
        
        return generated_text or heuristic_summary(repo_full_name, event_type, compact_files, meta)
        
    except Exception as exc:
        logger.exception("LLM summary failed: %s", exc)
        return heuristic_summary(repo_full_name, event_type, compact_files, meta)


def heuristic_summary(repo_full_name, event_type, compact_files, meta):
    if not compact_files:
        return f"{event_type.title()} event in {repo_full_name}. GitHub did not provide text patches for this change."

    parts = []
    for item in compact_files[:5]:
        filename = item["filename"]
        status = item.get("status", "modified")
        additions = item.get("additions", 0)
        deletions = item.get("deletions", 0)
        parts.append(f"{filename} ({status}, +{additions}/-{deletions})")

    extra = ""
    if len(compact_files) > 5:
        extra = f" and {len(compact_files) - 5} more file(s)"

    action = meta.get("action")
    action_part = f" action={action}" if action else ""
    return (
        f"{event_type.title()} event in {repo_full_name}{action_part}. "
        f"Key files touched: {', '.join(parts)}{extra}. "
        "This likely changes behavior in the listed areas and should be reviewed for impact and regressions."
    )


def persist_event(get_db, delivery_id, event_type, payload, summary_record=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        repository = payload.get("repository") or {}
        repo_full_name = repository.get("full_name") or "unknown/unknown"
        actor_login = (payload.get("sender") or {}).get("login")
        commit_sha = payload.get("after") or ((payload.get("pull_request") or {}).get("head") or {}).get("sha")
        pr_number = (payload.get("pull_request") or {}).get("number")
        source_url = repository.get("html_url")
        cursor.execute(
            """
            INSERT INTO github_events
            (delivery_id, event_type, repository_full_name, actor_login, commit_sha, pr_number, source_url, payload_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                event_type = VALUES(event_type),
                repository_full_name = VALUES(repository_full_name),
                actor_login = VALUES(actor_login),
                commit_sha = VALUES(commit_sha),
                pr_number = VALUES(pr_number),
                source_url = VALUES(source_url),
                payload_json = VALUES(payload_json)
            """,
            (
                delivery_id,
                event_type,
                repo_full_name,
                actor_login,
                commit_sha,
                pr_number,
                source_url,
                json.dumps(payload, default=str),
            ),
        )

        if summary_record:
            cursor.execute(
                """
                INSERT INTO github_summaries
                (delivery_id, event_type, repository_full_name, actor_login, commit_sha, pr_number, source_url, summary_text, diff_text, files_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    delivery_id,
                    event_type,
                    repo_full_name,
                    actor_login,
                    commit_sha,
                    pr_number,
                    source_url,
                    summary_record["summary_text"],
                    summary_record.get("diff_text"),
                    summary_record.get("files_json"),
                ),
            )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def process_github_event(get_db, payload, event_type, delivery_id):
    repository = payload.get("repository") or {}
    repo_full_name = repository.get("full_name")
    if not repo_full_name:
        raise ValueError("Missing repository.full_name in webhook payload")

    actor_login = (payload.get("sender") or {}).get("login")
    meta = {
        "delivery_id": delivery_id,
        "event_type": event_type,
        "action": payload.get("action"),
        "head_commit": payload.get("head_commit", {}),
        "ref": payload.get("ref"),
        "before": payload.get("before"),
        "after": payload.get("after"),
    }

    if event_type == "pull_request":
        pr = payload.get("pull_request") or {}
        pr_number = pr.get("number")
        if not pr_number:
            raise ValueError("Missing pull_request.number in webhook payload")
        files = fetch_pull_request_files(repo_full_name, pr_number)
        commit_sha = ((pr.get("head") or {}).get("sha")) or payload.get("after")
        source_url = pr.get("html_url") or repository.get("html_url")
    else:
        commit_sha = payload.get("after")
        if not commit_sha:
            raise ValueError("Missing commit SHA in webhook payload")
        commit_payload, files = fetch_commit_files(repo_full_name, commit_sha)
        meta["commit_message"] = (commit_payload.get("commit") or {}).get("message")
        source_url = (commit_payload.get("html_url")) or repository.get("html_url")
        pr_number = None

    compact_files = build_compact_diff(files)
    raw_diff = render_diff_text(compact_files)
    summary_text = summarize_with_llm(repo_full_name, event_type, actor_login, meta, compact_files, raw_diff)
    summary_record = {
        "summary_text": summary_text,
        "diff_text": raw_diff,
        "files_json": json.dumps(compact_files, ensure_ascii=True, default=str),
    }

    persist_event(get_db, delivery_id, event_type, payload, summary_record)
    return {
        "repository_full_name": repo_full_name,
        "commit_sha": commit_sha,
        "pr_number": pr_number,
        "summary_text": summary_text,
        "source_url": source_url,
    }


def enqueue_github_event(get_db, payload, event_type, delivery_id):
    worker = threading.Thread(
        target=_run_github_event_worker,
        args=(get_db, payload, event_type, delivery_id),
        daemon=True,
    )
    worker.start()


def _run_github_event_worker(get_db, payload, event_type, delivery_id):
    try:
        process_github_event(get_db, payload, event_type, delivery_id)
        logger.info("Processed GitHub event %s (%s)", delivery_id, event_type)
    except mysql.connector.Error:
        logger.exception("Database error while processing GitHub event %s", delivery_id)
    except Exception as exc:
        logger.exception("GitHub event processing failed for %s: %s", delivery_id, exc)


def fetch_recent_summaries(get_db, repository_full_name=None, limit=10, keyword=None):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT delivery_id, event_type, repository_full_name, actor_login, commit_sha, pr_number,
                   source_url, summary_text, diff_text, files_json, created_at
            FROM github_summaries
        """
        clauses = []
        params = []

        if repository_full_name:
            clauses.append("repository_full_name = %s")
            params.append(repository_full_name)

        if keyword:
            keyword_like = f"%{keyword}%"
            clauses.append("(summary_text LIKE %s OR diff_text LIKE %s OR files_json LIKE %s OR commit_sha LIKE %s)")
            params.extend([keyword_like, keyword_like, keyword_like, keyword_like])

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def answer_from_summaries(question, summaries):
    api_key, model = _llm_client_config()
    
    condensed_context = "\n\n".join(
        [
            f"Repo: {item['repository_full_name']}\n"
            f"Event: {item['event_type']}\n"
            f"Commit: {item.get('commit_sha')}\n"
            f"Summary: {item['summary_text']}\n"
            f"Time: {item.get('created_at')}"
            for item in summaries
        ]
    )

    if not api_key:
        if not summaries:
            return "No stored GitHub change summaries match that query yet."
        top = summaries[0]
        return (
            f"I found {len(summaries)} relevant change summary(ies). "
            f"The most recent one is for {top['repository_full_name']} ({top['event_type']}): {top['summary_text']}"
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "systemInstruction": {
            "parts": [{"text": "You are a helpful engineering assistant. Answer the user's question using only the provided GitHub change summaries. If the context is insufficient, say what is missing and mention the most relevant summaries."}]
        },
        "contents": [{
            "parts": [{"text": f"Question: {question}\n\nRelevant change summaries:\n{condensed_context}"}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 500
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Parse Gemini's JSON structure
        generated_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
        
        return generated_text or "I could not generate an answer from the stored summaries."
        
    except Exception as exc:
        logger.exception("LLM chat answer failed: %s", exc)
        return "I could not generate an answer from the stored summaries."


def extract_search_term(question):
    words = re.findall(r"[A-Za-z0-9_./-]+", question.lower())
    filtered = [word for word in words if len(word) > 2 and word not in {"what", "when", "where", "why", "how", "did", "the", "and", "for", "from", "with", "this", "that", "changed"}]
    return filtered[0] if filtered else None


def build_summary_query_result(question, summaries):
    keyword = extract_search_term(question)
    if keyword:
        scored = []
        for item in summaries:
            haystack = " ".join(
                [
                    str(item.get("repository_full_name", "")),
                    str(item.get("event_type", "")),
                    str(item.get("commit_sha", "")),
                    str(item.get("summary_text", "")),
                    str(item.get("diff_text", "")),
                    str(item.get("files_json", "")),
                ]
            ).lower()
            score = haystack.count(keyword.lower())
            if score:
                scored.append((score, item))
        if scored:
            scored.sort(key=lambda pair: pair[0], reverse=True)
            return [item for _, item in scored]
    return summaries