# Verification and project scope

This repository contains a **bounded agent harness MVP**. It demonstrates a complete local workflow from API request through tool planning, evaluation, retry, and persistence. It is **not** a production-ready autonomous agent and does not retrain model weights.

## How to reproduce the implementation

1. Follow the README quick start and open `http://127.0.0.1:8000`.
2. Execute the pre-filled calculator task and inspect its execution trace.
3. Open `http://127.0.0.1:8000/docs` to inspect the OpenAPI endpoints.
4. Run unit and integration tests:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q
   ```

5. Run the **offline smoke benchmark** from a **second** project terminal:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.benchmark_cli --provider demo --output reports/demo.json
   ```

The demo baseline is intentionally simple and is **not** evidence of AI capability gains. Check the exported `metadata.interpretation` field.

## Testing a real LLM (required before claiming LLM benchmark results)

1. Install and run Ollama, and pull the `llama3.2:3b` model.
2. In a new PowerShell terminal in this folder, run:

   ```powershell
   $env:LLM_PROVIDER = "ollama"
   $env:OLLAMA_MODEL = "llama3.2:3b"
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```

3. Confirm that `GET /health` reports `"provider": "ollama"`.
4. Test a numeric task with a known expected answer and inspect the steps.
5. Export an **illustrative**, real-model benchmark:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.benchmark_cli --provider ollama --output reports/ollama.json
   ```

6. Review individual outcomes, count retries, record local hardware and model version, and include those details when publishing any results.

**Benchmark caution:** The six sample tasks are not a held-out evaluation; they are useful for verifying plumbing, not establishing general performance improvement. To claim statistically credible gains, gather a larger held-out test set, run multiple seeds/runs, report spread and failure types, and compare under the same model configuration.

## Features you can accurately claim

- A FastAPI service with REST endpoints and a browser dashboard
- A bounded plan → tool → answer → evaluate → retry loop
- Safe, allowlisted tools (calculator and local note search)
- Optional local LLM integration through Ollama
- Reference-based evaluation (exact, contains, numeric) and basic structural checks
- SQLite persistence of execution traces
- Benchmark code recording success rate, latency and token usage
- Docker configuration and GitHub Actions test workflow

## Things this project deliberately does not claim

- Verified end-to-end Ollama performance (until you run it on your machine)
- Persistent model learning, autonomous web browsing, or arbitrary code execution
- Production-grade authentication, tenant isolation, background jobs, or scalability
- Statistically significant improvements over a baseline model

## Reviewer checklist before making a public repository

- [ ] All Python tests pass locally
- [ ] Dashboard loads and executes a task
- [ ] API documentation works
- [ ] Try an intentionally incorrect `expected_answer` and inspect bounded retry behavior
- [ ] Try a real Ollama model and document whether it succeeds
- [ ] Publish benchmark evidence only after checking it and labeling demo vs. Ollama
- [ ] Ensure `.env`, local databases, caches and API keys are not committed
- [ ] Verify Docker on a machine with Docker installed, or clearly note that it remains unverified

The `docs/dashboard.png` image shows the bundled browser UI rendering a real **offline demo** API response captured through FastAPI's test client (with browser API calls replayed from that response). It does not show a live Ollama run or prove any real-model performance gain.
