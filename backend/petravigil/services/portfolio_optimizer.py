"""OR-Tools procurement portfolios for the Phase 5 decision workspace."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ortools.linear_solver import pywraplp

from petravigil.models import DataStatus, PortfolioComparison, PortfolioRequest, ProcurementAllocation, ProcurementPortfolio
from petravigil.services.supply_network import SupplyNetworkService


PRICE_BY_GRADE = {"WTI Midland": 83.2, "Liza Light": 81.8, "Bonny Light": 82.4}


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
        candidates = self.network.alternatives(request.refinery, "HORMUZ")
        portfolios = [self._do_nothing(request)]
        portfolios.extend(self._solve(request, candidates, label, risk_penalty) for label, risk_penalty in (("LOWEST_COST", 0.0), ("BALANCED", 8.0), ("MAX_RESILIENCE", 28.0)))
        return self.repository.save(PortfolioComparison(comparison_id=f"PC-{str(uuid4()).upper()}", created_at=datetime.now(timezone.utc), status="COMPLETED", request=request, portfolios=portfolios))

    def _do_nothing(self, request: PortfolioRequest) -> ProcurementPortfolio:
        return ProcurementPortfolio(portfolio_id=f"PORT-{str(uuid4()).upper()}", label="DO_NOTHING", status=DataStatus.SIMULATED, refinery=request.refinery, total_volume_bpd=0, total_daily_cost_usd=0, weighted_route_risk=0.78, expected_avoided_exposure_usd=0, allocations=[], rationale="No pre-emptive rerouting: procurement remains exposed to the disrupted Hormuz corridor and panic-market timing.")

    def _solve(self, request: PortfolioRequest, candidates, label: str, risk_penalty: float) -> ProcurementPortfolio:
        solver = pywraplp.Solver.CreateSolver("GLOP")
        if solver is None:
            raise RuntimeError("Linear optimisation solver is unavailable")
        capacity = [int(option.available_volume_bpd * request.alternative_route_capacity_ratio) for option in candidates]
        variables = [solver.NumVar(0, capacity[index], f"v_{index}") for index in range(len(candidates))]
        solver.Add(solver.Sum(variables) == request.required_volume_bpd)
        if label == "BALANCED":
            for variable in variables:
                # A portfolio that simply fills the two cheapest routes is not
                # diversified. Keep any one source below 35% of demand, while
                # retaining enough headroom for the current seeded network.
                solver.Add(variable <= request.required_volume_bpd * 0.35)
        objective = solver.Objective()
        for index, option in enumerate(candidates):
            price = PRICE_BY_GRADE.get(option.crude_grade, 84.0)
            objective.SetCoefficient(variables[index], price + risk_penalty * option.route_risk_score)
        objective.SetMinimization()
        if solver.Solve() != pywraplp.Solver.OPTIMAL:
            raise RuntimeError("No feasible portfolio for current capacity assumptions")
        allocations = []
        for index, option in enumerate(candidates):
            volume = int(round(variables[index].solution_value()))
            if volume:
                allocations.append(ProcurementAllocation(supplier_country=option.supplier_country, crude_grade=option.crude_grade, route=option.route, volume_bpd=volume, cost_usd_per_bbl=PRICE_BY_GRADE.get(option.crude_grade, 84.0), route_risk_score=option.route_risk_score))
        total = sum(item.volume_bpd for item in allocations)
        daily_cost = sum(item.volume_bpd * item.cost_usd_per_bbl for item in allocations)
        weighted_risk = sum(item.volume_bpd * item.route_risk_score for item in allocations) / total
        label_text = label.replace("_", " ").title()
        return ProcurementPortfolio(portfolio_id=f"PORT-{str(uuid4()).upper()}", label=label, status=DataStatus.SIMULATED, refinery=request.refinery, total_volume_bpd=total, total_daily_cost_usd=round(daily_cost, 2), weighted_route_risk=round(weighted_risk, 3), expected_avoided_exposure_usd=round(daily_cost * (0.08 + risk_penalty / 100) * 14, 2), allocations=allocations, rationale=f"{label_text} allocation solved with refinery compatibility, alternative-route capacity, and route-risk weights.")
