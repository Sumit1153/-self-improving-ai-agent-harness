"""Evaluate a no-tools, one-call baseline vs the evaluated retry harness."""

import json
from pathlib import Path
from time import perf_counter
from .evaluation import score
from .harness import AgentHarness
from .schemas import BenchmarkItem, BenchmarkSummary, RunRequest


def run_benchmark(harness: AgentHarness, path: Path, limit: int, max_attempts: int) -> BenchmarkSummary:
    tasks = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Benchmark must contain at least one task")
    items = []
    for task in tasks[:limit]:
        request = RunRequest(task=task["task"], expected_answer=task["expected_answer"],
                             match_type=task.get("match_type", "exact"), max_attempts=max_attempts)
        start = perf_counter()
        try:
            reply = harness.provider.direct(request.task)
            baseline_answer = reply.text.strip()
            baseline_tokens = reply.tokens
        except Exception as exc:
            baseline_answer = f"Baseline error: {type(exc).__name__}"
            baseline_tokens = 0
        baseline_ms = round((perf_counter() - start) * 1000, 2)
        baseline_ok, _ = score(baseline_answer, request.expected_answer, request.match_type)
        result = harness.run(request)
        items.append(BenchmarkItem(
            task=request.task, expected_answer=request.expected_answer,
            match_type=request.match_type,
            baseline_answer=baseline_answer, baseline_passed=baseline_ok,
            harness_answer=result.answer, harness_passed=result.success,
            baseline_latency_ms=baseline_ms, harness_latency_ms=result.total_latency_ms,
            baseline_tokens=baseline_tokens, harness_tokens=result.total_tokens,
            harness_attempts=len(result.attempts),
        ))

    count = len(items)
    return BenchmarkSummary(
        count=count, provider=harness.provider_name,
        baseline_success_rate=round(sum(item.baseline_passed for item in items) / count * 100, 1),
        harness_success_rate=round(sum(item.harness_passed for item in items) / count * 100, 1),
        baseline_avg_latency_ms=round(sum(x.baseline_latency_ms for x in items) / count, 2),
        harness_avg_latency_ms=round(sum(x.harness_latency_ms for x in items) / count, 2),
        baseline_avg_tokens=round(sum(x.baseline_tokens for x in items) / count, 1),
        harness_avg_tokens=round(sum(x.harness_tokens for x in items) / count, 1),
        results=items,
    )
