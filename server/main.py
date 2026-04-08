from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from env import CodeReviewEnv
from models import CodeReviewAction
from tasks import TASKS

app = FastAPI(title="Code Review Environment")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_env: Optional[CodeReviewEnv] = None


class ResetRequest(BaseModel):
    task: str = Field(default="easy", description="Task name: easy, medium, or hard.")


@app.get("/health")
def health() -> dict:
    """Health check endpoint used by validators to confirm service liveness."""
    return {"status": "ok"}


@app.post("/reset")
def reset(request: Optional[ResetRequest] = None) -> dict:
    """Reset the environment for the selected task and return initial observation."""
    global _env
    task_name = (request.task if request else "easy") or "easy"
    try:
        _env = CodeReviewEnv(task_name=task_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _env.reset().model_dump()


@app.post("/step")
def step(action: CodeReviewAction) -> dict:
    """Execute the single review step using the agent action and return reward."""
    if _env is None:
        raise HTTPException(status_code=400, detail="Environment not initialized. Call /reset first.")
    return _env.step(action).model_dump()


@app.get("/state")
def state() -> dict:
    """Return the current internal state of the active environment episode."""
    if _env is None:
        raise HTTPException(status_code=400, detail="Environment not initialized. Call /reset first.")
    return _env.state().model_dump()


@app.get("/tasks")
def tasks() -> dict:
    """List available task names with descriptions and difficulty labels."""
    return {
        name: {
            "description": task["description"],
            "difficulty": task["difficulty"],
        }
        for name, task in TASKS.items()
    }
