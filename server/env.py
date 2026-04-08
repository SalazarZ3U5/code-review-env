from models import (
    CodeReviewAction,
    CodeReviewObservation,
    CodeReviewState,
    ResetResult,
    StepResult,
)
from tasks import TASKS, grade


class CodeReviewEnv:
    """Single-step deterministic environment for code review tasks."""

    def __init__(self, task_name: str = "easy"):
        if task_name not in TASKS:
            raise ValueError(f"Invalid task_name: {task_name}")
        self.task_name = task_name
        self.step_count = 0
        self.total_reward = 0.0
        self.done = False
        self._last_reward = 0.0

    def _build_observation(self) -> CodeReviewObservation:
        task = TASKS[self.task_name]
        return CodeReviewObservation(
            code_snippet=task["code"],
            language="python",
            task_description=task["description"],
            step_number=self.step_count,
        )

    def reset(self) -> ResetResult:
        self.step_count = 0
        self.total_reward = 0.0
        self.done = False
        self._last_reward = 0.0
        return ResetResult(observation=self._build_observation(), done=False)

    def step(self, action: CodeReviewAction) -> StepResult:
        if self.done:
            return StepResult(
                observation=self._build_observation(),
                reward=0.0,
                done=True,
                info={"warning": "Episode already done. Call reset() first."},
            )

        reward = grade(self.task_name, action)
        self.step_count += 1
        self._last_reward = reward
        self.total_reward += reward
        self.done = True

        return StepResult(
            observation=self._build_observation(),
            reward=reward,
            done=True,
            info={
                "task": self.task_name,
                "step_count": self.step_count,
                "total_reward": self.total_reward,
            },
        )

    def state(self) -> CodeReviewState:
        return CodeReviewState(
            task_name=self.task_name,
            current_code=TASKS[self.task_name]["code"],
            done=self.done,
            total_reward=self.total_reward,
            step_count=self.step_count,
        )
