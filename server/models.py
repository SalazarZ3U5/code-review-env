"""
models.py — Typed Pydantic models for the Prompt Injection Defense Environment.

Three action types (one per step):
  Step 1 — ClassifyAction
  Step 2 — SanitizeAction  
  Step 3 — VerifyAction

One observation type returned after every reset/step:
  InjectionObservation

One state type returned by /state:
  InjectionState
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class ClassifyAction(BaseModel):
    """Step 1 — agent classifies the prompt as safe or malicious."""
    decision: str = Field(
        ...,
        description="safe | malicious | uncertain"
    )
    threat_type: str = Field(
        ...,
        description="direct_injection | indirect_injection | data_injection | none"
    )
    confidence: float = Field(
        ...,
        description="Confidence score 0.0 to 1.0"
    )
    reasoning: str = Field(
        ...,
        description="One sentence explanation of the classification"
    )


class SanitizeAction(BaseModel):
    """Step 2 — agent removes injection while preserving legitimate content."""
    sanitized_prompt: str = Field(
        ...,
        description="Cleaned version of the input with injections removed"
    )
    removed_segments: List[str] = Field(
        ...,
        description="List of exact text segments that were removed"
    )
    sanitization_method: str = Field(
        ...,
        description="redaction | replacement | restructure"
    )


class VerifyAction(BaseModel):
    """Step 3 — agent verifies the sanitized prompt is safe."""
    verdict: str = Field(
        ...,
        description="safe | still_malicious"
    )
    remaining_risks: List[str] = Field(
        ...,
        description="Any remaining risks still present in the sanitized prompt"
    )
    final_prompt: str = Field(
        ...,
        description="The approved safe version to pass to the downstream LLM"
    )


class InjectionObservation(BaseModel):
    """What the agent sees at each step."""
    raw_prompt: str = Field(
        ...,
        description="The original prompt the agent must defend against"
    )
    step_number: int = Field(
        default=1,
        description="Current step: 1=classify, 2=sanitize, 3=verify"
    )
    task_name: str = Field(
        ...,
        description="easy | medium | hard"
    )
    task_description: str = Field(
        ...,
        description="Instructions for the agent"
    )
    previous_actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All actions taken so far this episode"
    )
    feedback: str = Field(
        default="",
        description="Grader feedback from the previous step"
    )
    current_phase: str = Field(
        default="classify",
        description="classify | sanitize | verify | complete"
    )


class InjectionState(BaseModel):
    """Internal environment state returned by /state."""
    task_name: str
    raw_prompt: str
    done: bool
    total_reward: float
    step_count: int
    current_phase: str


class StepResult(BaseModel):
    """Return type of the /step endpoint."""
    observation: InjectionObservation
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)


class ResetResult(BaseModel):
    """Return type of the /reset endpoint."""
    observation: InjectionObservation
    done: bool = False