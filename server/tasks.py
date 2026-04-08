from models import CodeReviewAction


TASKS = {
    "easy": {
        "code": """\
from flask import Flask, jsonify
app = Flask(__name__)
 
users = {
    1: {"name": "Alice", "email": "alice@example.com"},
    2: {"name": "Bob",   "email": "bob@example.com"},
}
 
@app.route("/user/<int:user_id>")
def get_user(user_id):
    user = users[user_id]
    return jsonify(user)
""",
        "description": (
            "Review this Flask route and identify any bugs. "
            "Report the exact line number(s) of each bug, explain why it is a bug, "
            "and suggest a corrected version of the code."
        ),
        "answer_key": {
            "bug_lines": [11],
            "fix_must_have_all": [
                ["users.get", ".get(user_id)", ".get("],
                ["404", "not found", "notfound"],
            ],
            "explanation_keywords": [
                "keyerror", "key error", "does not exist",
                "missing key", "crash", "exception", "raise"
            ],
            "precision_check": {
                "max_lines_flagged": 1,
                "min_fix_length": 30,
            },
        },
    },
 
    "medium": {
        "code": """\
from flask import Flask, request
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
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    user = cursor.fetchone()
    if user:
        return "Login successful"
    return "Invalid credentials"
""",
        "description": (
            "Review this Flask login route and identify any security vulnerabilities. "
            "Report the exact line number(s), explain the attack vector, "
            "and suggest a secure corrected version."
        ),
        "answer_key": {
            "bug_lines": [14],
            "fix_must_have_all": [
                ["cursor.execute("],
                ["?", "placeholder", "parameterized"],
            ],
            "explanation_keywords": [
                "sql injection", "injection", "interpolat",
                "f-string", "user input", "unsanitized",
                "bypass", "or '1'='1", "malicious"
            ],
            "precision_check": {
                "max_lines_flagged": 1,
                "min_fix_length": 40,
            },
        },
    },
 
    "hard": {
        "code": """\
from flask import Flask, request, jsonify
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
    cursor.execute(f"SELECT user_id FROM reset_tokens WHERE token='{token}'")
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Invalid token"}), 400
    user_id = row[0]
    hashed  = hashlib.md5(new_pass.encode()).hexdigest()
    cursor.execute(f"UPDATE users SET password='{hashed}' WHERE id={user_id}")
    db.commit()
    return jsonify({"success": True})
""",
        "description": (
            "Review this Flask password reset route carefully. "
            "It contains more than one bug. Identify ALL bug line numbers, "
            "explain why each is dangerous, and suggest fixes for each. "
            "Consider how the bugs might interact with each other."
        ),
        "answer_key": {
            "bug_lines": [14, 19],
            "fix_must_have_per_bug": {
                14: [
                    ["cursor.execute("],
                    ["?", "parameterized", "placeholder"],
                ],
                19: [
                    ["bcrypt", "scrypt", "argon2", "pbkdf2", "hashlib.scrypt"],
                ],
            },
            "explanation_keywords": [
                "sql injection", "injection", "md5", "weak hash",
                "broken", "cryptographically", "crack", "rainbow",
                "brute force", "collision", "token"
            ],
            "precision_check": {
                "max_lines_flagged": 2,
                "min_fix_length": 60,
            },
        },
    },
}
 
 
def _check_fix_groups(fix_lower: str, review_lower: str, groups: list) -> float:
    matched = 0
    for group in groups:
        if any(kw in fix_lower or kw in review_lower for kw in group):
            matched += 1
    return matched / len(groups) if groups else 0.0
 
 
def grade(task_name: str, action: CodeReviewAction) -> float:
    if task_name not in TASKS:
        raise ValueError(f"Unknown task: {task_name}")
 
    key = TASKS[task_name]["answer_key"]
    review_lower = action.review_text.lower()
    fix_lower = action.suggested_fix.lower()
    score = 0.05  # base — prevents pure 0.0
 
    if task_name in ("easy", "medium"):
        correct_lines = key["bug_lines"]
        fix_groups    = key["fix_must_have_all"]
        exp_keywords  = key["explanation_keywords"]
        precision     = key["precision_check"]
 
        # 35% — found the right line
        if any(line in action.identified_lines for line in correct_lines):
            score += 0.35
 
        # 40% — fix is correct (ALL groups must match)
        fix_ratio = _check_fix_groups(fix_lower, review_lower, fix_groups)
        score += 0.40 * fix_ratio
 
        # 15% — explanation (need 2+ keywords for full credit)
        exp_hits = sum(1 for kw in exp_keywords if kw in review_lower)
        if exp_hits >= 2:
            score += 0.15
        elif exp_hits == 1:
            score += 0.07
 
        # 10% precision bonus
        wrong_lines = [l for l in action.identified_lines if l not in correct_lines]
        fix_is_substantive = len(action.suggested_fix) >= precision["min_fix_length"]
        no_hallucinations  = len(action.identified_lines) <= precision["max_lines_flagged"]
        if no_hallucinations and fix_is_substantive and not wrong_lines:
            score += 0.10
 
        score -= len(wrong_lines) * 0.10
 
    elif task_name == "hard":
        correct_lines = key["bug_lines"]
        fix_per_bug   = key["fix_must_have_per_bug"]
        exp_keywords  = key["explanation_keywords"]
        precision     = key["precision_check"]
 
        # 35% — finding both lines (17.5% each)
        for line in correct_lines:
            if line in action.identified_lines:
                score += 0.175
 
        # 40% — correct fix per bug (20% each)
        for line, groups in fix_per_bug.items():
            fix_ratio = _check_fix_groups(fix_lower, review_lower, groups)
            score += 0.20 * fix_ratio
 
        # 15% — explanation (need 3+ keywords for full credit)
        exp_hits = sum(1 for kw in exp_keywords if kw in review_lower)
        if exp_hits >= 3:
            score += 0.15
        elif exp_hits == 2:
            score += 0.10
        elif exp_hits == 1:
            score += 0.05
 
        # 10% precision bonus
        wrong_lines = [l for l in action.identified_lines if l not in correct_lines]
        fix_is_substantive = len(action.suggested_fix) >= precision["min_fix_length"]
        no_hallucinations  = len(action.identified_lines) <= precision["max_lines_flagged"]
        if no_hallucinations and fix_is_substantive and not wrong_lines:
            score += 0.10
 
        score -= len(wrong_lines) * 0.10
 
    # Clamp to (0.05, 0.95) — never exactly 0.0 or 1.0
    return round(max(0.05, min(0.95, score)), 4)