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
    DecisionSafetyCheck,
    DecisionSafetyCheckState,
    DecisionSafetyGate,
    DecisionSafetySource,
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
from petravigil.services.portfolio_optimizer import (
    SPR_BRIDGE_SEEDED_CAPACITY_BPD,
    SPR_BRIDGE_MAX_DAYS,
    PortfolioFeasibilityError,
    PortfolioOptimizer,
)
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
        except RuntimeError as error:
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.ECONOMIC,
                    status="REQUIRES_REVIEW",
                    confidence=assumptions.confidence,
                    summary="Economic Agent could not complete the reproducible scenario run.",
                    rationale="The workflow stops rather than producing a procurement output without its required simulation stage.",
                    unknowns=[str(error)],
                )
            )
            gate = self._decision_safety_gate(
                proposal,
                assumptions,
                supply_outcome="UNAVAILABLE",
                runtime_error=error,
            )
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.PROCUREMENT,
                    status="REQUIRES_REVIEW",
                    confidence=assumptions.confidence,
                    summary="Procurement Agent was not enabled because the prerequisite scenario run failed.",
                    rationale="The decision-safety gate returned no recommendation rather than creating a portfolio from incomplete inputs.",
                    unknowns=gate.blockers,
                )
            )
            return self.repository.save_execution(
                self._blocked_execution(proposal, confirmation, simulation=None, gate=gate, agent_trace=base_trace)
            )

        preliminary_gate = self._decision_safety_gate(
            proposal,
            assumptions,
            supply_outcome="NOT_EVALUATED",
        )
        if preliminary_gate.status == "BLOCKED":
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.PROCUREMENT,
                    status="REQUIRES_REVIEW",
                    confidence=assumptions.confidence,
                    summary="Procurement Agent was withheld until the input safety controls are resolved.",
                    rationale="The decision-safety gate blocked portfolio generation before a low-confidence or unresolved-corridor input could become a recommendation.",
                    unknowns=preliminary_gate.blockers,
                )
            )
            return self.repository.save_execution(
                self._blocked_execution(
                    proposal,
                    confirmation,
                    simulation=simulation,
                    gate=preliminary_gate,
                    agent_trace=base_trace,
                )
            )

        try:
            chokepoint = self._selected_chokepoint(signal)
            portfolios = self.portfolio_optimizer.generate(
                PortfolioRequest(
                    refinery=proposal.refinery,
                    required_volume_bpd=proposal.required_volume_bpd,
                    alternative_route_capacity_ratio=assumptions.alternative_route_capacity_ratio,
                    disrupted_chokepoint=chokepoint,
                    spr_bridge_opt_in=assumptions.spr_bridge_opt_in,
                    government_authorization_assumed_for_scenario=assumptions.government_authorization_assumed_for_scenario,
                    spr_bridge_duration_days=assumptions.spr_bridge_duration_days,
                )
            )
        except PortfolioFeasibilityError as error:
            gate = self._decision_safety_gate(
                proposal,
                assumptions,
                supply_outcome="INFEASIBLE",
                feasibility_error=error,
            )
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.PROCUREMENT,
                    status="REQUIRES_REVIEW",
                    confidence=assumptions.confidence,
                    summary="Procurement Agent withheld a recommendation because the confirmed demand exceeds permitted capacity.",
                    rationale="The solver returned an auditable shortfall, so no portfolio or recommendation identifier was generated.",
                    unknowns=gate.blockers,
                )
            )
            return self.repository.save_execution(
                self._blocked_execution(proposal, confirmation, simulation=simulation, gate=gate, agent_trace=base_trace)
            )
        except RuntimeError as error:
            gate = self._decision_safety_gate(
                proposal,
                assumptions,
                supply_outcome="UNAVAILABLE",
                runtime_error=error,
            )
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.PROCUREMENT,
                    status="REQUIRES_REVIEW",
                    confidence=assumptions.confidence,
                    summary="Procurement Agent could not safely produce a portfolio.",
                    rationale="The decision-safety gate withheld an output because the optimisation stage did not complete.",
                    unknowns=gate.blockers,
                )
            )
            return self.repository.save_execution(
                self._blocked_execution(proposal, confirmation, simulation=simulation, gate=gate, agent_trace=base_trace)
            )

        gate = self._decision_safety_gate(
            proposal,
            assumptions,
            supply_outcome="FEASIBLE",
        )
        if gate.status == "BLOCKED":
            # Defensive guard for future changes: a recommendation may never
            # survive a newly discovered blocker after optimisation succeeds.
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.PROCUREMENT,
                    status="REQUIRES_REVIEW",
                    confidence=assumptions.confidence,
                    summary="Procurement Agent withheld the solver output after the decision-safety gate blocked it.",
                    rationale="A feasible calculation is insufficient when the evidence or corridor controls are not decision-ready.",
                    unknowns=gate.blockers,
                )
            )
            return self.repository.save_execution(
                self._blocked_execution(proposal, confirmation, simulation=simulation, gate=gate, agent_trace=base_trace)
            )

        try:
            selected = self._select_portfolio(portfolios, assumptions, signal, simulation)
            spr_summary = (
                f" The selected finite SPR contingency covers {selected.spr_bridge.bridge_volume_bpd:,} bpd for "
                f"{selected.spr_bridge.bridge_duration_days} days under user-entered authorization assumptions."
                if selected.spr_bridge.status == "CONTINGENCY_ALLOCATED"
                else ""
            )
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.PROCUREMENT,
                    status="COMPLETED",
                    confidence=assumptions.confidence,
                    summary=(
                        f"Procurement Agent generated {len(portfolios.portfolios)} portfolios using confirmed refinery and "
                        f"route-capacity constraints.{spr_summary}"
                    ),
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
                decision_safety_gate=gate,
                agent_trace=base_trace,
            )
        except RuntimeError as error:
            gate = self._decision_safety_gate(
                proposal,
                assumptions,
                supply_outcome="UNAVAILABLE",
                runtime_error=error,
            )
            base_trace.append(
                AgentTraceEntry(
                    stage=AgentStage.PROCUREMENT,
                    status="REQUIRES_REVIEW",
                    confidence=assumptions.confidence,
                    summary="Procurement Agent could not produce a feasible portfolio.",
                    rationale="The decision-safety gate withheld a recommendation instead of fabricating an allocation.",
                    unknowns=gate.blockers,
                )
            )
            execution = self._blocked_execution(
                proposal,
                confirmation,
                simulation=simulation,
                gate=gate,
                agent_trace=base_trace,
            )
        return self.repository.save_execution(execution)

    @staticmethod
    def _blocked_execution(
        proposal: WorkflowProposal,
        confirmation: WorkflowConfirmationRequest,
        *,
        simulation,
        gate: DecisionSafetyGate,
        agent_trace: list[AgentTraceEntry],
    ) -> WorkflowExecution:
        """Persist an auditable no-recommendation result without a portfolio."""

        return WorkflowExecution(
            workflow_id=proposal.workflow_id,
            status="BLOCKED",
            completed_at=datetime.now(timezone.utc),
            analyst_name=confirmation.analyst_name,
            processed_signal=proposal.processed_signal,
            assumptions=confirmation.assumptions,
            simulation=simulation,
            decision_safety_gate=gate,
            blocking_reason=gate.summary,
            agent_trace=agent_trace,
        )

    @staticmethod
    def _decision_safety_gate(
        proposal: WorkflowProposal,
        assumptions: WorkflowAssumptions,
        *,
        supply_outcome: str,
        feasibility_error: PortfolioFeasibilityError | None = None,
        runtime_error: RuntimeError | None = None,
    ) -> DecisionSafetyGate:
        """Return explicit decision controls, never an opaque solver verdict.

        The workflow always begins from a user-entered signal and a prototype
        network. Those limitations are warnings, not a fabricated reason to
        block the standard offline demo. The hard stops are low-confidence
        extraction, an unresolved critical chokepoint, and infeasible supply.
        """

        signal = proposal.processed_signal
        extraction = signal.gemini.proposal
        minimum_confidence = 0.35
        if extraction.confidence < minimum_confidence:
            extraction_state = DecisionSafetyCheckState.BLOCKER
            extraction_summary = (
                f"Extraction confidence is {round(extraction.confidence * 100)}%, below the "
                f"{round(minimum_confidence * 100)}% decision threshold."
            )
            extraction_actions = [
                "Obtain an independently sourced incident report and re-run extraction with the verified text.",
                "Have an analyst confirm the event type, severity, and affected assets before modelling procurement.",
            ]
        elif extraction.confidence < 0.6:
            extraction_state = DecisionSafetyCheckState.WARNING
            extraction_summary = (
                f"Extraction confidence is {round(extraction.confidence * 100)}%, so the event interpretation requires analyst review."
            )
            extraction_actions = [
                "Attach a source URL or publisher evidence before relying on the extracted event interpretation.",
            ]
        else:
            extraction_state = DecisionSafetyCheckState.PASS
            extraction_summary = (
                f"Extraction confidence is {round(extraction.confidence * 100)}%, above the local decision threshold."
            )
            extraction_actions = [
                "Retain the original source text and analyst confirmation with the decision record.",
            ]
        extraction_check = DecisionSafetyCheck(
            check_id="EXTRACTION_CONFIDENCE",
            state=extraction_state,
            summary=extraction_summary,
            sources=[
                DecisionSafetySource(
                    label="Gemini extraction proposal",
                    kind="EVIDENCE",
                    source_status=signal.gemini.provider_status,
                    detail=(
                        "The confidence value belongs to an unverified extraction proposal and is not evidence of an "
                        "operational disruption."
                    ),
                )
            ],
            next_actions=extraction_actions,
        )

        resolved_chokepoints = [
            item.canonical_name
            for item in signal.entity_resolutions
            if item.entity_type == "CHOKEPOINT" and item.resolved and item.canonical_name
        ]
        unresolved_chokepoints = [
            item.entity
            for item in signal.entity_resolutions
            if item.entity_type == "CHOKEPOINT" and not item.resolved
        ]
        corridor_sources = [
            DecisionSafetySource(
                label="Signal entity mention",
                kind="EVIDENCE",
                source_status=signal.source_status,
                detail="The corridor mention came from retained user-entered text and still requires provenance review.",
            ),
            DecisionSafetySource(
                label="Seeded supply-network match",
                kind="CONSTRAINT",
                source_status=DataStatus.HISTORICAL,
                detail="A matched chokepoint is resolved only against the local historical supply-network fixture, not live AIS data.",
            ),
        ]
        if not resolved_chokepoints:
            corridor_state = DecisionSafetyCheckState.BLOCKER
            corridor_summary = "No critical chokepoint was resolved in the seeded supply network, so rerouting cannot be constrained safely."
            corridor_actions = [
                "Confirm the affected chokepoint or corridor against a named external source before creating a procurement scenario.",
                "Add or correct the corridor mapping only after analyst review of its source evidence.",
            ]
        elif unresolved_chokepoints:
            corridor_state = DecisionSafetyCheckState.WARNING
            corridor_summary = (
                f"Resolved corridor controls are available for {', '.join(resolved_chokepoints)}, but unresolved chokepoint "
                f"mentions remain: {', '.join(unresolved_chokepoints)}."
            )
            corridor_actions = [
                "Resolve or explicitly dismiss the remaining chokepoint mentions before relying on a broader disruption scope.",
            ]
        else:
            corridor_state = DecisionSafetyCheckState.PASS
            corridor_summary = f"Critical corridor control is resolved to {', '.join(resolved_chokepoints)} in the seeded network."
            corridor_actions = [
                "Verify the resolved corridor against current shipping and regulatory evidence before operational use.",
            ]
        corridor_check = DecisionSafetyCheck(
            check_id="CORRIDOR_RESOLUTION",
            state=corridor_state,
            summary=corridor_summary,
            sources=corridor_sources,
            next_actions=corridor_actions,
        )

        provenance_check = DecisionSafetyCheck(
            check_id="SOURCE_PROVENANCE",
            state=DecisionSafetyCheckState.WARNING,
            summary=(
                "The workflow uses retained user-entered text plus offline prototype constraints; those sources are visible but not live operational evidence."
            ),
            sources=[
                DecisionSafetySource(
                    label="Workflow signal",
                    kind="EVIDENCE",
                    source_status=signal.source_status,
                    detail="The signal was submitted by a user and is preserved as unverified evidence rather than being elevated to a live feed.",
                ),
                DecisionSafetySource(
                    label="Extraction provider",
                    kind="EVIDENCE",
                    source_status=signal.gemini.provider_status,
                    detail="The extraction provider status labels whether Gemini was live or the deterministic cached demo fallback was used.",
                ),
                DecisionSafetySource(
                    label="Compatible route capacity fixture",
                    kind="CONSTRAINT",
                    source_status=DataStatus.HISTORICAL,
                    detail="Route availability and refinery compatibility are seeded historical prototype constraints, not current commercial nominations.",
                ),
            ],
            next_actions=[
                "Attach a source URL, publisher, and observed time for the signal before treating it as verified intelligence.",
                "Confirm tanker, port, sanctions, supplier, and route capacity through approved operational systems before approval.",
            ],
        )

        supply_sources = [
            DecisionSafetySource(
                label="Confirmed required volume",
                kind="ASSUMPTION",
                source_status=DataStatus.USER_ENTERED,
                detail=(
                    f"The {proposal.required_volume_bpd:,} bpd demand target is an analyst-confirmed workflow input, not a live refinery demand feed."
                ),
            ),
            DecisionSafetySource(
                label="Compatible external route capacity",
                kind="CONSTRAINT",
                source_status=DataStatus.HISTORICAL,
                detail="The optimiser uses local historical route capacities after the analyst-confirmed alternative-capacity ratio is applied.",
            ),
            DecisionSafetySource(
                label="Finite SPR bridge ceiling",
                kind="CONSTRAINT",
                source_status=DataStatus.SIMULATED,
                detail=(
                    f"The local scenario caps any finite SPR bridge at {SPR_BRIDGE_SEEDED_CAPACITY_BPD:,} bpd for {SPR_BRIDGE_MAX_DAYS} days; it is not a live reserve balance."
                ),
            ),
            DecisionSafetySource(
                label="SPR authorization assumption",
                kind="ASSUMPTION",
                source_status=DataStatus.USER_ENTERED,
                detail=(
                    "SPR permission is modelled only when the analyst enters a government-authorization assumption; the prototype cannot verify or grant it."
                ),
            ),
        ]
        if supply_outcome == "FEASIBLE":
            supply_state = DecisionSafetyCheckState.PASS
            supply_summary = (
                f"The solver met the confirmed {proposal.required_volume_bpd:,} bpd demand within the seeded route and permitted finite-SPR constraints."
            )
            supply_actions = [
                "Validate selected supplier capacity, grade compatibility, laycan, and route status before seeking human approval.",
            ]
        elif supply_outcome == "INFEASIBLE" and feasibility_error is not None:
            supply_state = DecisionSafetyCheckState.BLOCKER
            supply_summary = f"No recommendation yet: {feasibility_error}"
            supply_actions = [
                f"Provide verified compatible supplier or route capacity for at least the {feasibility_error.shortfall_bpd:,} bpd shortfall.",
                "Reduce the confirmed demand target or revise the disruption scenario only with documented analyst justification.",
            ]
            if feasibility_error.spr_permitted:
                supply_actions.append(
                    "Do not assume additional SPR volume: the permitted finite scenario bridge is already included in this shortfall."
                )
            else:
                supply_actions.append(
                    "If policy permits, model a finite SPR bridge only through explicit analyst and government-authorization assumptions."
                )
        elif supply_outcome == "NOT_EVALUATED":
            supply_state = DecisionSafetyCheckState.WARNING
            supply_summary = "Supply feasibility was not evaluated because an upstream decision-safety control already blocked portfolio generation."
            supply_actions = [
                "Resolve the upstream blocker, then rerun the workflow so the optimiser can test confirmed capacity.",
            ]
        else:
            supply_state = DecisionSafetyCheckState.BLOCKER
            failure_detail = str(runtime_error) if runtime_error is not None else "The optimisation stage did not return a usable result."
            supply_summary = f"No recommendation yet: supply feasibility could not be established. {failure_detail}"
            supply_actions = [
                "Restore the simulation and optimisation dependency, then rerun the capacity check before producing a portfolio.",
            ]
        supply_check = DecisionSafetyCheck(
            check_id="SUPPLY_FEASIBILITY",
            state=supply_state,
            summary=supply_summary,
            sources=supply_sources,
            next_actions=supply_actions,
        )

        checks = [extraction_check, corridor_check, provenance_check, supply_check]
        blockers = [check.summary for check in checks if check.state == DecisionSafetyCheckState.BLOCKER]
        warnings = [check.summary for check in checks if check.state == DecisionSafetyCheckState.WARNING]
        priority_checks = [check for check in checks if check.state != DecisionSafetyCheckState.PASS] or checks
        next_actions = list(dict.fromkeys(action for check in priority_checks for action in check.next_actions))
        if blockers:
            return DecisionSafetyGate(
                status="BLOCKED",
                decision="NO_RECOMMENDATION_YET",
                summary=f"No recommendation yet: {' '.join(blockers)}",
                checks=checks,
                blockers=blockers,
                warnings=warnings,
                next_actions=next_actions,
            )
        return DecisionSafetyGate(
            status="CLEARED",
            decision="RECOMMENDATION_READY",
            summary=(
                "Decision readiness is cleared for human review; source-provenance warnings remain visible and require operational validation before approval."
            ),
            checks=checks,
            warnings=warnings,
            next_actions=next_actions,
        )

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
                (
                    f"SPR bridge: {selected.spr_bridge.bridge_volume_bpd:,} bpd for "
                    f"{selected.spr_bridge.bridge_duration_days} days, using user-entered scenario authorization assumptions."
                    if selected.spr_bridge.status == "CONTINGENCY_ALLOCATED"
                    else "SPR bridge was not used in the selected portfolio."
                ),
            ],
            risk_factors=[
                f"Selected portfolio weighted route risk: {round(selected.weighted_route_risk * 100)}/100.",
                f"P50 supply impact: {round(simulation.supply_impact_bpd.p50):,} bpd.",
                f"P50 Brent premium: ${simulation.brent_premium_usd_per_bbl.p50}/bbl.",
                f"P50 SPR bridge requirement: {simulation.spr_bridge_days.p50} days.",
                (
                    "SPR bridge capacity and duration are finite seeded constraints, not a live reserve balance."
                    if selected.spr_bridge.status == "CONTINGENCY_ALLOCATED"
                    else "No SPR bridge allocation contributes to the selected portfolio."
                ),
            ],
            rejected_alternatives=rejected,
            unknowns=[
                "No live AIS, tanker, port-congestion, sanctions, supplier-reliability, inventory, or price feed is connected.",
                "Gemini output is a proposal and may require analyst review; it is not a source of operational fact.",
                "Any SPR scenario bridge requires real human and government authorization outside this prototype; the user-entered switch is not an authorization record.",
            ],
            why_this_won=(
                f"{selected.label.replace('_', ' ').title()} best matches the analyst-confirmed disruption severity, capacity, and "
                f"simulated P50 impact of {round(simulation.supply_impact_bpd.p50):,} bpd while maintaining refinery compatibility "
                f"in the seeded network. It is a decision-support recommendation, not a purchase order."
            ),
        )
