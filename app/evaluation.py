"""Objective scoring when ground truth is provided; structural checks otherwise."""

import re
from .schemas import MatchType


def normalize(text: str) -> str:
    return " ".join(text.casefold().strip().split()).rstrip(".! ")


def score(answer: str, expected: str | None, match_type: MatchType,
          tool_error: str = "", no_matches: bool = False) -> tuple[bool, str]:
    if tool_error:
        return False, f"Tool execution failed: {tool_error}. Re-plan with a valid tool input."
    if no_matches:
        return False, "Note search returned no matches. Try a more specific search query."
    if not answer.strip():
        return False, "Your answer is empty. Produce a concrete final answer."
    if expected is None:
        # Clearly NOT a factual verification. Only check basic response shape.
        if "demo provider" in answer.casefold():
            return False, "Demo mode cannot answer this task. Use Ollama or a supported tool."
        return True, "Structural check passed; correctness was NOT verified (no ground truth)."
    if match_type == "exact":
        correct = normalize(answer) == normalize(expected)
    elif match_type == "contains":
        correct = normalize(expected) in normalize(answer)
    else:
        try:
            # Numeric tasks must contain one number only (apart from surrounding punctuation).
            correct = abs(float(answer.strip()) - float(expected.strip())) <= 1e-6
        except ValueError:
            correct = False
    return (True, "Matched the expected answer.") if correct else (
        False, "Answer did not match the evaluator. Re-check your tool result, "
               "then give a concise corrected answer."
    )
