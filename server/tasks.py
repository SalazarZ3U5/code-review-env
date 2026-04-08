from models import CodeReviewAction


TASKS = {
    "easy": {
        "name": "easy",
        "difficulty": "easy",
        "description": (
            "Review this Flask route and identify any bugs. Report the exact "
            "line number(s) of each bug, explain why it is a bug, and suggest a "
            "corrected version of the code."
        ),
        "code_snippet": """from flask import Flask, jsonify
app = Flask(__name__)

users = {
    1: {"name": "Alice", "email": "alice@example.com"},
    2: {"name": "Bob",   "email": "bob@example.com"},
}

@app.route("/user/<int:user_id>")
def get_user(user_id):
    user = users[user_id]        # BUG: KeyError if user_id missing
    return jsonify(user)""",
        "answer_key": {
            "bug_lines": [11],
            "fix_keywords": ["users.get", ".get(user_id)", "404", "not found"],
            "explanation_keywords": [
                "keyerror",
                "key error",
                "does not exist",
                "missing key",
                "crash",
                "exception",
            ],
        },
    },
    "medium": {
        "name": "medium",
        "difficulty": "medium",
        "description": (
            "Review this Flask login route and identify any security "
            "vulnerabilities. Report the exact line number(s), explain the attack "
            "vector, and suggest a secure corrected version."
        ),
        "code_snippet": """from flask import Flask, request
import sqlite3
app = Flask(__name__)

def get_db():
    return sqlite3.connect("app.db")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    db = get_db()
    cursor = db.cursor()
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"  # BUG: SQL injection
    cursor.execute(query)
    user = cursor.fetchone()
    if user:
        return "Login successful"
    return "Invalid credentials"
""",
        "answer_key": {
            "bug_lines": [14],
            "fix_keywords": [
                "parameterized",
                "placeholder",
                "cursor.execute(",
                "?, (username",
                "?, (",
                "prepared statement",
            ],
            "explanation_keywords": [
                "sql injection",
                "injection",
                "interpolat",
                "f-string",
                "user input",
                "unsanitized",
                "bypass",
                "or '1'='1",
            ],
        },
    },
    "hard": {
        "name": "hard",
        "difficulty": "hard",
        "description": (
            "Review this Flask password reset route carefully. It contains more "
            "than one bug. Identify ALL bug line numbers, explain why each is "
            "dangerous, and suggest fixes for each. Consider how the bugs "
            "interact with each other."
        ),
        "code_snippet": """from flask import Flask, request, jsonify
import sqlite3, hashlib, os
app = Flask(__name__)

def get_db():
    return sqlite3.connect("app.db")

@app.route("/reset-password", methods=["POST"])
def reset_password():
    token    = request.json["token"]
    new_pass = request.json["new_password"]
    db       = get_db()
    cursor   = db.cursor()
    cursor.execute(f"SELECT user_id FROM reset_tokens WHERE token='{token}'")  # BUG 1: SQL injection
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Invalid token"}), 400
    user_id = row[0]
    hashed  = hashlib.md5(new_pass.encode()).hexdigest()   # BUG 2: MD5 is broken
    cursor.execute(f"UPDATE users SET password='{hashed}' WHERE id={user_id}")
    db.commit()
    return jsonify({"success": True})""",
        "answer_key": {
            "bug_lines": [14, 19],
            "fix_keywords_per_bug": {
                14: ["parameterized", "placeholder", "?, (token", "prepared"],
                19: [
                    "bcrypt",
                    "scrypt",
                    "argon2",
                    "pbkdf2",
                    "hashlib.scrypt",
                    "werkzeug.security",
                ],
            },
            "explanation_keywords": [
                "sql injection",
                "injection",
                "md5",
                "weak hash",
                "broken",
                "cryptographically",
                "crack",
                "rainbow",
                "token bypass",
                "brute force",
                "collision",
            ],
        },
    },
}


def _contains_any(haystack: str, keywords: list[str]) -> bool:
    return any(keyword in haystack for keyword in keywords)


def _count_matches(haystack: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if keyword in haystack)


def grade(task_name: str, action: CodeReviewAction) -> float:
    """Deterministic grader for code review quality."""
    if task_name not in TASKS:
        return 0.0

    task = TASKS[task_name]
    answer_key = task["answer_key"]
    review_text = action.review_text.lower()
    combined_text = (action.review_text + " " + action.suggested_fix).lower()
    identified = action.identified_lines
    score = 0.0

    if task_name in {"easy", "medium"}:
        bug_lines = answer_key["bug_lines"]
        if any(line in identified for line in bug_lines):
            score += 0.40
        if _contains_any(combined_text, answer_key["fix_keywords"]):
            score += 0.40
        if _contains_any(review_text, answer_key["explanation_keywords"]):
            score += 0.20
        hallucinated = sum(1 for line in identified if line not in bug_lines)
        score -= 0.10 * hallucinated
    else:
        bug_lines = answer_key["bug_lines"]
        if 14 in identified:
            score += 0.20
        if 19 in identified:
            score += 0.20
        bug14_keywords = answer_key["fix_keywords_per_bug"][14]
        bug19_keywords = answer_key["fix_keywords_per_bug"][19]
        if _contains_any(combined_text, bug14_keywords):
            score += 0.20
        if _contains_any(combined_text, bug19_keywords):
            score += 0.20
        explanation_match_count = _count_matches(review_text, answer_key["explanation_keywords"])
        if explanation_match_count >= 2:
            score += 0.20
        elif explanation_match_count == 1:
            score += 0.10
        hallucinated = sum(1 for line in identified if line not in bug_lines)
        score -= 0.10 * hallucinated

    score = max(0.0, min(1.0, score))
    return round(score, 4)
