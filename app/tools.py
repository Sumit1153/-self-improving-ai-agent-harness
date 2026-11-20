"""Safe, explicit tools. No shell access, arbitrary Python execution or network browsing."""

import ast
import json
import operator
import re
from pathlib import Path


class ToolError(ValueError):
    """A tool could not safely process the given input."""


_OPERATIONS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def calculate(expression: str) -> str:
    """Evaluate a small arithmetic expression through an AST allowlist."""
    expression = expression.strip()
    if not expression or len(expression) > 120:
        raise ToolError("Expression must contain 1 to 120 characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolError("Invalid arithmetic expression") from exc
    if sum(1 for _ in ast.walk(tree)) > 35:
        raise ToolError("Expression is too complex")

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            if abs(node.value) > 1e9:
                raise ToolError("Numbers are limited to magnitude 1e9")
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPERATIONS:
            left, right = evaluate(node.left), evaluate(node.right)
            try:
                value = _OPERATIONS[type(node.op)](left, right)
            except ZeroDivisionError as exc:
                raise ToolError("Cannot divide by zero") from exc
            if abs(value) > 1e12:
                raise ToolError("Result is too large")
            return value
        raise ToolError("Only numbers, parentheses, +, -, * and / are allowed")

    value = evaluate(tree)
    return f"{value:.12g}"


STOP_WORDS = {
    "a", "an", "the", "is", "in", "are", "this", "that", "what", "which", "how",
    "does", "do", "for", "to", "of", "and", "your", "you", "it", "its", "with", "use",
    "used", "from", "my", "on", "project", "agent", "harness", "answer",
}


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOP_WORDS


class Tools:
    def __init__(self, notes_path: Path):
        notes = json.loads(notes_path.read_text(encoding="utf-8"))
        if not isinstance(notes, list):
            raise ValueError("notes.json must contain a list")
        self.notes = notes

    def execute(self, name: str, tool_input: str) -> str:
        if name == "calculator":
            return calculate(tool_input)
        if name == "note_search":
            query = words(tool_input)
            scored = []
            for note in self.notes:
                tokens = words(note["text"] + " " + " ".join(note.get("tags", [])))
                score = len(tokens & query)
                if score:
                    scored.append((score, note))
            scored.sort(key=lambda x: -x[0])
            matches = [entry[1] for entry in scored[:2]]
            return json.dumps({"matches": matches}, ensure_ascii=False)
        raise ToolError(f"Unknown tool: {name}")
