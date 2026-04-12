"""
env.py — Core environment logic for the Prompt Injection Defense Environment.

Multi-step episode (up to 3 steps):
  Step 1 — classify:  agent decides safe or malicious
  Step 2 — sanitize:  agent removes injection keeping legitimate content
  Step 3 — verify:    agent confirms sanitized version is safe

Early termination:
  If agent says "safe" at step 1 AND prompt is actually malicious
    → done=True immediately, heavy penalty already applied by grader
  If agent says "safe" at step 1 AND prompt is actually safe
    → done=True immediately, reward applied
  Otherwise episode runs all 3 steps.
"""

from typing import Any, Dict

from models import (
    InjectionObservation,
    InjectionState,
    ResetResult,
    StepResult,
)
from tasks import TASKS, grade_step


class InjectionDefenseEnv:

    VALID_TASKS = list(TASKS.keys())
    MAX_STEPS = 3

    def __init__(self, task_name: str = "easy"):
        if task_name not in self.VALID_TASKS:
            raise ValueError(
                f"Invalid task '{task_name}'. Must be one of: {self.VALID_TASKS}"
            )
        self.task_name = task_name
        self.step_count = 0
        self.total_reward = 0.0
        self.done = False
        self.current_phase = "classify"
        self.action_history: list = []
        self.feedback = ""

    # -----------------------------------------------------------------------
    # reset()
    # -----------------------------------------------------------------------
    def reset(self) -> ResetResult:
        self.step_count = 0
        self.total_reward = 0.0
        self.done = False
        self.current_phase = "classify"
        self.action_history = []
        self.feedback = ""

        task = TASKS[self.task_name]
        observation = InjectionObservation(
            raw_prompt=task["raw_prompt"],
            step_number=1,
            task_name=self.task_name,
            task_description=task["description"],
            previous_actions=[],
            feedback="",
            current_phase="classify",
        )
        return ResetResult(observation=observation, done=False)

    # -----------------------------------------------------------------------
    # step()
    # -----------------------------------------------------------------------
    def step(self, action: Dict[str, Any]) -> StepResult:
        if self.done:
            return StepResult(
                observation=self._build_observation(),
                reward=0.0,
                done=True,
                info={"warning": "Episode already done. Call reset() first."},
            )

        self.step_count += 1

        # Grade this step
        reward, feedback = grade_step(
            self.task_name, self.step_count, action, self
        )

        self.total_reward += reward
        self.action_history.append(action)
        self.feedback = feedback

        # Determine if episode should end
        self.done = self._should_terminate(action)

        # Advance phase
        if not self.done:
            self._advance_phase()
        else:
            self.current_phase = "complete"

        # Clamp total reward to (0.05, 0.95)
        clamped = round(max(0.05, min(0.95, self.total_reward)), 4)

        info = {
            "task": self.task_name,
            "phase": self.current_phase,
            "step_count": self.step_count,
            "step_reward": round(reward, 4),
            "total_reward": clamped,
            "feedback": feedback,
        }

        return StepResult(
            observation=self._build_observation(),
            reward=round(reward, 4),
            done=self.done,
            info=info,
        )

    # -----------------------------------------------------------------------
    # state()
    # -----------------------------------------------------------------------
    def state(self) -> InjectionState:
        return InjectionState(
            task_name=self.task_name,
            raw_prompt=TASKS[self.task_name]["raw_prompt"],
            done=self.done,
            total_reward=round(max(0.05, min(0.95, self.total_reward)), 4),
            step_count=self.step_count,
            current_phase=self.current_phase,
        )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def _build_observation(self) -> InjectionObservation:
        task = TASKS[self.task_name]
        return InjectionObservation(
            raw_prompt=task["raw_prompt"],
            step_number=self.step_count + 1,
            task_name=self.task_name,
            task_description=task["description"],
            previous_actions=list(self.action_history),
            feedback=self.feedback,
            current_phase=self.current_phase,
        )

    def _should_terminate(self, action: Dict[str, Any]) -> bool:
        # Always terminate after step 3
        if self.step_count >= self.MAX_STEPS:
            return True

        # Early termination at step 1 if agent says "safe"
        # (both correct and incorrect — real security pipelines
        #  don't sanitize what they think is safe)
        if self.step_count == 1:
            decision = str(action.get("decision", "")).lower().strip()
            if decision == "safe":
                return True

        return False

    def _advance_phase(self) -> None:
        phase_map = {
            "classify": "sanitize",
            "sanitize": "verify",
            "verify": "complete",
        }
        self.current_phase = phase_map.get(self.current_phase, "complete")