"""Environment-based configuration. No external settings dependency required."""

from dataclasses import dataclass
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    provider: str = "demo"
    model: str = "llama3.2:3b"
    ollama_url: str = "http://localhost:11434"
    database_path: Path = ROOT / "data" / "runs.db"
    notes_path: Path = ROOT / "data" / "notes.json"
    benchmark_path: Path = ROOT / "data" / "benchmark.json"
    timeout_seconds: float = 90.0

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("LLM_PROVIDER", "demo").lower().strip()
        if provider not in {"demo", "ollama"}:
            raise ValueError("LLM_PROVIDER must be 'demo' or 'ollama'")
        return cls(
            provider=provider,
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
            database_path=Path(os.getenv("DATABASE_PATH", str(ROOT / "data" / "runs.db"))),
            notes_path=Path(os.getenv("NOTES_PATH", str(ROOT / "data" / "notes.json"))),
            benchmark_path=Path(os.getenv("BENCHMARK_PATH", str(ROOT / "data" / "benchmark.json"))),
            timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "90")),
        )
