"""
main.py — FastAPI server for the Prompt Injection Defense Environment.

Endpoints:
  POST /reset   — start a new episode
  POST /step    — submit an action (dict, schema changes per step)
  GET  /state   — get current environment state
  GET  /health  — health check
  GET  /tasks   — list available tasks
"""

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from env import InjectionDefenseEnv
from models import ResetResult, StepResult, InjectionState
from tasks import TASKS

app = FastAPI(
    title="Prompt Injection Defense Environment",
    description="OpenEnv-compatible environment for evaluating LLM security agents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_env: Optional[InjectionDefenseEnv] = None


def get_env() -> InjectionDefenseEnv:
    if _env is None:
        raise HTTPException(
            status_code=400,
            detail="Environment not initialized. Call POST /reset first."
        )
    return _env


class ResetRequest:
    def __init__(self, task: str = "easy"):
        self.task = task


from pydantic import BaseModel

class ResetRequestBody(BaseModel):
    task: str = "easy"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset(request: ResetRequestBody = ResetRequestBody()) -> dict:
    global _env

    if request.task not in TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{request.task}'. Valid: {list(TASKS.keys())}"
        )

    _env = InjectionDefenseEnv(task_name=request.task)
    result: ResetResult = _env.reset()
    return result.model_dump()


@app.post("/step")
def step(action: Dict[str, Any]) -> dict:
    """
    Submit an action for the current step.
    Action schema changes per step:
      Step 1: ClassifyAction fields
      Step 2: SanitizeAction fields
      Step 3: VerifyAction fields
    """
    env = get_env()
    result: StepResult = env.step(action)
    return result.model_dump()


@app.get("/state")
def state() -> dict:
    env = get_env()
    result: InjectionState = env.state()
    return result.model_dump()


@app.get("/tasks")
def list_tasks() -> dict:
    return {
        task_name: {
            "description": task_data["description"],
            "difficulty": task_name,
        }
        for task_name, task_data in TASKS.items()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=True)