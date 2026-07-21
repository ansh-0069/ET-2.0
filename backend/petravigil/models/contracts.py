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
    disrupted_chokepoint: str = Field(default="HORMUZ", min_length=3, max_length=80)
    # This is deliberately an explicit analyst-entered scenario switch. It
    # does not query, claim, or authorize any real strategic reserve stock.
    spr_bridge_opt_in: bool = False
    government_authorization_assumed_for_scenario: bool = False
    spr_bridge_duration_days: int = Field(default=7, ge=1, le=7)

    @model_validator(mode="after")
    def validate_spr_bridge_opt_in(self) -> "PortfolioRequest":
        if self.spr_bridge_opt_in and not self.government_authorization_assumed_for_scenario:
            raise ValueError(
                "SPR bridge modelling requires a user-entered government authorization assumption; "
                "this prototype cannot verify or grant authorization."
            )
        return self


class ProcurementAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_country: str
    crude_grade: str
    route: str
    volume_bpd: int = Field(gt=0)
    cost_usd_per_bbl: float = Field(gt=0)
    route_risk_score: Probability


class SprBridgeAllocation(BaseModel):
    """A finite, local-only SPR contingency constraint used by the solver.

    The object makes the bridge a visible portfolio component rather than a
    Monte Carlo metric. Its capacity is a seeded simulated constraint; it is
    never a statement about live reserve inventory or an external activation.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["NOT_REQUESTED", "NOT_NEEDED", "CONTINGENCY_ALLOCATED"]
    data_status: Literal[DataStatus.SIMULATED] = DataStatus.SIMULATED
    capacity_source_status: Literal[DataStatus.SIMULATED] = DataStatus.SIMULATED
    authorization_source_status: Literal[DataStatus.USER_ENTERED] = DataStatus.USER_ENTERED
    seeded_capacity_bpd: int = Field(gt=0)
    seeded_max_bridge_days: int = Field(gt=0)
    bridge_volume_bpd: int = Field(ge=0)
    bridge_duration_days: int = Field(ge=0)
    bridge_volume_bbl: int = Field(ge=0)
    analyst_opt_in: bool
    government_authorization_assumed_for_scenario: bool
    requires_human_approval: Literal[True] = True
    requires_government_authorization: Literal[True] = True
    activation_conditions: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_finite_bridge(self) -> "SprBridgeAllocation":
        if self.bridge_volume_bpd > self.seeded_capacity_bpd:
            raise ValueError("SPR bridge volume cannot exceed the seeded scenario capacity")
        if self.bridge_duration_days > self.seeded_max_bridge_days:
            raise ValueError("SPR bridge duration cannot exceed the seeded maximum bridge days")
        if self.bridge_volume_bbl != self.bridge_volume_bpd * self.bridge_duration_days:
            raise ValueError("SPR bridge barrels must equal daily bridge volume multiplied by duration")
        if self.status == "CONTINGENCY_ALLOCATED":
            if not self.analyst_opt_in or not self.government_authorization_assumed_for_scenario:
                raise ValueError("An allocated SPR bridge requires explicit analyst and scenario authorization assumptions")
            if self.bridge_volume_bpd <= 0 or self.bridge_duration_days <= 0:
                raise ValueError("An allocated SPR bridge requires positive finite volume and duration")
        elif any((self.bridge_volume_bpd, self.bridge_duration_days, self.bridge_volume_bbl)):
            raise ValueError("Only an allocated SPR bridge may contain bridge volume or duration")
        return self


def _default_spr_bridge_allocation() -> SprBridgeAllocation:
    """Keep previously persisted local portfolio records readable."""

    return SprBridgeAllocation(
        status="NOT_REQUESTED",
        seeded_capacity_bpd=75_000,
        seeded_max_bridge_days=7,
        bridge_volume_bpd=0,
        bridge_duration_days=0,
        bridge_volume_bbl=0,
        analyst_opt_in=False,
        government_authorization_assumed_for_scenario=False,
        activation_conditions=["No SPR bridge was requested for this portfolio."],
        limitations=["No live SPR inventory or authorization record is connected."],
    )

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
    spr_bridge: SprBridgeAllocation = Field(default_factory=_default_spr_bridge_allocation)
    rationale: str


class PortfolioComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comparison_id: str = Field(pattern=r"^PC-[A-F0-9-]+$")
    created_at: datetime
    status: Literal["COMPLETED"]
    request: PortfolioRequest
    portfolios: list[ProcurementPortfolio] = Field(min_length=4, max_length=4)


class MultiRefineryDemandLine(BaseModel):
    """One analyst-entered refinery demand in the shared-capacity scenario."""

    model_config = ConfigDict(extra="forbid")

    refinery: str = Field(min_length=2, max_length=120)
    required_volume_bpd: int = Field(ge=10_000, le=500_000)
    source_status: Literal[DataStatus.USER_ENTERED] = DataStatus.USER_ENTERED


def _default_multi_refinery_demand_lines() -> list[MultiRefineryDemandLine]:
    """A feasible offline demo that deliberately creates route competition.

    Jamnagar and Kochi both need the seeded US Gulf route. Jamnagar and
    Paradip both need the seeded Guyana route. The values remain below the
    aggregate, scaled network capacity so the result can demonstrate an
    executable *scenario* allocation as well as its contention ledger.
    """

    return [
        MultiRefineryDemandLine(refinery="Jamnagar", required_volume_bpd=120_000),
        MultiRefineryDemandLine(refinery="Paradip", required_volume_bpd=50_000),
        MultiRefineryDemandLine(refinery="Kochi", required_volume_bpd=80_000),
    ]


class MultiRefineryPortfolioRequest(BaseModel):
    """Input to the local shared-cargo procurement allocation scenario.

    It intentionally does not expose the single-refinery SPR switch. A reserve
    bridge must be globally finite across all refineries before it can be
    included safely; that multi-refinery reserve constraint is not implemented
    in this local prototype.
    """

    model_config = ConfigDict(extra="forbid")

    scenario_label: str = Field(
        default="HORMUZ_MULTI_REFINERY_CAPACITY_CONTENTION",
        min_length=8,
        max_length=120,
    )
    demand_lines: list[MultiRefineryDemandLine] = Field(
        default_factory=_default_multi_refinery_demand_lines,
        min_length=2,
        max_length=12,
    )
    alternative_route_capacity_ratio: Probability = 0.72
    disrupted_chokepoint: str = Field(default="HORMUZ", min_length=3, max_length=80)
    assumption_source_status: Literal[DataStatus.USER_ENTERED] = DataStatus.USER_ENTERED

    @model_validator(mode="after")
    def validate_distinct_refineries(self) -> "MultiRefineryPortfolioRequest":
        normalized = [line.refinery.casefold().strip() for line in self.demand_lines]
        if len(set(normalized)) != len(normalized):
            raise ValueError("each refinery may appear only once in a multi-refinery allocation request")
        return self


class MultiRefineryAllocation(BaseModel):
    """One simulated allocation linked to a historical seeded route capacity."""

    model_config = ConfigDict(extra="forbid")

    refinery: str
    supplier_country: str
    crude_grade: str
    route: str
    volume_bpd: int = Field(gt=0)
    cost_usd_per_bbl: float = Field(gt=0)
    route_risk_score: Probability
    allocation_status: Literal[DataStatus.SIMULATED] = DataStatus.SIMULATED
    route_capacity_source_status: Literal[DataStatus.HISTORICAL] = DataStatus.HISTORICAL


class MultiRefineryResultLine(BaseModel):
    """Demand fulfillment for one refinery, including any unserved residual."""

    model_config = ConfigDict(extra="forbid")

    refinery: str
    requested_volume_bpd: int = Field(ge=0)
    allocated_volume_bpd: int = Field(ge=0)
    unserved_volume_bpd: int = Field(ge=0)
    fulfillment_status: Literal["FULLY_ALLOCATED", "PARTIALLY_ALLOCATED", "UNSERVED", "UNKNOWN_REFINERY"]
    demand_source_status: Literal[DataStatus.USER_ENTERED] = DataStatus.USER_ENTERED
    compatible_route_count: int = Field(ge=0)
    allocations: list[MultiRefineryAllocation] = Field(default_factory=list)
    note: str = Field(min_length=15, max_length=1_000)

    @model_validator(mode="after")
    def validate_fulfillment_balance(self) -> "MultiRefineryResultLine":
        if self.allocated_volume_bpd + self.unserved_volume_bpd != self.requested_volume_bpd:
            raise ValueError("allocated and unserved volume must exactly equal requested volume")
        allocated_from_lines = sum(item.volume_bpd for item in self.allocations)
        if allocated_from_lines != self.allocated_volume_bpd:
            raise ValueError("allocation lines must exactly equal the refinery allocated volume")
        if self.fulfillment_status == "FULLY_ALLOCATED" and self.unserved_volume_bpd:
            raise ValueError("a fully allocated refinery cannot have unserved volume")
        if self.fulfillment_status in {"UNSERVED", "UNKNOWN_REFINERY"} and self.allocated_volume_bpd:
            raise ValueError("an unserved refinery cannot contain allocated volume")
        return self


class SharedRouteUtilization(BaseModel):
    """Global physical-route capacity ledger across every refinery demand line."""

    model_config = ConfigDict(extra="forbid")

    route: str
    supplier_country: str
    seed_capacity_bpd: int = Field(gt=0)
    alternative_route_capacity_ratio: Probability
    effective_capacity_bpd: int = Field(ge=0)
    allocated_capacity_bpd: int = Field(ge=0)
    remaining_capacity_bpd: int = Field(ge=0)
    transit_days: int = Field(ge=1)
    route_risk_score: Probability
    route_capacity_source_status: Literal[DataStatus.HISTORICAL] = DataStatus.HISTORICAL
    allocation_status: Literal[DataStatus.SIMULATED] = DataStatus.SIMULATED

    @model_validator(mode="after")
    def validate_shared_route_capacity(self) -> "SharedRouteUtilization":
        if self.effective_capacity_bpd != round(self.seed_capacity_bpd * self.alternative_route_capacity_ratio):
            raise ValueError("effective route capacity must match the seeded capacity scaled by the scenario ratio")
        if self.allocated_capacity_bpd > self.effective_capacity_bpd:
            raise ValueError("a physical route cannot be allocated above its effective global capacity")
        if self.remaining_capacity_bpd != self.effective_capacity_bpd - self.allocated_capacity_bpd:
            raise ValueError("remaining route capacity must equal effective capacity minus allocated capacity")
        return self


class CargoContentionParticipant(BaseModel):
    """A refinery that could consume the same physical route in this scenario."""

    model_config = ConfigDict(extra="forbid")

    refinery: str
    scenario_requested_volume_bpd: int = Field(ge=0)
    allocated_volume_bpd: int = Field(ge=0)
    demand_source_status: Literal[DataStatus.USER_ENTERED] = DataStatus.USER_ENTERED


class CargoContentionRecord(BaseModel):
    """Transparent capacity competition; scenario demand is not a live order book."""

    model_config = ConfigDict(extra="forbid")

    route: str
    competing_refineries: list[str] = Field(min_length=2)
    scenario_requested_capacity_bpd: int = Field(ge=0)
    effective_capacity_bpd: int = Field(ge=0)
    allocated_capacity_bpd: int = Field(ge=0)
    status: Literal["CONTESTED", "SHARED_WITH_HEADROOM"]
    participants: list[CargoContentionParticipant] = Field(min_length=2)
    route_capacity_source_status: Literal[DataStatus.HISTORICAL] = DataStatus.HISTORICAL
    allocation_status: Literal[DataStatus.SIMULATED] = DataStatus.SIMULATED
    note: str = Field(min_length=20, max_length=1_000)

    @model_validator(mode="after")
    def validate_contention_ledger(self) -> "CargoContentionRecord":
        if self.scenario_requested_capacity_bpd != sum(
            participant.scenario_requested_volume_bpd for participant in self.participants
        ):
            raise ValueError("contention requested capacity must equal the participant total")
        if self.allocated_capacity_bpd != sum(participant.allocated_volume_bpd for participant in self.participants):
            raise ValueError("contention allocated capacity must equal the participant allocation total")
        if self.allocated_capacity_bpd > self.effective_capacity_bpd:
            raise ValueError("contention allocations cannot exceed physical route capacity")
        if self.status == "CONTESTED" and self.scenario_requested_capacity_bpd <= self.effective_capacity_bpd:
            raise ValueError("a contested route requires scenario demand above effective capacity")
        if self.status == "SHARED_WITH_HEADROOM" and self.scenario_requested_capacity_bpd > self.effective_capacity_bpd:
            raise ValueError("a shared route with headroom cannot exceed effective capacity")
        return self


class MultiRefineryProvenance(BaseModel):
    """Source label for the allocator's demand, network, and computed output."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=3, max_length=160)
    source_status: Literal[DataStatus.USER_ENTERED, DataStatus.HISTORICAL, DataStatus.SIMULATED]
    detail: str = Field(min_length=20, max_length=1_000)


class MultiRefineryPortfolioResponse(BaseModel):
    """Auditable output from the local shared-cargo capacity allocator."""

    model_config = ConfigDict(extra="forbid")

    allocation_id: str = Field(pattern=r"^MR-PORT-[A-F0-9-]+$")
    created_at: datetime
    status: Literal["FEASIBLE", "INFEASIBLE"]
    decision: Literal["ALLOCATION_READY", "NO_RECOMMENDATION_YET"]
    data_status: Literal[DataStatus.SIMULATED] = DataStatus.SIMULATED
    network_source_status: Literal[DataStatus.HISTORICAL] = DataStatus.HISTORICAL
    demand_source_status: Literal[DataStatus.USER_ENTERED] = DataStatus.USER_ENTERED
    live_data_connected: Literal[False] = False
    request: MultiRefineryPortfolioRequest
    refinery_results: list[MultiRefineryResultLine] = Field(min_length=2, max_length=12)
    shared_route_utilization: list[SharedRouteUtilization]
    cargo_contention: list[CargoContentionRecord]
    spr_bridge_status: Literal["NOT_MODELED"] = "NOT_MODELED"
    provenance: list[MultiRefineryProvenance] = Field(min_length=3, max_length=3)
    limitations: list[str] = Field(min_length=3, max_length=8)
    rationale: str = Field(min_length=30, max_length=1_500)
    requires_human_approval: Literal[True] = True
    execution_external: Literal[False] = False

    @model_validator(mode="after")
    def validate_multi_refinery_outcome(self) -> "MultiRefineryPortfolioResponse":
        requested_names = [line.refinery for line in self.request.demand_lines]
        result_names = [line.refinery for line in self.refinery_results]
        if requested_names != result_names:
            raise ValueError("refinery results must correspond to request demand lines in order")
        any_unserved = any(line.unserved_volume_bpd for line in self.refinery_results)
        if self.status == "FEASIBLE":
            if any_unserved or self.decision != "ALLOCATION_READY":
                raise ValueError("a feasible allocation must fully meet demand and be allocation ready")
        elif not any_unserved or self.decision != "NO_RECOMMENDATION_YET":
            raise ValueError("an infeasible allocation must show unserved volume and no-recommendation status")
        route_allocations: dict[str, int] = {}
        for refinery in self.refinery_results:
            for allocation in refinery.allocations:
                route_allocations[allocation.route] = route_allocations.get(allocation.route, 0) + allocation.volume_bpd
        for route in self.shared_route_utilization:
            if route_allocations.get(route.route, 0) != route.allocated_capacity_bpd:
                raise ValueError("shared route utilization must reconcile with per-refinery allocations")
        return self


class AgentStage(StrEnum):
    """Named, independently auditable stages in the lightweight workflow."""

    SIGNAL = "SIGNAL"
    INTELLIGENCE = "INTELLIGENCE"
    RISK = "RISK"
    ECONOMIC = "ECONOMIC"
    PROCUREMENT = "PROCUREMENT"
    EXECUTIVE = "EXECUTIVE"


class AgentTraceEntry(BaseModel):
    """Concise, user-facing rationale rather than hidden model reasoning."""

    model_config = ConfigDict(extra="forbid")

    stage: AgentStage
    status: Literal["COMPLETED", "REQUIRES_REVIEW"]
    confidence: Probability
    summary: str = Field(min_length=10, max_length=800)
    rationale: str = Field(min_length=10, max_length=1_200)
    unknowns: list[str] = Field(default_factory=list)


class WorkflowAssumptions(BaseModel):
    """Explicit assumptions proposed from the processed signal for analyst review."""

    model_config = ConfigDict(extra="forbid")

    closure_severity: Probability
    disruption_duration_days: int = Field(ge=1, le=120)
    brent_elasticity_usd_per_mmbpd: float = Field(ge=0.1, le=30)
    alternative_route_capacity_ratio: Probability
    n_runs: int = Field(ge=100, le=5000)
    random_seed: int = Field(ge=0)
    confidence: Probability
    rationale: str = Field(min_length=20, max_length=1_200)
    unknowns: list[str] = Field(default_factory=list)
    # The confirmation request carries these fields, so a bridge can only be
    # modelled after the same analyst confirmation used by the workflow.
    spr_bridge_opt_in: bool = False
    government_authorization_assumed_for_scenario: bool = False
    spr_bridge_duration_days: int = Field(default=7, ge=1, le=7)

    @model_validator(mode="after")
    def validate_spr_bridge_opt_in(self) -> "WorkflowAssumptions":
        if self.spr_bridge_opt_in and not self.government_authorization_assumed_for_scenario:
            raise ValueError(
                "SPR bridge modelling requires a user-entered government authorization assumption; "
                "this prototype cannot verify or grant authorization."
            )
        return self


class WorkflowProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=20, max_length=12_000)
    refinery: str = Field(default="Jamnagar", min_length=2, max_length=120)
    required_volume_bpd: int = Field(default=210_000, ge=50_000, le=500_000)


class WorkflowProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(pattern=r"^WF-[A-F0-9-]+$")
    status: Literal["AWAITING_ANALYST_CONFIRMATION"]
    created_at: datetime
    refinery: str
    required_volume_bpd: int
    processed_signal: ProcessedSignal
    proposed_assumptions: WorkflowAssumptions
    agent_trace: list[AgentTraceEntry] = Field(min_length=3, max_length=3)


class WorkflowConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analyst_confirmed: Literal[True]
    analyst_name: str = Field(min_length=2, max_length=100)
    assumptions: WorkflowAssumptions


class RecommendationTransparency(BaseModel):
    """Decision-ready evidence and limitations for the selected portfolio."""

    model_config = ConfigDict(extra="forbid")

    selected_portfolio: Literal["LOWEST_COST", "BALANCED", "MAX_RESILIENCE"]
    confidence: Probability
    evidence: list[str] = Field(min_length=1)
    assumptions: list[str] = Field(min_length=1)
    risk_factors: list[str] = Field(min_length=1)
    rejected_alternatives: list[str] = Field(min_length=1)
    unknowns: list[str] = Field(min_length=1)
    why_this_won: str = Field(min_length=30, max_length=1_500)
    requires_human_approval: Literal[True] = True


class DecisionSafetyCheckState(StrEnum):
    """The result of one explicit decision-readiness control."""

    PASS = "PASS"
    WARNING = "WARNING"
    BLOCKER = "BLOCKER"


class DecisionSafetySource(BaseModel):
    """Provenance for evidence, an input assumption, or a model constraint."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=3, max_length=160)
    kind: Literal["EVIDENCE", "CONSTRAINT", "ASSUMPTION"]
    source_status: DataStatus
    detail: str = Field(min_length=20, max_length=1_000)


class DecisionSafetyCheck(BaseModel):
    """A reviewable gate instead of an implicit failure hidden in a solver."""

    model_config = ConfigDict(extra="forbid")

    check_id: Literal[
        "EXTRACTION_CONFIDENCE",
        "CORRIDOR_RESOLUTION",
        "SOURCE_PROVENANCE",
        "SUPPLY_FEASIBILITY",
    ]
    state: DecisionSafetyCheckState
    summary: str = Field(min_length=20, max_length=1_000)
    sources: list[DecisionSafetySource] = Field(min_length=1)
    next_actions: list[str] = Field(min_length=1, max_length=5)


class DecisionSafetyGate(BaseModel):
    """Decision-readiness outcome returned with every newly executed workflow.

    A CLEARED gate can still contain warnings because user-entered and
    prototype-only provenance must be visible without pretending that the
    standard demo is unusable. A BLOCKED gate must never carry a procurement
    recommendation.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["CLEARED", "BLOCKED"]
    decision: Literal["RECOMMENDATION_READY", "NO_RECOMMENDATION_YET"]
    summary: str = Field(min_length=20, max_length=1_000)
    checks: list[DecisionSafetyCheck] = Field(min_length=4, max_length=4)
    blockers: list[str] = Field(default_factory=list, max_length=8)
    warnings: list[str] = Field(default_factory=list, max_length=12)
    next_actions: list[str] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_gate_outcome(self) -> "DecisionSafetyGate":
        has_blocker = any(check.state == DecisionSafetyCheckState.BLOCKER for check in self.checks)
        if self.status == "CLEARED":
            if self.decision != "RECOMMENDATION_READY" or has_blocker or self.blockers:
                raise ValueError("a cleared decision gate cannot contain a blocker")
        elif self.decision != "NO_RECOMMENDATION_YET" or not has_blocker or not self.blockers:
            raise ValueError("a blocked decision gate requires a blocker and no-recommendation outcome")
        return self


class WorkflowExecution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(pattern=r"^WF-[A-F0-9-]+$")
    status: Literal["COMPLETED", "BLOCKED"]
    completed_at: datetime
    analyst_name: str
    processed_signal: ProcessedSignal
    assumptions: WorkflowAssumptions
    recommendation_id: str | None = Field(default=None, pattern=r"^PA-[A-F0-9-]+$")
    simulation: SimulationResult | None = None
    portfolios: PortfolioComparison | None = None
    executive_brief: GeminiExplanationResponse | None = None
    transparency: RecommendationTransparency | None = None
    # Optional only so records saved before the decision-readiness upgrade can
    # still be read. All newly executed workflows include this object.
    decision_safety_gate: DecisionSafetyGate | None = None
    blocking_reason: str | None = Field(default=None, max_length=1_000)
    agent_trace: list[AgentTraceEntry] = Field(min_length=4, max_length=6)

    @model_validator(mode="after")
    def validate_decision_gate_outcome(self) -> "WorkflowExecution":
        if self.decision_safety_gate is None:
            return self
        if self.status == "BLOCKED":
            if self.decision_safety_gate.status != "BLOCKED":
                raise ValueError("a blocked workflow requires a blocked decision-safety gate")
            if any((self.recommendation_id, self.portfolios, self.executive_brief, self.transparency)):
                raise ValueError("a blocked workflow cannot expose a recommendation or portfolio output")
        elif self.decision_safety_gate.status != "CLEARED":
            raise ValueError("a completed workflow requires a cleared decision-safety gate")
        return self


# The replay models deliberately accept only local scenario, historical, or
# user-entered provenance. They are used to demonstrate the product journey
# without presenting a live intelligence feed or external citations.
ReplaySourceStatus = Literal[
    DataStatus.SIMULATED,
    DataStatus.HISTORICAL,
    DataStatus.USER_ENTERED,
]
Longitude = Annotated[float, Field(ge=-180, le=180)]
Latitude = Annotated[float, Field(ge=-90, le=90)]


class ReplayEvidenceEvent(BaseModel):
    """One ordered, source-labelled item in an offline crisis replay."""

    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    label: str = Field(min_length=3, max_length=120)
    source_status: ReplaySourceStatus
    reliability: Probability
    summary: str = Field(min_length=20, max_length=1_000)
    impact: str = Field(min_length=20, max_length=1_000)


class ReplayRoute(BaseModel):
    """A schematic route for map rendering, not live vessel telemetry."""

    model_config = ConfigDict(extra="forbid")

    route_id: str = Field(pattern=r"^RPL-[A-Z0-9-]+$")
    name: str = Field(min_length=5, max_length=240)
    coordinates: list[tuple[Longitude, Latitude]] = Field(min_length=2)
    status: Literal["EXPOSED", "ALTERNATIVE"]
    source_status: ReplaySourceStatus
    transit_days: int = Field(ge=1, le=180)
    available_volume_bpd: int = Field(ge=0)
    route_risk_score: Probability
    note: str = Field(min_length=20, max_length=600)


class ReplayLocation(BaseModel):
    """Named map anchor in a local replay schematic."""

    model_config = ConfigDict(extra="forbid")

    location_id: str = Field(pattern=r"^LOC-[A-Z0-9-]+$")
    name: str = Field(min_length=3, max_length=120)
    kind: Literal["CHOKEPOINT", "ORIGIN", "DESTINATION", "WAYPOINT"]
    coordinates: tuple[Longitude, Latitude]
    source_status: ReplaySourceStatus


class CrisisReplayResponse(BaseModel):
    """A complete, explicitly non-live crisis replay for local demos."""

    model_config = ConfigDict(extra="forbid")

    replay_id: str = Field(pattern=r"^RPL-[A-Z0-9-]+$")
    title: str = Field(min_length=5, max_length=200)
    disclaimer: str = Field(min_length=50, max_length=1_500)
    chokepoint: str = Field(min_length=3, max_length=120)
    replay_signal: str = Field(min_length=20, max_length=1_500)
    evidence: list[ReplayEvidenceEvent] = Field(min_length=3)
    routes: list[ReplayRoute] = Field(min_length=2)
    locations: list[ReplayLocation] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_replay_structure(self) -> "CrisisReplayResponse":
        expected_sequences = list(range(1, len(self.evidence) + 1))
        actual_sequences = [event.sequence for event in self.evidence]
        if actual_sequences != expected_sequences:
            raise ValueError("replay evidence must be ordered consecutively starting at 1")
        route_statuses = {route.status for route in self.routes}
        if not {"EXPOSED", "ALTERNATIVE"}.issubset(route_statuses):
            raise ValueError("replay must contain both exposed and alternative routes")
        return self


# Decision-clock values are deliberately limited to local scenario provenance.
# "Seeded" means a fixed local baseline in the prototype, not an observed
# current inventory, laycan, or approval value.
DecisionClockSourceStatus = Literal[
    DataStatus.SIMULATED,
    "Seeded",
    DataStatus.USER_ENTERED,
]


class DecisionClockMetric(BaseModel):
    """One source-labelled quantitative value displayed by the Decision Clock."""

    model_config = ConfigDict(extra="forbid")

    key: Literal[
        "base_decision_window_hours",
        "stockout_threshold_hours",
        "baseline_approval_delay_hours",
        "laycan_cutoff_hours",
        "protected_inventory_buffer_hours",
        "usable_stock_cover_hours",
        "decision_lead_time_hours",
        "last_responsible_action_offset_hours",
        "effective_approval_delay_hours",
    ]
    label: str = Field(min_length=3, max_length=160)
    value: int = Field(ge=0, le=2_000)
    unit: Literal["hours"]
    source_status: DecisionClockSourceStatus
    rationale: str = Field(min_length=20, max_length=1_000)


class DecisionClockStage(BaseModel):
    """One ordered moment in the local, non-live decision deadline timeline."""

    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    offset_hours: int = Field(ge=0, le=2_000)
    label: str = Field(min_length=3, max_length=160)
    source_status: DecisionClockSourceStatus
    kind: Literal[
        "SIGNAL",
        "ANALYST_REVIEW",
        "LAST_RESPONSIBLE_ACTION",
        "APPROVAL_COMPLETION",
        "LAYCAN_CUTOFF",
        "STOCKOUT_THRESHOLD",
    ]
    action: str = Field(min_length=5, max_length=240)
    detail: str = Field(min_length=20, max_length=1_000)


class DecisionClockAssumption(BaseModel):
    """A source-labelled input or derived rule used by the local clock."""

    model_config = ConfigDict(extra="forbid")

    assumption_id: str = Field(pattern=r"^DCA-[A-Z0-9-]+$")
    label: str = Field(min_length=3, max_length=160)
    value: str = Field(min_length=1, max_length=240)
    source_status: DecisionClockSourceStatus
    rationale: str = Field(min_length=20, max_length=1_000)


class DecisionClockResponse(BaseModel):
    """Deterministic, source-labelled decision timing for an offline replay."""

    model_config = ConfigDict(extra="forbid")

    clock_id: str = Field(pattern=r"^CLK-[A-Z0-9-]+$")
    title: str = Field(min_length=5, max_length=200)
    disclaimer: str = Field(min_length=80, max_length=2_000)
    replay_id: str = Field(pattern=r"^RPL-[A-Z0-9-]+$")
    base_decision_window_hours: int = Field(ge=0, le=2_000)
    stockout_threshold_hours: int = Field(ge=1, le=2_000)
    baseline_approval_delay_hours: int = Field(ge=0, le=2_000)
    laycan_cutoff_hours: int = Field(ge=0, le=2_000)
    protected_inventory_buffer_hours: int = Field(ge=0, le=2_000)
    usable_stock_cover_hours: int = Field(ge=0, le=2_000)
    decision_lead_time_hours: int = Field(ge=0, le=2_000)
    last_responsible_action_offset_hours: int = Field(ge=0, le=2_000)
    effective_approval_delay_hours: int = Field(ge=0, le=2_000)
    metrics: list[DecisionClockMetric] = Field(min_length=9, max_length=9)
    stages: list[DecisionClockStage] = Field(min_length=6, max_length=6)
    assumptions: list[DecisionClockAssumption] = Field(min_length=4)

    @model_validator(mode="after")
    def validate_clock_structure(self) -> "DecisionClockResponse":
        metric_values = {
            "base_decision_window_hours": self.base_decision_window_hours,
            "stockout_threshold_hours": self.stockout_threshold_hours,
            "baseline_approval_delay_hours": self.baseline_approval_delay_hours,
            "laycan_cutoff_hours": self.laycan_cutoff_hours,
            "protected_inventory_buffer_hours": self.protected_inventory_buffer_hours,
            "usable_stock_cover_hours": self.usable_stock_cover_hours,
            "decision_lead_time_hours": self.decision_lead_time_hours,
            "last_responsible_action_offset_hours": self.last_responsible_action_offset_hours,
            "effective_approval_delay_hours": self.effective_approval_delay_hours,
        }
        if {metric.key for metric in self.metrics} != set(metric_values):
            raise ValueError("decision clock metrics must label every quantitative field")
        if any(metric.value != metric_values[metric.key] for metric in self.metrics):
            raise ValueError("decision clock metric values must match their top-level fields")

        expected_sequences = list(range(1, len(self.stages) + 1))
        if [stage.sequence for stage in self.stages] != expected_sequences:
            raise ValueError("decision clock stages must be ordered consecutively starting at 1")
        if [stage.offset_hours for stage in self.stages] != sorted(stage.offset_hours for stage in self.stages):
            raise ValueError("decision clock stages must be ordered by non-decreasing offset")

        stage_offsets = {stage.kind: stage.offset_hours for stage in self.stages}
        required_kinds = {
            "SIGNAL",
            "ANALYST_REVIEW",
            "LAST_RESPONSIBLE_ACTION",
            "APPROVAL_COMPLETION",
            "LAYCAN_CUTOFF",
            "STOCKOUT_THRESHOLD",
        }
        if set(stage_offsets) != required_kinds:
            raise ValueError("decision clock must contain every required stage")
        if stage_offsets["LAST_RESPONSIBLE_ACTION"] != self.last_responsible_action_offset_hours:
            raise ValueError("last responsible action stage must match the reported offset")
        if stage_offsets["APPROVAL_COMPLETION"] != self.effective_approval_delay_hours:
            raise ValueError("approval stage must match the effective approval delay")
        if stage_offsets["LAYCAN_CUTOFF"] != self.laycan_cutoff_hours:
            raise ValueError("laycan stage must match the reported cutoff")
        if stage_offsets["STOCKOUT_THRESHOLD"] != self.stockout_threshold_hours:
            raise ValueError("stockout stage must match the reported threshold")

        if self.base_decision_window_hours != self.laycan_cutoff_hours - self.baseline_approval_delay_hours:
            raise ValueError("baseline decision window must equal laycan cutoff minus baseline approval delay")
        if self.usable_stock_cover_hours != self.stockout_threshold_hours - self.protected_inventory_buffer_hours:
            raise ValueError("usable stock cover must equal stockout threshold minus protected buffer")
        expected_last_action = max(0, self.laycan_cutoff_hours - self.effective_approval_delay_hours)
        if self.last_responsible_action_offset_hours != expected_last_action:
            raise ValueError("last responsible action must reflect laycan cutoff and approval delay")
        if self.decision_lead_time_hours != self.last_responsible_action_offset_hours:
            raise ValueError("decision lead time must equal the last responsible action offset")
        return self
