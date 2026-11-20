"""Ollama LLM client and an explicitly non-LLM offline demo provider."""

from dataclasses import dataclass
import json
import re
from typing import Protocol
import httpx

from .config import Settings


@dataclass
class LLMReply:
    text: str
    tokens: int = 0


class Provider(Protocol):
    def plan(self, task: str, feedback: str) -> LLMReply: ...
    def answer(self, task: str, tool_name: str, tool_output: str, feedback: str) -> LLMReply: ...
    def direct(self, task: str) -> LLMReply: ...


class OllamaProvider:
    def __init__(self, settings: Settings):
        self.url = settings.ollama_url
        self.model = settings.model
        self.timeout = settings.timeout_seconds

    def _chat(self, system: str, user: str, json_mode: bool = False) -> LLMReply:
        body: dict = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": 0},
        }
        if json_mode:
            body["format"] = "json"
        try:
            response = httpx.post(f"{self.url}/api/chat", json=body, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            content = data["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        return LLMReply(str(content), int(data.get("prompt_eval_count", 0) or 0) +
                        int(data.get("eval_count", 0) or 0))

    def plan(self, task: str, feedback: str) -> LLMReply:
        return self._chat(
            "You are a tool-planning assistant. Return ONLY one JSON object with keys "
            "'tool' and 'tool_input'. Tools: calculator (arithmetic expression using + - * / "
            "and parentheses), note_search (short keywords to query local notes), none "
            "(general tasks). Use calculator for numeric arithmetic, note_search for factual "
            "questions that might be in project notes. Never invent additional tool names. "
            "Do not use any shell commands or Python code.",
            f"Task: {task}\nFeedback from previous attempt: {feedback or 'None'}",
            json_mode=True,
        )

    def answer(self, task: str, tool_name: str, tool_output: str, feedback: str) -> LLMReply:
        return self._chat(
            "Answer the user's task briefly and accurately. A tool result is supplied when "
            "available; use it as authoritative for arithmetic. Do not invent facts not in "
            "notes. For a numeric task, output ONLY the number. For a factual task, output a "
            "short standalone answer with no prefix. Don't mention evaluation rules.",
            f"Task: {task}\nTool: {tool_name}\nTool output: {tool_output}\n"
            f"Previous evaluator feedback: {feedback or 'None'}",
        )

    def direct(self, task: str) -> LLMReply:
        return self._chat("Answer the task without using tools. Give a concise final answer.", task)


class DemoProvider:
    """A predictable rule-based demo, NOT an LLM and NOT a meaningful LLM benchmark."""

    def plan(self, task: str, feedback: str) -> LLMReply:
        # Extract arithmetic segment from simple English questions, where present.
        candidates = re.findall(r"[0-9(][0-9\s.+*/()\-]*[0-9)]", task)
        if candidates:
            expression = max(candidates, key=len).strip().rstrip(" .")
            if any(op in expression for op in "+-*/"):
                return LLMReply(json.dumps({"tool": "calculator", "tool_input": expression}))
        return LLMReply(json.dumps({"tool": "note_search", "tool_input": task}))

    def answer(self, task: str, tool_name: str, tool_output: str, feedback: str) -> LLMReply:
        if tool_name == "calculator":
            return LLMReply(tool_output)
        if tool_name == "note_search":
            matches = json.loads(tool_output).get("matches", [])
            if matches:
                return LLMReply(matches[0]["text"])
        return LLMReply("Demo provider has no answer; connect Ollama for open-ended tasks.")

    def direct(self, task: str) -> LLMReply:
        return LLMReply("Demo provider cannot solve tasks without tools.")


def make_provider(settings: Settings) -> Provider:
    if settings.provider == "demo":
        return DemoProvider()
    if settings.provider == "ollama":
        return OllamaProvider(settings)
    raise ValueError(f"Unknown provider: {settings.provider}")
