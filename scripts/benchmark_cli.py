"""Run a reproducible baseline-vs-harness experiment and export its raw results.

Usage:
    python -m scripts.benchmark_cli --provider demo --output reports/demo.json
    python -m scripts.benchmark_cli --provider ollama --output reports/ollama.json

Important: demo mode is a smoke test, not evidence of LLM improvement.
"""

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys

from app.benchmark import run_benchmark
from app.config import Settings
from app.harness import AgentHarness
from app.providers import make_provider
from app.storage import RunStore
from app.tools import Tools


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["demo", "ollama"], default="demo")
    parser.add_argument("--limit", type=int, default=6, help="Number of benchmark tasks (1-20)")
    parser.add_argument("--max-attempts", type=int, default=3, help="Maximum per-task attempts (1-5)")
    parser.add_argument("--output", type=Path, default=Path("reports/benchmark.json"))
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 20:
        parser.error("--limit must be between 1 and 20")
    if not 1 <= args.max_attempts <= 5:
        parser.error("--max-attempts must be between 1 and 5")

    settings = replace(Settings.from_env(), provider=args.provider)
    harness = AgentHarness(
        make_provider(settings), Tools(settings.notes_path),
        RunStore(settings.database_path), settings.provider, settings.model
    )
    summary = run_benchmark(harness, settings.benchmark_path, args.limit, args.max_attempts)
    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "provider": settings.provider,
            "model": harness.model,
            "max_attempts": args.max_attempts,
            "benchmark_file": settings.benchmark_path.name,
            "interpretation": (
                "Functional smoke test; NOT a real-LLM accuracy comparison"
                if settings.provider == "demo"
                else "Local-model illustrative comparison; repeat on held-out data before drawing conclusions"
            ),
        },
        "summary": summary.model_dump(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Provider: {settings.provider} | tasks: {summary.count}")
    print(f"Baseline success: {summary.baseline_success_rate}%")
    print(f"Harness success:  {summary.harness_success_rate}%")
    print(f"Baseline mean latency: {summary.baseline_avg_latency_ms} ms")
    print(f"Harness mean latency:  {summary.harness_avg_latency_ms} ms")
    print(f"Saved raw results: {args.output}")
    if settings.provider == "demo":
        print("WARNING: demo results are only a smoke test; they do not measure LLM improvement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
