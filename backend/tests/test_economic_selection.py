from fastapi.testclient import TestClient

from petravigil.main import app


client = TestClient(app)


def test_simulated_price_impact_can_escalate_the_selected_portfolio(monkeypatch) -> None:
    """The economic stage must change the procurement posture, not merely decorate it."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    proposed = client.post(
        "/api/v1/workflows/propose",
        json={
            "text": "Shipping advisory reports tanker deviation near Hormuz affecting India-bound crude cargoes.",
            "refinery": "Jamnagar",
            "required_volume_bpd": 210000,
        },
    )
    assert proposed.status_code == 201
    proposal = proposed.json()
    assumptions = proposal["proposed_assumptions"]
    # Corridor risk and closure remain below the resilience threshold; only the
    # simulation-derived price impact should change the selected posture.
    assumptions.update({"closure_severity": 0.6, "brent_elasticity_usd_per_mmbpd": 15.0})

    executed = client.post(
        f"/api/v1/workflows/{proposal['workflow_id']}/execute",
        json={"analyst_confirmed": True, "analyst_name": "Economic reviewer", "assumptions": assumptions},
    )

    assert executed.status_code == 200
    workflow = executed.json()
    assert workflow["simulation"]["brent_premium_usd_per_bbl"]["p50"] >= 8
    assert workflow["transparency"]["selected_portfolio"] == "MAX_RESILIENCE"
    assert "simulated P50 impact" in workflow["transparency"]["why_this_won"]
