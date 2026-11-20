"""Request/response models shared by the API and core logic."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator


MatchType = Literal["exact", "contains", "numeric"]


class RunRequest(BaseModel):
    task: str = Field(min_length=3, max_length=500)
    expected_answer: str | None = Field(default=None, max_length=500)
    match_type: MatchType = "exact"
    max_attempts: int = Field(default=3, ge=1, le=5)

    @model_validator(mode="after")
    def check_expected(self):
        if self.expected_answer is not None and not self.expected_answer.strip():
            raise ValueError("expected_answer must be nonblank or null")
        return self


class ToolPlan(BaseModel):
    tool: Literal["calculator", "note_search", "none"]
    tool_input: str = Field(default="", max_length=250)


class AttemptResult(BaseModel):
    number: int
    plan: ToolPlan | None = None
    tool_output: str = ""
    answer: str = ""
    passed: bool = False
    feedback: str = ""
    latency_ms: float = 0
    tokens: int = 0


class RunResult(BaseModel):
    run_id: str
    task: str
    provider: str
    model: str
    success: bool
    answer: str
    attempts: list[AttemptResult]
    total_latency_ms: float
    total_tokens: int


class BenchmarkItem(BaseModel):
    task: str
    expected_answer: str
    match_type: MatchType = "exact"
    baseline_answer: str
    baseline_passed: bool
    harness_answer: str
    harness_passed: bool
    baseline_latency_ms: float
    harness_latency_ms: float
    baseline_tokens: int
    harness_tokens: int
    harness_attempts: int


class BenchmarkSummary(BaseModel):
    count: int
    provider: str
    baseline_success_rate: float
    harness_success_rate: float
    baseline_avg_latency_ms: float
    harness_avg_latency_ms: float
    baseline_avg_tokens: float
    harness_avg_tokens: float
    results: list[BenchmarkItem]


class BenchmarkRequest(BaseModel):
    limit: int = Field(default=6, ge=1, le=20)
    max_attempts: int = Field(default=3, ge=1, le=5)
