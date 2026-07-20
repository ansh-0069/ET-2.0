"""Stable Phase 0 contracts shared by the PetraVigil MVP pipeline."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


Probability = Annotated[float, Field(ge=0, le=1)]
Severity = Annotated[float, Field(ge=1, le=10)]


class DataStatus(StrEnum):
    LIVE_API = "Live API"
    HISTORICAL = "Historical"
    SIMULATED = "Simulated"
    USER_ENTERED = "User-entered"
    CACHED_DEMO_RESULT = "Cached demo result"


class EvidenceReference(BaseModel):
    """A source cited by a risk event or recommendation."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(pattern=r"^EV-[A-Z0-9-]+$")
    title: str = Field(min_length=3, max_length=300)
    status: DataStatus
    observed_at: datetime
    reliability: Probability
    excerpt: str = Field(min_length=3, max_length=1_000)
    url: HttpUrl | None = None


class RiskEvent(BaseModel):
    """Validated structured event accepted into the decision pipeline."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(pattern=r"^RE-[A-Z0-9-]+$")
    event_type: Literal[
        "SANCTIONS_CHANGE",
        "MILITARY_ACTION",
        "PORT_DISRUPTION",
        "PIPELINE_ATTACK",
        "DIPLOMATIC_SHIFT",
        "OPEC_DECISION",
        "WEATHER_EVENT",
        "PIRACY_INCIDENT",
        "REGIME_CHANGE",
        "TRADE_POLICY",
        "SHIPPING_DISRUPTION",
    ]
    status: DataStatus
    occurred_at: datetime
    affected_countries: list[str] = Field(min_length=1)
    affected_chokepoints: list[str] = Field(min_length=1)
    affected_corridors: list[str] = Field(min_length=1)
    severity: Severity
    confidence: Probability
    time_horizon: Literal["IMMEDIATE", "DAYS", "WEEKS", "MONTHS"]
    estimated_supply_impact_bpd: int = Field(ge=0)
    summary: str = Field(min_length=20, max_length=1_000)
    evidence_ids: list[str] = Field(min_length=1)


class RiskScore(BaseModel):
    """Explainable disruption-probability score for a single corridor."""

    model_config = ConfigDict(extra="forbid")

    corridor_id: str = Field(min_length=3)
    score: Probability
    calculated_at: datetime
    components: dict[str, Probability] = Field(min_length=1)
    event_ids: list[str] = Field(min_length=1)


class ScenarioAssumptions(BaseModel):
    """Inputs that must remain visible and testable in the Scenario Lab."""

    model_config = ConfigDict(extra="forbid")

    closure_severity: Probability
    disruption_duration_days: int = Field(ge=1, le=365)
    brent_elasticity_usd_per_mmbpd: float = Field(ge=0, le=100)
    alternative_route_capacity_ratio: Probability
    risk_appetite: Literal["LOW", "BALANCED", "HIGH"]
    random_seed: int = Field(ge=0)


class FeasibilityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal["GRADE", "CAPACITY", "ROUTE_RISK", "LEAD_TIME", "SANCTIONS", "PORT"]
    passed: bool
    rationale: str = Field(min_length=10, max_length=500)


class ProcurementRecommendation(BaseModel):
    """An action candidate; Phase 0 models it but does not execute anything."""

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(pattern=r"^PA-[A-Z0-9-]+$")
    status: DataStatus
    rank: int = Field(ge=1)
    action: Literal["INCREASE_VOLUME", "REDIRECT_EXISTING", "ACTIVATE_SPR"]
    supplier_country: str | None = None
    crude_grade: str | None = None
    refinery: str | None = None
    volume_bpd: int = Field(ge=0)
    route: str | None = None
    transit_days: int | None = Field(default=None, ge=0)
    cost_premium_usd_per_bbl: float | None = None
    route_risk_score: Probability
    confidence: Probability
    rationale: str = Field(min_length=20, max_length=1_000)
    feasibility_checks: list[FeasibilityCheck] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_action_details(self) -> "ProcurementRecommendation":
        if self.action == "ACTIVATE_SPR":
            return self
        if not all((self.supplier_country, self.crude_grade, self.refinery, self.route)):
            raise ValueError("supplier, grade, refinery, and route are required for supply actions")
        return self


class ApprovalDecision(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class ApprovalRecord(BaseModel):
    """Local decision record. It never creates or submits a purchase order."""

    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(pattern=r"^AP-[A-Z0-9-]+$")
    recommendation_id: str = Field(pattern=r"^PA-[A-Z0-9-]+$")
    decision: ApprovalDecision
    decided_by: str = Field(min_length=2, max_length=100)
    decided_at: datetime
    justification: str = Field(min_length=10, max_length=1_000)
    execution_external: Literal[False] = False


class ApprovalCreateRequest(BaseModel):
    """Human decision input for the local-only approval workflow."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal[ApprovalDecision.APPROVED, ApprovalDecision.REJECTED, ApprovalDecision.DEFERRED]
    decided_by: str = Field(min_length=2, max_length=100)
    justification: str = Field(min_length=10, max_length=1_000)


class CanonicalScenarioResponse(BaseModel):
    """Deterministic Phase 0 payload used as the integration-test oracle."""

    model_config = ConfigDict(extra="forbid")

    fixture_version: Literal["phase-0.1"]
    scenario_id: Literal["SC-HORMUZ-PARTIAL-BLOCKADE"]
    scenario_name: Literal["Hormuz Partial Blockade"]
    status: DataStatus
    risk_event: RiskEvent
    evidence: list[EvidenceReference] = Field(min_length=1)
    risk_score: RiskScore
    assumptions: ScenarioAssumptions
    expected_outcomes: dict[str, float | int]
    recommendations: list[ProcurementRecommendation] = Field(min_length=1)
    approval: ApprovalRecord


class ScenarioRunRecord(BaseModel):
    """Persisted local record for the Phase 1 walking-skeleton flow."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(pattern=r"^RUN-[A-F0-9-]+$")
    status: Literal["COMPLETED"]
    created_at: datetime
    scenario: CanonicalScenarioResponse


class RefineryProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    operator: str
    capacity_mmtpa: float = Field(gt=0)
    complexity_index: float = Field(gt=0)
    compatible_grades: list[str] = Field(min_length=1)


class NetworkSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    countries: int = Field(ge=0)
    crude_grades: int = Field(ge=0)
    refineries: int = Field(ge=0)
    routes: int = Field(ge=0)
    chokepoints: int = Field(ge=0)
    data_status: DataStatus


class AlternativeRouteOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_id: str
    supplier_country: str
    crude_grade: str
    refinery: str
    route: str
    avoids_chokepoint: str
    transit_days: int = Field(ge=1)
    route_risk_score: Probability
    available_volume_bpd: int = Field(gt=0)
    compatibility_note: str
    data_status: DataStatus


class GeminiSignalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=20, max_length=12_000)


class GeminiSignalProposal(BaseModel):
    """An unverified Gemini extraction that must not be treated as fact yet."""

    model_config = ConfigDict(extra="forbid")

    energy_relevant: bool
    event_type: str
    severity: Severity
    confidence: Probability
    affected_countries: list[str]
    affected_chokepoints: list[str]
    time_horizon: Literal["IMMEDIATE", "DAYS", "WEEKS", "MONTHS"]
    summary: str = Field(min_length=20, max_length=1_000)
    evidence_note: str = Field(min_length=10, max_length=600)


class GeminiSignalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_status: DataStatus
    model: str
    proposal: GeminiSignalProposal
    disclaimer: str


class GeminiExplanationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_status: DataStatus
    model: str
    explanation: str = Field(min_length=20, max_length=1_500)
    risks: list[str] = Field(min_length=1, max_length=4)
    next_question: str = Field(min_length=10, max_length=300)


class SignalProcessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=20, max_length=12_000)
    source_status: DataStatus = DataStatus.USER_ENTERED


class EntityResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: str
    entity_type: Literal["COUNTRY", "CHOKEPOINT", "CORRIDOR"]
    resolved: bool
    canonical_name: str | None = None
    note: str


class ProcessedSignal(BaseModel):
    """Auditable Signal Mesh output. It is not an approval or execution event."""

    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(pattern=r"^SIG-[A-F0-9-]+$")
    created_at: datetime
    source_status: DataStatus
    raw_text: str
    gemini: GeminiSignalResponse
    entity_resolutions: list[EntityResolution] = Field(min_length=1)
    risk_scores: list[RiskScore]
    review_required: bool


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closure_severity: Probability = 0.6
    disruption_duration_days: int = Field(default=21, ge=1, le=120)
    brent_elasticity_usd_per_mmbpd: float = Field(default=5.4, ge=0.1, le=30)
    alternative_route_capacity_ratio: Probability = 0.72
    n_runs: int = Field(default=1000, ge=100, le=5000)
    random_seed: int = Field(default=20260720, ge=0)


class PercentileRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p10: float
    p50: float
    p90: float


class SimulationSeriesPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: int = Field(ge=1)
    brent_premium: PercentileRange


class SimulationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulation_id: str = Field(pattern=r"^SIM-[A-F0-9-]+$")
    created_at: datetime
    status: Literal["COMPLETED"]
    data_status: DataStatus
    assumptions: SimulationRequest
    supply_impact_bpd: PercentileRange
    brent_premium_usd_per_bbl: PercentileRange
    additional_cost_usd_per_day: PercentileRange
    spr_bridge_days: PercentileRange
    act_now_avoided_cost_usd: float = Field(ge=0)
    series: list[SimulationSeriesPoint] = Field(min_length=1)


class PortfolioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refinery: str = "Jamnagar"
    required_volume_bpd: int = Field(default=210_000, ge=50_000, le=500_000)
    alternative_route_capacity_ratio: Probability = 0.72


class ProcurementAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_country: str
    crude_grade: str
    route: str
    volume_bpd: int = Field(gt=0)
    cost_usd_per_bbl: float = Field(gt=0)
    route_risk_score: Probability


class ProcurementPortfolio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    portfolio_id: str = Field(pattern=r"^PORT-[A-F0-9-]+$")
    label: Literal["DO_NOTHING", "LOWEST_COST", "BALANCED", "MAX_RESILIENCE"]
    status: DataStatus
    refinery: str
    total_volume_bpd: int = Field(ge=0)
    total_daily_cost_usd: float = Field(ge=0)
    weighted_route_risk: Probability
    expected_avoided_exposure_usd: float = Field(ge=0)
    allocations: list[ProcurementAllocation]
    rationale: str


class PortfolioComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comparison_id: str = Field(pattern=r"^PC-[A-F0-9-]+$")
    created_at: datetime
    status: Literal["COMPLETED"]
    request: PortfolioRequest
    portfolios: list[ProcurementPortfolio] = Field(min_length=4, max_length=4)
