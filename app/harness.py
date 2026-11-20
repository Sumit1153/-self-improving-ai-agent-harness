"""Bounded plan -> tool -> answer -> evaluate -> retry agent loop."""

import json
from time import perf_counter
from uuid import uuid4

from .evaluation import score
from .providers import Provider
from .schemas import AttemptResult, RunRequest, RunResult, ToolPlan
from .storage import RunStore
from .tools import Tools, ToolError


class AgentHarness:
    def __init__(self, provider: Provider, tools: Tools, store: RunStore,
                 provider_name: str, model: str):
        self.provider = provider
        self.tools = tools
        self.store = store
        self.provider_name = provider_name
        self.model = model if provider_name == "ollama" else "rule-based-demo (not an LLM)"

    def run(self, request: RunRequest) -> RunResult:
        run_start = perf_counter()
        attempts: list[AttemptResult] = []
        feedback = ""
        for number in range(1, request.max_attempts + 1):
            start = perf_counter()
            plan = None
            tool_output = ""
            answer = ""
            tokens = 0
            failure = ""
            no_matches = False
            try:
                planned = self.provider.plan(request.task, feedback)
                tokens += planned.tokens
                plan = ToolPlan.model_validate(json.loads(planned.text))
                if plan.tool != "none":
                    tool_output = self.tools.execute(plan.tool, plan.tool_input)
                    if plan.tool == "note_search":
                        no_matches = not json.loads(tool_output).get("matches")
                answered = self.provider.answer(request.task, plan.tool, tool_output, feedback)
                tokens += answered.tokens
                answer = answered.text.strip()
            except (ValueError, TypeError, ToolError, json.JSONDecodeError) as exc:
                failure = f"Invalid plan or tool input: {str(exc)[:220]}"
            except RuntimeError as exc:
                failure = str(exc)[:220]
            except Exception as exc:
                # Unexpected library failure stays visible in run feedback (without stack traces).
                failure = f"Unexpected processing error: {type(exc).__name__}"

            passed, new_feedback = score(
                answer, request.expected_answer, request.match_type,
                tool_error=failure, no_matches=no_matches,
            )
            attempts.append(AttemptResult(
                number=number, plan=plan, tool_output=tool_output[:4000],
                answer=answer[:2000], passed=passed, feedback=new_feedback,
                latency_ms=round((perf_counter() - start) * 1000, 2), tokens=tokens,
            ))
            feedback = new_feedback
            if passed:
                break

        result = RunResult(
            run_id=str(uuid4()), task=request.task,
            provider=self.provider_name, model=self.model,
            success=attempts[-1].passed,
            answer=attempts[-1].answer,
            attempts=attempts,
            total_latency_ms=round((perf_counter() - run_start) * 1000, 2),
            total_tokens=sum(attempt.tokens for attempt in attempts),
        )
        self.store.save(result)
        return result
