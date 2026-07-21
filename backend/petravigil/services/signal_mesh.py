"""Phase 3 Signal Mesh: extraction, resolution, transparent DPS, and audit storage."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from petravigil.models import (
    DataStatus,
    EntityResolution,
    ProcessedSignal,
    RiskScore,
    SignalProcessRequest,
)
from petravigil.services.gemini import GeminiService
from petravigil.services.supply_network import SupplyNetworkService


class SignalRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS processed_signals (signal_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def save(self, signal: ProcessedSignal) -> ProcessedSignal:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO processed_signals (signal_id, created_at, payload) VALUES (?, ?, ?)",
                (signal.signal_id, signal.created_at.isoformat(), json.dumps(signal.model_dump(mode="json"))),
            )
        return signal

    def latest(self, limit: int = 12) -> list[ProcessedSignal]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM processed_signals ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [ProcessedSignal.model_validate_json(row["payload"]) for row in rows]


class SignalMeshService:
    def __init__(self, repository: SignalRepository, gemini: GeminiService, network: SupplyNetworkService) -> None:
        self.repository = repository
        self.gemini = gemini
        self.network = network

    async def process(self, request: SignalProcessRequest) -> ProcessedSignal:
        gemini_result = await self.gemini.extract_signal(request.text)
        resolutions = self._resolve(gemini_result.proposal.affected_countries, gemini_result.proposal.affected_chokepoints)
        signal_id = f"SIG-{str(uuid4()).upper()}"
        risk_scores = self._risk_scores(signal_id, request.text, gemini_result.proposal.severity, gemini_result.proposal.confidence, resolutions)
        review_required = (
            request.source_status == DataStatus.USER_ENTERED
            or gemini_result.provider_status != DataStatus.LIVE_API
            or any(not result.resolved for result in resolutions)
        )
        return self.repository.save(
            ProcessedSignal(
                signal_id=signal_id,
                created_at=datetime.now(timezone.utc),
                source_status=request.source_status,
                raw_text=request.text,
                gemini=gemini_result,
                entity_resolutions=resolutions,
                risk_scores=risk_scores,
                review_required=review_required,
            )
        )

    def _resolve(self, countries: list[str], chokepoints: list[str]) -> list[EntityResolution]:
        known_countries = {country.casefold(): country for country in self.network.payload["countries"]}
        known_chokepoints = {item.casefold(): item for item in self.network.payload["chokepoints"]}
        output: list[EntityResolution] = []
        for country in countries:
            match = known_countries.get(country.casefold())
            output.append(EntityResolution(entity=country, entity_type="COUNTRY", resolved=match is not None, canonical_name=match, note="Matched seeded supplier network." if match else "Requires analyst entity review."))
        for chokepoint in chokepoints:
            match = known_chokepoints.get(chokepoint.casefold())
            output.append(EntityResolution(entity=chokepoint, entity_type="CHOKEPOINT", resolved=match is not None, canonical_name=match, note="Matched seeded chokepoint network." if match else "Requires analyst entity review."))
        return output or [EntityResolution(entity="No entities extracted", entity_type="CORRIDOR", resolved=False, note="No resolvable supply-network entities were extracted.")]

    def _risk_scores(self, signal_id: str, raw_text: str, severity: float, confidence: float, resolutions: list[EntityResolution]) -> list[RiskScore]:
        resolved_chokepoints = {item.canonical_name for item in resolutions if item.entity_type == "CHOKEPOINT" and item.resolved}
        text = raw_text.casefold()
        maritime = 0.72 if any(word in text for word in ("vessel", "ais", "shipping", "tanker")) else 0.35
        insurance = 0.65 if any(word in text for word in ("insurance", "premium", "war risk")) else 0.3
        scores: list[RiskScore] = []
        for route in self.network.payload["routes"]:
            if not resolved_chokepoints.intersection(route["chokepoints"]):
                continue
            chokepoint = max(0.82 if item == "HORMUZ" else 0.62 for item in route["chokepoints"])
            historical = 0.58 if "HORMUZ" in route["chokepoints"] else 0.36
            geopolitical = round((severity / 10) * confidence, 3)
            score = min(1.0, round(0.35 * geopolitical + 0.25 * chokepoint + 0.15 * historical + 0.15 * maritime + 0.10 * insurance, 3))
            scores.append(RiskScore(corridor_id=route["name"], score=score, calculated_at=datetime.now(timezone.utc), components={"geopolitical": geopolitical, "chokepoint_concentration": chokepoint, "historical_frequency": historical, "maritime_anomaly": maritime, "insurance": insurance}, event_ids=[signal_id]))
        return scores
