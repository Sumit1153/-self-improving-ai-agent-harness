import json
import os
from pathlib import Path
import subprocess
import sys

from app.config import ROOT


def test_cli_writes_labeled_smoke_report(tmp_path):
    output = tmp_path / "bench.json"
    env = os.environ.copy()
    env["DATABASE_PATH"] = str(tmp_path / "runs.db")
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.benchmark_cli",
         "--provider", "demo", "--limit", "2", "--output", str(output)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["count"] == 2
    assert payload["metadata"]["provider"] == "demo"
    assert "smoke test" in payload["metadata"]["interpretation"].lower()
