from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from petravigil.fixtures.loader import load_canonical_scenario
from petravigil.models import (
    ApprovalCreateRequest,
    ApprovalRecord,
    AlternativeRouteOption,
    CanonicalScenarioResponse,
    DataStatus,
    GeminiExplanationResponse,
    GeminiSignalRequest,
    GeminiSignalResponse,
    NetworkSummary,
    ProcessedSignal,
    PortfolioComparison,
    PortfolioRequest,
    RefineryProfile,
    ScenarioRunRecord,
    SimulationRequest,
    SimulationResult,
    SignalProcessRequest,
    WorkflowConfirmationRequest,
    WorkflowExecution,
    WorkflowProposal,
    WorkflowProposalRequest,
)
from petravigil.services.gemini import get_gemini_service
from petravigil.services.scenario_runs import ScenarioRunRepository
from petravigil.services.signal_mesh import SignalMeshService, SignalRepository
from petravigil.services.scenario_engine import ScenarioEngine, SimulationRepository
from petravigil.services.portfolio_optimizer import PortfolioOptimizer, PortfolioRepository
from petravigil.services.approvals import ApprovalRepository
from petravigil.services.supply_network import get_supply_network
from petravigil.services.decision_workflow import DecisionWorkflowRepository, DecisionWorkflowService


app = FastAPI(
    title="PetraVigil API",
    version="0.2.0",
    description="Analyst-confirmed energy supply resilience decision workflow with explicit local prototype data labels.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

scenario_runs = ScenarioRunRepository(Path(".state") / "petravigil.sqlite3")
signal_repository = SignalRepository(Path(".state") / "petravigil.sqlite3")
simulation_repository = SimulationRepository(Path(".state") / "petravigil.sqlite3")
portfolio_repository = PortfolioRepository(Path(".state") / "petravigil.sqlite3")
approval_repository = ApprovalRepository(Path(".state") / "petravigil.sqlite3")
workflow_repository = DecisionWorkflowRepository(Path(".state") / "petravigil.sqlite3")


def get_decision_workflow_service() -> DecisionWorkflowService:
    """Compose explicit prototype agents around the existing, tested services."""
    network = get_supply_network()
    gemini = get_gemini_service()
    return DecisionWorkflowService(
        repository=workflow_repository,
        signal_mesh=SignalMeshService(signal_repository, gemini, network),
        scenario_engine=ScenarioEngine(simulation_repository),
        portfolio_optimizer=PortfolioOptimizer(portfolio_repository, network),
        gemini=gemini,
        approval_repository=approval_repository,
    )


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "phase": "8",
        "workflow": "analyst-confirmed",
        "runtime": "local-prototype",
    }


@app.get(
    "/api/v1/scenarios/canonical",
    response_model=CanonicalScenarioResponse,
    tags=["scenarios"],
)
def get_canonical_scenario() -> CanonicalScenarioResponse:
    """Return the stable, explicitly simulated Hormuz scenario contract."""
    return load_canonical_scenario()


@app.post(
    "/api/v1/scenario-runs/canonical",
    response_model=ScenarioRunRecord,
    status_code=status.HTTP_201_CREATED,
    tags=["scenario runs"],
)
def run_canonical_scenario() -> ScenarioRunRecord:
    """Persist and return a deterministic end-to-end showcase run."""
    return scenario_runs.create(load_canonical_scenario())


@app.get(
    "/api/v1/scenario-runs/latest",
    response_model=ScenarioRunRecord,
    tags=["scenario runs"],
)
def get_latest_scenario_run() -> ScenarioRunRecord:
    record = scenario_runs.latest()
    if record is None:
        raise HTTPException(status_code=404, detail="No scenario run exists yet")
    return record


@app.get(
    "/api/v1/scenario-runs/{run_id}",
    response_model=ScenarioRunRecord,
    tags=["scenario runs"],
)
def get_scenario_run(run_id: str) -> ScenarioRunRecord:
    record = scenario_runs.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Scenario run not found")
    return record


@app.get("/api/v1/network/summary", response_model=NetworkSummary, tags=["network"])
def get_network_summary() -> NetworkSummary:
    return get_supply_network().summary()


@app.get("/api/v1/network/refineries", response_model=list[RefineryProfile], tags=["network"])
def get_refineries() -> list[RefineryProfile]:
    return get_supply_network().refineries()


@app.get("/api/v1/network/alternatives", response_model=list[AlternativeRouteOption], tags=["network"])
def get_alternatives(refinery: str, disrupted_chokepoint: str = "HORMUZ") -> list[AlternativeRouteOption]:
    try:
        return get_supply_network().alternatives(refinery, disrupted_chokepoint)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"Unknown refinery: {refinery}") from error


@app.post("/api/v1/intelligence/extract", response_model=GeminiSignalResponse, tags=["intelligence"])
async def extract_signal(request: GeminiSignalRequest) -> GeminiSignalResponse:
    return await get_gemini_service().extract_signal(request.text)


@app.post("/api/v1/intelligence/explain", response_model=GeminiExplanationResponse, tags=["intelligence"])
async def explain_recommendation() -> GeminiExplanationResponse:
    recommendation = load_canonical_scenario().recommendations[0]
    return await get_gemini_service().explain_recommendation(
        recommendation.supplier_country or "Unknown supplier",
        recommendation.crude_grade or "Unknown grade",
        recommendation.refinery or "Unknown refinery",
        recommendation.route or "Unknown route",
    )


@app.post("/api/v1/signals/process", response_model=ProcessedSignal, status_code=status.HTTP_201_CREATED, tags=["signals"])
async def process_signal(request: SignalProcessRequest) -> ProcessedSignal:
    # This public endpoint receives manually pasted content. Only trusted source
    # adapters (not implemented in this prototype) may create live/historical
    # provenance records, so callers cannot self-label text as a live feed.
    trusted_request = request.model_copy(update={"source_status": DataStatus.USER_ENTERED})
    service = SignalMeshService(signal_repository, get_gemini_service(), get_supply_network())
    return await service.process(trusted_request)


@app.get("/api/v1/signals", response_model=list[ProcessedSignal], tags=["signals"])
def get_signal_history(limit: int = 12) -> list[ProcessedSignal]:
    return signal_repository.latest(min(max(limit, 1), 50))


@app.post("/api/v1/simulations", response_model=SimulationResult, status_code=status.HTTP_201_CREATED, tags=["scenarios"])
def run_simulation(request: SimulationRequest) -> SimulationResult:
    return ScenarioEngine(simulation_repository).simulate(request)


@app.get("/api/v1/simulations/latest", response_model=SimulationResult, tags=["scenarios"])
def get_latest_simulation() -> SimulationResult:
    result = simulation_repository.latest()
    if result is None:
        raise HTTPException(status_code=404, detail="No simulation exists yet")
    return result


@app.post("/api/v1/portfolios", response_model=PortfolioComparison, status_code=status.HTTP_201_CREATED, tags=["procurement"])
def generate_portfolios(request: PortfolioRequest) -> PortfolioComparison:
    return PortfolioOptimizer(portfolio_repository, get_supply_network()).generate(request)


@app.get("/api/v1/portfolios/latest", response_model=PortfolioComparison, tags=["procurement"])
def get_latest_portfolios() -> PortfolioComparison:
    comparison = portfolio_repository.latest()
    if comparison is None:
        raise HTTPException(status_code=404, detail="No portfolio comparison exists yet")
    return comparison


@app.post("/api/v1/portfolios/{label}/brief", response_model=GeminiExplanationResponse, tags=["procurement", "intelligence"])
async def brief_portfolio(label: str) -> GeminiExplanationResponse:
    comparison = portfolio_repository.latest()
    if comparison is None:
        raise HTTPException(status_code=404, detail="Generate portfolios before requesting a briefing")
    portfolio = next((item for item in comparison.portfolios if item.label == label), None)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return await get_gemini_service().explain_portfolio(portfolio.label, portfolio.rationale)


@app.post("/api/v1/approvals/canonical", response_model=ApprovalRecord, status_code=status.HTTP_201_CREATED, tags=["approvals"])
def create_canonical_approval(request: ApprovalCreateRequest) -> ApprovalRecord:
    """Record a human decision for the canonical action; never execute it externally."""
    recommendation_id = load_canonical_scenario().recommendations[0].recommendation_id
    return approval_repository.create(recommendation_id, request)


@app.get("/api/v1/approvals", response_model=list[ApprovalRecord], tags=["approvals"])
def get_approvals(limit: int = 12) -> list[ApprovalRecord]:
    return approval_repository.latest(min(max(limit, 1), 50))


@app.post(
    "/api/v1/workflows/propose",
    response_model=WorkflowProposal,
    status_code=status.HTTP_201_CREATED,
    tags=["decision workflows"],
)
async def propose_decision_workflow(request: WorkflowProposalRequest) -> WorkflowProposal:
    """Process a signal and stop for explicit analyst confirmation of assumptions."""
    try:
        return await get_decision_workflow_service().propose(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post(
    "/api/v1/workflows/{workflow_id}/execute",
    response_model=WorkflowExecution,
    tags=["decision workflows"],
)
async def execute_decision_workflow(
    workflow_id: str, confirmation: WorkflowConfirmationRequest
) -> WorkflowExecution:
    """Run the downstream economic, procurement, and executive stages after review."""
    try:
        return await get_decision_workflow_service().execute(workflow_id, confirmation)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Decision workflow not found") from error


@app.post(
    "/api/v1/workflows/{workflow_id}/approval",
    response_model=ApprovalRecord,
    status_code=status.HTTP_201_CREATED,
    tags=["decision workflows", "approvals"],
)
def approve_decision_workflow(workflow_id: str, request: ApprovalCreateRequest) -> ApprovalRecord:
    """Record a local-only approval against the actual selected workflow recommendation."""
    try:
        return get_decision_workflow_service().approve(workflow_id, request)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Decision workflow not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
