"""OR-Tools procurement portfolios for the Phase 5 decision workspace."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ortools.linear_solver import pywraplp

from petravigil.models import (
    DataStatus,
    PortfolioComparison,
    PortfolioRequest,
    ProcurementAllocation,
    ProcurementPortfolio,
    SprBridgeAllocation,
)
from petravigil.services.supply_network import SupplyNetworkService


PRICE_BY_GRADE = {"WTI Midland": 83.2, "Liza Light": 81.8, "Bonny Light": 82.4}

# Local prototype constraints only. These values are intentionally not read
# from a reserve system and must never be interpreted as live inventory or an
# authorization to draw strategic reserves.
SPR_BRIDGE_SEEDED_CAPACITY_BPD = 75_000
SPR_BRIDGE_MAX_DAYS = 7


class PortfolioFeasibilityError(RuntimeError):
    """A structured capacity shortfall that must not become a fake allocation."""

    def __init__(
        self,
        *,
        required_volume_bpd: int,
        external_capacity_bpd: int,
        permitted_spr_capacity_bpd: int,
        spr_permitted: bool,
        portfolio_label: str,
    ) -> None:
        self.required_volume_bpd = required_volume_bpd
        self.external_capacity_bpd = external_capacity_bpd
        self.permitted_spr_capacity_bpd = permitted_spr_capacity_bpd
        self.spr_permitted = spr_permitted
        self.portfolio_label = portfolio_label
        self.total_available_bpd = external_capacity_bpd + permitted_spr_capacity_bpd
        self.shortfall_bpd = max(0, required_volume_bpd - self.total_available_bpd)
        bridge_clause = (
            f"including the permitted finite {permitted_spr_capacity_bpd:,} bpd SPR scenario bridge"
            if spr_permitted
            else "without a permitted SPR scenario bridge"
        )
        super().__init__(
            f"Confirmed demand of {required_volume_bpd:,} bpd cannot be met by {external_capacity_bpd:,} bpd "
            f"of seeded compatible route capacity {bridge_clause}; shortfall is {self.shortfall_bpd:,} bpd."
        )


class PortfolioRepository:
    def __init__(self, database_path: Path) -> None:
        self.path = database_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS portfolio_comparisons (comparison_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def save(self, comparison: PortfolioComparison) -> PortfolioComparison:
        with self._connect() as connection:
            connection.execute("INSERT INTO portfolio_comparisons (comparison_id, created_at, payload) VALUES (?, ?, ?)", (comparison.comparison_id, comparison.created_at.isoformat(), json.dumps(comparison.model_dump(mode="json"))))
        return comparison

    def latest(self) -> PortfolioComparison | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM portfolio_comparisons ORDER BY created_at DESC LIMIT 1").fetchone()
        return PortfolioComparison.model_validate_json(row["payload"]) if row else None


class PortfolioOptimizer:
    def __init__(self, repository: PortfolioRepository, network: SupplyNetworkService) -> None:
        self.repository = repository
        self.network = network

    def generate(self, request: PortfolioRequest) -> PortfolioComparison:
        candidates = self.network.alternatives(request.refinery, request.disrupted_chokepoint)
        portfolios = [self._do_nothing(request)]
        portfolios.extend(self._solve(request, candidates, label, risk_penalty) for label, risk_penalty in (("LOWEST_COST", 0.0), ("BALANCED", 8.0), ("MAX_RESILIENCE", 28.0)))
        return self.repository.save(PortfolioComparison(comparison_id=f"PC-{str(uuid4()).upper()}", created_at=datetime.now(timezone.utc), status="COMPLETED", request=request, portfolios=portfolios))

    def _do_nothing(self, request: PortfolioRequest) -> ProcurementPortfolio:
        return ProcurementPortfolio(
            portfolio_id=f"PORT-{str(uuid4()).upper()}",
            label="DO_NOTHING",
            status=DataStatus.SIMULATED,
            refinery=request.refinery,
            total_volume_bpd=0,
            total_daily_cost_usd=0,
            weighted_route_risk=0.78,
            expected_avoided_exposure_usd=0,
            allocations=[],
            spr_bridge=self._spr_bridge(request, bridge_volume_bpd=0),
            rationale="No pre-emptive rerouting: procurement remains exposed to the disrupted Hormuz corridor and panic-market timing.",
        )

    def _solve(self, request: PortfolioRequest, candidates, label: str, risk_penalty: float) -> ProcurementPortfolio:
        solver = pywraplp.Solver.CreateSolver("GLOP")
        if solver is None:
            raise RuntimeError("Linear optimisation solver is unavailable")
        # Round rather than truncate: binary floating-point representation of
        # values such as 0.70 must not turn a valid 63,000 bpd capacity into
        # 62,999 bpd and falsely report an infeasible portfolio.
        capacity = [round(option.available_volume_bpd * request.alternative_route_capacity_ratio) for option in candidates]
        # The bridge can only cover the residual left after the externally
        # sourced, refinery-compatible routes have been exhausted. It is not a
        # cheaper synthetic supplier that the optimizer can choose freely.
        permitted_spr_capacity_bpd = SPR_BRIDGE_SEEDED_CAPACITY_BPD if request.spr_bridge_opt_in else 0
        diversification_limit = float("inf")
        if label == "BALANCED":
            diversification_limit = request.required_volume_bpd * 0.35
            # Keep 35% as the diversification target, but do not turn a
            # globally feasible demand into a false "no recommendation" just
            # because the seeded network has one larger compatible route.
            balanced_total = round(sum(min(item, diversification_limit) for item in capacity))
            if balanced_total + permitted_spr_capacity_bpd < request.required_volume_bpd:
                diversification_limit = max(capacity, default=0)
        usable_external_capacity = [min(item, diversification_limit) for item in capacity]
        external_capacity_bpd = round(sum(usable_external_capacity))
        residual_bpd = max(0, request.required_volume_bpd - external_capacity_bpd)
        if residual_bpd > permitted_spr_capacity_bpd:
            raise PortfolioFeasibilityError(
                required_volume_bpd=request.required_volume_bpd,
                external_capacity_bpd=external_capacity_bpd,
                permitted_spr_capacity_bpd=permitted_spr_capacity_bpd,
                spr_permitted=request.spr_bridge_opt_in,
                portfolio_label=label,
            )
        external_target_bpd = request.required_volume_bpd - residual_bpd
        variables = [solver.NumVar(0, capacity[index], f"v_{index}") for index in range(len(candidates))]
        solver.Add(solver.Sum(variables) == external_target_bpd)
        if label == "BALANCED":
            for variable in variables:
                # A portfolio that simply fills the two cheapest routes is not
                # diversified. The normal target is 35% of demand per source;
                # only the feasibility-preserving relaxation above can exceed it.
                solver.Add(variable <= diversification_limit)
        objective = solver.Objective()
        for index, option in enumerate(candidates):
            price = PRICE_BY_GRADE.get(option.crude_grade, 84.0)
            objective.SetCoefficient(variables[index], price + risk_penalty * option.route_risk_score)
        objective.SetMinimization()
        if solver.Solve() != pywraplp.Solver.OPTIMAL:
            raise PortfolioFeasibilityError(
                required_volume_bpd=request.required_volume_bpd,
                external_capacity_bpd=external_capacity_bpd,
                permitted_spr_capacity_bpd=permitted_spr_capacity_bpd,
                spr_permitted=request.spr_bridge_opt_in,
                portfolio_label=label,
            )
        allocations = []
        for index, option in enumerate(candidates):
            volume = int(round(variables[index].solution_value()))
            if volume:
                allocations.append(ProcurementAllocation(supplier_country=option.supplier_country, crude_grade=option.crude_grade, route=option.route, volume_bpd=volume, cost_usd_per_bbl=PRICE_BY_GRADE.get(option.crude_grade, 84.0), route_risk_score=option.route_risk_score))
        external_total = sum(item.volume_bpd for item in allocations)
        total = external_total + residual_bpd
        daily_cost = sum(item.volume_bpd * item.cost_usd_per_bbl for item in allocations)
        weighted_risk = (
            sum(item.volume_bpd * item.route_risk_score for item in allocations) / external_total
            if external_total
            else 0.0
        )
        label_text = label.replace("_", " ").title()
        spr_bridge = self._spr_bridge(request, bridge_volume_bpd=residual_bpd)
        bridge_clause = (
            f" A finite {residual_bpd:,} bpd SPR bridge is modelled for {spr_bridge.bridge_duration_days} days "
            "only because external seeded capacity is insufficient; it remains subject to human and government authorization."
            if residual_bpd
            else ""
        )
        return ProcurementPortfolio(
            portfolio_id=f"PORT-{str(uuid4()).upper()}",
            label=label,
            status=DataStatus.SIMULATED,
            refinery=request.refinery,
            total_volume_bpd=total,
            total_daily_cost_usd=round(daily_cost, 2),
            weighted_route_risk=round(weighted_risk, 3),
            expected_avoided_exposure_usd=round(daily_cost * (0.08 + risk_penalty / 100) * 14, 2),
            allocations=allocations,
            spr_bridge=spr_bridge,
            rationale=(
                f"{label_text} allocation solved with refinery compatibility, alternative-route capacity, and route-risk weights."
                f"{bridge_clause}"
            ),
        )

    @staticmethod
    def _spr_bridge(request: PortfolioRequest, bridge_volume_bpd: int) -> SprBridgeAllocation:
        if bridge_volume_bpd:
            status = "CONTINGENCY_ALLOCATED"
            duration_days = request.spr_bridge_duration_days
        elif request.spr_bridge_opt_in:
            status = "NOT_NEEDED"
            duration_days = 0
        else:
            status = "NOT_REQUESTED"
            duration_days = 0

        return SprBridgeAllocation(
            status=status,
            seeded_capacity_bpd=SPR_BRIDGE_SEEDED_CAPACITY_BPD,
            seeded_max_bridge_days=SPR_BRIDGE_MAX_DAYS,
            bridge_volume_bpd=bridge_volume_bpd,
            bridge_duration_days=duration_days,
            bridge_volume_bbl=bridge_volume_bpd * duration_days,
            analyst_opt_in=request.spr_bridge_opt_in,
            government_authorization_assumed_for_scenario=request.government_authorization_assumed_for_scenario,
            activation_conditions=[
                "An analyst must explicitly opt in to this finite scenario bridge.",
                "Government authorization must be obtained and recorded outside this local prototype before any activation.",
                "The scenario authorization switch is user-entered modelling input, not evidence of a real authorization.",
            ],
            limitations=[
                f"Capacity is a seeded simulated ceiling of {SPR_BRIDGE_SEEDED_CAPACITY_BPD:,} bpd for no more than {SPR_BRIDGE_MAX_DAYS} days.",
                "No live SPR inventory, allocation, quality, transport, legal, or release-status feed is connected.",
                "This output does not execute or authorize a reserve draw, purchase, or logistics action.",
            ],
        )
