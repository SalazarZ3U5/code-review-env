import asyncio
import json
import os
from typing import Any, Dict

import httpx
from openai import OpenAI

ENV_NAME = "code-review-env"
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
IMAGE_NAME = os.getenv("IMAGE_NAME", "")
MAX_STEPS = 1
SUCCESS_SCORE_THRESHOLD = 0.5

SYSTEM_PROMPT = """
You are a senior software engineer performing a code review.
You will be given a Python Flask code snippet that contains one or more bugs.

Your task:
1. Identify the exact line numbers containing bugs
2. Explain why each is a bug and what the attack vector or failure mode is
3. Suggest a specific corrected fix with actual code

You must respond with ONLY a valid JSON object in this exact format:
{
  "review_text": "<your full explanation of bugs and why they are dangerous>",
  "identified_lines": [<integer line numbers of bugs>],
  "suggested_fix": "<your proposed fix with specific code or function names>"
}

No markdown. No code fences. No text outside the JSON.
For SQL bugs: always use the word "parameterized" and show the ? placeholder syntax.
For hashing bugs: always name a specific secure library like bcrypt or scrypt.
For KeyError bugs: always mention .get() and returning a 404 response.
""".strip()

USER_PROMPT_TEMPLATE = """
Task: {task_description}

Code to review:
{code_snippet}

Respond with only the JSON object.
""".strip()


def add_line_numbers(code: str) -> str:
    lines = code.split("\n")
    numbered = []
    for i, line in enumerate(lines, start=1):
        numbered.append(f"{i:2}  {line}")
    return "\n".join(numbered)


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def _fallback_action() -> Dict[str, Any]:
    return {"review_text": "parse error", "identified_lines": [], "suggested_fix": ""}


def _summarize_action(action: Dict[str, Any]) -> str:
    lines = action.get("identified_lines", [])
    if not isinstance(lines, list):
        lines = []
    summary = f"lines={lines} fix={str(action.get('suggested_fix', ''))[:80]}"
    return summary.replace("\n", " ").strip()[:140]


async def _reset_task(client: httpx.AsyncClient, task_name: str) -> Dict[str, Any]:
    response = await client.post(f"{ENV_BASE_URL}/reset", json={"task": task_name})
    response.raise_for_status()
    return response.json()


async def _step_task(client: httpx.AsyncClient, action: Dict[str, Any]) -> Dict[str, Any]:
    response = await client.post(f"{ENV_BASE_URL}/step", json=action)
    response.raise_for_status()
    return response.json()


def _call_llm(code_snippet: str, task_description: str) -> Dict[str, Any]:
    if not HF_TOKEN:
        return _fallback_action()

    numbered_code = add_line_numbers(code_snippet)
    prompt = USER_PROMPT_TEMPLATE.format(
        task_description=task_description, code_snippet=numbered_code
    )
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    content = completion.choices[0].message.content or ""
    cleaned = _strip_markdown_fences(content)
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        return _fallback_action()
    return {
        "review_text": str(parsed.get("review_text", "")),
        "identified_lines": parsed.get("identified_lines", []),
        "suggested_fix": str(parsed.get("suggested_fix", "")),
    }


async def run_task(task_name: str) -> None:
    print(f"[START] task={task_name} env={ENV_NAME} model={MODEL_NAME}")
    reward_value = 0.0
    done_value = False
    error_value: Any = None
    action = _fallback_action()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            reset_payload = await _reset_task(client, task_name)
            observation = reset_payload.get("observation", {})
            code_snippet = str(observation.get("code_snippet", ""))
            task_description = str(observation.get("task_description", ""))

            try:
                action = _call_llm(code_snippet, task_description)
            except Exception as llm_exc:  # noqa: BLE001
                action = _fallback_action()
                error_value = str(llm_exc)

            step_payload = await _step_task(client, action)
            reward_value = float(step_payload.get("reward", 0.0))
            done_value = bool(step_payload.get("done", False))
    except Exception as exc:  # noqa: BLE001
        error_value = str(exc)

    error_text = "null" if error_value is None else str(error_value).replace("\n", " ")
    action_summary = _summarize_action(action)
    print(
        f"[STEP] step=1 action={action_summary} "
        f"reward={reward_value:.2f} done={str(done_value).lower()} error={error_text}"
    )
    score = reward_value
    success = score >= SUCCESS_SCORE_THRESHOLD
    print(
        f"[END] success={str(success).lower()} steps=1 score={score:.3f} rewards={reward_value:.2f}"
    )


async def main() -> None:
    _ = IMAGE_NAME
    for task in ("easy", "medium", "hard"):
        await run_task(task)


if __name__ == "__main__":
    asyncio.run(main())
