from fastapi.testclient import TestClient

from petravigil.main import app


client = TestClient(app)


def test_linked_workflow_requires_confirmation_then_preserves_evidence(monkeypatch) -> None:
    """The judge flow must remain a real, linked chain rather than UI choreography."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    proposed = client.post(
        "/api/v1/workflows/propose",
        json={
            "text": "Shipping advisory reports tanker deviation and rising insurance premiums near Hormuz affecting India-bound crude cargoes.",
            "refinery": "Jamnagar",
            "required_volume_bpd": 210000,
        },
    )

    assert proposed.status_code == 201
    proposal = proposed.json()
    assert proposal["status"] == "AWAITING_ANALYST_CONFIRMATION"
    assert [item["stage"] for item in proposal["agent_trace"]] == ["SIGNAL", "INTELLIGENCE", "RISK"]
    assert proposal["processed_signal"]["source_status"] == "User-entered"
    assert proposal["proposed_assumptions"]["confidence"] > 0

    executed = client.post(
        f"/api/v1/workflows/{proposal['workflow_id']}/execute",
        json={
            "analyst_confirmed": True,
            "analyst_name": "Demo Procurement Lead",
            "assumptions": proposal["proposed_assumptions"],
        },
    )

    assert executed.status_code == 200
    workflow = executed.json()
    assert workflow["status"] == "COMPLETED"
    assert workflow["processed_signal"]["signal_id"] == proposal["processed_signal"]["signal_id"]
    assert workflow["simulation"]["assumptions"]["closure_severity"] == proposal["proposed_assumptions"]["closure_severity"]
    assert workflow["portfolios"]["request"]["refinery"] == "Jamnagar"
    assert workflow["transparency"]["requires_human_approval"] is True
    assert len(workflow["agent_trace"]) == 6

    approval = client.post(
        f"/api/v1/workflows/{proposal['workflow_id']}/approval",
        json={
            "decision": "APPROVED",
            "decided_by": "Demo Procurement Lead",
            "justification": "Approved for analyst-led commercial validation only; no purchase order is authorised.",
        },
    )
    assert approval.status_code == 201
    assert approval.json()["recommendation_id"] == workflow["recommendation_id"]
    assert approval.json()["execution_external"] is False


def test_workflow_cannot_execute_without_a_known_proposal() -> None:
    response = client.post(
        "/api/v1/workflows/WF-00000000-0000-0000-0000-000000000000/execute",
        json={
            "analyst_confirmed": True,
            "analyst_name": "Analyst",
            "assumptions": {
                "closure_severity": 0.6,
                "disruption_duration_days": 21,
                "brent_elasticity_usd_per_mmbpd": 5.4,
                "alternative_route_capacity_ratio": 0.72,
                "n_runs": 1000,
                "random_seed": 20260720,
                "confidence": 0.6,
                "rationale": "A valid-looking request still cannot bypass the analyst-confirmation workflow record.",
                "unknowns": ["No linked signal."],
            },
        },
    )

    assert response.status_code == 404


def test_public_signal_input_cannot_self_declare_live_provenance(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/api/v1/signals/process",
        json={
            "text": "Shipping advisory reports possible disruption near Hormuz affecting India-bound crude cargoes.",
            "source_status": "Live API",
        },
    )

    assert response.status_code == 201
    assert response.json()["source_status"] == "User-entered"


def test_offline_fallback_does_not_invent_an_energy_disruption(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/api/v1/workflows/propose",
        json={
            "text": "The office cafeteria will close early for a staff event tomorrow afternoon.",
            "refinery": "Jamnagar",
            "required_volume_bpd": 210000,
        },
    )

    assert response.status_code == 422
    assert "No seeded corridor" in response.json()["detail"]
