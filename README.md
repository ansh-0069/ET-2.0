# PetraVigil MVP

## Phase 8: Integration and demo hardening

Phase 8 protects the complete judge journey: a user-entered disruption signal is
validated and scored, simulated with reproducible Monte Carlo assumptions,
converted into constrained procurement portfolios, explained through Gemini (or
its labelled offline fallback), and recorded as a local human decision. The
final approval is explicitly non-executing.

Before presenting, run the complete backend regression suite:

```powershell
uv run pytest
```

Then open `http://localhost:3000`, click **Start 30-second crisis replay**, and
confirm that the final approval record says **Local only**. This rehearses the
same safe, evidence-first path that the automated Phase 8 test protects.

Phase 0 establishes the contract shared by every later phase: a canonical,
explicitly simulated Hormuz scenario; validated models; provenance labels; and
a deterministic API fixture.

## Run locally

```powershell
uv sync --all-groups
uv run pytest
uv run uvicorn petravigil.main:app --app-dir backend --reload
```

Open `http://127.0.0.1:8000/docs` and call
`GET /api/v1/scenarios/canonical`.

The endpoint intentionally returns fixture data only. It is the regression
contract for later signal extraction, risk scoring, simulation, optimisation,
and approval-workflow phases.
