# PetraVigil MVP

PetraVigil is an **analyst-confirmed energy-supply decision prototype**. It turns a user-entered disruption signal into a reviewable, reproducible procurement recommendation. It is deliberately local and does not create purchase orders, contact suppliers, or claim unverified inputs are live evidence.

## What is implemented now

```text
User-entered signal
  -> Gemini extraction / labelled deterministic fallback
  -> seeded entity resolution + deterministic corridor score
  -> analyst-confirmed assumptions
  -> reproducible NumPy Monte Carlo scenario
  -> constrained OR-Tools portfolio comparison
  -> Gemini executive explanation / labelled deterministic fallback
  -> local-only human decision record
```

The proposal endpoint, `POST /api/v1/workflows/propose`, persists the signal and stops before scenario execution so an analyst can inspect and edit the assumptions. `POST /api/v1/workflows/{workflow_id}/execute` runs only after that confirmation. A subsequent decision is attached to that specific workflow recommendation ID.

### Decision-resilience upgrades

- **Source-labelled Hormuz replay:** `GET /api/v1/replays/hormuz` supplies an offline, projected-world-map replay with simulated, historical, and user-entered evidence labels. It is not AIS, vessel telemetry, or a current route instruction.
- **Decision Clock:** `GET /api/v1/decision-clock/hormuz` shows the local replay's analyst review, last-responsible-action, laycan, and scenario-buffer milestones. An optional `approval_delay_hours` sensitivity changes only user-entered timing assumptions; it is not a live deadline.
- **Finite SPR contingency:** a single-refinery portfolio can include a seeded, 75,000 bpd maximum / seven-day maximum strategic-reserve bridge only after the analyst records both the opt-in and a user-entered scenario authorization assumption. It requires human and government authorization and never triggers a drawdown.
- **No-recommendation safety gate:** each newly executed workflow returns `decision_safety_gate`. It exposes confidence, corridor, provenance, and supply-feasibility checks. A capacity shortfall returns `NO_RECOMMENDATION_YET` with blockers and next actions, never a fabricated portfolio.

### Shared multi-refinery capacity scenario

`POST /api/v1/portfolios/multi-refinery` is a separate, local-only allocation scenario for competing refinery demand. It makes each physical route a **global** scaled-capacity constraint, so the US Gulf or Guyana route cannot be allocated independently to every refinery. A no-body request runs a deterministic Jamnagar/Paradip/Kochi demo; its response includes per-refinery served/unserved volume, route utilization, and cargo-contention records. It is explicitly labelled `User-entered` (demand assumptions), `Historical` (seeded network), and `Simulated` (solver output), and returns `NO_RECOMMENDATION_YET` with a structured shortfall if capacity cannot meet all demand.

SPR is intentionally excluded from this multi-refinery endpoint: the prototype has not configured one globally finite reserve constraint, so it must never add a separate reserve bridge to each refinery.

## Prototype truthfulness matrix

| Capability | Current status | What it means |
|---|---|---|
| Signal intake | Implemented | Text is always stored as `User-entered`; callers cannot self-label pasted text as live evidence. |
| Gemini extraction and briefing | Implemented with fallback | With `GEMINI_API_KEY`, Gemini provides structured extraction and a portfolio explanation. Without it, the UI visibly labels deterministic local fallback output as `Cached demo result`. |
| Risk scoring | Implemented, seeded | A deterministic score uses extracted proposals, bundled route data, and text cues. It is not a calibrated live probability. |
| Scenario simulation | Implemented, simulated | NumPy Monte Carlo uses visible analyst-confirmed assumptions and a reproducible random seed. |
| Portfolio optimisation | Implemented, seeded | OR-Tools enforces bundled grade-compatibility and route-capacity constraints; supplier availability is not live. |
| Human decision | Implemented, local only | Decisions are stored locally in SQLite and never execute externally. |
| Offline replay map and Decision Clock | Implemented, local-only | A D3-projected world basemap and timing replay render bundled, source-labelled local scenario data. They are not live tracking or operational deadlines. |
| Live AIS/news/prices, RAG, Neo4j, Redis, LangGraph | Roadmap only | Architecture and planning documents discuss these integrations, but they are not active runtime dependencies. |

## Run locally

Prerequisites: Python with [`uv`](https://docs.astral.sh/uv/), Node.js, and npm.

In the repository root, install and start the API:

```powershell
uv sync --all-groups
uv run pytest
uv run uvicorn petravigil.main:app --app-dir backend --reload
```

In a second terminal, install and start the frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev -- -p 3000
```

Open [http://localhost:3000](http://localhost:3000). Interactive API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Five-step demo runbook

1. **Open the workspace.** Start with the source-labelled Hormuz replay and Decision Clock. Show the map's offline disclaimer, then vary the approval-delay sensitivity to demonstrate how the local last-responsible-action milestone moves.
2. **Create a proposal.** Use **Load Hormuz example** or paste an energy-relevant disruption signal, select a refinery and volume, then choose **Analyse signal and propose assumptions**. Explain that the raw text is retained as unverified evidence.
3. **Review the first three stages.** Inspect the extracted proposal, entity matching, corridor score, confidence, and visible unknowns. Do not describe the signal as a live feed unless a real source integration has been added.
4. **Confirm assumptions and run.** Adjust closure severity, duration, alternative capacity, elasticity, simulation count, or seed as needed; then choose **Confirm assumptions and run workflow**. This produces reproducible scenario results and constrained portfolio alternatives.
5. **Record a local human decision.** Review the selected portfolio, rejected alternatives, and the labelled Gemini/fallback explanation. Record Approve, Defer, or Reject with a justification. State explicitly that this records a local audit decision only; no external procurement action occurs.

## Gemini and frontend configuration

The project works without Gemini. In that mode, the backend returns labelled deterministic fallback output so a demo can run offline; the fallback does not invent unrelated energy events.

To enable Gemini for the backend, set `GEMINI_API_KEY` in the terminal that starts Uvicorn. `GEMINI_MODEL` is optional and defaults to `gemini-2.5-flash`.

```powershell
$env:GEMINI_API_KEY = "your-key"
$env:GEMINI_MODEL = "gemini-2.5-flash" # optional
uv run uvicorn petravigil.main:app --app-dir backend --reload
```

The frontend calls `http://localhost:8000` by default. To point it at another API, create `frontend/.env.local` with:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Restart the Next.js development server after changing `.env.local`. [`.env.example`](.env.example) lists safe variable names and placeholder values. The FastAPI service does not automatically load a root `.env` file, so export backend variables in the launch environment (or configure them in your deployment platform).

## Verification

Run the backend suite before presenting:

```powershell
uv run pytest
```

For a frontend production check:

```powershell
cd frontend
npm.cmd run build
```
