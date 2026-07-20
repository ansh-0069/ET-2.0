"""Reproducible NumPy Monte Carlo engine for the Phase 4 Scenario Lab."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np

from petravigil.models import DataStatus, PercentileRange, SimulationRequest, SimulationResult, SimulationSeriesPoint


class SimulationRepository:
    def __init__(self, database_path: Path) -> None:
        self.path = database_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS simulations (simulation_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def save(self, result: SimulationResult) -> SimulationResult:
        with self._connect() as connection:
            connection.execute("INSERT INTO simulations (simulation_id, created_at, payload) VALUES (?, ?, ?)", (result.simulation_id, result.created_at.isoformat(), json.dumps(result.model_dump(mode="json"))))
        return result

    def latest(self) -> SimulationResult | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM simulations ORDER BY created_at DESC LIMIT 1").fetchone()
        return SimulationResult.model_validate_json(row["payload"]) if row else None


def percentile_range(values: np.ndarray) -> PercentileRange:
    p10, p50, p90 = np.percentile(values, [10, 50, 90])
    return PercentileRange(p10=round(float(p10), 2), p50=round(float(p50), 2), p90=round(float(p90), 2))


class ScenarioEngine:
    def __init__(self, repository: SimulationRepository) -> None:
        self.repository = repository

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        rng = np.random.default_rng(request.random_seed)
        volatility = rng.lognormal(mean=0, sigma=0.22, size=request.n_runs)
        duration = np.clip(rng.normal(request.disruption_duration_days, request.disruption_duration_days * 0.28, request.n_runs), 1, 180)
        supply = np.clip(2_000_000 * request.closure_severity * volatility, 50_000, 2_500_000)
        premium = np.clip((supply / 1_000_000) * request.brent_elasticity_usd_per_mmbpd * rng.normal(1, 0.16, request.n_runs), 0.1, 40)
        cost = supply * premium
        spr_days = np.clip((supply * duration) / 4_500_000, 1, 60)
        horizon = min(request.disruption_duration_days, 30)
        series: list[SimulationSeriesPoint] = []
        for day in range(1, horizon + 1):
            decay = np.clip(1 - (day - 1) / np.maximum(duration, 1) * 0.45, 0.45, 1)
            series.append(SimulationSeriesPoint(day=day, brent_premium=percentile_range(premium * decay)))
        result = SimulationResult(
            simulation_id=f"SIM-{str(uuid4()).upper()}",
            created_at=datetime.now(timezone.utc),
            status="COMPLETED",
            data_status=DataStatus.SIMULATED,
            assumptions=request,
            supply_impact_bpd=percentile_range(supply),
            brent_premium_usd_per_bbl=percentile_range(premium),
            additional_cost_usd_per_day=percentile_range(cost),
            spr_bridge_days=percentile_range(spr_days),
            act_now_avoided_cost_usd=round(float(np.percentile(cost, 50) * (0.15 + request.alternative_route_capacity_ratio * 0.35) * min(request.disruption_duration_days, 30)), 2),
            series=series,
        )
        return self.repository.save(result)
