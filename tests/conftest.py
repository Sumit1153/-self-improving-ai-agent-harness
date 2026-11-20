from pathlib import Path
import pytest
from app.config import ROOT, Settings
from app.providers import DemoProvider
from app.storage import RunStore
from app.tools import Tools
from app.harness import AgentHarness


@pytest.fixture
def settings(tmp_path):
    return Settings(provider="demo", database_path=tmp_path / "runs.db",
                    notes_path=ROOT / "data/notes.json",
                    benchmark_path=ROOT / "data/benchmark.json")


@pytest.fixture
def harness(settings):
    return AgentHarness(DemoProvider(), Tools(settings.notes_path),
                        RunStore(settings.database_path), settings.provider, settings.model)
