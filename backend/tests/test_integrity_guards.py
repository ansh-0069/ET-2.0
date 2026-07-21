import asyncio
from pathlib import Path

import pytest

from petravigil.models import DataStatus, SignalProcessRequest
from petravigil.services.gemini import GeminiService
from petravigil.services.signal_mesh import SignalMeshService, SignalRepository
from petravigil.services.supply_network import get_supply_network


def test_offline_fallback_does_not_invent_seeded_entities_for_generic_energy_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = GeminiService()._fallback_signal(
        "Oil prices rose after a refinery maintenance notice, and shipping insurance is being watched."
    )

    assert result.energy_relevant is True
    assert result.event_type == "UNCLASSIFIED"
    assert result.affected_countries == []
    assert result.affected_chokepoints == []
    assert "will not infer Hormuz" in result.evidence_note


def test_offline_fallback_only_returns_entities_explicitly_mentioned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = GeminiService()._fallback_signal(
        "A tanker advisory near the Strait of Hormuz affects Indian crude cargoes."
    )

    assert result.affected_chokepoints == ["HORMUZ"]
    assert result.affected_countries == ["India"]
    assert "Iran" not in result.affected_countries


def test_user_entered_signal_requires_review_even_when_gemini_is_live(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = SignalMeshService(
        repository=SignalRepository(tmp_path / "signals.sqlite3"),
        gemini=GeminiService(),
        network=get_supply_network(),
    )

    # Keep the fixture deterministic while asserting the provenance rule independently.
    from petravigil.models import GeminiSignalProposal, GeminiSignalResponse

    async def declared_live_extract(_: str) -> GeminiSignalResponse:
        return GeminiSignalResponse(
            provider_status=DataStatus.LIVE_API,
            model="test-live-provider",
            proposal=GeminiSignalProposal(
                energy_relevant=True,
                event_type="SHIPPING_DISRUPTION",
                severity=7.0,
                confidence=0.8,
                affected_countries=["India"],
                affected_chokepoints=["HORMUZ"],
                time_horizon="DAYS",
                summary="A test provider reported an explicit Hormuz shipping disruption.",
                evidence_note="Test-only live-provider response with explicit seeded entities.",
            ),
            disclaimer="Test response.",
        )

    monkeypatch.setattr(service.gemini, "extract_signal", declared_live_extract)
    processed = asyncio.run(
        service.process(
            SignalProcessRequest(
                text="A tanker advisory near Hormuz affects India-bound crude cargoes.",
                source_status=DataStatus.USER_ENTERED,
            )
        )
    )

    assert processed.gemini.provider_status == DataStatus.LIVE_API
    assert processed.review_required is True
