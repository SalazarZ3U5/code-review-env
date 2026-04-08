# Code Review Environment

## Overview
Code Review Environment is an OpenEnv-compatible benchmark environment where an LLM agent performs practical backend security and reliability reviews on Flask snippets. It is designed for training and evaluating review quality under deterministic scoring so model progress can be measured consistently. The environment models a real-world engineering task: identifying concrete bug locations, explaining impact, and proposing actionable fixes.

## Environment Description
- Task: LLM agent reviews Flask Python code snippets with planted bugs
- Episode type: Single-step (agent submits one review per episode)
- Reward range: 0.0 to 1.0
- Number of tasks: 3 (easy, medium, hard)

## Action Space
`CodeReviewAction` fields:
- `review_text` (`str`): Full explanation of all identified bugs and why they are dangerous.
- `identified_lines` (`List[int]`): Exact line numbers believed to contain bugs.
- `suggested_fix` (`str`): Corrected code or specific remediation details.

Example:
```json
{
  "review_text": "Line 11 can raise a KeyError when the user does not exist, causing an exception and crash path.",
  "identified_lines": [11],
  "suggested_fix": "Use users.get(user_id) and return a 404 not found response when missing."
}
```

## Observation Space
`CodeReviewObservation` fields:
- `code_snippet` (`str`): Source code the agent must review.
- `language` (`str`): Language label (default: `python`).
- `task_description` (`str`): Task instructions.
- `step_number` (`int`): Current step index (starts at `0`).

Example:
```json
{
  "code_snippet": "from flask import Flask, jsonify\napp = Flask(__name__)\n...",
  "language": "python",
  "task_description": "Review this Flask route and identify any bugs...",
  "step_number": 0
}
```

## Tasks
- **easy (difficulty: easy)**  
  Identify a runtime bug where dictionary indexing can raise `KeyError` in a user lookup route.  
  Expected score range (frontier models): `0.80 - 1.00`  
  Expected score range (weak models): `0.00 - 0.50`

- **medium (difficulty: medium)**  
  Identify SQL injection in a login flow and propose a parameterized query fix.  
  Expected score range (frontier models): `0.70 - 1.00`  
  Expected score range (weak models): `0.00 - 0.40`

- **hard (difficulty: hard)**  
  Identify interacting vulnerabilities: SQL injection plus weak MD5 password hashing in reset logic.  
  Expected score range (frontier models): `0.60 - 1.00`  
  Expected score range (weak models): `0.00 - 0.40`

## Reward Function
Scoring is deterministic and based on keyword and line checks:
- Line identification: 40%
- Fix suggestion: 40%
- Explanation quality: 20%
- Hallucination penalty: -0.10 per wrong line

The hard task splits credit across both bugs while preserving the same total reward range and hallucination penalty behavior. Final reward is clamped to `[0.0, 1.0]`.

## Baseline Scores
| Task   | Baseline Score | Model Used |
|--------|---------------|------------|
| easy   | TBD           | Qwen2.5-72B |
| medium | TBD           | Qwen2.5-72B |
| hard   | TBD           | Qwen2.5-72B |

## Setup & Usage

### Local Development
```bash
cd server
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 7860
```

### Docker
```bash
docker build -t code-review-env .
docker run -p 7860:7860 code-review-env
```

### Running the Baseline
```bash
export HF_TOKEN=your_token_here
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
python inference.py
```

### API Endpoints
1. `GET /health`
```bash
curl -X GET http://localhost:7860/health
```

2. `POST /reset`
```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task":"easy"}'
```

3. `POST /step`
```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"review_text":"KeyError crash exception","identified_lines":[11],"suggested_fix":"users.get(user_id) return 404"}'
```

4. `GET /state`
```bash
curl -X GET http://localhost:7860/state
```

5. `GET /tasks`
```bash
curl -X GET http://localhost:7860/tasks
```

## Validation
```bash
./validate-submission.sh https://your-space.hf.space
```
