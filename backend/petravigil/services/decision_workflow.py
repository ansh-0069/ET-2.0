"""Linked, auditable decision workflow for the PetraVigil prototype.

This service deliberately composes small, explicit agents instead of claiming an
opaque autonomous system. Each stage consumes a persisted result from the prior
stage; Gemini is limited to extraction and executive explanation.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from petravigil.models import (
    AgentStage,
    AgentTraceEntry,
    ApprovalCreateRequest,
    ApprovalRecord,
    DataStatus,
    PortfolioComparison,
    PortfolioRequest,
    RecommendationTransparency,
    SimulationRequest,
    WorkflowAssumptions,
    WorkflowConfirmationRequest,
    WorkflowExecution,
    WorkflowProposal,
    WorkflowProposalRequest,
)
from petravigil.services.approvals import ApprovalRepository
from petravigil.services.gemini import GeminiService
from petravigil.services.portfolio_optimizer import PortfolioOptimizer
from petravigil.services.scenario_engine import ScenarioEngine
from petravigil.services.signal_mesh import SignalMeshService


class DecisionWorkflowRepository:
    """Stores the proposal and final decision together in the local demo store."""

    def __init__(self, database_path: Path) -> None:
        self.path = database_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS decision_workflows "
                "(workflow_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def create(self, proposal: WorkflowProposal) -> WorkflowProposal:
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps({"proposal": proposal.model_dump(mode="json")})
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO decision_workflows (workflow_id, created_at, updated_at, payload) VALUES (?, ?, ?, ?)",
                (proposal.workflow_id, proposal.created_at.isoformat(), now, payload),
            )
        return proposal

    def proposal(self, workflow_id: str) -> WorkflowProposal | None:
        record = self._record(workflow_id)
        return WorkflowProposal.model_validate(record["proposal"]) if record else None

    def execution(self, workflow_id: str) -> WorkflowExecution | None:
        record = self._record(workflow_id)
        if not record or "execution" not in record:
            return None
        return WorkflowExecution.model_validate(record["execution"])

    def save_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        record = self._record(execution.workflow_id)
        if record is None:
            raise KeyError(execution.workflow_id)
        record["execution"] = execution.model_dump(mode="json")
        with self._connect() as connection:
            connection.execute(
                "UPDATE decision_workflows SET updated_at = ?, payload = ? WHERE workflow_id = ?",
                (datetime.now(timezone.utc).isoformat(), json.dumps(record), execution.workflow_id),
            )
        return execution

    def _record(self, workflow_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM decision_workflows WHERE workflow_id = ?", (workflow_id,)
            ).fetchone()
        return json.loads(row["payload"]) if row else None


class DecisionWorkflowService:
    """A small agent chain that is honest about input quality and unknowns."""

    def __init__(
        self,
        repository: DecisionWorkflowRepository,
        signal_mesh: SignalMeshService,
        scenario_engine: ScenarioEngine,
        portfolio_optimizer: PortfolioOptimizer,
        gemini: GeminiService,
        approval_repository: ApprovalRepository,
    ) -> None:
        self.repository = repository
        self.signal_mesh = signal_mesh
        self.scenario_engine = scenario_engine
        self.portfolio_optimizer = portfolio_optimizer
        self.gemini = gemini
        self.approval_repository = approval_repository

    async def propose(self, request: WorkflowProposalRequest) -> WorkflowProposal:
        # Publicly pasted material is never allowed to self-declare as live evidence.
        from petravigil.models import SignalProcessRequest

        signal = await self.signal_mesh.process(
            SignalProcessRequest(text=request.text, source_status=DataStatus.USER_ENTERED)
        )
        resolution_rate = sum(item.resolved for item in signal.entity_resolutions) / len(signal.entity_resolutions)
        primary_risk = max(signal.risk_scores, key=lambda item: item.score, default=None)
        if primary_risk is None:
            raise ValueError("No seeded corridor could be linked to this signal; analyst review is required before modelling.")
        assumptions = self._propose_assumptions(signal, primary_risk.score)
        workflow_id = f"WF-{str(uuid4()).upper()}"
        trace = [
            AgentTraceEntry(
                stage=AgentStage.SIGNAL,
                status="REQUIRES_REVIEW" if signal.review_required else "COMPLETED",
                confidence=signal.gemini.proposal.confidence,
                summary=f"Signal Agent stored {signal.signal_id} as {signal.source_status} input.",
                rationale="Gemini extracted a structured proposal; the original text is retained and is not treated as verified fact.",
                unknowns=["External source URL and publisher verification were not supplied with this user-entered signal."],
            ),
            AgentTraceEntry(
                stage=AgentStage.INTELLIGENCE,
                status="REQUIRES_REVIEW" if resolution_rate < 1 or signal.review_required else "COMPLETED",
                confidence=round(resolution_rate * signal.gemini.proposal.confidence, 3),
                summary=f"Intelligence Agent resolved {sum(item.resolved for item in signal.entity_resolutions)}/{len(signal.entity_resolutions)} extracted entities.",
                rationale="Only entities present in the seeded network are passed downstream; unresolved names remain visible for analyst review.",
                unknowns=[item.entity for item in signal.entity_resolutions if not item.resolved] or ["No independent AIS, sanctions, or market feed is connected in this prototype."],
            ),
            AgentTraceEntry(
                stage=AgentStage.RISK,
                status="REQUIRES_REVIEW",
                confidence=assumptions.confidence,
                summary=f"Risk Agent selected {primary_risk.corridor_id} at {round(primary_risk.score * 100)}% disruption probability.",
                rationale=assumptions.rationale,
                unknowns=assumptions.unknowns,
            ),
        ]
        proposal = WorkflowProposal(
            workflow_id=workflow_id,
            status="AWAITING_ANALYST_CONFIRMATION",
            created_at=datetime.now(timezone.utc),
            refinery=request.refinery,
            required_volume_bpd=request.required_volume_bpd,
            processed_signal=signal,
            proposed_assumptions=assumptions,
            agent_trace=trace,
        )
        return self.repository.create(proposal)

    async def execute(self, workflow_id: str, confirmation: WorkflowConfirmationRequest) -> WorkflowExecution:
        proposal = self.repository.proposal(workflow_id)
        if proposal is None:
            raise KeyError(workflow_id)
        existing = self.repository.execution(workflow_id)
        if existing is not None:
            return existing

        signal = proposal.processed_signal
        assumptions = confirmation.assumptions
        base_trace = list(proposal.agent_trace)
        try:
            simulation = self.scenario_engine.simulate(
                SimulationRequest(
                    closure_severity=assumptions.closure_severity,
                    disruption_duration_days=assumptions.disruption_duration_days,
                    brent_elasticity_usd_per_mmbpd=assumptions.brent_elasticity_usd_per_mmbpd,
                    alternative_route_capacity_ratio=assumptions.alternative_route_capacity_ratio,
                    n_runs=assumptions.n_runs,
                    random_seed=assumptions.random_seed,
                )
            )
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.ECONOMIC,
                    status="COMPLETED",
                    confidence=assumptions.confidence,
                    summary=f"Economic Agent completed {assumptions.n_runs:,} reproducible simulation runs ({simulation.simulation_id}).",
                    rationale="The scenario engine consumed the analyst-confirmed closure, duration, elasticity, and alternative-capacity assumptions.",
                    unknowns=["Price elasticity remains a visible prototype assumption, not a live market forecast."],
                )
            )
            chokepoint = self._selected_chokepoint(signal)
            portfolios = self.portfolio_optimizer.generate(
                PortfolioRequest(
                    refinery=proposal.refinery,
                    required_volume_bpd=proposal.required_volume_bpd,
                    alternative_route_capacity_ratio=assumptions.alternative_route_capacity_ratio,
                    disrupted_chokepoint=chokepoint,
                )
            )
            selected = self._select_portfolio(portfolios, assumptions, signal, simulation)
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.PROCUREMENT,
                    status="COMPLETED",
                    confidence=assumptions.confidence,
                    summary=f"Procurement Agent generated {len(portfolios.portfolios)} portfolios using confirmed refinery and route-capacity constraints.",
                    rationale=(
                        f"{selected.label.replace('_', ' ').title()} was selected using confirmed route constraints plus "
                        f"the simulated P50 supply impact of {round(simulation.supply_impact_bpd.p50):,} bpd and "
                        f"Brent premium of ${simulation.brent_premium_usd_per_bbl.p50}/bbl."
                    ),
                    unknowns=["Tanker availability, port congestion, sanctions clearance, supplier reliability, and contractual capacity are not integrated."],
                )
            )
            brief = await self.gemini.explain_portfolio(selected.label, selected.rationale)
            transparency = self._transparency(proposal, assumptions, portfolios, selected, simulation)
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.EXECUTIVE,
                    status="REQUIRES_REVIEW" if brief.provider_status != DataStatus.LIVE_API else "COMPLETED",
                    confidence=transparency.confidence,
                    summary=f"Executive Agent produced a constrained explanation using {brief.provider_status}.",
                    rationale="The executive narrative explains the selected deterministic portfolio; it does not calculate prices, capacities, legal status, or approvals.",
                    unknowns=transparency.unknowns,
                )
            )
            execution = WorkflowExecution(
                workflow_id=workflow_id,
                status="COMPLETED",
                completed_at=datetime.now(timezone.utc),
                analyst_name=confirmation.analyst_name,
                processed_signal=signal,
                assumptions=assumptions,
                recommendation_id=f"PA-{workflow_id[3:]}",
                simulation=simulation,
                portfolios=portfolios,
                executive_brief=brief,
                transparency=transparency,
                agent_trace=base_trace,
            )
        except RuntimeError as error:
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.PROCUREMENT,
                    status="REQUIRES_REVIEW",
                    confidence=assumptions.confidence,
                    summary="Procurement Agent could not produce a feasible portfolio.",
                    rationale="The solver rejected the confirmed volume and capacity constraints instead of fabricating an allocation.",
                    unknowns=[str(error)],
                )
            )
            execution = WorkflowExecution(
                workflow_id=workflow_id,
                status="BLOCKED",
                completed_at=datetime.now(timezone.utc),
                analyst_name=confirmation.analyst_name,
                processed_signal=signal,
                assumptions=assumptions,
                blocking_reason=str(error),
                agent_trace=base_trace,
            )
        return self.repository.save_execution(execution)

    def approve(self, workflow_id: str, request: ApprovalCreateRequest) -> ApprovalRecord:
        execution = self.repository.execution(workflow_id)
        if execution is None or execution.status != "COMPLETED" or execution.recommendation_id is None:
            raise ValueError("A completed, decision-ready workflow is required before recording approval.")
        return self.approval_repository.create(execution.recommendation_id, request)

    @staticmethod
    def _propose_assumptions(signal, risk_score: float) -> WorkflowAssumptions:
        proposal = signal.gemini.proposal
        duration_by_horizon = {"IMMEDIATE": 10, "DAYS": 21, "WEEKS": 35, "MONTHS": 60}
        severity = min(0.95, max(0.2, round((proposal.severity / 10) * 0.65 + risk_score * 0.35, 2)))
        capacity = round(max(0.3, min(0.9, 1 - severity * 0.42)), 2)
        confidence = round(min(0.95, proposal.confidence * 0.65 + risk_score * 0.35), 2)
        return WorkflowAssumptions(
            closure_severity=severity,
            disruption_duration_days=duration_by_horizon[proposal.time_horizon],
            brent_elasticity_usd_per_mmbpd=5.4,
            alternative_route_capacity_ratio=capacity,
            n_runs=1000,
            random_seed=20260720,
            confidence=confidence,
            rationale=(
                f"Proposed from extracted severity {proposal.severity}/10, confidence {round(proposal.confidence * 100)}%, "
                f"and selected corridor score {round(risk_score * 100)}%. Capacity is reduced as closure severity rises."
            ),
            unknowns=[
                "These are analyst-reviewable scenario assumptions, not live market observations.",
                "Tanker availability, port congestion, inventory, sanctions, and supplier reliability remain unverified.",
            ],
        )

    @staticmethod
    def _selected_chokepoint(signal) -> str:
        for entity in signal.entity_resolutions:
            if entity.entity_type == "CHOKEPOINT" and entity.resolved and entity.canonical_name:
                return entity.canonical_name
        return "HORMUZ"

    @staticmethod
    def _select_portfolio(portfolios: PortfolioComparison, assumptions: WorkflowAssumptions, signal, simulation):
        risk = max((item.score for item in signal.risk_scores), default=0.0)
        economic_escalation = (
            simulation.supply_impact_bpd.p50 >= 1_500_000
            or simulation.brent_premium_usd_per_bbl.p50 >= 8
            or simulation.spr_bridge_days.p50 >= 10
        )
        desired = "MAX_RESILIENCE" if risk >= 0.78 or assumptions.closure_severity >= 0.75 or economic_escalation else "BALANCED"
        return next(item for item in portfolios.portfolios if item.label == desired)

    @staticmethod
    def _transparency(proposal, assumptions, portfolios, selected, simulation) -> RecommendationTransparency:
        alternatives = [item for item in portfolios.portfolios if item.label != selected.label]
        rejected = []
        for alternative in alternatives:
            if alternative.label == "DO_NOTHING":
                rejected.append("Do nothing was rejected because it leaves the confirmed disruption exposure unmitigated.")
            elif alternative.weighted_route_risk > selected.weighted_route_risk:
                rejected.append(f"{alternative.label.replace('_', ' ').title()} was not selected because its weighted route risk is higher ({round(alternative.weighted_route_risk * 100)}/100).")
            else:
                rejected.append(f"{alternative.label.replace('_', ' ').title()} was not selected because it provides a weaker resilience trade-off for the confirmed disruption assumptions.")
        primary = max(proposal.processed_signal.risk_scores, key=lambda item: item.score)
        return RecommendationTransparency(
            selected_portfolio=selected.label,
            confidence=assumptions.confidence,
            evidence=[
                f"User-entered signal {proposal.processed_signal.signal_id} was retained with provider status {proposal.processed_signal.gemini.provider_status}.",
                f"Selected corridor: {primary.corridor_id} at {round(primary.score * 100)}/100 disruption probability.",
                f"Simulation {simulation.simulation_id} used analyst-confirmed assumptions and {assumptions.n_runs:,} runs.",
                f"Portfolio comparison {portfolios.comparison_id} used seeded refinery-compatible alternatives.",
            ],
            assumptions=[
                f"Closure severity: {round(assumptions.closure_severity * 100)}%.",
                f"Disruption duration: {assumptions.disruption_duration_days} days.",
                f"Alternative-route capacity: {round(assumptions.alternative_route_capacity_ratio * 100)}%.",
                "All commercial availability values remain seeded prototype constraints.",
            ],
            risk_factors=[
                f"Selected portfolio weighted route risk: {round(selected.weighted_route_risk * 100)}/100.",
                f"P50 supply impact: {round(simulation.supply_impact_bpd.p50):,} bpd.",
                f"P50 Brent premium: ${simulation.brent_premium_usd_per_bbl.p50}/bbl.",
                f"P50 SPR bridge requirement: {simulation.spr_bridge_days.p50} days.",
            ],
            rejected_alternatives=rejected,
            unknowns=[
                "No live AIS, tanker, port-congestion, sanctions, supplier-reliability, inventory, or price feed is connected.",
                "Gemini output is a proposal and may require analyst review; it is not a source of operational fact.",
            ],
            why_this_won=(
                f"{selected.label.replace('_', ' ').title()} best matches the analyst-confirmed disruption severity, capacity, and "
                f"simulated P50 impact of {round(simulation.supply_impact_bpd.p50):,} bpd while maintaining refinery compatibility "
                f"in the seeded network. It is a decision-support recommendation, not a purchase order."
            ),
        )
