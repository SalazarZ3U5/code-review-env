from typing import Dict, List

from pydantic import BaseModel, Field


class CodeReviewAction(BaseModel):
    """Action payload submitted by the reviewing agent."""

    review_text: str = Field(
        ...,
        description="Full explanation of bugs found, why they are dangerous, and impact.",
    )
    identified_lines: List[int] = Field(
        ...,
        description="Exact source line numbers the agent identifies as buggy.",
    )
    suggested_fix: str = Field(
        ...,
        description="Proposed corrected code or concrete remediation guidance.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "review_text": "Line 11 can raise a KeyError when user_id does not exist.",
                    "identified_lines": [11],
                    "suggested_fix": "Use users.get(user_id) and return a 404 when missing.",
                }
            ]
        }
    }


class CodeReviewObservation(BaseModel):
    """Observation shown to the agent for a given task."""

    code_snippet: str = Field(..., description="The code snippet to review.")
    language: str = Field(
        default="python",
        description="Programming language of the snippet, defaults to python.",
    )
    task_description: str = Field(
        ..., description="Task instructions describing what issues to identify."
    )
    step_number: int = Field(
        default=0,
        description="Current step index in the episode, starts at 0.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code_snippet": "from flask import Flask",
                    "language": "python",
                    "task_description": "Review this route for bugs.",
                    "step_number": 0,
                }
            ]
        }
    }


class CodeReviewState(BaseModel):
    """Internal environment state representation."""

    task_name: str = Field(..., description="Currently selected task name.")
    current_code: str = Field(..., description="Current task code snippet.")
    done: bool = Field(..., description="Whether the episode is finished.")
    total_reward: float = Field(..., description="Cumulative reward for the episode.")
    step_count: int = Field(..., description="How many steps have been executed.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task_name": "easy",
                    "current_code": "from flask import Flask, jsonify",
                    "done": False,
                    "total_reward": 0.0,
                    "step_count": 0,
                }
            ]
        }
    }


class StepResult(BaseModel):
    """Response payload returned by /step."""

    observation: CodeReviewObservation = Field(
        ..., description="Post-step observation for the agent."
    )
    reward: float = Field(..., description="Reward awarded for this step.")
    done: bool = Field(..., description="Whether the episode has completed.")
    info: Dict = Field(default_factory=dict, description="Auxiliary metadata for debugging.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "observation": {
                        "code_snippet": "from flask import Flask",
                        "language": "python",
                        "task_description": "Review this route for bugs.",
                        "step_number": 1,
                    },
                    "reward": 0.8,
                    "done": True,
                    "info": {"task": "easy", "step_count": 1, "total_reward": 0.8},
                }
            ]
        }
    }


class ResetResult(BaseModel):
    """Response payload returned by /reset."""

    observation: CodeReviewObservation = Field(
        ..., description="Initial observation after environment reset."
    )
    done: bool = Field(default=False, description="Episode done flag, false at reset.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "observation": {
                        "code_snippet": "from flask import Flask",
                        "language": "python",
                        "task_description": "Review this route for bugs.",
                        "step_number": 0,
                    },
                    "done": False,
                }
            ]
        }
    }
